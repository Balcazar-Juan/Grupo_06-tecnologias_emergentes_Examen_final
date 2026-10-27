"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  FileCheck2,
  FileText,
  GraduationCap,
  Layers3,
  LockKeyhole,
  LogOut,
  Mail,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  UserRound,
  UsersRound,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  type AgentName,
  type AgentStatus,
  type AgentVerdict,
  type AIStatus,
  type EligibleCourse,
  type EnrollmentRequest,
  hypermatApi,
  openCertificate,
  type RequestDetail,
  type SessionUser,
  type Student,
  type StudentContext,
} from "@/lib/hypermat-api";

type AuthState = { token: string; user: SessionUser };
type StudentPhase = "start" | "selection" | "result";
type AdminView = "requests" | "students";

const agentMeta: Record<AgentName, { label: string; role: string; icon: typeof Layers3 }> = {
  coordinator: { label: "Coordinador", role: "Orquesta la validación", icon: Layers3 },
  academic: { label: "Académico", role: "Historial y malla", icon: GraduationCap },
  financial: { label: "Admin-Financiero", role: "Pago y requisitos", icon: CircleDollarSign },
  executor: { label: "Ejecutor", role: "Registra la matrícula", icon: ShieldCheck },
  rpa: { label: "RPA", role: "Constancia y notificación", icon: Bot },
};

const agentOrder: AgentName[] = ["coordinator", "academic", "financial", "executor", "rpa"];

function statusLabel(value: AgentStatus | string) {
  const labels: Record<string, string> = {
    APPROVED: "APROBADO",
    OBSERVED: "OBSERVADO",
    REJECTED: "RECHAZADO",
    PENDING: "PENDIENTE",
    EXECUTED: "EJECUTADO",
    DRAFT: "BORRADOR",
    IN_PROGRESS: "EN PROCESO",
    PREVALIDATED: "APTO PARA SELECCIONAR",
    ERROR: "ERROR TÉCNICO",
  };
  return labels[value] || value;
}

function verdictTone(value: AgentStatus | string) {
  if (["APPROVED", "EXECUTED", "PREVALIDATED"].includes(value)) return "success";
  if (["OBSERVED", "IN_PROGRESS"].includes(value)) return "warning";
  if (value === "REJECTED") return "danger";
  return "neutral";
}

function StatusPill({ value }: { value: AgentStatus | string }) {
  return (
    <span className={`status-pill status-${verdictTone(value)}`}>
      <span />
      {statusLabel(value)}
    </span>
  );
}

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function formatDate(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("es-PE", { dateStyle: "short", timeStyle: "short" });
}

function ErrorNotice({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="error-notice">
      <AlertTriangle />
      <span>{message}</span>
    </div>
  );
}

function AIChip({ status }: { status: AIStatus | null }) {
  return (
    <span className={`model-chip ${status?.configured ? "ai-online" : "ai-offline"}`}>
      <Sparkles /> {status?.configured ? status.model : "IA sin clave configurada"}
    </span>
  );
}

function AppHeader({ auth, aiStatus, onLogout }: { auth: AuthState; aiStatus: AIStatus | null; onLogout: () => void }) {
  return (
    <header className="topbar auth-topbar">
      <div className="brand">
        <div className="brand-mark"><GraduationCap /></div>
        <div><strong>HyperMat <em>IA</em></strong><span>Matrícula universitaria</span></div>
      </div>
      <div className="session-role">
        {auth.user.role === "ADMIN" ? <UsersRound /> : <UserRound />}
        <span>{auth.user.role === "ADMIN" ? "Administración" : "Estudiante"}</span>
      </div>
      <div className="topbar-meta">
        <AIChip status={aiStatus} />
        <div className="user-identity">
          <div className="avatar">{initials(auth.user.full_name)}</div>
          <div><strong>{auth.user.full_name}</strong><span>{auth.user.email}</span></div>
        </div>
        <Button variant="outline" size="sm" onClick={onLogout}><LogOut /> Salir</Button>
      </div>
    </header>
  );
}

function LoginPage({ onAuthenticated }: { onAuthenticated: (auth: AuthState) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [adminExists, setAdminExists] = useState<boolean | null>(null);
  const [setup, setSetup] = useState({ full_name: "", email: "", password: "" });
  const [setupMessage, setSetupMessage] = useState<string | null>(null);

  useEffect(() => {
    hypermatApi.setupStatus().then((data) => setAdminExists(data.admin_exists)).catch(() => setAdminExists(null));
  }, []);

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await hypermatApi.login(username, password);
      localStorage.setItem("hypermat_token", result.token);
      onAuthenticated(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar sesión.");
    } finally {
      setBusy(false);
    }
  }

  async function createInitialAdmin(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSetupMessage(null);
    try {
      await hypermatApi.bootstrapAdmin(setup);
      setAdminExists(true);
      setUsername(setup.email);
      setPassword(setup.password);
      setSetupMessage("Administrador creado. Ya puedes iniciar sesión con esas credenciales.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear el administrador inicial.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-hero">
        <div className="brand login-brand"><div className="brand-mark"><GraduationCap /></div><div><strong>HyperMat <em>IA</em></strong><span>UNFV · Matrícula inteligente</span></div></div>
        <div className="login-copy">
          <span>HIPERAUTOMATIZACIÓN UNIVERSITARIA</span>
          <h1>Tu matrícula, validada con datos reales.</h1>
          <p>HyperMat consulta MongoDB, aplica reglas académicas y administrativas y utiliza Gemini para explicar cada veredicto sin alterar la decisión.</p>
        </div>
        <div className="login-flow-mini">
          <div><Layers3 /><span>Coordinador</span></div><ChevronRight />
          <div><GraduationCap /><span>Académico</span></div><ChevronRight />
          <div><CircleDollarSign /><span>Financiero</span></div><ChevronRight />
          <div><ShieldCheck /><span>Ejecutor</span></div>
        </div>
      </section>

      <section className="login-panel">
        <div className="login-card surface-card">
          <div className="login-heading"><span>ACCESO</span><h2>Inicia sesión</h2><p>Estudiantes: código universitario como usuario y contraseña inicial igual al DNI. Administradores: correo registrado.</p></div>
          <ErrorNotice message={error} />
          {setupMessage && <div className="success-notice"><CheckCircle2 />{setupMessage}</div>}
          <form onSubmit={handleLogin} className="login-form">
            <div className="field"><Label htmlFor="login-username">Usuario</Label><Input id="login-username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Código universitario (estudiante) o correo (admin)" required /></div>
            <div className="field"><Label htmlFor="login-password">Contraseña</Label><Input id="login-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Tu contraseña" required /></div>
            <Button className="primary-action" size="lg" disabled={busy}>{busy ? <RefreshCw className="spin" /> : <LockKeyhole />} Ingresar</Button>
          </form>
          <div className="login-security"><ShieldCheck /><div><strong>Roles reales</strong><span>El portal que se abre depende de la cuenta autenticada; ya no hay selector manual de rol.</span></div></div>
        </div>

        {adminExists === false && (
          <form onSubmit={createInitialAdmin} className="setup-card surface-card">
            <div><span>PRIMERA EJECUCIÓN</span><h3>Crear administrador inicial</h3><p>Este formulario solo está disponible mientras no exista ninguna cuenta ADMIN.</p></div>
            <div className="field"><Label>Nombre</Label><Input value={setup.full_name} onChange={(e) => setSetup({ ...setup, full_name: e.target.value })} required /></div>
            <div className="field"><Label>Correo administrador</Label><Input type="email" value={setup.email} onChange={(e) => setSetup({ ...setup, email: e.target.value })} required /></div>
            <div className="field"><Label>Contraseña</Label><Input type="password" minLength={6} value={setup.password} onChange={(e) => setSetup({ ...setup, password: e.target.value })} required /></div>
            <Button variant="outline" disabled={busy}><Plus /> Crear administrador</Button>
          </form>
        )}
      </section>
    </main>
  );
}

function AgentFlow({ verdicts, onOpen }: { verdicts: AgentVerdict[]; onOpen: (verdict: AgentVerdict) => void }) {
  const byAgent = new Map(verdicts.map((item) => [item.agent, item]));
  return (
    <div className="agent-flow" aria-label="Flujo multiagente">
      {agentOrder.map((agent, index) => {
        const meta = agentMeta[agent];
        const Icon = meta.icon;
        const verdict = byAgent.get(agent) || ({ request_id: "", agent, status: "PENDING", summary: "Pendiente de ejecución.", evidence: [] } as AgentVerdict);
        return (
          <div className="flow-unit" key={agent}>
            <button className={`agent-node node-${verdictTone(verdict.status)}`} onClick={() => onOpen(verdict)}>
              <div className="node-icon"><Icon /></div>
              <div className="node-copy"><strong>{meta.label}</strong><span>{meta.role}</span></div>
              <span className="node-expand"><ChevronRight /></span>
              <StatusPill value={verdict.status} />
            </button>
            {index < agentOrder.length - 1 && <div className={`flow-link ${verdict.status === "PENDING" ? "link-pending" : ""}`}><span /><ChevronRight /></div>}
          </div>
        );
      })}
    </div>
  );
}

function AgentDetail({ verdict }: { verdict: AgentVerdict | null }) {
  if (!verdict) return null;
  const meta = agentMeta[verdict.agent];
  const Icon = meta.icon;
  return (
    <div className="detail-body">
      <div className="detail-agent"><div className="detail-icon"><Icon /></div><div><span>VEREDICTO DEL AGENTE</span><h3>{meta.label}</h3></div></div>
      <StatusPill value={verdict.status} />
      <p className="detail-summary">{verdict.summary}</p>
      <div className="check-list">
        {(verdict.evidence?.length ? verdict.evidence : ["Sin observaciones adicionales."]).map((item) => <div key={item}><CheckCircle2 /><span>{item}</span></div>)}
      </div>
      <div className="audit-note"><Clock3 /><div><strong>Registro de auditoría</strong><span>{verdict.created_at ? `Procesado ${formatDate(verdict.created_at)}.` : "El resultado se registra junto con la solicitud."}</span></div></div>
      <div className="llm-note"><Sparkles /><div><strong>{verdict.explanation_source === "GEMINI" ? "Explicación generada por Gemini" : "Explicación determinista"}</strong><span>{verdict.explanation_source === "GEMINI" ? `${verdict.model || "Gemini"} redactó este resumen a partir del resultado calculado por reglas y MongoDB.` : "La IA no cambió el veredicto. Cuando Gemini no está disponible, HyperMat conserva la explicación calculada por reglas."}</span></div></div>
    </div>
  );
}

function StudentStart({ student, busy, error, onStart, resumable, onResume }: { student: Student; busy: boolean; error: string | null; onStart: (period: string) => void; resumable?: EnrollmentRequest | null; onResume: (requestId: string) => void }) {
  const [period, setPeriod] = useState("2026-II");
  return (
    <section className="student-grid">
      <div className="form-card surface-card">
        <div className="section-heading"><div><span>NUEVA SOLICITUD</span><h1>Inicia tu matrícula</h1><p>Los datos mostrados vienen de MongoDB. HyperMat no carga un estudiante ficticio en el navegador.</p></div><div className="step-count">01</div></div>
        <ErrorNotice message={error} />
        <div className="request-form">
          <div className="field"><Label>Código universitario</Label><Input value={student.student_code} readOnly /></div>
          <div className="field"><Label>Periodo académico</Label><NativeSelect value={period} onChange={(e) => setPeriod(e.target.value)}><NativeSelectOption value="2026-II">2026-II</NativeSelectOption></NativeSelect></div>
          <div className="field"><Label>Escuela profesional</Label><Input value={student.program_name || student.program_id} readOnly /></div>
          <div className="field"><Label>Plan curricular</Label><Input value={student.plan || "—"} readOnly /></div>
          <div className="consent-row"><ShieldCheck /><span>Al iniciar, los agentes consultan historial académico, pagos y requisitos registrados para tu cuenta.</span></div>
          <Button className="primary-action" onClick={() => onStart(period)} disabled={busy}>{busy ? <RefreshCw className="spin" /> : <Sparkles />} Validar mi situación <ArrowRight /></Button>
          {resumable && <Button variant="outline" disabled={busy} onClick={() => onResume(resumable.request_id)}><RefreshCw /> Retomar solicitud {resumable.request_id} ({statusLabel(resumable.status)})</Button>}
        </div>
      </div>
      <aside className="student-aside">
        <div className="profile-card">
          <div className="profile-top"><div className="profile-avatar">{initials(student.full_name)}</div><div><strong>{student.full_name}</strong><span>{student.email}</span></div></div>
          <dl><div><dt>Ciclo</dt><dd>{student.current_cycle}.°</dd></div><div><dt>Máximo</dt><dd>{student.max_credits} cr.</dd></div><div><dt>Estado</dt><dd>{student.academic_status === "ACTIVE" ? "Activo" : "Inactivo"}</dd></div></dl>
        </div>
        <div className="info-card"><CircleDollarSign /><div><strong>Datos administrados</strong><p>Pago, deuda, documentos e historial se cargan desde el panel administrativo. Si falta información, HyperMat la mostrará como pendiente.</p></div></div>
        <div className="mini-timeline"><div className="done"><span>1</span><div><strong>Validación</strong><small>Agentes consultan tus registros</small></div></div><div><span>2</span><div><strong>Selección</strong><small>Solo cursos habilitados</small></div></div><div><span>3</span><div><strong>Resultado</strong><small>Registro, trazabilidad y constancia</small></div></div></div>
      </aside>
    </section>
  );
}

function CourseSelection({ student, requestId, courses, verdicts, busy, error, onConfirm, onAgent, onRevalidate }: { student: Student; requestId: string; courses: EligibleCourse[]; verdicts: AgentVerdict[]; busy: boolean; error: string | null; onConfirm: (sectionIds: string[]) => void; onAgent: (verdict: AgentVerdict) => void; onRevalidate: () => void }) {
  const [selected, setSelected] = useState<string[]>([]);
  const selectedCourses = courses.filter((course) => course.section_id && selected.includes(course.section_id));
  const credits = selectedCourses.reduce((sum, course) => sum + course.credits, 0);
  const enabledCount = courses.filter((course) => course.eligible).length;
  const blocked = verdicts.some((v) => v.status === "OBSERVED" || v.status === "REJECTED");

  function toggle(course: EligibleCourse) {
    if (!course.eligible || !course.section_id) return;
    setSelected((current) => current.includes(course.section_id!) ? current.filter((id) => id !== course.section_id) : [...current, course.section_id!]);
  }

  return (
    <div className="workflow-page">
      <div className="page-title"><div><span>SOLICITUD {requestId}</span><h1>Selecciona tus cursos</h1><p>{enabledCount} cursos están habilitados con los datos actuales de tu expediente.</p></div><StatusPill value={verdicts.some((v) => v.status === "REJECTED") ? "REJECTED" : verdicts.some((v) => v.status === "OBSERVED") ? "OBSERVED" : "APPROVED"} /></div>
      <ErrorNotice message={error} />
      <section className="surface-card flow-card"><div className="card-heading"><div><h2>Flujo de validación</h2><p>Abre cualquier agente para revisar la evidencia consultada.</p></div></div><AgentFlow verdicts={verdicts} onOpen={onAgent} /></section>
      <section className="courses-layout">
        <div className="surface-card courses-card">
          <div className="card-heading"><div><span>PASO 2 DE 3</span><h2>Oferta habilitada</h2><p>La selección se vuelve a validar al confirmar.</p></div><div className={`credit-meter ${credits > student.max_credits ? "near-limit" : ""}`}><strong>{credits}</strong><span>/ {student.max_credits} créditos</span><Progress value={Math.min(100, (credits / student.max_credits) * 100)} /></div></div>
          <div className="course-list">
            {courses.length === 0 && <div className="empty-state"><GraduationCap /><strong>No hay cursos disponibles</strong><span>Revisa la malla, ciclo y secciones cargadas desde Administración.</span></div>}
            {courses.map((course) => {
              const checked = !!course.section_id && selected.includes(course.section_id);
              const overLimit = !checked && credits + course.credits > student.max_credits;
              const disabled = !course.eligible || !course.section_id || overLimit;
              const reason = overLimit ? `Superaría el máximo de ${student.max_credits} créditos.` : course.messages.find((item) => item.severity === "BLOCKER")?.message;
              return (
                <label key={`${course.course_id}-${course.section_id || "none"}`} className={`course-row ${disabled ? "course-locked" : ""} ${checked ? "course-selected" : ""}`}>
                  <Checkbox checked={checked} disabled={disabled} onCheckedChange={() => toggle(course)} />
                  <div className="course-main"><div><strong>{course.name}</strong><Badge variant="outline">{course.code}</Badge></div><span>Sección {course.section || "—"} · {course.schedule || "Sin horario"}</span>{reason && <small><LockKeyhole /> {reason}</small>}</div>
                  <div className="course-meta"><strong>{course.credits}</strong><span>créditos</span><small>{Math.max(0, course.capacity - course.enrolled)} vacantes</small></div>
                </label>
              );
            })}
          </div>
        </div>
        <aside className="surface-card summary-card"><span>RESUMEN</span><h3>Cursos seleccionados</h3><div className="selected-list">{selectedCourses.length === 0 && <small>Aún no seleccionaste cursos.</small>}{selectedCourses.map((course) => <div key={course.section_id}><span>{course.name}</span><strong>{course.credits} cr.</strong></div>)}</div><div className="summary-total"><span>Total</span><strong>{credits} créditos</strong></div><div className="summary-check"><CheckCircle2 /><span>El backend repetirá prerrequisitos, vacantes, créditos, pago, deuda y documentos antes de registrar.</span></div><Button onClick={() => onConfirm(selected)} disabled={!selected.length || busy || blocked} size="lg" className="primary-action">{busy ? <RefreshCw className="spin" /> : <ShieldCheck />} Confirmar matrícula <ArrowRight /></Button>{blocked && <><p className="detail-summary">La solicitud tiene una observación o bloqueo. El sistema no avanzará al Ejecutor ni a RPA hasta regularizarla.</p><Button variant="outline" onClick={onRevalidate} disabled={busy}><RefreshCw /> Volver a validar</Button></>}</aside>
      </section>
    </div>
  );
}

function StudentResult({ detail, busy, error, onAgent, onCertificate, onNew, onResume }: { detail: RequestDetail; busy: boolean; error: string | null; onAgent: (verdict: AgentVerdict) => void; onCertificate: () => void; onNew: () => void; onResume: () => void }) {
  const approved = detail.request.status === "APPROVED";
  const rejected = detail.request.status === "REJECTED";
  return (
    <div className="workflow-page">
      <div className={`completion-banner ${rejected ? "result-rejected" : approved ? "" : "result-observed"}`}><div className="completion-icon">{approved ? <Check /> : rejected ? <XCircle /> : <AlertTriangle />}</div><div><span>{approved ? "MATRÍCULA APROBADA" : rejected ? "MATRÍCULA NO REGISTRADA" : "SOLICITUD OBSERVADA"}</span><h1>{approved ? "Tu matrícula fue registrada" : rejected ? "Hay condiciones que impiden el registro" : "Tu solicitud necesita regularización"}</h1><p>{approved ? `El resultado quedó asociado a ${detail.student.email}.` : "Revisa los agentes para conocer exactamente qué dato debes regularizar."}</p></div><StatusPill value={detail.request.status} /></div>
      <ErrorNotice message={error} />
      <section className="surface-card flow-card"><div className="card-heading"><div><h2>Flujo final</h2><p>Los resúmenes muestran si Gemini intervino como capa explicativa.</p></div><span className="request-code">{detail.request.request_id}</span></div><AgentFlow verdicts={detail.verdicts} onOpen={onAgent} /></section>
      <section className="completion-grid">
        <div className="surface-card final-summary"><div className="card-heading"><div><span>PASO 3 DE 3</span><h2>Resultado y documentos</h2></div></div>
          {approved && <div className="delivery-row"><div className="delivery-icon"><FileCheck2 /></div><div><strong>Constancia de matrícula</strong><span>Generada desde la selección registrada en MongoDB.</span></div><Button variant="outline" onClick={onCertificate} disabled={busy}><FileText /> Ver PDF</Button></div>}
          <div className="delivery-row"><div className="delivery-icon"><Mail /></div><div><strong>Notificación</strong><span>{detail.notification?.recipient || detail.student.email} · {detail.notification?.status || "Pendiente"}</span></div><Badge variant="outline">{detail.notification?.status || "—"}</Badge></div>
          <div className="result-actions">{!approved && !rejected && <Button variant="outline" onClick={onResume} disabled={busy}><RefreshCw /> Revalidar tras regularización</Button>}<Button variant="outline" onClick={onNew}><RefreshCw /> Nueva solicitud</Button></div>
        </div>
        <div className="surface-card trace-card"><span>TRAZABILIDAD</span><h3>Eventos registrados</h3><dl>{detail.audit.slice(-6).map((item, index) => <div key={`${item.event_type}-${index}`}><dt>{item.event_type}</dt><dd>{formatDate(item.created_at)}</dd></div>)}</dl></div>
      </section>
    </div>
  );
}

function StudentPortal({ auth, onAIStatus }: { auth: AuthState; onAIStatus: (status: AIStatus) => void }) {
  const [student, setStudent] = useState<Student | null>(null);
  const [phase, setPhase] = useState<StudentPhase>("start");
  const [period, setPeriod] = useState("2026-II");
  const [requestId, setRequestId] = useState("");
  const [courses, setCourses] = useState<EligibleCourse[]>([]);
  const [resumable, setResumable] = useState<EnrollmentRequest | null>(null);
  const [verdicts, setVerdicts] = useState<AgentVerdict[]>([]);
  const [detail, setDetail] = useState<RequestDetail | null>(null);
  const [openVerdict, setOpenVerdict] = useState<AgentVerdict | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([hypermatApi.myStudent(auth.token), hypermatApi.aiStatus(auth.token), hypermatApi.myRequests(auth.token)])
      .then(([profile, ai, requests]) => { setStudent(profile); onAIStatus(ai); setResumable(requests.find((r) => ["DRAFT", "OBSERVED", "PREVALIDATED"].includes(r.status)) || null); })
      .catch((err) => setError(err instanceof Error ? err.message : "No se pudo cargar el perfil."));
  }, [auth.token, onAIStatus]);

  async function startValidation(nextPeriod: string) {
    setBusy(true); setError(null); setPeriod(nextPeriod);
    try {
      const request = await hypermatApi.createRequest(auth.token, { period: nextPeriod, selected_section_ids: [] });
      const [validation, availableCourses] = await Promise.all([
        hypermatApi.validateRequest(auth.token, request.request_id),
        hypermatApi.eligibleCourses(auth.token, nextPeriod),
      ]);
      setRequestId(request.request_id);
      setVerdicts(validation.verdicts);
      setCourses(availableCourses);
      if (validation.status === "REJECTED") {
        setDetail(await hypermatApi.requestDetail(auth.token, request.request_id));
        setPhase("result");
      } else {
        setPhase("selection");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar la validación.");
    } finally { setBusy(false); }
  }

  async function resume(requestToResume: string) {
    setBusy(true); setError(null);
    try {
      const current = await hypermatApi.requestDetail(auth.token, requestToResume);
      setRequestId(requestToResume);
      setPeriod(current.request.period);
      const result = await hypermatApi.validateRequest(auth.token, requestToResume);
      setVerdicts(result.verdicts);
      setCourses(await hypermatApi.eligibleCourses(auth.token, current.request.period));
      if (result.status === "REJECTED") {
        setDetail(await hypermatApi.requestDetail(auth.token, requestToResume));
        setPhase("result");
      } else {
        setPhase("selection");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo retomar la solicitud.");
    } finally { setBusy(false); }
  }

  async function revalidate() {
    setBusy(true); setError(null);
    try {
      const result = await hypermatApi.validateRequest(auth.token, requestId);
      setVerdicts(result.verdicts);
      setCourses(await hypermatApi.eligibleCourses(auth.token, period));
      if (result.status === "REJECTED") {
        setDetail(await hypermatApi.requestDetail(auth.token, requestId));
        setPhase("result");
      } else {
        setPhase("selection");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo repetir la validación.");
    } finally { setBusy(false); }
  }

  async function confirm(sectionIds: string[]) {
    setBusy(true); setError(null);
    try {
      await hypermatApi.confirmRequest(auth.token, requestId, sectionIds);
      const current = await hypermatApi.requestDetail(auth.token, requestId);
      setDetail(current);
      setVerdicts(current.verdicts);
      setPhase("result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo confirmar la matrícula.");
    } finally { setBusy(false); }
  }

  async function showCertificate() {
    if (!detail) return;
    setBusy(true); setError(null);
    try { await openCertificate(auth.token, detail.request.request_id); }
    catch (err) { setError(err instanceof Error ? err.message : "No se pudo abrir la constancia."); }
    finally { setBusy(false); }
  }

  function reset() {
    setPhase("start"); setRequestId(""); setCourses([]); setVerdicts([]); setDetail(null); setError(null);
  }

  if (!student) return <main className="app-shell"><div className="loading-card surface-card"><RefreshCw className="spin" /><span>Cargando tu información desde MongoDB...</span><ErrorNotice message={error} /></div></main>;

  return (
    <main className="app-shell">
      {phase === "start" && <StudentStart student={student} busy={busy} error={error} onStart={startValidation} resumable={resumable} onResume={resume} />}
      {phase === "selection" && <CourseSelection student={student} requestId={requestId} courses={courses} verdicts={verdicts} busy={busy} error={error} onConfirm={confirm} onAgent={setOpenVerdict} onRevalidate={revalidate} />}
      {phase === "result" && detail && <StudentResult detail={detail} busy={busy} error={error} onAgent={setOpenVerdict} onCertificate={showCertificate} onNew={reset} onResume={revalidate} />}
      <Sheet open={!!openVerdict} onOpenChange={(open) => !open && setOpenVerdict(null)}><SheetContent className="detail-sheet sm:max-w-[500px]"><SheetHeader><SheetTitle>Detalle del veredicto</SheetTitle><SheetDescription>{requestId || detail?.request.request_id || period} · Datos registrados por HyperMat.</SheetDescription></SheetHeader><AgentDetail verdict={openVerdict} /></SheetContent></Sheet>
    </main>
  );
}

function RequestDetailPanel({ detail }: { detail: RequestDetail | null }) {
  if (!detail) return <div className="sheet-loading"><RefreshCw className="spin" /> Cargando solicitud...</div>;
  return (
    <div className="case-detail">
      <div className="case-verdict"><StatusPill value={detail.request.status} /><p>{detail.request.scenario || "Solicitud de matrícula"}</p></div>
      <div className="case-facts"><div><span>Estudiante</span><strong>{detail.student.full_name}</strong></div><div><span>Código</span><strong>{detail.student.student_code}</strong></div><div><span>Periodo</span><strong>{detail.request.period}</strong></div><div><span>Créditos</span><strong>{detail.request.credits ?? "—"}</strong></div></div>
      <h3>Agentes</h3>
      <div className="vertical-flow">{agentOrder.map((agent) => { const verdict = detail.verdicts.find((item) => item.agent === agent); const meta = agentMeta[agent]; const Icon = meta.icon; return <div key={agent} className="vertical-node"><span className={`v-icon node-${verdictTone(verdict?.status || "PENDING")}`}><Icon /></span><div><strong>{meta.label}</strong><small>{verdict?.summary || "Pendiente"}</small></div><StatusPill value={verdict?.status || "PENDING"} /></div>; })}</div>
      <h3>Mensajes entre agentes</h3>
      <div className="compact-table">{(detail.agent_messages || []).length === 0 ? <p>Sin traspasos registrados.</p> : (detail.agent_messages || []).map((m, i) => <p key={i}><strong>{m.sender} → {m.receiver}</strong> · {m.payload.status} · {m.payload.summary}</p>)}</div>
      <h3>Traza de herramientas y decisiones</h3>
      <div className="compact-table">{(detail.agent_trace || []).length === 0 ? <p>Sin traza disponible.</p> : (detail.agent_trace || []).map((e) => <p key={e.seq}><strong>#{e.seq} · {e.agent}</strong> · {e.event_type} {e.tool ? `· ${e.tool}` : ""} {e.status ? `· ${e.status}` : ""} {e.event_type === "TOOL_PLAN" && e.detail ? `· ${JSON.stringify(e.detail)}` : ""}</p>)}</div>
      <div className="admin-action-note"><Sparkles /><div><strong>Capa IA auditable</strong><span>Los veredictos guardan la fuente de la explicación. Cuando aparece GEMINI, el modelo redactó el resumen sin cambiar la regla.</span></div></div>
    </div>
  );
}

function StudentContextEditor({ token, context, onSaved }: { token: string; context: StudentContext; onSaved: () => Promise<void> }) {
  const [profile, setProfile] = useState({ current_cycle: String(context.student.current_cycle), academic_status: context.student.academic_status, max_credits: String(context.student.max_credits) });
  const [payment, setPayment] = useState({ period: "2026-II", status: context.payment?.status || "NOT_REGISTERED", amount: String(context.payment?.amount ?? 0), expected_amount: String(context.payment?.expected_amount ?? 0), outstanding_debt: String(context.payment?.outstanding_debt ?? 0) });
  const [requirements, setRequirements] = useState({ period: "2026-II", documents_complete: context.requirements?.documents_complete || false, insurance_status: context.requirements?.insurance_status || "NOT_REGISTERED", notes: context.requirements?.notes || "" });
  const [record, setRecord] = useState({ course_id: "", attempt: "1", status: "PASSED", grade: "", period: "2025-II" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true); setError(null); setMessage(null);
    try { await action(); setMessage(success); await onSaved(); }
    catch (err) { setError(err instanceof Error ? err.message : "No se pudo guardar el cambio."); }
    finally { setBusy(false); }
  }

  return (
    <div className="student-context-editor">
      <ErrorNotice message={error} />
      {message && <div className="success-notice"><CheckCircle2 />{message}</div>}
      <section className="context-block"><div className="context-title"><div><span>PERFIL</span><h3>{context.student.full_name}</h3><p>{context.student.student_code} · {context.student.email}</p></div><StatusPill value={context.student.academic_status === "ACTIVE" ? "APPROVED" : "REJECTED"} /></div>
        <div className="context-form three-cols"><div className="field"><Label>Ciclo</Label><Input type="number" min={1} max={12} value={profile.current_cycle} onChange={(e) => setProfile({ ...profile, current_cycle: e.target.value })} /></div><div className="field"><Label>Estado académico</Label><NativeSelect value={profile.academic_status} onChange={(e) => setProfile({ ...profile, academic_status: e.target.value as "ACTIVE" | "INACTIVE" })}><NativeSelectOption value="ACTIVE">Activo</NativeSelectOption><NativeSelectOption value="INACTIVE">Inactivo</NativeSelectOption></NativeSelect></div><div className="field"><Label>Máx. créditos</Label><Input type="number" value={profile.max_credits} onChange={(e) => setProfile({ ...profile, max_credits: e.target.value })} /></div></div>
        <Button variant="outline" disabled={busy} onClick={() => run(() => hypermatApi.updateStudent(token, context.student.student_code, { current_cycle: Number(profile.current_cycle), academic_status: profile.academic_status, max_credits: Number(profile.max_credits) }), "Perfil actualizado.")}><Check /> Guardar perfil</Button>
      </section>

      <section className="context-block"><div className="context-title"><div><span>FINANZAS</span><h3>Pago y deuda</h3><p>Estos datos afectan directamente el agente administrativo-financiero.</p></div></div>
        <div className="context-form"><div className="field"><Label>Estado del pago</Label><NativeSelect value={payment.status} onChange={(e) => setPayment({ ...payment, status: e.target.value })}><NativeSelectOption value="PAID">Pagado</NativeSelectOption><NativeSelectOption value="PENDING">Pendiente</NativeSelectOption><NativeSelectOption value="MISMATCH">Monto no coincide</NativeSelectOption><NativeSelectOption value="NOT_REGISTERED">Sin registrar</NativeSelectOption></NativeSelect></div><div className="field"><Label>Monto pagado</Label><Input type="number" step="0.01" value={payment.amount} onChange={(e) => setPayment({ ...payment, amount: e.target.value })} /></div><div className="field"><Label>Monto esperado</Label><Input type="number" step="0.01" value={payment.expected_amount} onChange={(e) => setPayment({ ...payment, expected_amount: e.target.value })} /></div><div className="field"><Label>Deuda pendiente</Label><Input type="number" step="0.01" value={payment.outstanding_debt} onChange={(e) => setPayment({ ...payment, outstanding_debt: e.target.value })} /></div></div>
        <Button variant="outline" disabled={busy} onClick={() => run(() => hypermatApi.updatePayment(token, context.student.student_code, { ...payment, amount: Number(payment.amount), expected_amount: Number(payment.expected_amount), outstanding_debt: Number(payment.outstanding_debt) }), "Situación financiera guardada.")}><CircleDollarSign /> Guardar finanzas</Button>
      </section>

      <section className="context-block"><div className="context-title"><div><span>REQUISITOS</span><h3>Documentación administrativa</h3></div></div>
        <div className="context-form"><label className="check-field"><Checkbox checked={requirements.documents_complete} onCheckedChange={(value) => setRequirements({ ...requirements, documents_complete: value === true })} /><span>Documentos completos</span></label><div className="field"><Label>Vigencia</Label><NativeSelect value={requirements.insurance_status} onChange={(e) => setRequirements({ ...requirements, insurance_status: e.target.value })}><NativeSelectOption value="VALID">Válido</NativeSelectOption><NativeSelectOption value="EXPIRED">Vencido</NativeSelectOption><NativeSelectOption value="PENDING">Pendiente</NativeSelectOption><NativeSelectOption value="NOT_REGISTERED">Sin registrar</NativeSelectOption></NativeSelect></div><div className="field field-wide"><Label>Observación</Label><Input value={requirements.notes} onChange={(e) => setRequirements({ ...requirements, notes: e.target.value })} /></div></div>
        <Button variant="outline" disabled={busy} onClick={() => run(() => hypermatApi.updateRequirements(token, context.student.student_code, requirements), "Requisitos guardados.")}><FileCheck2 /> Guardar requisitos</Button>
      </section>

      <section className="context-block"><div className="context-title"><div><span>HISTORIAL</span><h3>Agregar o actualizar curso</h3><p>Usa el ID de la malla (por ejemplo 54, 55, 56…).</p></div></div>
        <div className="context-form"><div className="field"><Label>Course ID</Label><Input value={record.course_id} onChange={(e) => setRecord({ ...record, course_id: e.target.value })} placeholder="54" /></div><div className="field"><Label>Estado</Label><NativeSelect value={record.status} onChange={(e) => setRecord({ ...record, status: e.target.value })}><NativeSelectOption value="PASSED">Aprobado</NativeSelectOption><NativeSelectOption value="FAILED">Desaprobado</NativeSelectOption><NativeSelectOption value="IN_PROGRESS">En curso</NativeSelectOption></NativeSelect></div><div className="field"><Label>Nota</Label><Input type="number" min={0} max={20} value={record.grade} onChange={(e) => setRecord({ ...record, grade: e.target.value })} /></div><div className="field"><Label>Periodo</Label><Input value={record.period} onChange={(e) => setRecord({ ...record, period: e.target.value })} /></div></div>
        <Button variant="outline" disabled={busy || !record.course_id} onClick={() => run(() => hypermatApi.upsertAcademicRecord(token, context.student.student_code, { course_id: record.course_id, attempt: Number(record.attempt), status: record.status, grade: record.grade === "" ? null : Number(record.grade), period: record.period }), "Historial actualizado.")}><Plus /> Guardar curso</Button>
        <div className="compact-table"><Table><TableHeader><TableRow><TableHead>Curso</TableHead><TableHead>Estado</TableHead><TableHead>Nota</TableHead><TableHead>Periodo</TableHead></TableRow></TableHeader><TableBody>{context.academic_records.length === 0 ? <TableRow><TableCell colSpan={4}>Sin historial cargado.</TableCell></TableRow> : context.academic_records.map((item) => <TableRow key={`${item.course_id}-${item.attempt}`}><TableCell>{item.course_id}</TableCell><TableCell>{item.status}</TableCell><TableCell>{item.grade ?? "—"}</TableCell><TableCell>{item.period}</TableCell></TableRow>)}</TableBody></Table></div>
      </section>
    </div>
  );
}

function AdminDashboard({ auth, onAIStatus }: { auth: AuthState; onAIStatus: (status: AIStatus) => void }) {
  const [view, setView] = useState<AdminView>("requests");
  const [requests, setRequests] = useState<EnrollmentRequest[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [selectedRequest, setSelectedRequest] = useState<RequestDetail | null>(null);
  const [requestOpen, setRequestOpen] = useState(false);
  const [selectedContext, setSelectedContext] = useState<StudentContext | null>(null);
  const [studentOpen, setStudentOpen] = useState(false);
  const [studentCodeOpen, setStudentCodeOpen] = useState<string | null>(null);
  const [newStudent, setNewStudent] = useState({ student_code: "", full_name: "", document: "", email: "", phone: "", current_cycle: "1", plan: "2019", max_credits: "22", initial_password: "" });

  async function refresh() {
    setBusy(true); setError(null);
    try {
      const [requestRows, studentRows, ai] = await Promise.all([hypermatApi.listRequests(auth.token), hypermatApi.listStudents(auth.token), hypermatApi.aiStatus(auth.token)]);
      setRequests(requestRows); setStudents(studentRows); onAIStatus(ai);
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudo actualizar el panel."); }
    finally { setBusy(false); }
  }

  useEffect(() => { refresh(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const counts = useMemo(() => ({ all: requests.length, approved: requests.filter((r) => r.status === "APPROVED").length, observed: requests.filter((r) => r.status === "OBSERVED").length, rejected: requests.filter((r) => r.status === "REJECTED").length }), [requests]);
  const filteredRequests = requests.filter((item) => (filter === "ALL" || item.status === filter) && `${item.request_id} ${item.student_code} ${item.student?.full_name || ""}`.toLowerCase().includes(query.toLowerCase()));
  const filteredStudents = students.filter((item) => `${item.full_name} ${item.student_code} ${item.email}`.toLowerCase().includes(query.toLowerCase()));

  async function openRequest(requestId: string) {
    setRequestOpen(true); setSelectedRequest(null); setError(null);
    try { setSelectedRequest(await hypermatApi.requestDetail(auth.token, requestId)); }
    catch (err) { setError(err instanceof Error ? err.message : "No se pudo cargar la solicitud."); }
  }

  async function loadStudentContext(code: string) {
    setStudentCodeOpen(code); setStudentOpen(true); setSelectedContext(null); setError(null);
    try { setSelectedContext(await hypermatApi.studentContext(auth.token, code)); }
    catch (err) { setError(err instanceof Error ? err.message : "No se pudo cargar el estudiante."); }
  }

  async function reloadOpenStudent() {
    if (!studentCodeOpen) return;
    setSelectedContext(await hypermatApi.studentContext(auth.token, studentCodeOpen));
    const rows = await hypermatApi.listStudents(auth.token);
    setStudents(rows);
  }

  async function createStudent(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null); setMessage(null);
    try {
      await hypermatApi.createStudent(auth.token, { student_code: newStudent.student_code, full_name: newStudent.full_name, document: newStudent.document, email: newStudent.email, phone: newStudent.phone, program_id: "IS", program_name: "Ingeniería de Sistemas", plan: newStudent.plan, current_cycle: Number(newStudent.current_cycle), academic_status: "ACTIVE", max_credits: Number(newStudent.max_credits), overload_authorized: false, initial_password: newStudent.initial_password || undefined });
      setMessage(`Estudiante creado. Puede ingresar con ${newStudent.email} y, si no definiste otra contraseña, con el DNI ${newStudent.document}.`);
      setNewStudent({ student_code: "", full_name: "", document: "", email: "", phone: "", current_cycle: "1", plan: "2019", max_credits: "22", initial_password: "" });
      setStudents(await hypermatApi.listStudents(auth.token));
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudo crear el estudiante."); }
    finally { setBusy(false); }
  }

  return (
    <main className="admin-shell">
      <div className="admin-title"><div><span>PERIODO 2026-II</span><h1>Administración HyperMat</h1><p>Carga datos reales y revisa cómo afectan las validaciones de matrícula.</p></div><Button variant="outline" onClick={refresh} disabled={busy}><RefreshCw className={busy ? "spin" : ""} /> Actualizar</Button></div>
      <ErrorNotice message={error} />
      {message && <div className="success-notice"><CheckCircle2 />{message}</div>}
      <div className="admin-view-switch"><button className={view === "requests" ? "active" : ""} onClick={() => setView("requests")}><Layers3 /> Solicitudes</button><button className={view === "students" ? "active" : ""} onClick={() => setView("students")}><UsersRound /> Estudiantes y datos</button></div>

      {view === "requests" && <>
        <section className="kpi-grid"><button className={filter === "ALL" ? "active" : ""} onClick={() => setFilter("ALL")}><div className="kpi-icon kpi-orange"><Layers3 /></div><div><span>Total</span><strong>{counts.all}</strong><small>solicitudes registradas</small></div></button><button className={filter === "APPROVED" ? "active" : ""} onClick={() => setFilter("APPROVED")}><div className="kpi-icon kpi-green"><CheckCircle2 /></div><div><span>Aprobadas</span><strong>{counts.approved}</strong><small>registro completado</small></div></button><button className={filter === "OBSERVED" ? "active" : ""} onClick={() => setFilter("OBSERVED")}><div className="kpi-icon kpi-amber"><AlertTriangle /></div><div><span>Observadas</span><strong>{counts.observed}</strong><small>información pendiente</small></div></button><button className={filter === "REJECTED" ? "active" : ""} onClick={() => setFilter("REJECTED")}><div className="kpi-icon kpi-red"><XCircle /></div><div><span>Rechazadas</span><strong>{counts.rejected}</strong><small>condición bloqueante</small></div></button></section>
        <section className="surface-card admin-table-card"><div className="table-toolbar"><div><h2>Solicitudes de matrícula</h2><p>{filteredRequests.length} resultados almacenados en MongoDB.</p></div><div className="admin-tools"><div className="search-box"><Search /><Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar estudiante o solicitud" /></div><NativeSelect value={filter} onChange={(e) => setFilter(e.target.value)}><NativeSelectOption value="ALL">Todos los estados</NativeSelectOption><NativeSelectOption value="APPROVED">Aprobadas</NativeSelectOption><NativeSelectOption value="OBSERVED">Observadas</NativeSelectOption><NativeSelectOption value="REJECTED">Rechazadas</NativeSelectOption><NativeSelectOption value="DRAFT">Borradores</NativeSelectOption></NativeSelect></div></div><div className="table-wrap"><Table><TableHeader><TableRow><TableHead>Solicitud</TableHead><TableHead>Estudiante</TableHead><TableHead>Periodo</TableHead><TableHead>Créditos</TableHead><TableHead>Estado</TableHead><TableHead>Actualización</TableHead><TableHead /></TableRow></TableHeader><TableBody>{filteredRequests.length === 0 ? <TableRow><TableCell colSpan={7}>No hay solicitudes para este filtro.</TableCell></TableRow> : filteredRequests.map((item) => <TableRow key={item.request_id} className="clickable-row" onClick={() => openRequest(item.request_id)}><TableCell><strong>{item.request_id}</strong></TableCell><TableCell><strong>{item.student?.full_name || item.student_code}</strong><span className="cell-sub">{item.student_code}</span></TableCell><TableCell>{item.period}</TableCell><TableCell>{item.credits ?? "—"}</TableCell><TableCell><StatusPill value={item.status} /></TableCell><TableCell>{formatDate(item.updated_at)}</TableCell><TableCell><ChevronRight /></TableCell></TableRow>)}</TableBody></Table></div></section>
      </>}

      {view === "students" && <>
        <section className="surface-card student-create-card"><div className="table-toolbar"><div><h2>Crear estudiante</h2><p>El perfil queda guardado en MongoDB. El usuario de acceso será el código universitario y el correo se usará solo para notificaciones.</p></div></div><form className="admin-create-form" onSubmit={createStudent}><div className="field"><Label>Código universitario</Label><Input value={newStudent.student_code} onChange={(e) => setNewStudent({ ...newStudent, student_code: e.target.value })} required /></div><div className="field"><Label>Nombre completo</Label><Input value={newStudent.full_name} onChange={(e) => setNewStudent({ ...newStudent, full_name: e.target.value })} required /></div><div className="field"><Label>DNI</Label><Input value={newStudent.document} onChange={(e) => setNewStudent({ ...newStudent, document: e.target.value })} required /></div><div className="field"><Label>Correo de notificación</Label><Input type="email" value={newStudent.email} onChange={(e) => setNewStudent({ ...newStudent, email: e.target.value })} required /></div><div className="field"><Label>Celular</Label><Input value={newStudent.phone} onChange={(e) => setNewStudent({ ...newStudent, phone: e.target.value })} /></div><div className="field"><Label>Ciclo</Label><Input type="number" min={1} max={12} value={newStudent.current_cycle} onChange={(e) => setNewStudent({ ...newStudent, current_cycle: e.target.value })} /></div><div className="field"><Label>Plan</Label><Input value={newStudent.plan} onChange={(e) => setNewStudent({ ...newStudent, plan: e.target.value })} /></div><div className="field"><Label>Máx. créditos</Label><Input type="number" value={newStudent.max_credits} onChange={(e) => setNewStudent({ ...newStudent, max_credits: e.target.value })} /></div><div className="field field-wide"><Label>Contraseña inicial opcional</Label><Input type="password" value={newStudent.initial_password} onChange={(e) => setNewStudent({ ...newStudent, initial_password: e.target.value })} placeholder="Déjala vacía para usar el DNI" /></div><Button className="primary-action" disabled={busy}><Plus /> Crear estudiante y cuenta</Button></form></section>
        <section className="surface-card admin-table-card"><div className="table-toolbar"><div><h2>Estudiantes</h2><p>Selecciona un alumno para cargar pagos, requisitos e historial.</p></div><div className="search-box"><Search /><Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar estudiante" /></div></div><div className="table-wrap"><Table><TableHeader><TableRow><TableHead>Código</TableHead><TableHead>Estudiante</TableHead><TableHead>Ciclo</TableHead><TableHead>Estado</TableHead><TableHead>Máx. créditos</TableHead><TableHead /></TableRow></TableHeader><TableBody>{filteredStudents.length === 0 ? <TableRow><TableCell colSpan={6}>Todavía no hay estudiantes cargados.</TableCell></TableRow> : filteredStudents.map((item) => <TableRow key={item.student_code} className="clickable-row" onClick={() => loadStudentContext(item.student_code)}><TableCell><strong>{item.student_code}</strong></TableCell><TableCell><strong>{item.full_name}</strong><span className="cell-sub">{item.email}</span></TableCell><TableCell>{item.current_cycle}.°</TableCell><TableCell>{item.academic_status}</TableCell><TableCell>{item.max_credits}</TableCell><TableCell><ChevronRight /></TableCell></TableRow>)}</TableBody></Table></div></section>
      </>}

      <Sheet open={requestOpen} onOpenChange={(open) => { setRequestOpen(open); if (!open) setSelectedRequest(null); }}><SheetContent className="case-sheet sm:max-w-[650px]"><SheetHeader><SheetTitle>{selectedRequest?.request.request_id || "Solicitud"}</SheetTitle><SheetDescription>Detalle real almacenado por HyperMat.</SheetDescription></SheetHeader><RequestDetailPanel detail={selectedRequest} /></SheetContent></Sheet>
      <Sheet open={studentOpen} onOpenChange={(open) => { setStudentOpen(open); if (!open) { setSelectedContext(null); setStudentCodeOpen(null); } }}><SheetContent className="case-sheet student-data-sheet sm:max-w-[760px]"><SheetHeader><SheetTitle>Datos del estudiante</SheetTitle><SheetDescription>Modifica el contexto que los agentes utilizarán durante la matrícula.</SheetDescription></SheetHeader>{selectedContext ? <StudentContextEditor key={`${selectedContext.student.student_code}-${selectedContext.academic_records.length}-${selectedContext.payment?.status}-${selectedContext.requirements?.insurance_status}`} token={auth.token} context={selectedContext} onSaved={reloadOpenStudent} /> : <div className="sheet-loading"><RefreshCw className="spin" /> Cargando datos...</div>}</SheetContent></Sheet>
    </main>
  );
}

export default function Home() {
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [checking, setChecking] = useState(true);
  const [aiStatus, setAIStatus] = useState<AIStatus | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("hypermat_token");
    if (!token) { setChecking(false); return; }
    hypermatApi.me(token)
      .then((user) => setAuth({ token, user }))
      .catch(() => localStorage.removeItem("hypermat_token"))
      .finally(() => setChecking(false));
  }, []);

  async function logout() {
    if (auth) {
      try { await hypermatApi.logout(auth.token); } catch {}
    }
    localStorage.removeItem("hypermat_token");
    setAuth(null); setAIStatus(null);
  }

  if (checking) return <main className="boot-screen"><div className="brand-mark"><GraduationCap /></div><RefreshCw className="spin" /><span>Conectando con HyperMat...</span></main>;
  if (!auth) return <LoginPage onAuthenticated={(next) => { setAuth(next); setChecking(false); }} />;

  return (
    <div className="site-root">
      <AppHeader auth={auth} aiStatus={aiStatus} onLogout={logout} />
      {auth.user.role === "ADMIN" ? <AdminDashboard auth={auth} onAIStatus={setAIStatus} /> : <StudentPortal auth={auth} onAIStatus={setAIStatus} />}
    </div>
  );
}
