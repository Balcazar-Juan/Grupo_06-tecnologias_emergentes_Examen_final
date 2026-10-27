from app.services.multiagent import schedule_overlaps, decide_path


def test_overlap_exact_and_partial():
    assert schedule_overlaps("Sáb 08:00-11:00", "Sáb 08:00-11:00")
    assert schedule_overlaps("Lun 09:00-11:00", "Lun 10:00-12:00")
    assert not schedule_overlaps("Lun 09:00-10:00", "Lun 10:00-12:00")
    assert not schedule_overlaps("Lun 09:00-11:00", "Mar 09:00-11:00")


def test_supervisor_refuses_to_advance_after_failure():
    for phase in [True, False]:
        for agent in ["coordinator", "academic", "financial"]:
            assert decide_path("REJECTED", phase, agent) == "REJECTED"
            assert decide_path("OBSERVED", phase, agent) == "OBSERVED"


def test_prevalidation_never_final_approval():
    assert decide_path("APPROVED", False, "financial") == "PREVALIDATED"
    assert decide_path("APPROVED", True, "financial") == "CONTINUE"
    assert decide_path("EXECUTED", True, "rpa") == "APPROVED"
