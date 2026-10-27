from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.auth import hash_password  # noqa: E402
from app.db import get_db  # noqa: E402

DATA = ROOT / "data"
PERIOD = "2026-II"
NOTIFICATION_EMAIL = "2021023703@unfv.edu.pe"

COLLECTIONS = {
    "programs": {"required": ["program_id", "name", "plan"]},
    "courses": {"required": ["course_id", "code", "name", "cycle", "credits", "prerequisites"]},
    "sections": {"required": ["section_id", "course_id", "period", "capacity", "enrolled"]},
    "students": {"required": ["student_code", "full_name", "program_id", "plan", "academic_status"]},
    "accounts": {"required": ["username", "role", "status"]},
    "sessions": {"required": ["token_hash", "account_username", "role", "expires_at"]},
    "academic_records": {"required": ["student_code", "course_id", "status"]},
    "payments": {"required": ["student_code", "period", "status", "amount"]},
    "administrative_requirements": {"required": ["student_code", "period", "documents_complete"]},
    "enrollment_requests": {"required": ["request_id", "student_code", "period", "status", "scenario"]},
    "agent_verdicts": {"required": ["request_id", "agent", "status", "summary"]},
    "enrollments": {"required": ["request_id", "student_code", "period", "status"]},
    "notifications": {"required": ["request_id", "channel", "status", "recipient"]},
    "automation_runs": {"required": ["request_id", "automation", "status"]},
    "audit_events": {"required": ["request_id", "event_type", "created_at"]},
    "agent_traces": {"required": ["run_id", "request_id", "seq", "agent", "event_type", "created_at"]},
    "agent_messages": {"required": ["run_id", "request_id", "sender", "receiver", "created_at"]},
    "orchestration_runs": {"required": ["run_id", "request_id", "status", "started_at"]},
}

# students.email NO es único: en pruebas todos reciben notificaciones en el mismo buzón.
INDEXES = {
    "programs": [("program_id", True)],
    "courses": [("course_id", True), ("code", True), ("cycle", False)],
    "sections": [("section_id", True), (("course_id", "period", "section"), True)],
    "students": [("student_code", True), ("email", False)],
    "accounts": [("username", True), ("student_code", True)],
    "sessions": [("token_hash", True), ("expires_at", False)],
    "academic_records": [(("student_code", "course_id", "attempt"), True)],
    "payments": [(("student_code", "period"), True)],
    "administrative_requirements": [(("student_code", "period"), True)],
    "enrollment_requests": [("request_id", True), (("student_code", "period"), False), ("status", False)],
    "agent_verdicts": [(("request_id", "agent"), True)],
    "enrollments": [("request_id", True), (("student_code", "period"), True)],
    "notifications": [(("request_id", "channel"), True)],
    "automation_runs": [(("request_id", "automation"), True)],
    "audit_events": [("request_id", False), ("created_at", False)],
    "agent_traces": [("run_id", False), (("request_id", "seq"), False)],
    "agent_messages": [("run_id", False), ("request_id", False)],
    "orchestration_runs": [("run_id", True), ("request_id", False)],
}

# Estas 10 filas son PRECONDICIONES. No se siembran solicitudes ni veredictos.
# El resultado debe aparecer recién cuando el alumno usa el aplicativo.
TEST_CASES = [{'case_id': 'C01', 'student_code': '2021023703', 'full_name': 'Alumno Prueba Principal', 'document': '70000001', 'phone': '900000001', 'scenario': 'Matrícula regular', 'academic_status': 'ACTIVE', 'payment': {'status': 'PAID', 'amount': 450, 'expected_amount': 450, 'outstanding_debt': 0}, 'requirements': {'documents_complete': True, 'insurance_status': 'VALID', 'notes': 'Datos de prueba controlados'}, 'recommended_sections': ['2026-II-60-A', '2026-II-61-A', '2026-II-63-A', '2026-II-64-A'], 'expected_final_status': 'APPROVED', 'expected_agent': 'rpa', 'expected_reason': 'Registro completo; constancia habilitada', 'remove_passed_courses': [], 'ui_note': '', 'remediation_required': False}, {'case_id': 'C02', 'student_code': '2099000002', 'full_name': 'Ana Torres Vega', 'document': '70000002', 'phone': '900000002', 'scenario': 'Estado académico inactivo', 'academic_status': 'INACTIVE', 'payment': {'status': 'PAID', 'amount': 450, 'expected_amount': 450, 'outstanding_debt': 0}, 'requirements': {'documents_complete': True, 'insurance_status': 'VALID', 'notes': 'Datos de prueba controlados'}, 'recommended_sections': ['2026-II-60-A', '2026-II-61-A'], 'expected_final_status': 'REJECTED', 'expected_agent': 'coordinator', 'expected_reason': 'INACTIVE: no se delega a Académico', 'remove_passed_courses': [], 'ui_note': '', 'remediation_required': False}, {'case_id': 'C03', 'student_code': '2099000003', 'full_name': 'Bruno Salazar Rojas', 'document': '70000003', 'phone': '900000003', 'scenario': 'Cruce de horarios', 'academic_status': 'ACTIVE', 'payment': {'status': 'PAID', 'amount': 450, 'expected_amount': 450, 'outstanding_debt': 0}, 'requirements': {'documents_complete': True, 'insurance_status': 'VALID', 'notes': 'Datos de prueba controlados'}, 'recommended_sections': ['2026-II-63-A', '2026-II-69-A'], 'expected_final_status': 'REJECTED', 'expected_agent': 'academic', 'expected_reason': 'Dos secciones sábado 08:00-11:00', 'remove_passed_courses': [], 'ui_note': '', 'remediation_required': False}, {'case_id': 'C04', 'student_code': '2099000004', 'full_name': 'Camila Mendoza Ruiz', 'document': '70000004', 'phone': '900000004', 'scenario': 'Prerrequisito no aprobado', 'academic_status': 'ACTIVE', 'payment': {'status': 'PAID', 'amount': 450, 'expected_amount': 450, 'outstanding_debt': 0}, 'requirements': {'documents_complete': True, 'insurance_status': 'VALID', 'notes': 'Datos de prueba controlados'}, 'recommended_sections': ['2026-II-60-A'], 'expected_final_status': 'REJECTED', 'expected_agent': 'academic', 'expected_reason': 'Falta curso 54, no seleccionar desde UI / forzar API de validación', 'remove_passed_courses': ['54'], 'ui_note': 'Curso bloqueado desde UI; validar defensa backend con un request autorizado de prueba.', 'remediation_required': False}, {'case_id': 'C05', 'student_code': '2099000005', 'full_name': 'Diego Paredes Soto', 'document': '70000005', 'phone': '900000005', 'scenario': 'Deuda pendiente bloqueante', 'academic_status': 'ACTIVE', 'payment': {'status': 'PAID', 'amount': 450, 'expected_amount': 450, 'outstanding_debt': 320}, 'requirements': {'documents_complete': True, 'insurance_status': 'VALID', 'notes': 'Datos de prueba controlados'}, 'recommended_sections': ['2026-II-60-A', '2026-II-61-A'], 'expected_final_status': 'REJECTED', 'expected_agent': 'financial', 'expected_reason': 'Deuda S/ 320; no se delega al Ejecutor', 'remove_passed_courses': [], 'ui_note': '', 'remediation_required': False}, {'case_id': 'C06', 'student_code': '2099000006', 'full_name': 'Elena Huamán León', 'document': '70000006', 'phone': '900000006', 'scenario': 'Pago pendiente conciliación', 'academic_status': 'ACTIVE', 'payment': {'status': 'PENDING', 'amount': 450, 'expected_amount': 450, 'outstanding_debt': 0}, 'requirements': {'documents_complete': True, 'insurance_status': 'VALID', 'notes': 'Datos de prueba controlados'}, 'recommended_sections': ['2026-II-60-A', '2026-II-61-A'], 'expected_final_status': 'OBSERVED', 'expected_agent': 'financial', 'expected_reason': 'Admin regulariza a PAID y estudiante revalida', 'remove_passed_courses': [], 'ui_note': '', 'remediation_required': True}, {'case_id': 'C07', 'student_code': '2099000007', 'full_name': 'Fabio Chávez Díaz', 'document': '70000007', 'phone': '900000007', 'scenario': 'Monto pagado distinto', 'academic_status': 'ACTIVE', 'payment': {'status': 'MISMATCH', 'amount': 130, 'expected_amount': 450, 'outstanding_debt': 0}, 'requirements': {'documents_complete': True, 'insurance_status': 'VALID', 'notes': 'Datos de prueba controlados'}, 'recommended_sections': ['2026-II-60-A', '2026-II-61-A'], 'expected_final_status': 'OBSERVED', 'expected_agent': 'financial', 'expected_reason': 'Admin corrige monto y estado, luego revalidar', 'remove_passed_courses': [], 'ui_note': '', 'remediation_required': True}, {'case_id': 'C08', 'student_code': '2099000008', 'full_name': 'Gabriela Ramírez Peña', 'document': '70000008', 'phone': '900000008', 'scenario': 'Documento vencido', 'academic_status': 'ACTIVE', 'payment': {'status': 'PAID', 'amount': 450, 'expected_amount': 450, 'outstanding_debt': 0}, 'requirements': {'documents_complete': True, 'insurance_status': 'EXPIRED', 'notes': 'Datos de prueba controlados'}, 'recommended_sections': ['2026-II-60-A', '2026-II-61-A'], 'expected_final_status': 'OBSERVED', 'expected_agent': 'financial', 'expected_reason': 'Admin regulariza vigencia y revalidar', 'remove_passed_courses': [], 'ui_note': '', 'remediation_required': True}, {'case_id': 'C09', 'student_code': '2099000009', 'full_name': 'Hugo Flores Castro', 'document': '70000009', 'phone': '900000009', 'scenario': 'Sección sin vacantes', 'academic_status': 'ACTIVE', 'payment': {'status': 'PAID', 'amount': 450, 'expected_amount': 450, 'outstanding_debt': 0}, 'requirements': {'documents_complete': True, 'insurance_status': 'VALID', 'notes': 'Datos de prueba controlados'}, 'recommended_sections': ['2026-II-62-A'], 'expected_final_status': 'REJECTED', 'expected_agent': 'academic', 'expected_reason': 'Sección 62 está FULL; UI la muestra bloqueada', 'remove_passed_courses': [], 'ui_note': 'Curso bloqueado desde UI; validar defensa backend con un request autorizado de prueba.', 'remediation_required': False}, {'case_id': 'C10', 'student_code': '2099000010', 'full_name': 'Ivana Ortiz Silva', 'document': '70000010', 'phone': '900000010', 'scenario': 'Requisitos sin expediente', 'academic_status': 'ACTIVE', 'payment': {'status': 'PAID', 'amount': 450, 'expected_amount': 450, 'outstanding_debt': 0}, 'requirements': None, 'recommended_sections': ['2026-II-60-A', '2026-II-61-A'], 'expected_final_status': 'OBSERVED', 'expected_agent': 'financial', 'expected_reason': 'Admin registra requisitos y revalida', 'remove_passed_courses': [], 'ui_note': '', 'remediation_required': True}]


def ensure_collections(db) -> None:
    existing = set(db.list_collection_names())
    for name, definition in COLLECTIONS.items():
        validator = {"$jsonSchema": {"bsonType": "object", "required": definition["required"]}}
        if name not in existing:
            db.create_collection(name, validator=validator, validationLevel="moderate")
        else:
            db.command("collMod", name, validator=validator, validationLevel="moderate")

    # Versiones anteriores tenían students.email como índice UNIQUE. Se elimina para
    # permitir que varios alumnos de prueba compartan un único buzón de notificación.
    student_indexes = db.students.index_information()
    email_index = student_indexes.get("email_1")
    if email_index and email_index.get("unique"):
        db.students.drop_index("email_1")

    for collection, indexes in INDEXES.items():
        for fields, unique in indexes:
            keys = [(field, 1) for field in fields] if isinstance(fields, tuple) else [(fields, 1)]
            try:
                db[collection].create_index(keys, unique=unique)
            except Exception as exc:
                # Si existe un índice con mismo nombre y distinta configuración, se recrea.
                index_name = "_".join(f"{field}_1" for field, _ in keys)
                info = db[collection].index_information().get(index_name)
                if info is not None:
                    db[collection].drop_index(index_name)
                    db[collection].create_index(keys, unique=unique)
                else:
                    raise exc


def upsert_many(collection, documents: list[dict], key: str | tuple[str, ...]) -> None:
    for document in documents:
        query = {field: document[field] for field in key} if isinstance(key, tuple) else {key: document[key]}
        collection.update_one(query, {"$set": document}, upsert=True)


def seed_catalog(db) -> list[dict]:
    raw_courses = json.loads((DATA / "curriculum_2019.json").read_text(encoding="utf-8"))
    courses = [
        {
            "course_id": course["id"],
            "code": course["code"],
            "name": course["name"],
            "cycle": course["cycle"],
            "credits": course["credits"],
            "prerequisites": course.get("prerequisites", []),
            "program_id": "IS",
            "plan": "2019",
            "active": True,
        }
        for course in raw_courses
    ]
    upsert_many(
        db.programs,
        [
            {
                "program_id": "IS",
                "name": "Ingeniería de Sistemas",
                "faculty": "Facultad de Ingeniería Industrial y de Sistemas",
                "plan": "2019",
                "max_regular_credits": 22,
                "active": True,
            }
        ],
        "program_id",
    )
    upsert_many(db.courses, courses, "course_id")

    schedules = [
        "Lun 18:00-20:15",
        "Mar 18:00-20:15",
        "Mié 18:00-20:15",
        "Jue 18:00-20:15",
        "Vie 18:00-20:15",
        "Sáb 08:00-11:00",
    ]
    sections = []
    for index, course in enumerate(courses):
        enrolled = 30 if course["course_id"] == "62" else 18 + index % 16
        capacity = 30 if course["course_id"] == "62" else 35
        sections.append(
            {
                "section_id": f"{PERIOD}-{course['course_id']}-A",
                "course_id": course["course_id"],
                "period": PERIOD,
                "section": "A",
                "schedule": schedules[index % len(schedules)],
                "capacity": capacity,
                "enrolled": enrolled,
                "status": "OPEN" if enrolled < capacity else "FULL",
            }
        )
    # Horarios controlados: C01 no cruza; C03 sí; C09 usa sección llena.
    fixed = {"60": "Mié 18:00-20:15", "61": "Jue 18:00-20:15",
             "62": "Vie 18:00-20:15", "63": "Sáb 08:00-11:00",
             "64": "Lun 18:00-20:15", "69": "Sáb 08:00-11:00"}
    for section in sections:
        if section["course_id"] in fixed:
            section["schedule"] = fixed[section["course_id"]]
    upsert_many(db.sections, sections, "section_id")
    return courses


def _clear_existing_test_context(db, student_codes: list[str]) -> None:
    db.students.delete_many({"student_code": {"$in": student_codes}})
    db.accounts.delete_many({"student_code": {"$in": student_codes}})
    db.academic_records.delete_many({"student_code": {"$in": student_codes}})
    db.payments.delete_many({"student_code": {"$in": student_codes}, "period": PERIOD})
    db.administrative_requirements.delete_many({"student_code": {"$in": student_codes}, "period": PERIOD})
    db.sessions.delete_many({"account_username": {"$in": student_codes}})


def reset_test_flow(db, student_codes: list[str]) -> dict:
    request_ids = [
        row["request_id"]
        for row in db.enrollment_requests.find({"student_code": {"$in": student_codes}}, {"request_id": 1})
    ]
    deleted = {}
    if request_ids:
        deleted["agent_verdicts"] = db.agent_verdicts.delete_many({"request_id": {"$in": request_ids}}).deleted_count
        deleted["enrollments"] = db.enrollments.delete_many({"request_id": {"$in": request_ids}}).deleted_count
        deleted["notifications"] = db.notifications.delete_many({"request_id": {"$in": request_ids}}).deleted_count
        deleted["automation_runs"] = db.automation_runs.delete_many({"request_id": {"$in": request_ids}}).deleted_count
        deleted["audit_events"] = db.audit_events.delete_many({"request_id": {"$in": request_ids}}).deleted_count
        deleted["agent_traces"] = db.agent_traces.delete_many({"request_id": {"$in": request_ids}}).deleted_count
        deleted["agent_messages"] = db.agent_messages.delete_many({"request_id": {"$in": request_ids}}).deleted_count
        deleted["orchestration_runs"] = db.orchestration_runs.delete_many({"request_id": {"$in": request_ids}}).deleted_count
    deleted["enrollment_requests"] = db.enrollment_requests.delete_many({"student_code": {"$in": student_codes}}).deleted_count
    return deleted


def seed_test_students(db, courses: list[dict], reset_context: bool = False) -> dict:
    now = datetime.now(UTC)
    codes = [case["student_code"] for case in TEST_CASES]
    if reset_context:
        _clear_existing_test_context(db, codes)

    students: list[dict] = []
    accounts: list[dict] = []
    records: list[dict] = []
    payments: list[dict] = []
    requirements: list[dict] = []

    # Base común: todos los cursos de ciclos 1-8 aprobados. Así las asignaturas de
    # ciclo 9 usadas en las pruebas quedan habilitadas por prerrequisito.
    base_passed = [course for course in courses if int(course["cycle"]) < 9]
    period_by_cycle = {
        1: "2022-I", 2: "2022-II", 3: "2023-I", 4: "2023-II",
        5: "2024-I", 6: "2024-II", 7: "2025-I", 8: "2025-II",
    }

    for index, case in enumerate(TEST_CASES, start=1):
        code = case["student_code"]
        students.append(
            {
                "student_code": code,
                "full_name": case["full_name"],
                "document": case["document"],
                "email": NOTIFICATION_EMAIL,
                "phone": case["phone"],
                "program_id": "IS",
                "program_name": "Ingeniería de Sistemas",
                "plan": "2019",
                "current_cycle": 9,
                "academic_status": case["academic_status"],
                "max_credits": 22,
                "overload_authorized": False,
                "test_case_id": case["case_id"],
                "test_scenario": case["scenario"],
                "created_at": now,
            }
        )
        # IMPORTANTE: username = código universitario. El correo ya no identifica la cuenta.
        # La cuenta se deja ACTIVE incluso en C09 para poder ingresar y permitir que el
        # Agente Coordinador detecte academic_status=INACTIVE durante el proceso.
        accounts.append(
            {
                "username": code,
                "email": NOTIFICATION_EMAIL,
                "student_code": code,
                "password_hash": hash_password(case["document"]),
                "role": "STUDENT",
                "status": "ACTIVE",
                "created_at": now,
            }
        )

        for attempt_index, course in enumerate(base_passed, start=1):
            if course["course_id"] in case.get("remove_passed_courses", []):
                continue
            records.append(
                {
                    "student_code": code,
                    "course_id": course["course_id"],
                    "attempt": 1,
                    "status": "PASSED",
                    "grade": 13 + ((attempt_index + index) % 7),
                    "period": period_by_cycle[int(course["cycle"])],
                    "seed_source": "TEST_BASE_CYCLES_1_TO_8",
                }
            )

        payment = case["payment"]
        if payment is not None:
            payments.append(
                {
                    "student_code": code,
                    "period": PERIOD,
                    **payment,
                    "updated_at": now,
                }
            )
        else:
            # Garantiza C07 incluso si el script se ejecutó antes con otra configuración.
            db.payments.delete_many({"student_code": code, "period": PERIOD})

        requirement = case["requirements"]
        if requirement is not None:
            requirements.append(
                {
                    "student_code": code,
                    "period": PERIOD,
                    **requirement,
                    "updated_at": now,
                }
            )
        else:
            # Garantiza C08 incluso si el script se ejecutó antes con otra configuración.
            db.administrative_requirements.delete_many({"student_code": code, "period": PERIOD})

    upsert_many(db.students, students, "student_code")
    upsert_many(db.accounts, accounts, "student_code")
    upsert_many(db.academic_records, records, ("student_code", "course_id", "attempt"))
    upsert_many(db.payments, payments, ("student_code", "period"))
    upsert_many(db.administrative_requirements, requirements, ("student_code", "period"))

    return {
        "students": len(students),
        "accounts": len(accounts),
        "academic_records": len(records),
        "payments": len(payments),
        "administrative_requirements": len(requirements),
        "notification_email": NOTIFICATION_EMAIL,
        "login_policy": "username = student_code; password inicial = document",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicializa HyperMat IA en MongoDB Atlas")
    parser.add_argument(
        "--test-data",
        action="store_true",
        help="Carga 10 alumnos con precondiciones para probar el flujo real (sin sembrar resultados)",
    )
    parser.add_argument(
        "--reset-test-context",
        action="store_true",
        help="Reemplaza el perfil/contexto de los 10 alumnos de prueba antes de volver a sembrarlos",
    )
    parser.add_argument(
        "--reset-test-flow",
        action="store_true",
        help="Borra solicitudes, veredictos, matrículas, notificaciones, automatizaciones y auditoría generadas por esos 10 alumnos",
    )
    args = parser.parse_args()

    db = get_db()
    db.command("ping")
    ensure_collections(db)
    courses = seed_catalog(db)

    codes = [case["student_code"] for case in TEST_CASES]
    reset_result = None
    if args.reset_test_flow:
        reset_result = reset_test_flow(db, codes)

    test_result = None
    if args.test_data:
        test_result = seed_test_students(db, courses, reset_context=args.reset_test_context)

    print(
        json.dumps(
            {
                "database": db.name,
                "catalog_seeded": True,
                "test_data_seeded": args.test_data,
                "test_seed": test_result,
                "test_flow_reset": reset_result,
                "process_collections_are_not_preseeded": [
                    "enrollment_requests",
                    "agent_verdicts",
                    "enrollments",
                    "notifications",
                    "automation_runs",
                    "audit_events",
                ],
                "collections": {name: db[name].count_documents({}) for name in COLLECTIONS},
                "result": "seed_completed",
            },
            default=str,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
