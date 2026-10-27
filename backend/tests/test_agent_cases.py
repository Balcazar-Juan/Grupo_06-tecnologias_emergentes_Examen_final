"""Domain agent cases without Atlas; E2E against deployed backend is separate."""
from app.services.multiagent import Context, Coordinator, Academic, Financial

PERIOD = "2026-II"
BASE = {"student_code": "2021023703", "academic_status": "ACTIVE", "plan": "2019", "program_id": "IS", "current_cycle": 9, "max_credits": 22}

class C:
    def __init__(self, doc=None): self.doc = doc
    def find_one(self, _): return self.doc

class DB:
    def __init__(self):
        self.courses=C({"course_id": "60", "program_id": "IS", "name": "Taller Tesis II", "cycle":9,"credits":3,"prerequisites":["54"]})
        self.enrollments=C(None)


def context(selection=None):
    return Context(db=DB(), request={"request_id":"MAT-T", "student_code":BASE["student_code"],"period":PERIOD,
                                    "selected_section_ids":selection or []}, run_id="test", confirm=True, student=dict(BASE))


def sec(id, courseid, schedule):
    return {"section_id":id,"course_id":courseid,"period":PERIOD,"capacity":35,"enrolled":25,"schedule":schedule}


def test_coordinator_inactive_blocks_early():
    ctx=context();inactive={**BASE,"academic_status":"INACTIVE"}
    status,*_=Coordinator().decide(ctx,{"student_profile":inactive,"approved_enrollment":None})
    assert status=="REJECTED"


def test_financial_valid_case():
    status,*_=Financial().decide(context(),{"payment":{"status":"PAID","amount":450,"expected_amount":450,"outstanding_debt":0},
                                           "requirements":{"documents_complete":True,"insurance_status":"VALID"}})
    assert status=="APPROVED"


def test_financial_hard_debt():
    status,*_=Financial().decide(context(),{"payment":{"status":"PAID","amount":450,"expected_amount":450,"outstanding_debt":320},
                                           "requirements":{"documents_complete":True,"insurance_status":"VALID"}})
    assert status=="REJECTED"


def test_financial_observed():
    for p,r in [({"status":"PENDING","amount":450,"expected_amount":450,"outstanding_debt":0},{"documents_complete":True,"insurance_status":"VALID"}),
                ({"status":"MISMATCH","amount":130,"expected_amount":450,"outstanding_debt":0},{"documents_complete":True,"insurance_status":"VALID"}),
                ({"status":"PAID","amount":450,"expected_amount":450,"outstanding_debt":0},{"documents_complete":True,"insurance_status":"EXPIRED"}),
                ({"status":"PAID","amount":450,"expected_amount":450,"outstanding_debt":0},None)]:
        status,*_=Financial().decide(context(),{"payment":p,"requirements":r})
        assert status=="OBSERVED"


def test_academic_missing_prereq():
    ctx=context(["2026-II-60-A"])
    status,*_=Academic().decide(ctx,{"transcript":[],"sections":[sec("2026-II-60-A","60","Mié 18:00-20:15")]})
    assert status=="REJECTED"


def test_academic_full_section():
    ctx=context(["2026-II-60-A"])
    full={**sec("2026-II-60-A","60","Mié 18:00-20:15"),"enrolled":35}
    status,*_=Academic().decide(ctx,{"transcript":[{"course_id":"54"}],"sections":[full]})
    assert status=="REJECTED"


def test_academic_crossing():
    ctx=context(["2026-II-63-A","2026-II-69-A"])
    # The stub returns the same course metadata for both sections; force two hydrated courses here.
    class Courses:
        def find_one(self, query):
            return {"course_id":query["course_id"],"name":"Curso "+query["course_id"],"program_id":"IS", "cycle":9 if query["course_id"]=="63" else 10,
                    "credits":2,"prerequisites":[]}
    ctx.db.courses=Courses()
    status,*_=Academic().decide(ctx,{"transcript":[],"sections":[sec("2026-II-63-A","63","Sáb 08:00-11:00"),sec("2026-II-69-A","69","Sáb 09:00-12:00")]})
    assert status=="REJECTED"
