from typing import Literal
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    state: str | None = Field(default="Karnataka", description="State of residence (e.g. Karnataka, Maharashtra)")
    age: int | None = Field(default=None, ge=1, le=120, description="Applicant age")
    gender: Literal["woman", "man", "other", ""] | None = Field(default="", description="Gender: woman, man, other")
    location: Literal["rural", "urban", ""] | None = Field(default="", description="Residence area: rural, urban")
    occupation: Literal["farmer", "student", "worker", "self-employed", "other", ""] | None = Field(
        default="", description="Applicant occupation"
    )
    income: Literal["below-1", "1-2.5", "2.5-5", "above-5", ""] | None = Field(
        default="", description="Approximate household annual income tier"
    )

class CriterionCheck(BaseModel):
    criterion: str
    passed: bool
    details: str

class SchemeEligibilityResult(BaseModel):
    scheme_id: str
    scheme_name: str
    category: str
    match_status: Literal["eligible", "likely_eligible", "check_criteria", "not_eligible"]
    match_score: float
    relevance_reason: str
    criteria_breakdown: list[CriterionCheck]
    tailored_documents: list[str]
    official_url: str

class EligibilityCheckRequest(BaseModel):
    profile: UserProfile
    language: str = "en"
    scheme_id: str | None = None

class EligibilityCheckResponse(BaseModel):
    total_evaluated: int
    matching_schemes: list[SchemeEligibilityResult]
    user_profile: UserProfile
    language: str
