export type Verdict = "APROBADO" | "OBSERVADO" | "RECHAZADO" | "PENDIENTE" | "EJECUTADO";
export type Course = { id: string; code: string; name: string; cycle: number; credits: number; section: string; schedule: string; capacity: number; enrolled: number; eligible: boolean; reason?: string };
export type AgentStep = { id: "coordinator" | "academic" | "financial" | "executor" | "rpa"; label: string; role: string; verdict: Verdict; summary: string; checks: string[]; at: string };
export type EnrollmentCase = { id: string; studentCode: string; student: string; email: string; cycle: number; period: string; credits: number; status: "APROBADA" | "OBSERVADA" | "RECHAZADA" | "EN PROCESO"; scenario: string; updatedAt: string; steps: AgentStep[] };

export const courses: Course[] = [
  { id: "60", code: "101543", name: "Taller de Tesis II", cycle: 9, credits: 3, section: "A", schedule: "Lun 18:00–20:15", capacity: 35, enrolled: 24, eligible: true },
  { id: "61", code: "101544", name: "Evaluación de Proyectos de TI", cycle: 9, credits: 3, section: "A", schedule: "Mar 18:00–20:15", capacity: 35, enrolled: 31, eligible: true },
  { id: "62", code: "101545", name: "Tópicos Especiales de Big Data", cycle: 9, credits: 3, section: "C", schedule: "Mié 18:00–20:15", capacity: 30, enrolled: 30, eligible: false, reason: "La sección C alcanzó su capacidad máxima." },
  { id: "63", code: "101546", name: "Arquitectura Empresarial", cycle: 9, credits: 2, section: "A", schedule: "Jue 18:00–19:30", capacity: 40, enrolled: 28, eligible: true },
  { id: "64", code: "101547", name: "Ciberseguridad", cycle: 9, credits: 3, section: "A", schedule: "Vie 18:00–20:15", capacity: 35, enrolled: 29, eligible: true },
  { id: "65", code: "101548", name: "Prácticas Preprofesionales I", cycle: 9, credits: 4, section: "C", schedule: "Sáb 08:00–11:00", capacity: 45, enrolled: 33, eligible: true },
  { id: "66", code: "101549", name: "Auditoría de Sistemas de Información", cycle: 10, credits: 3, section: "A", schedule: "Lun 20:15–22:30", capacity: 35, enrolled: 27, eligible: false, reason: "Requiere Ciberseguridad (64) aprobada." },
  { id: "67", code: "101550", name: "Gerencia de Proyectos de TI", cycle: 10, credits: 4, section: "A", schedule: "Mar 20:15–22:30", capacity: 35, enrolled: 22, eligible: true },
  { id: "68", code: "101551", name: "Fundamentos de Business Analytics", cycle: 10, credits: 3, section: "A", schedule: "Mié 20:15–22:30", capacity: 35, enrolled: 26, eligible: true },
  { id: "69", code: "101552", name: "Tecnologías Emergentes e Innovación Tecnológica", cycle: 10, credits: 3, section: "C", schedule: "Jue 20:15–22:30", capacity: 35, enrolled: 34, eligible: true },
  { id: "70", code: "101553", name: "Prácticas Preprofesionales II", cycle: 10, credits: 4, section: "A", schedule: "Sáb 08:00–11:00", capacity: 30, enrolled: 18, eligible: false, reason: "Requiere Prácticas Preprofesionales I (65) aprobada." },
  { id: "71", code: "105207", name: "Trabajo de Investigación", cycle: 10, credits: 3, section: "B", schedule: "Vie 20:15–22:30", capacity: 35, enrolled: 19, eligible: false, reason: "Requiere Taller de Tesis II (60) aprobada." },
];

export const studentSteps: AgentStep[] = [
  { id: "coordinator", label: "Coordinador", role: "Orquesta la solicitud", verdict: "APROBADO", summary: "Identidad, periodo y solicitud consistentes.", checks: ["Código activo", "Periodo 2026-II abierto", "Solicitud no duplicada"], at: "14:31:08" },
  { id: "academic", label: "Académico", role: "Valida historial y cursos", verdict: "OBSERVADO", summary: "8 cursos habilitados y 4 bloqueados por reglas académicas.", checks: ["Prerrequisitos consultados en la malla 2019", "Créditos máximos: 22", "Una sección sin vacantes"], at: "14:31:10" },
  { id: "financial", label: "Admin-financiero", role: "Revisa pagos y documentos", verdict: "APROBADO", summary: "Pago conciliado, sin deuda y documentos vigentes.", checks: ["Pago S/ 450.00 confirmado", "Deuda S/ 0.00", "Documentos vigentes"], at: "14:31:12" },
  { id: "executor", label: "Ejecutor", role: "Registra la matrícula", verdict: "PENDIENTE", summary: "Esperando la selección final de cursos.", checks: ["Registro SIS pendiente", "Control de vacantes al confirmar", "Reserva temporal: 10 min"], at: "—" },
  { id: "rpa", label: "RPA", role: "Genera constancia y notifica", verdict: "PENDIENTE", summary: "Se activa después del registro académico.", checks: ["Constancia PDF", "Correo de resultado", "Trazabilidad de entrega"], at: "—" },
];

const caseRows: Array<[string,string,string,number,EnrollmentCase["status"],string,number]> = [
  ["MAT-260901","Andrea Salazar Núñez","2020011042",22,"APROBADA","Matrícula regular sin observaciones",7],
  ["MAT-260902","Bruno Campos Rojas","2021023703",18,"OBSERVADA","Un curso bloqueado por prerrequisito",6],
  ["MAT-260903","Camila Torres Vega","2021012251",20,"RECHAZADA","Deuda pendiente de S/ 320.00",8],
  ["MAT-260904","Diego Mendoza Ruiz","2022011824",16,"OBSERVADA","Pago aún no conciliado",6],
  ["MAT-260905","Elena Paredes Soto","2020011718",19,"OBSERVADA","Sección seleccionada sin vacantes",9],
  ["MAT-260906","Fabio Huamán León","2021021487",25,"RECHAZADA","Excede el máximo de 22 créditos",8],
  ["MAT-260907","Gabriela Chávez Díaz","2020011935",17,"OBSERVADA","Cruce de horarios en dos asignaturas",9],
  ["MAT-260908","Hugo Ramírez Peña","2022021048",18,"OBSERVADA","Documento administrativo vencido",6],
  ["MAT-260909","Ivana Flores Castro","2019011632",0,"RECHAZADA","Estado académico inactivo",10],
  ["MAT-260910","Javier Ortiz Silva","2020021981",15,"OBSERVADA","Curso ya aprobado en periodo previo",7],
  ["MAT-260911","Karen Vilca Ríos","2021011405",18,"APROBADA","Repitencia autorizada dentro del límite",7],
  ["MAT-260912","Luis Quispe Molina","2022021176",0,"OBSERVADA","No hay sección disponible para un curso obligatorio",6],
  ["MAT-260913","María Cárdenas Paz","2020011564",22,"APROBADA","Carga completa de 22 créditos",9],
  ["MAT-260914","Nicolás Guerra Luna","2019011243",26,"APROBADA","Sobrecarga autorizada por resolución",10],
  ["MAT-260915","Olivia Vásquez Mora","2021021659",18,"OBSERVADA","Monto pagado no coincide con la orden",7],
  ["MAT-260916","Paolo Medina Cruz","2020011877",12,"RECHAZADA","Plan curricular no coincide con la solicitud",8],
  ["MAT-260917","Renata López Rey","2022021320",14,"OBSERVADA","Prerrequisito aún en curso",6],
  ["MAT-260918","Sergio Núñez Alba","2021011788",17,"OBSERVADA","Una observación; cinco cursos habilitados",7],
  ["MAT-260919","Tamara Rojas Gil","2020011196",20,"EN PROCESO","Registro RPA requiere reintento",9],
  ["MAT-260920","Víctor Espinoza Mar","2021011511",19,"APROBADA","Matrícula registrada; correo pendiente de reenvío",8],
];

function stepsFor(status: EnrollmentCase["status"], scenario: string): AgentStep[] {
  const steps = studentSteps.map((step) => ({ ...step, checks: [...step.checks] }));
  if (status === "APROBADA") {
    steps[1].verdict = "APROBADO"; steps[1].summary = "Cursos, prerrequisitos, créditos y horarios conformes.";
    steps[3].verdict = "EJECUTADO"; steps[3].summary = "Matrícula registrada en el sistema académico."; steps[3].at = "14:31:18";
    steps[4].verdict = scenario.includes("correo pendiente") ? "OBSERVADO" : "EJECUTADO"; steps[4].summary = scenario.includes("correo pendiente") ? "Constancia generada; correo en cola de reenvío." : "Constancia PDF y correo enviados correctamente."; steps[4].at = "14:31:22";
  } else if (status === "RECHAZADA") {
    const idx = /deuda|pago|monto/i.test(scenario) ? 2 : 1; steps[idx].verdict = "RECHAZADO"; steps[idx].summary = scenario;
    steps[3].summary = "No ejecutado por una regla bloqueante."; steps[4].verdict = "EJECUTADO"; steps[4].summary = "Correo de rechazo enviado con el motivo y la acción requerida."; steps[4].at = "14:31:18";
  } else if (status === "EN PROCESO") {
    steps[1].verdict = "APROBADO"; steps[3].verdict = "EJECUTADO"; steps[3].summary = "Matrícula registrada; falta cerrar la automatización documental."; steps[4].verdict = "OBSERVADO"; steps[4].summary = scenario;
  } else {
    const idx = /pago|monto|deuda|documento/i.test(scenario) ? 2 : 1; steps[idx].verdict = "OBSERVADO"; steps[idx].summary = scenario;
    steps[3].summary = "En pausa hasta levantar la observación."; steps[4].verdict = "EJECUTADO"; steps[4].summary = "Correo de observación enviado con el detalle del caso."; steps[4].at = "14:31:18";
  }
  return steps;
}

export const enrollmentCases: EnrollmentCase[] = caseRows.map(([id,student,studentCode,credits,status,scenario,cycle],index) => ({
  id, student, studentCode, email: `${student.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").split(" ")[0]}.${studentCode}@alumno.unfv.demo`, cycle, period: "2026-II", credits, status, scenario,
  updatedAt: `20/09/2026 ${String(9 + Math.floor(index / 4)).padStart(2,"0")}:${String((index * 7) % 60).padStart(2,"0")}`,
  steps: stepsFor(status, scenario),
}));

export const studentProfile = { code: "2021023703", names: "Juan José Balcázar Vega", document: "72845196", email: "2021023703@unfv.edu.pe", phone: "987 654 321", program: "Ingeniería de Sistemas", plan: "2019", cycle: 9, period: "2026-II", maxCredits: 22 };

