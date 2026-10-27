from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=4, max_length=128)


class BootstrapAdminRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=6, max_length=128)


class StudentCreate(BaseModel):
    student_code: str = Field(pattern=r"^\d{6,12}$")
    full_name: str = Field(min_length=3, max_length=140)
    document: str = Field(min_length=6, max_length=15)
    email: str = Field(min_length=5, max_length=160)
    phone: str = Field(default="", max_length=30)
    program_id: str = "IS"
    program_name: str = "Ingeniería de Sistemas"
    plan: str = "2019"
    current_cycle: int = Field(default=1, ge=1, le=12)
    academic_status: Literal["ACTIVE", "INACTIVE"] = "ACTIVE"
    max_credits: int = Field(default=22, ge=1, le=40)
    overload_authorized: bool = False
    initial_password: str | None = Field(default=None, min_length=4, max_length=128)


class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=140)
    document: str | None = Field(default=None, min_length=6, max_length=15)
    email: str | None = Field(default=None, min_length=5, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    program_id: str | None = None
    program_name: str | None = None
    plan: str | None = None
    current_cycle: int | None = Field(default=None, ge=1, le=12)
    academic_status: Literal["ACTIVE", "INACTIVE"] | None = None
    max_credits: int | None = Field(default=None, ge=1, le=40)
    overload_authorized: bool | None = None


class PaymentUpdate(BaseModel):
    period: str = "2026-II"
    status: Literal["PAID", "PENDING", "MISMATCH", "NOT_REGISTERED"] = "NOT_REGISTERED"
    amount: float = Field(default=0, ge=0)
    expected_amount: float = Field(default=0, ge=0)
    outstanding_debt: float = Field(default=0, ge=0)


class RequirementUpdate(BaseModel):
    period: str = "2026-II"
    documents_complete: bool = False
    insurance_status: Literal["VALID", "EXPIRED", "PENDING", "NOT_REGISTERED"] = "NOT_REGISTERED"
    notes: str = Field(default="", max_length=500)


class AcademicRecordUpsert(BaseModel):
    course_id: str = Field(min_length=1, max_length=20)
    attempt: int = Field(default=1, ge=1, le=10)
    status: Literal["PASSED", "FAILED", "IN_PROGRESS"] = "PASSED"
    grade: float | None = Field(default=None, ge=0, le=20)
    period: str = "2025-II"


class EnrollmentCreate(BaseModel):
    student_code: str | None = Field(default=None, pattern=r"^\d{6,12}$")
    period: str = "2026-II"
    program_id: str = "IS"
    selected_section_ids: list[str] = Field(default_factory=list)


class EnrollmentConfirm(BaseModel):
    selected_section_ids: list[str] = Field(default_factory=list)


class ValidationMessage(BaseModel):
    code: str
    severity: Literal["INFO", "OBSERVATION", "BLOCKER"]
    message: str


class AgentVerdict(BaseModel):
    agent: Literal["coordinator", "academic", "financial", "executor", "rpa"]
    status: Literal["APPROVED", "OBSERVED", "REJECTED", "PENDING", "EXECUTED"]
    summary: str
    messages: list[ValidationMessage] = Field(default_factory=list)
