"""HyperMat multi-agent runtime.

Independent workers own their tool allowlists, the supervisor routes using validated
state transitions, and a durable MongoDB trace documents every call and handoff.
LLM suggestions are constrained to *which read-only tools to call first*, never
academic/financial policy, authorization, or writes.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING

import httpx
if TYPE_CHECKING:
    from pymongo.database import Database

from ..config import get_settings
from ..rules import validate_course
from .emailer import send_result_email
from .gemini import explain_verdict

AGENTS = ("coordinator", "academic", "financial", "executor", "rpa")
NEXT = {"coordinator": "academic", "academic": "financial", "financial": "executor", "executor": "rpa"}


def now():
    return datetime.now(UTC)


def redact(obj: dict) -> dict:
    """Only technical metadata goes into agent trace, never DNI, password or API key."""
    return {key: value for key, value in obj.items() if key not in {"document", "password_hash", "token", "gemini_api_key"}}


def decide_path(status: str, is_confirm: bool, stage: str) -> str:
    """Pure supervisor state machine used by tests and production."""
    if status == "REJECTED":
        return "REJECTED"
    if status == "OBSERVED":
        return "OBSERVED"
    if stage == "financial" and not is_confirm:
        return "PREVALIDATED"
    if stage == "rpa":
        return "APPROVED"
    return "CONTINUE"


def schedule_overlaps(a: str, b: str) -> bool:
    """Supports 'Lun 18:00-20:15' and time interval overlap, not string equality."""
    rx = r"^(.+?)\s+(\d\d:\d\d)-(\d\d:\d\d)$"
    ma, mb = re.match(rx, a or ""), re.match(rx, b or "")
    if not ma or not mb:
        return bool(a and b and a == b)
    return ma.group(1) == mb.group(1) and ma.group(2) < mb.group(3) and mb.group(2) < ma.group(3)


@dataclass
class Context:
    db: Database
    request: dict
    run_id: str
    confirm: bool
    student: dict = field(default_factory=dict)
    selected: list[dict] = field(default_factory=list)
    credits: int = 0
    findings: dict = field(default_factory=dict)
    seq: int = 0
    steps: int = 0

    @property
    def request_id(self):
        return self.request["request_id"]

    def event(self, agent: str, kind: str, *, tool: str | None = None, status: str | None = None, detail: Any = None):
        self.seq += 1
        payload = {
            "run_id": self.run_id,
            "request_id": self.request_id,
            "seq": self.seq,
            "agent": agent,
            "event_type": kind,
            "tool": tool,
            "status": status,
            "detail": detail,
            "created_at": now(),
        }
        self.db.agent_traces.insert_one(payload)
        return payload

    def handoff(self, sender: str, receiver: str, status: str, summary: str):
        message = {
            "message_id": uuid.uuid4().hex,
            "run_id": self.run_id,
            "request_id": self.request_id,
            "sender": sender,
            "receiver": receiver,
            "message_type": "HANDOFF",
            "payload": {"status": status, "summary": summary, "period": self.request["period"]},
            "created_at": now(),
        }
        self.db.agent_messages.insert_one(message)
        self.event(sender, "HANDOFF", status=status, detail={"to": receiver, "message_id": message["message_id"]})


async def llm_tool_plan(agent: str, allowed: list[str], context: Context) -> tuple[list[str], str]:
    """LLM chooses permitted read-only tools; deterministic fallback is explicit."""
    conf = get_settings()
    if not conf.gemini_api_key:
        return allowed, "RULES"
    prompt = (
        "Eres un agente especializado dentro de un sistema de matrícula universitario. "
        "Elige el orden de estas herramientas AUTORIZADAS para tu rol (todas deben ejecutarse): "
        f"{json.dumps(allowed)}. Agente: {agent}; etapa: {'confirmación' if context.confirm else 'prevalidación'}. "
        "No puedes aprobar matrículas, cambiar la política ni añadir herramientas. "
        'Responde SOLO JSON: {"tools":["nombre"]}. Nunca incluyas PII.'
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{conf.gemini_model}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            result = await client.post(url, params={"key": conf.gemini_api_key}, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0, "maxOutputTokens": 110, "responseMimeType": "application/json"},
            })
        result.raise_for_status()
        raw = result.json()["candidates"][0]["content"]["parts"][0]["text"]
        proposed = json.loads(raw)["tools"]
        if not isinstance(proposed, list) or set(proposed) != set(allowed) or len(proposed) != len(allowed):
            raise ValueError("Plan fuera de herramientas permitidas")
        return proposed, "GEMINI"
    except Exception:
        return allowed, "RULES_FALLBACK"


class Worker:
    name = ""
    tools: tuple[str, ...] = ()

    async def run(self, ctx: Context) -> dict:
        ctx.steps += 1
        if ctx.steps > 6:
            raise RuntimeError("Límite de pasos del orquestador excedido")
        started = time.perf_counter()
        ctx.event(self.name, "START", detail={"phase": "CONFIRM" if ctx.confirm else "PRECHECK"})
        ordered, source = await llm_tool_plan(self.name, list(self.tools), ctx)
        ctx.event(self.name, "TOOL_PLAN", detail={"tools": ordered, "source": source})
        fetched = {}
        for name in ordered:
            ctx.event(self.name, "TOOL_CALL", tool=name)
            fetched[name] = self.call(ctx, name)
            ctx.event(self.name, "TOOL_RESULT", tool=name, detail=self.tool_meta(name, fetched[name]))
        status, summary, evidence = self.decide(ctx, fetched)
        explanation = await explain_verdict(self.name, {"status": status, "summary": summary, "evidence": evidence})
        verdict = {
            "request_id": ctx.request_id, "agent": self.name, "status": status,
            "summary": explanation["text"], "deterministic_summary": summary,
            "evidence": evidence, "explanation_source": explanation["source"],
            "model": explanation.get("model"), "run_id": ctx.run_id, "created_at": now(),
        }
        ctx.db.agent_verdicts.update_one({"request_id": ctx.request_id, "agent": self.name}, {"$set": verdict}, upsert=True)
        ctx.event(self.name, "VERDICT", status=status, detail={"evidence": evidence, "elapsed_ms": round((time.perf_counter()-started)*1000)})
        ctx.findings[self.name] = status
        return verdict

    def call(self, ctx: Context, tool: str):
        raise NotImplementedError

    def tool_meta(self, tool: str, data: Any):
        if isinstance(data, dict):
            return {"exists": bool(data), "fields": sorted([str(k) for k in data if k not in {"document", "email", "full_name", "password_hash"}])[:12]}
        if isinstance(data, list):
            return {"count": len(data)}
        return {"result": bool(data)}

    def decide(self, ctx: Context, fetched: dict):
        raise NotImplementedError


class Coordinator(Worker):
    name = "coordinator"
    tools = ("student_profile", "approved_enrollment")

    def call(self, ctx, tool):
        if tool == "student_profile":
            return ctx.db.students.find_one({"student_code": ctx.request["student_code"]})
        if tool == "approved_enrollment":
            return ctx.db.enrollments.find_one({"student_code": ctx.request["student_code"], "period": ctx.request["period"], "status": "REGISTERED", "request_id": {"$ne": ctx.request_id}})
        raise ValueError("Herramienta no autorizada")

    def decide(self, ctx, fetched):
        student = fetched["student_profile"]
        if not student:
            return "REJECTED", "No existe expediente académico para el estudiante.", ["STUDENT_NOT_FOUND"]
        ctx.student = student
        evidence = []
        if student.get("academic_status") != "ACTIVE":
            evidence.append("Estado académico distinto de ACTIVE")
        if fetched["approved_enrollment"]:
            evidence.append("Ya existe matrícula registrada para el periodo")
        if ctx.request.get("period") != "2026-II":
            evidence.append("Periodo académico no habilitado en el PMV")
        if student.get("plan") != "2019" or student.get("program_id") != "IS":
            evidence.append("Plan o programa no coincide con el catálogo del PMV")
        if evidence:
            return "REJECTED", "Identidad, vigencia académica o unicidad de matrícula no conformes.", evidence
        return "APPROVED", "Identidad, plan, periodo y ausencia de matrícula duplicada verificados.", ["Alumno activo", "Periodo disponible"]


class Academic(Worker):
    name = "academic"
    tools = ("transcript", "sections")

    def call(self, ctx, tool):
        if tool == "transcript":
            return list(ctx.db.academic_records.find({"student_code": ctx.student["student_code"], "status": "PASSED"}))
        if tool == "sections":
            ids = ctx.request.get("selected_section_ids", [])
            if not ctx.confirm:
                return list(ctx.db.sections.find({"period": ctx.request["period"]}))
            return list(ctx.db.sections.find({"section_id": {"$in": ids}, "period": ctx.request["period"]}))
        raise ValueError("Herramienta no autorizada")

    def decide(self, ctx, fetched):
        passed = {r["course_id"] for r in fetched["transcript"]}
        sections = fetched["sections"]
        if not ctx.confirm:
            active = [s for s in sections if s.get("status") == "OPEN"
                      and s.get("enrolled", 0) < s.get("capacity", 0)
                      and (lambda c: bool(c) and int(c.get("cycle", -1)) in {
                          int(ctx.student.get("current_cycle", 1)), int(ctx.student.get("current_cycle", 1))+1
                      })(ctx.db.courses.find_one({"course_id": s["course_id"], "program_id": ctx.student.get("program_id")}))]
            if not active:
                return "OBSERVED", "No hay secciones con vacantes. Requiere intervención administrativa.", ["Oferta sin vacantes"]
            return "APPROVED", "Historial consultado y oferta académica disponible para seleccionar.", [f"{len(active)} secciones con vacantes"]
        ids = ctx.request.get("selected_section_ids", [])
        if not ids:
            return "REJECTED", "La selección académica está vacía.", ["NO_SELECTION"]
        if len(set(ids)) != len(ids):
            return "REJECTED", "Existen secciones duplicadas en la solicitud.", ["DUPLICATE_SECTIONS"]
        indexed = {s["section_id"]: s for s in sections}
        messages, selected, credits = [], [], 0
        for section_id in ids:
            section = indexed.get(section_id)
            if not section:
                messages.append(f"Sección inexistente o no disponible: {section_id}")
                continue
            course = ctx.db.courses.find_one({"course_id": section["course_id"], "program_id": ctx.student.get("program_id")})
            if not course:
                messages.append(f"Curso no corresponde al programa: {section_id}")
                continue
            hydrated = {**course, **section}
            if int(course["cycle"]) not in {int(ctx.student.get("current_cycle", 1)), int(ctx.student.get("current_cycle", 1))+1}:
                messages.append(f"Curso fuera de ciclo habilitado: {course['course_id']}")
            if course["course_id"] in passed:
                messages.append(f"Curso ya aprobado: {course['name']}")
            messages += [m["message"] for m in validate_course(hydrated, passed, credits, int(ctx.student.get("max_credits", 22)))]
            for other in selected:
                if schedule_overlaps(hydrated.get("schedule", ""), other.get("schedule", "")):
                    messages.append(f"Cruce de horario: {hydrated['name']} y {other['name']} ({hydrated.get('schedule')}).")
                if hydrated["course_id"] == other["course_id"]:
                    messages.append(f"Curso repetido en dos secciones: {hydrated['name']}")
            selected.append(hydrated)
            credits += int(hydrated.get("credits", 0))
        ctx.selected = selected
        ctx.credits = credits
        if messages:
            return "REJECTED", "Restricciones académicas detectadas; no se delega a Finanzas.", messages
        return "APPROVED", "Prerrequisitos, vacantes, horarios y créditos conformes.", [f"{len(selected)} secciones", f"{credits} créditos"]


class Financial(Worker):
    name = "financial"
    tools = ("payment", "requirements")

    def call(self, ctx, tool):
        filt = {"student_code": ctx.student["student_code"], "period": ctx.request["period"]}
        if tool == "payment":
            return ctx.db.payments.find_one(filt)
        if tool == "requirements":
            return ctx.db.administrative_requirements.find_one(filt)
        raise ValueError("Herramienta no autorizada")

    def decide(self, ctx, fetched):
        pay, req = fetched["payment"], fetched["requirements"]
        hard, fixable = [], []
        if pay is None:
            fixable.append("Falta registro de pago: registrar conciliación")
        else:
            debt = float(pay.get("outstanding_debt") or 0)
            if debt > 0:
                hard.append(f"Deuda pendiente: S/ {debt:.2f}")
            if pay.get("status") != "PAID":
                fixable.append(f"Estado del pago: {pay.get('status', 'NOT_REGISTERED')}")
            if abs(float(pay.get("amount") or 0) - float(pay.get("expected_amount") or 0)) > 0.01:
                fixable.append("Monto pagado distinto del esperado")
        if req is None:
            fixable.append("Falta expediente administrativo")
        else:
            if not req.get("documents_complete"):
                fixable.append("Documentación administrativa incompleta")
            if req.get("insurance_status") != "VALID":
                fixable.append(f"Seguro/documento sin vigencia VALID: {req.get('insurance_status')}")
        if hard:
            return "REJECTED", "Bloqueo por deuda vencida; se detiene el flujo.", hard + fixable
        if fixable:
            return "OBSERVED", "Se requiere regularización y nueva validación antes de continuar.", fixable
        return "APPROVED", "Pago, ausencia de deuda y documentación conforme.", ["Pago conciliado", "Expediente completo"]


class Executor(Worker):
    name = "executor"
    tools = ("persist_enrollment",)

    def call(self, ctx, tool):
        if tool != "persist_enrollment":
            raise ValueError("Herramienta no autorizada")
        if ctx.db.enrollments.find_one({"request_id": ctx.request_id}):
            return {"registered": True, "idempotent": True}
        reserved = []
        try:
            for section in ctx.selected:
                changed = ctx.db.sections.update_one({"section_id": section["section_id"], "enrolled": {"$lt": section["capacity"]}}, {"$inc": {"enrolled": 1}})
                if changed.modified_count != 1:
                    raise RuntimeError(f"Sin vacantes durante registro: {section['section_id']}")
                reserved.append(section["section_id"])
            ctx.db.enrollments.insert_one({
                "request_id": ctx.request_id, "student_code": ctx.student["student_code"],
                "period": ctx.request["period"], "status": "REGISTERED", "credits": ctx.credits,
                "selected_section_ids": [s["section_id"] for s in ctx.selected], "registered_at": now(),
            })
        except Exception:
            for section_id in reserved:
                ctx.db.sections.update_one({"section_id": section_id}, {"$inc": {"enrolled": -1}})
            raise
        return {"registered": True, "reserved": len(reserved)}

    def decide(self, ctx, fetched):
        return "EXECUTED", "Matrícula persistida y vacantes reservadas.", [f"{ctx.credits} créditos registrados"]


class RPA(Worker):
    name = "rpa"
    tools = ("notify_result",)

    def call(self, ctx, tool):
        if tool != "notify_result":
            raise ValueError("Herramienta no autorizada")
        recipient = ctx.student.get("email", "")
        status, err = "SIMULATED", None
        try:
            status = send_result_email(recipient, f"Matrícula {ctx.request_id} aprobada", "Tu matrícula fue registrada. Descarga la constancia desde HyperMat IA.", None)
        except Exception as exc:
            status, err = "FAILED", type(exc).__name__
        ctx.db.notifications.update_one({"request_id": ctx.request_id, "channel": "EMAIL"}, {"$set": {
            "request_id": ctx.request_id, "channel": "EMAIL", "status": status,
            "recipient": recipient, "subject": f"Matrícula {ctx.request_id} aprobada",
            "error": err, "created_at": now(),
        }}, upsert=True)
        ctx.db.automation_runs.update_one({"request_id": ctx.request_id, "automation": "CERTIFICATE_AND_EMAIL"}, {"$set": {
            "request_id": ctx.request_id, "automation": "CERTIFICATE_AND_EMAIL",
            "status": "COMPLETED" if status in ("SENT", "SIMULATED") else "FAILED",
            "updated_at": now(),
        }}, upsert=True)
        return {"notification_status": status}

    def decide(self, ctx, fetched):
        result = fetched["notify_result"]["notification_status"]
        return "EXECUTED", "Constancia habilitada para descarga y notificación procesada.", [f"Canal EMAIL: {result}"]


WORKERS = {a.name: a() for a in (Coordinator, Academic, Financial, Executor, RPA)}


async def orchestrate(request: dict, db: Database, *, confirm: bool) -> dict:
    """Supervisor with bounded handoffs and durable, correlated trace."""
    if request.get("status") in ("APPROVED", "REJECTED"):
        raise ValueError("La solicitud está finalizada y no puede procesarse nuevamente")
    run_id = uuid.uuid4().hex
    ctx = Context(db=db, request=request, run_id=run_id, confirm=confirm)
    start = time.perf_counter()
    db.orchestration_runs.insert_one({"run_id": run_id, "request_id": ctx.request_id, "phase": "CONFIRM" if confirm else "PRECHECK", "status": "RUNNING", "started_at": now()})
    docs = []
    outcome = "REJECTED"
    last_agent = "supervisor"
    try:
        chosen = AGENTS if confirm else AGENTS[:3]
        for agent_name in chosen:
            ctx.handoff(last_agent, agent_name, "AUTHORIZED", "El supervisor delega la etapa siguiente")
            verdict = await WORKERS[agent_name].run(ctx)
            docs.append(verdict)
            last_agent = agent_name
            routing = decide_path(verdict["status"], confirm, agent_name)
            if routing != "CONTINUE":
                outcome = routing
                break
        else:
            outcome = "APPROVED" if confirm else "PREVALIDATED"
        # PREVALIDATED means eligible to choose, NEVER registered.
        db.enrollment_requests.update_one({"request_id": ctx.request_id}, {"$set": {
            "status": outcome, "credits": ctx.credits, "updated_at": now(),
            "last_run_id": run_id,
        }})
        ctx.event("supervisor", "FINAL", status=outcome, detail={"executed_agents": [d["agent"] for d in docs]})
        db.audit_events.insert_one({"event_id": uuid.uuid4().hex, "request_id": ctx.request_id,
                                    "event_type": "FINAL_VALIDATION" if confirm else "PRE_VALIDATION",
                                    "actor": "multiagent_supervisor", "created_at": now()})
        db.orchestration_runs.update_one({"run_id": run_id}, {"$set": {"status": outcome, "completed_at": now(), "duration_ms": round((time.perf_counter()-start)*1000), "agents_executed": [d["agent"] for d in docs]}})
        return {"request_id": ctx.request_id, "run_id": run_id, "status": outcome, "credits": ctx.credits, "verdicts": docs, "agents_executed": [d["agent"] for d in docs]}
    except Exception as exc:
        ctx.event("supervisor", "ERROR", status="FAILED", detail={"error_type": type(exc).__name__})
        db.orchestration_runs.update_one({"run_id": run_id}, {"$set": {"status": "FAILED", "completed_at": now(), "error_type": type(exc).__name__}})
        # Never fabricate approval after an execution or persistence error.
        db.enrollment_requests.update_one({"request_id": ctx.request_id}, {"$set": {"status": "ERROR", "updated_at": now()}})
        raise
