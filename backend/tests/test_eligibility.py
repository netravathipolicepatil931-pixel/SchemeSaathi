import pytest
from backend.database import init_db
from backend.routers.schemes import check_eligibility, recommend_schemes
from backend.models.profile import EligibilityCheckRequest, UserProfile

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_farmer_profile_eligibility():
    req = EligibilityCheckRequest(
        profile=UserProfile(
            state="Karnataka",
            age=38,
            gender="man",
            location="rural",
            occupation="farmer",
            income="below-1",
        ),
        language="en",
    )
    res = check_eligibility(req)
    assert res.total_evaluated >= 5

    pm_kisan = next((s for s in res.matching_schemes if s.scheme_id == "pm-kisan"), None)
    assert pm_kisan is not None
    assert pm_kisan.match_status in ("eligible", "likely_eligible")
    assert pm_kisan.match_score >= 80

def test_student_profile_eligibility():
    req = EligibilityCheckRequest(
        profile=UserProfile(
            state="Karnataka",
            age=19,
            gender="woman",
            location="urban",
            occupation="student",
            income="1-2.5",
        ),
        language="en",
    )
    res = check_eligibility(req)
    nsp = next((s for s in res.matching_schemes if s.scheme_id == "national-scholarship"), None)
    assert nsp is not None
    assert nsp.match_status in ("eligible", "likely_eligible")

def test_rural_woman_profile_eligibility():
    req = EligibilityCheckRequest(
        profile=UserProfile(
            state="Karnataka",
            age=34,
            gender="woman",
            location="rural",
            occupation="worker",
            income="below-1",
        ),
        language="kn",
    )
    res = check_eligibility(req)
    ujjwala = next((s for s in res.matching_schemes if s.scheme_id == "pm-ujjwala"), None)
    assert ujjwala is not None
    assert ujjwala.match_status in ("eligible", "likely_eligible")

    gruha = next((s for s in res.matching_schemes if s.scheme_id == "gruha-lakshmi"), None)
    assert gruha is not None
    assert gruha.match_status in ("eligible", "likely_eligible")

def test_recommend_endpoint():
    req = EligibilityCheckRequest(
        profile=UserProfile(
            state="Karnataka",
            age=45,
            gender="man",
            location="rural",
            occupation="farmer",
            income="below-1",
        ),
        language="hi",
    )
    res = recommend_schemes(req)
    assert res.total_evaluated >= 5
    assert len(res.matching_schemes) >= 5
