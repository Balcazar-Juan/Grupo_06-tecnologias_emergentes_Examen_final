export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export type UserRole = "STUDENT" | "ADMIN";
export type SessionUser = { email: string; role: UserRole; student_code?: string | null; full_name: string };
export type LoginResponse = { token: string; user: SessionUser };

export type Student = {
  _id?: string;
  student_code: string;
  full_name: string;
  document?: string;
  email: string;
  phone?: string;
  program_id: string;
  program_name?: string;
  plan: string;
  current_cycle: number;
  academic_status: "ACTIVE" | "INACTIVE";
  max_credits: number;
  overload_authorized?: boolean;
};

export type ValidationMessage = { code: string; severity: "INFO" | "OBSERVATION" | "BLOCKER"; message: string };
export type EligibleCourse = {
  course_id: string;
  code: string;
  name: string;
  cycle: number;
  credits: number;
  prerequisites: string[];
  section_id?: string | null;
  section?: string | null;
  schedule?: string | null;
  capacity: number;
  enrolled: number;
  eligible: boolean;
  messages: ValidationMessage[];
};

export type AgentName = "coordinator" | "academic" | "financial" | "executor" | "rpa";
export type AgentStatus = "APPROVED" | "OBSERVED" | "REJECTED" | "PENDING" | "EXECUTED";
export type AgentVerdict = {
  request_id: string;
  agent: AgentName;
  status: AgentStatus;
  summary: string;
  deterministic_summary?: string;
  evidence?: string[];
  explanation_source?: "GEMINI" | "RULES" | "RULES_FALLBACK" | "DEMO" | string;
  model?: string | null;
  created_at?: string;
};

export type EnrollmentRequest = {
  request_id: string;
  student_code: string;
  period: string;
  program_id: string;
  selected_section_ids?: string[];
  status: "DRAFT" | "APPROVED" | "OBSERVED" | "REJECTED" | "IN_PROGRESS" | string;
  scenario?: string;
  credits?: number;
  created_at?: string;
  updated_at?: string;
  student?: { full_name?: string; email?: string; current_cycle?: number };
};

export type RequestDetail = {
  request: EnrollmentRequest;
  student: Student;
  verdicts: AgentVerdict[];
  audit: Array<{ event_type: string; actor?: string; created_at?: string }>;
  notification?: { status?: string; recipient?: string; subject?: string } | null;
  enrollment?: { status?: string; credits?: number; selected_section_ids?: string[] } | null;
  agent_trace?: Array<{ seq: number; agent: string; event_type: string; tool?: string | null; status?: string | null; detail?: unknown }>;
  agent_messages?: Array<{ sender: string; receiver: string; payload: { status: string; summary: string } }>;
};

export type Payment = {
  student_code: string;
  period: string;
  status: "PAID" | "PENDING" | "MISMATCH" | "NOT_REGISTERED";
  amount: number;
  expected_amount: number;
  outstanding_debt: number;
};

export type Requirements = {
  student_code: string;
  period: string;
  documents_complete: boolean;
  insurance_status: "VALID" | "EXPIRED" | "PENDING" | "NOT_REGISTERED";
  notes?: string;
};

export type AcademicRecord = {
  student_code: string;
  course_id: string;
  attempt: number;
  status: "PASSED" | "FAILED" | "IN_PROGRESS";
  grade?: number | null;
  period: string;
};

export type StudentContext = {
  student: Student;
  payment: Payment | null;
  requirements: Requirements | null;
  academic_records: AcademicRecord[];
  requests: EnrollmentRequest[];
};

export type AIStatus = { configured: boolean; model: string; role: string };

function detailText(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => (typeof item === "object" && item && "msg" in item ? String((item as { msg: unknown }).msg) : String(item))).join(" · ");
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return "Ocurrió un error al comunicarse con HyperMat.";
}

export async function apiFetch<T>(path: string, options: RequestInit = {}, token?: string | null): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, cache: "no-store" });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = detailText(body.detail ?? body);
    } catch {
      // Mantiene el texto HTTP si la respuesta no es JSON.
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const hypermatApi = {
  setupStatus: () => apiFetch<{ admin_exists: boolean }>("/api/auth/setup-status"),
  bootstrapAdmin: (payload: { full_name: string; email: string; password: string }) =>
    apiFetch<{ created: boolean; email: string; role: "ADMIN" }>("/api/auth/bootstrap-admin", { method: "POST", body: JSON.stringify(payload) }),
  login: (username: string, password: string) =>
    apiFetch<LoginResponse>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: (token: string) => apiFetch<SessionUser>("/api/auth/me", {}, token),
  logout: (token: string) => apiFetch<{ ok: boolean }>("/api/auth/logout", { method: "POST" }, token),
  aiStatus: (token: string) => apiFetch<AIStatus>("/api/ai/status", {}, token),

  myStudent: (token: string) => apiFetch<Student>("/api/me/student", {}, token),
  eligibleCourses: (token: string, period = "2026-II") => apiFetch<EligibleCourse[]>(`/api/me/eligible-courses?period=${encodeURIComponent(period)}`, {}, token),
  myRequests: (token: string) => apiFetch<EnrollmentRequest[]>("/api/me/enrollment-requests", {}, token),
  createRequest: (token: string, payload: { period: string; selected_section_ids?: string[]; student_code?: string }) =>
    apiFetch<EnrollmentRequest>("/api/enrollment-requests", { method: "POST", body: JSON.stringify(payload) }, token),
  validateRequest: (token: string, requestId: string) =>
    apiFetch<{ request_id: string; status: string; credits: number; verdicts: AgentVerdict[] }>(`/api/enrollment-requests/${requestId}/validate`, { method: "POST" }, token),
  confirmRequest: (token: string, requestId: string, selected_section_ids: string[]) =>
    apiFetch<{ request_id: string; status: string; credits: number; verdicts: AgentVerdict[] }>(`/api/enrollment-requests/${requestId}/confirm`, { method: "POST", body: JSON.stringify({ selected_section_ids }) }, token),
  requestDetail: (token: string, requestId: string) => apiFetch<RequestDetail>(`/api/enrollment-requests/${requestId}`, {}, token),
  agentTrace: (token: string, requestId: string) => apiFetch<{ run: unknown; events: RequestDetail["agent_trace"]; messages: RequestDetail["agent_messages"] }>(`/api/enrollment-requests/${requestId}/trace`, {}, token),
  listRequests: (token: string) => apiFetch<EnrollmentRequest[]>("/api/enrollment-requests", {}, token),

  listStudents: (token: string, query = "") => apiFetch<Student[]>(`/api/admin/students?query=${encodeURIComponent(query)}`, {}, token),
  createStudent: (token: string, payload: Record<string, unknown>) => apiFetch<{ student: Student; login: { email: string; password_policy: string } }>("/api/admin/students", { method: "POST", body: JSON.stringify(payload) }, token),
  updateStudent: (token: string, studentCode: string, payload: Record<string, unknown>) => apiFetch<Student>(`/api/admin/students/${studentCode}`, { method: "PUT", body: JSON.stringify(payload) }, token),
  studentContext: (token: string, studentCode: string, period = "2026-II") => apiFetch<StudentContext>(`/api/admin/students/${studentCode}/context?period=${encodeURIComponent(period)}`, {}, token),
  updatePayment: (token: string, studentCode: string, payload: Record<string, unknown>) => apiFetch<Payment>(`/api/admin/students/${studentCode}/payment`, { method: "PUT", body: JSON.stringify(payload) }, token),
  updateRequirements: (token: string, studentCode: string, payload: Record<string, unknown>) => apiFetch<Requirements>(`/api/admin/students/${studentCode}/requirements`, { method: "PUT", body: JSON.stringify(payload) }, token),
  upsertAcademicRecord: (token: string, studentCode: string, payload: Record<string, unknown>) => apiFetch<AcademicRecord>(`/api/admin/students/${studentCode}/academic-records`, { method: "POST", body: JSON.stringify(payload) }, token),
};

export async function openCertificate(token: string, requestId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/enrollment-requests/${requestId}/certificate`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) {
    let message = "No se pudo abrir la constancia.";
    try {
      const body = await response.json();
      message = detailText(body.detail ?? body);
    } catch {}
    throw new Error(message);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener,noreferrer");
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
