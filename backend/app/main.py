from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO

from bson import ObjectId
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pymongo.database import Database

from .auth import create_session, get_current_user, hash_password, require_role, revoke_session, verify_password
from .config import get_settings
from .db import get_db
from .rules import validate_course
from .schemas import (
    AcademicRecordUpsert,
    BootstrapAdminRequest,
    EnrollmentConfirm,
    EnrollmentCreate,
    LoginRequest,
    PaymentUpdate,
    RequirementUpdate,
    StudentCreate,
    StudentUpdate,
)
from .services.certificate import build_certificate
from .services.emailer import send_result_email
from .services.gemini import explain_verdict
from .services.multiagent import orchestrate


def clean(value):
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    return value


def normalize_email(value: str) -> str:
    return value.strip().lower()


def public_user(account: dict, db: Database) -> dict:
    role = account.get("role", "STUDENT").upper()
    student = None
    if role == "STUDENT" and account.get("student_code"):
        student = db.students.find_one({"student_code": account["student_code"]})
    return {
        "email": account.get("email") or account.get("username"),
        "role": role,
        "student_code": account.get("student_code") if role == "STUDENT" else None,
        "full_name": (student or {}).get("full_name") or account.get("full_name") or "Usuario HyperMat",
    }


def ensure_owner_or_admin(user: dict, student_code: str) -> None:
    if user.get("role") == "ADMIN":
        return
    if user.get("student_code") != student_code:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo puedes consultar tu propia información")


def _request_for_user(request_id: str, user: dict, db: Database) -> dict:
    request = db.enrollment_requests.find_one({"request_id": request_id})
    if not request:
        raise HTTPException(404, "Solicitud no encontrada")
    ensure_owner_or_admin(user, request["student_code"])
    return request


def _hydrate_section(section: dict, db: Database) -> dict:
    course = db.courses.find_one({"course_id": section["course_id"]}) or {}
    return {**course, **section}


def _passed_courses(student_code: str, db: Database) -> set[str]:
    return {
        row["course_id"]
        for row in db.academic_records.find(
            {"student_code": student_code, "status": "PASSED"}, {"course_id": 1}
        )
    }


def _eligible_courses(student: dict, period: str, db: Database) -> list[dict]:
    passed = _passed_courses(student["student_code"], db)
    current_cycle = int(student.get("current_cycle") or 1)
    max_credits = int(student.get("max_credits") or 22)
    response: list[dict] = []
    query = {
        "program_id": student.get("program_id", "IS"),
        "cycle": {"$in": [current_cycle, current_cycle + 1]},
        "active": {"$ne": False},
    }
    for course in db.courses.find(query).sort([("cycle", 1), ("course_id", 1)]):
        section = db.sections.find_one(
            {"course_id": course["course_id"], "period": period, "status": {"$in": ["OPEN", "FULL"]}}
        )
        hydrated = {
            **course,
            **(
                {
                    "capacity": section.get("capacity", 0),
                    "enrolled": section.get("enrolled", 0),
                    "section_id": section.get("section_id"),
                    "section": section.get("section"),
                    "schedule": section.get("schedule"),
                }
                if section
                else {"capacity": 0, "enrolled": 0, "section_id": None, "section": None, "schedule": None}
            ),
        }
        messages = validate_course(hydrated, passed, 0, max_credits)
        if course["course_id"] in passed:
            messages.append(
                {
                    "code": "ALREADY_PASSED",
                    "severity": "BLOCKER",
                    "message": "El curso ya figura como aprobado en el historial académico.",
                }
            )
        if not section:
            messages.append(
                {
                    "code": "NO_SECTION",
                    "severity": "BLOCKER",
                    "message": f"No existe una sección disponible para el periodo {period}.",
                }
            )
        response.append(
            {
                **clean(hydrated),
                "eligible": not any(item["severity"] == "BLOCKER" for item in messages),
                "messages": messages,
            }
        )
    return response


async def _save_verdict(
    db: Database,
    request_id: str,
    agent: str,
    verdict_status: str,
    deterministic_summary: str,
    evidence: list[str] | None = None,
) -> dict:
    result = {
        "status": verdict_status,
        "summary": deterministic_summary,
        "evidence": evidence or [],
    }
    explanation = await explain_verdict(agent, result)
    document = {
        "request_id": request_id,
        "agent": agent,
        "status": verdict_status,
        "summary": explanation["text"],
        "deterministic_summary": deterministic_summary,
        "evidence": evidence or [],
        "explanation_source": explanation["source"],
        "model": explanation.get("model"),
        "created_at": datetime.now(UTC),
    }
    if explanation.get("provider_error"):
        document["provider_error"] = explanation["provider_error"]
    db.agent_verdicts.update_one(
        {"request_id": request_id, "agent": agent}, {"$set": document}, upsert=True
    )
    return document


async def _validate_request(request: dict, db: Database, include_executor: bool = False) -> dict:
    """Compatibility wrapper; orchestration now runs independent workers and handoffs."""
    return await orchestrate(request, db, confirm=include_executor)


settings = get_settings()
app = FastAPI(title="HyperMat IA API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:3000", "http://localhost:4173", "http://127.0.0.1:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health(db: Database = Depends(get_db)):
    db.command("ping")
    return {
        "status": "ok",
        "database": db.name,
        "gemini_configured": bool(settings.gemini_api_key),
        "gemini_model": settings.gemini_model,
    }


# ----------------------------- Autenticación -----------------------------


@app.get("/api/auth/setup-status")
def setup_status(db: Database = Depends(get_db)):
    return {"admin_exists": db.accounts.count_documents({"role": "ADMIN"}) > 0}


@app.post("/api/auth/bootstrap-admin", status_code=201)
def bootstrap_admin(payload: BootstrapAdminRequest, db: Database = Depends(get_db)):
    if db.accounts.count_documents({"role": "ADMIN"}) > 0:
        raise HTTPException(409, "El administrador inicial ya fue creado")
    email = normalize_email(payload.email)
    document = {
        "username": email,
        "email": email,
        "student_code": "ADMIN",
        "full_name": payload.full_name.strip(),
        "password_hash": hash_password(payload.password),
        "role": "ADMIN",
        "status": "ACTIVE",
        "created_at": datetime.now(UTC),
    }
    db.accounts.insert_one(document)
    return {"created": True, "email": email, "role": "ADMIN"}


@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Database = Depends(get_db)):
    identifier = payload.username.strip().lower()

    # Estudiantes: username = código universitario.
    # Administradores: pueden seguir ingresando con su correo.
    account = db.accounts.find_one({"username": identifier})
    if not account and "@" in identifier:
        account = db.accounts.find_one({"role": "ADMIN", "email": normalize_email(identifier)})

    if not account:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos")

    valid_password = verify_password(payload.password, account.get("password_hash"))
    if not valid_password and account.get("role") == "STUDENT":
        student = db.students.find_one({"student_code": account.get("student_code")})
        # Migración transparente para cuentas antiguas que aún no tenían hash.
        if student and str(student.get("document", "")) == payload.password:
            valid_password = True
            db.accounts.update_one(
                {"_id": account["_id"]},
                {
                    "$set": {
                        "username": str(student["student_code"]),
                        "password_hash": hash_password(payload.password),
                    }
                },
            )
            account = db.accounts.find_one({"_id": account["_id"]})

    if not valid_password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos")
    if account.get("status") != "ACTIVE":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La cuenta está inactiva")

    token = create_session(db, account)
    db.accounts.update_one({"_id": account["_id"]}, {"$set": {"last_login_at": datetime.now(UTC)}})
    return {"token": token, "user": public_user(account, db)}


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    return public_user(user, db)


@app.post("/api/auth/logout")
def logout(
    authorization: str | None = Header(default=None),
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    del user
    if authorization and authorization.lower().startswith("bearer "):
        revoke_session(db, authorization.split(" ", 1)[1].strip())
    return {"ok": True}


@app.get("/api/ai/status")
def ai_status(user: dict = Depends(get_current_user)):
    del user
    return {
        "configured": bool(settings.gemini_api_key),
        "model": settings.gemini_model,
        "role": "Gemini redacta explicaciones; las reglas y MongoDB deciden.",
    }


# ----------------------------- Portal estudiante -----------------------------


@app.get("/api/me/student")
def my_student(user: dict = Depends(require_role("STUDENT")), db: Database = Depends(get_db)):
    student = db.students.find_one({"student_code": user["student_code"]})
    if not student:
        raise HTTPException(404, "Perfil de estudiante no encontrado")
    return clean(student)


@app.get("/api/me/eligible-courses")
def my_eligible_courses(
    period: str = "2026-II",
    user: dict = Depends(require_role("STUDENT")),
    db: Database = Depends(get_db),
):
    student = db.students.find_one({"student_code": user["student_code"]})
    if not student:
        raise HTTPException(404, "Perfil de estudiante no encontrado")
    return _eligible_courses(student, period, db)


@app.get("/api/me/enrollment-requests")
def my_requests(user: dict = Depends(require_role("STUDENT")), db: Database = Depends(get_db)):
    return [
        clean(item)
        for item in db.enrollment_requests.find({"student_code": user["student_code"]})
        .sort("updated_at", -1)
        .limit(30)
    ]


@app.get("/api/students/{student_code}")
def get_student(
    student_code: str,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    ensure_owner_or_admin(user, student_code)
    student = db.students.find_one({"student_code": student_code})
    if not student:
        raise HTTPException(404, "Estudiante no encontrado")
    return clean(student)


@app.get("/api/students/{student_code}/eligible-courses")
def eligible_courses(
    student_code: str,
    period: str = "2026-II",
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    ensure_owner_or_admin(user, student_code)
    student = db.students.find_one({"student_code": student_code})
    if not student:
        raise HTTPException(404, "Estudiante no encontrado")
    return _eligible_courses(student, period, db)


# ----------------------------- Solicitudes -----------------------------


@app.get("/api/enrollment-requests")
def list_requests(
    request_status: str | None = Query(default=None, alias="status"),
    user: dict = Depends(require_role("ADMIN")),
    db: Database = Depends(get_db),
):
    del user
    query = {"status": request_status} if request_status else {}
    result = []
    for item in db.enrollment_requests.find(query).sort("updated_at", -1).limit(100):
        student = db.students.find_one({"student_code": item["student_code"]}, {"full_name": 1, "email": 1, "current_cycle": 1})
        result.append({**clean(item), "student": clean(student)})
    return result


@app.get("/api/enrollment-requests/{request_id}")
def get_request(
    request_id: str,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    request = _request_for_user(request_id, user, db)
    return {
        "request": clean(request),
        "student": clean(db.students.find_one({"student_code": request["student_code"]})),
        "verdicts": [clean(item) for item in db.agent_verdicts.find({"request_id": request_id, "run_id": request.get("last_run_id")}).sort("created_at", 1)],
        "audit": [clean(item) for item in db.audit_events.find({"request_id": request_id}).sort("created_at", 1)],
        "notification": clean(db.notifications.find_one({"request_id": request_id})),
        "enrollment": clean(db.enrollments.find_one({"request_id": request_id})),
        "agent_trace": [clean(item) for item in db.agent_traces.find({"run_id": request.get("last_run_id")}).sort("seq", 1).limit(80)] if request.get("last_run_id") else [],
        "agent_messages": [clean(item) for item in db.agent_messages.find({"run_id": request.get("last_run_id")}).sort("created_at", 1).limit(20)] if request.get("last_run_id") else [],
    }


@app.get("/api/enrollment-requests/{request_id}/trace")
def request_agent_trace(request_id: str, user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    request = _request_for_user(request_id, user, db)
    run_id = request.get("last_run_id")
    if not run_id:
        return {"request_id": request_id, "run": None, "events": [], "messages": []}
    return {
        "request_id": request_id,
        "run": clean(db.orchestration_runs.find_one({"run_id": run_id})),
        "events": [clean(row) for row in db.agent_traces.find({"run_id": run_id}).sort("seq", 1).limit(100)],
        "messages": [clean(row) for row in db.agent_messages.find({"run_id": run_id}).sort("created_at", 1).limit(30)],
    }


@app.post("/api/enrollment-requests", status_code=201)
def create_request(
    payload: EnrollmentCreate,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    student_code = payload.student_code if user.get("role") == "ADMIN" else user.get("student_code")
    if not student_code:
        raise HTTPException(422, "Falta el código del estudiante")
    student = db.students.find_one({"student_code": student_code})
    if not student:
        raise HTTPException(404, "Estudiante no encontrado")

    count = db.enrollment_requests.count_documents({"period": payload.period}) + 1
    request_id = f"MAT-{datetime.now(UTC):%y%m}{count:03d}"
    while db.enrollment_requests.find_one({"request_id": request_id}):
        count += 1
        request_id = f"MAT-{datetime.now(UTC):%y%m}{count:03d}"

    document = {
        "request_id": request_id,
        "student_code": student_code,
        "period": payload.period,
        "program_id": student.get("program_id", payload.program_id),
        "selected_section_ids": payload.selected_section_ids,
        "status": "DRAFT",
        "scenario": "Solicitud creada desde el portal",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    db.enrollment_requests.insert_one(document)
    db.audit_events.insert_one(
        {
            "event_id": f"{request_id}-CREATED",
            "request_id": request_id,
            "event_type": "REQUEST_CREATED",
            "actor": user.get("username"),
            "created_at": datetime.now(UTC),
        }
    )
    return clean(document)


@app.post("/api/enrollment-requests/{request_id}/validate")
async def validate_request_endpoint(
    request_id: str,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    request = _request_for_user(request_id, user, db)
    if request.get("status") in ("APPROVED", "REJECTED"):
        raise HTTPException(409, "La solicitud está finalizada; inicia una nueva solicitud")
    return await _validate_request(request, db, include_executor=False)


@app.post("/api/enrollment-requests/{request_id}/confirm")
async def confirm_request(
    request_id: str,
    payload: EnrollmentConfirm,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    request = _request_for_user(request_id, user, db)
    if request.get("status") == "APPROVED":
        raise HTTPException(409, "La matrícula ya se encuentra registrada")
    if not payload.selected_section_ids:
        raise HTTPException(422, "Selecciona al menos una sección")

    db.enrollment_requests.update_one(
        {"request_id": request_id},
        {"$set": {"selected_section_ids": payload.selected_section_ids, "updated_at": datetime.now(UTC)}},
    )
    request = db.enrollment_requests.find_one({"request_id": request_id})
    try:
        return await _validate_request(request, db, include_executor=True)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc



@app.get("/api/enrollment-requests/{request_id}/certificate")
def certificate(
    request_id: str,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    request = _request_for_user(request_id, user, db)
    if request.get("status") != "APPROVED" or not db.enrollments.find_one({"request_id": request_id, "status": "REGISTERED"}):
        raise HTTPException(409, "La matrícula todavía no está registrada; constancia no disponible")
    student = db.students.find_one({"student_code": request["student_code"]})
    selected = []
    for section_id in request.get("selected_section_ids", []):
        section = db.sections.find_one({"section_id": section_id})
        if section:
            selected.append(_hydrate_section(section, db))
    pdf = build_certificate(student, request, selected)
    return StreamingResponse(
        BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=constancia_{request_id}.pdf"},
    )


# ----------------------------- Administración de datos -----------------------------


@app.get("/api/admin/students")
def admin_students(
    query: str = "",
    user: dict = Depends(require_role("ADMIN")),
    db: Database = Depends(get_db),
):
    del user
    mongo_query = {}
    if query.strip():
        escaped = query.strip()
        mongo_query = {
            "$or": [
                {"full_name": {"$regex": escaped, "$options": "i"}},
                {"student_code": {"$regex": escaped, "$options": "i"}},
                {"email": {"$regex": escaped, "$options": "i"}},
            ]
        }
    return [clean(item) for item in db.students.find(mongo_query).sort("full_name", 1).limit(200)]


@app.post("/api/admin/students", status_code=201)
def admin_create_student(
    payload: StudentCreate,
    user: dict = Depends(require_role("ADMIN")),
    db: Database = Depends(get_db),
):
    del user
    email = normalize_email(payload.email)
    if db.students.find_one({"student_code": payload.student_code}) or db.accounts.find_one({"username": payload.student_code}):
        raise HTTPException(409, "El código universitario ya existe")

    student = payload.model_dump(exclude={"initial_password"})
    student["email"] = email
    student["created_at"] = datetime.now(UTC)
    db.students.insert_one(student)
    db.accounts.insert_one(
        {
            "username": payload.student_code,
            "email": email,
            "student_code": payload.student_code,
            "password_hash": hash_password(payload.initial_password or payload.document),
            "role": "STUDENT",
            # La cuenta puede iniciar sesión incluso si el expediente académico está INACTIVE;
            # esa condición la evalúa el Agente Coordinador durante la matrícula.
            "status": "ACTIVE",
            "created_at": datetime.now(UTC),
        }
    )
    return {"student": clean(student), "login": {"username": payload.student_code, "password_policy": "DNI si no se indicó otra contraseña inicial", "notification_email": email}}


@app.put("/api/admin/students/{student_code}")
def admin_update_student(
    student_code: str,
    payload: StudentUpdate,
    user: dict = Depends(require_role("ADMIN")),
    db: Database = Depends(get_db),
):
    del user
    current = db.students.find_one({"student_code": student_code})
    if not current:
        raise HTTPException(404, "Estudiante no encontrado")
    updates = {key: value for key, value in payload.model_dump().items() if value is not None}
    if "email" in updates:
        updates["email"] = normalize_email(updates["email"])
    updates["updated_at"] = datetime.now(UTC)
    db.students.update_one({"student_code": student_code}, {"$set": updates})
    account_updates = {}
    if "email" in updates:
        account_updates["email"] = updates["email"]
    # account.status representa acceso al portal; academic_status se valida en el proceso.
    if "academic_status" in updates:
        account_updates["status"] = "ACTIVE"
    if account_updates:
        db.accounts.update_one({"student_code": student_code}, {"$set": account_updates})
    return clean(db.students.find_one({"student_code": student_code}))


@app.get("/api/admin/students/{student_code}/context")
def admin_student_context(
    student_code: str,
    period: str = "2026-II",
    user: dict = Depends(require_role("ADMIN")),
    db: Database = Depends(get_db),
):
    del user
    student = db.students.find_one({"student_code": student_code})
    if not student:
        raise HTTPException(404, "Estudiante no encontrado")
    return {
        "student": clean(student),
        "payment": clean(db.payments.find_one({"student_code": student_code, "period": period})),
        "requirements": clean(db.administrative_requirements.find_one({"student_code": student_code, "period": period})),
        "academic_records": [
            clean(item)
            for item in db.academic_records.find({"student_code": student_code}).sort([("period", -1), ("course_id", 1)])
        ],
        "requests": [
            clean(item)
            for item in db.enrollment_requests.find({"student_code": student_code}).sort("updated_at", -1).limit(20)
        ],
    }


@app.put("/api/admin/students/{student_code}/payment")
def admin_update_payment(
    student_code: str,
    payload: PaymentUpdate,
    user: dict = Depends(require_role("ADMIN")),
    db: Database = Depends(get_db),
):
    del user
    if not db.students.find_one({"student_code": student_code}):
        raise HTTPException(404, "Estudiante no encontrado")
    document = {
        "student_code": student_code,
        **payload.model_dump(),
        "updated_at": datetime.now(UTC),
    }
    db.payments.update_one(
        {"student_code": student_code, "period": payload.period}, {"$set": document}, upsert=True
    )
    return clean(db.payments.find_one({"student_code": student_code, "period": payload.period}))


@app.put("/api/admin/students/{student_code}/requirements")
def admin_update_requirements(
    student_code: str,
    payload: RequirementUpdate,
    user: dict = Depends(require_role("ADMIN")),
    db: Database = Depends(get_db),
):
    del user
    if not db.students.find_one({"student_code": student_code}):
        raise HTTPException(404, "Estudiante no encontrado")
    document = {
        "student_code": student_code,
        **payload.model_dump(),
        "updated_at": datetime.now(UTC),
    }
    db.administrative_requirements.update_one(
        {"student_code": student_code, "period": payload.period}, {"$set": document}, upsert=True
    )
    return clean(db.administrative_requirements.find_one({"student_code": student_code, "period": payload.period}))


@app.post("/api/admin/students/{student_code}/academic-records")
def admin_upsert_academic_record(
    student_code: str,
    payload: AcademicRecordUpsert,
    user: dict = Depends(require_role("ADMIN")),
    db: Database = Depends(get_db),
):
    del user
    if not db.students.find_one({"student_code": student_code}):
        raise HTTPException(404, "Estudiante no encontrado")
    if not db.courses.find_one({"course_id": payload.course_id}):
        raise HTTPException(404, "El course_id no existe en la malla cargada")
    document = {
        "student_code": student_code,
        **payload.model_dump(),
        "updated_at": datetime.now(UTC),
    }
    db.academic_records.update_one(
        {"student_code": student_code, "course_id": payload.course_id, "attempt": payload.attempt},
        {"$set": document},
        upsert=True,
    )
    return clean(
        db.academic_records.find_one(
            {"student_code": student_code, "course_id": payload.course_id, "attempt": payload.attempt}
        )
    )


@app.get("/api/admin/courses")
def admin_courses(user: dict = Depends(require_role("ADMIN")), db: Database = Depends(get_db)):
    del user
    return [clean(item) for item in db.courses.find({"active": {"$ne": False}}).sort([("cycle", 1), ("course_id", 1)])]
