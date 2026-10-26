import pytest
from fastapi import HTTPException
from backend.database import init_db
from backend.routers.schemes import (
    list_schemes,
    get_scheme_detail,
    get_categories,
    check_eligibility,
    recommend_schemes,
)
from backend.models.profile import EligibilityCheckRequest, UserProfile

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_list_all_schemes():
    schemes = list_schemes(query=None, category="all", state="all", language="en")
    assert len(schemes) >= 5
    ids = [s.id for s in schemes]
    assert "pm-kisan" in ids
    assert "ayushman-bharat" in ids
    assert "pmay-g" in ids
    assert "pm-ujjwala" in ids

def test_filter_by_category():
    schemes = list_schemes(category="farmer")
    assert len(schemes) >= 1
    assert all(s.category == "farmer" for s in schemes)

def test_search_by_keyword():
    schemes = list_schemes(query="scholarship")
    assert len(schemes) >= 1
    assert any("scholarship" in s.id.lower() or "scholarship" in s.name.lower() for s in schemes)

def test_categories_endpoint():
    cats_en = get_categories(language="en")
    assert len(cats_en) >= 5
    assert any(c["id"] == "farmer" and c["label"] == "Agriculture" for c in cats_en)

    cats_kn = get_categories(language="kn")
    assert any(c["id"] == "farmer" and c["label"] == "ಕೃಷಿ" for c in cats_kn)

def test_multilingual_detail():
    # English
    en_scheme = get_scheme_detail(scheme_id="pm-kisan", language="en")
    assert en_scheme.id == "pm-kisan"
    assert "PM-KISAN" in en_scheme.name
    assert len(en_scheme.documents) >= 3

    # Kannada
    kn_scheme = get_scheme_detail(scheme_id="pm-kisan", language="kn")
    assert "ಪಿಎಂ-ಕಿಸಾನ್" in kn_scheme.name
    assert len(kn_scheme.documents) >= 3

    # Hindi
    hi_scheme = get_scheme_detail(scheme_id="pm-kisan", language="hi")
    assert "पीएम-किसान" in hi_scheme.name

def test_scheme_detail_not_found():
    with pytest.raises(HTTPException) as exc:
        get_scheme_detail(scheme_id="invalid-non-existent-scheme", language="en")
    assert exc.value.status_code == 404
