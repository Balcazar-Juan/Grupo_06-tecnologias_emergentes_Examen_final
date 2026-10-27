from app.rules import evaluate_case, validate_course


def test_rejects_outstanding_debt():
    result = evaluate_case(["outstanding_debt"], 18)
    assert result.status == "REJECTED"
    assert "outstanding_debt" in result.blockers


def test_authorized_overload_is_approved():
    result = evaluate_case(["authorized_overload"], 26, overload_authorized=True)
    assert result.status == "APPROVED"


def test_course_blocks_missing_prerequisite_and_full_section():
    course = {"prerequisites": ["58"], "credits": 3, "capacity": 30, "enrolled": 30}
    messages = validate_course(course, set(), 15, 22)
    assert {item["code"] for item in messages} == {"MISSING_PREREQUISITE", "SECTION_FULL"}
