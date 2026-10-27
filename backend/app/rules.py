from dataclasses import dataclass, field
from typing import Iterable


BLOCKING_FLAGS = {"outstanding_debt", "credit_limit", "inactive_student", "curriculum_mismatch"}
OBSERVATION_FLAGS = {
    "missing_prerequisite", "payment_pending", "section_full", "schedule_conflict",
    "document_expired", "already_passed", "no_section", "payment_mismatch",
    "prerequisite_in_progress", "partial_eligibility", "rpa_retry", "email_retry",
}


@dataclass
class RuleResult:
    status: str
    blockers: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)


def evaluate_case(flags: Iterable[str], credits: int, max_credits: int = 22, overload_authorized: bool = False) -> RuleResult:
    flags = set(flags)
    blockers = sorted(flags & BLOCKING_FLAGS)
    observations = sorted(flags & OBSERVATION_FLAGS)
    if credits > max_credits and not overload_authorized and "credit_limit" not in blockers:
        blockers.append("credit_limit")
    if blockers:
        return RuleResult("REJECTED", blockers, observations)
    if observations:
        return RuleResult("OBSERVED", [], observations)
    return RuleResult("APPROVED")


def validate_course(course: dict, passed_course_ids: set[str], selected_credits: int, max_credits: int) -> list[dict]:
    messages: list[dict] = []
    missing = [item for item in course.get("prerequisites", []) if item not in passed_course_ids]
    if missing:
        messages.append({"code": "MISSING_PREREQUISITE", "severity": "BLOCKER", "message": f"Falta aprobar: {', '.join(missing)}."})
    if course.get("enrolled", 0) >= course.get("capacity", 0):
        messages.append({"code": "SECTION_FULL", "severity": "BLOCKER", "message": "La sección no tiene vacantes."})
    if selected_credits + course["credits"] > max_credits:
        messages.append({"code": "CREDIT_LIMIT", "severity": "BLOCKER", "message": f"Supera el máximo de {max_credits} créditos."})
    return messages
