from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from backend.models.profile import EligibilityCheckRequest, EligibilityCheckResponse
from backend.models.scheme import SchemeSummary, SchemeDetail
from backend.services.eligibility_engine import EligibilityEngine
from backend.services.scheme_service import SchemeService

router = APIRouter(prefix="/api/schemes", tags=["Schemes"])

CATEGORY_METADATA = {
    "all": {"en": "All categories", "kn": "ಎಲ್ಲಾ ವಿಭಾಗಗಳು", "hi": "सभी श्रेणियाँ"},
    "farmer": {"en": "Agriculture", "kn": "ಕೃಷಿ", "hi": "कृषि"},
    "housing": {"en": "Housing", "kn": "ವಸತಿ", "hi": "आवास"},
    "health": {"en": "Health", "kn": "ಆರೋಗ್ಯ", "hi": "स्वास्थ्य"},
    "women": {"en": "Women & families", "kn": "ಮಹಿಳೆ ಮತ್ತು ಕುಟುಂಬ", "hi": "महिलाएँ और परिवार"},
    "education": {"en": "Education", "kn": "ಶಿಕ್ಷಣ", "hi": "शिक्षा"},
    "worker": {"en": "Workers & Livelihood", "kn": "ಕಾರ್ಮಿಕರು & ಜೀವನೋಪಾಯ", "hi": "कामगार व आजीविका"},
    "self-employed": {"en": "Business & Self-Employed", "kn": "ವ್ಯಾಪಾರ ಮತ್ತು ಸ್ವಯಂ ಉದ್ಯೋಗ", "hi": "व्यवसाय और स्वरोजगार"},
}

@router.get("", response_model=list[SchemeSummary])
def list_schemes(
    query: Annotated[Optional[str], Query(description="Search keyword in scheme title or description")] = None,
    category: Annotated[str, Query(description="Category filter (e.g. farmer, housing, health)")] = "all",
    state: Annotated[str, Query(description="State filter (e.g. Karnataka, Maharashtra, all)")] = "all",
    language: Annotated[str, Query(description="Localization language: en, kn, hi")] = "en",
):
    """
    Retrieve all government welfare schemes matching query and category filters,
    localized in English, Kannada, or Hindi.
    """
    return SchemeService.filter_schemes(
        query=query, category=category, state=state, language=language
    )

@router.get("/categories")
def get_categories(
    language: Annotated[str, Query(description="Language code (en, kn, hi)")] = "en"
):
    """
    Returns available scheme categories with localized titles and metadata.
    """
    lang = language if language in ("en", "kn", "hi") else "en"
    return [
        {"id": cat_id, "label": labels.get(lang, labels["en"])}
        for cat_id, labels in CATEGORY_METADATA.items()
    ]

@router.get("/{scheme_id}", response_model=SchemeDetail)
def get_scheme_detail(
    scheme_id: Annotated[str, Path(description="Unique scheme ID, e.g. 'pm-kisan', 'ayushman-bharat'")],
    language: Annotated[str, Query(description="Language code (en, kn, hi)")] = "en",
):
    """
    Retrieve comprehensive scheme details including eligibility requirements,
    required documents, application roadmap, and verified official portals.
    """
    scheme = SchemeService.get_scheme_detail(scheme_id, language=language)
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found.")
    return scheme

@router.post("/check-eligibility", response_model=EligibilityCheckResponse)
def check_eligibility(payload: EligibilityCheckRequest):
    """
    Smart Rule Evaluation Engine:
    Evaluates citizen demographics (state, age, gender, occupation, location, income)
    against national and state scheme criteria to compute match score and personalized guidance.
    """
    return EligibilityEngine.evaluate_all(
        profile=payload.profile,
        language=payload.language,
        scheme_id=payload.scheme_id,
    )

@router.post("/recommend", response_model=EligibilityCheckResponse)
def recommend_schemes(payload: EligibilityCheckRequest):
    """
    Personalized recommendation endpoint matching demographic profile to prioritized schemes.
    """
    return EligibilityEngine.evaluate_all(
        profile=payload.profile,
        language=payload.language,
        scheme_id=payload.scheme_id,
    )
