from pydantic import BaseModel, Field
from backend.models.profile import UserProfile
from backend.models.scheme import SchemeSummary

class ChatRequest(BaseModel):
    query: str = Field(..., description="User query in English, Kannada, or Hindi")
    language: str = Field(default="en", description="Preferred response language ('en', 'kn', 'hi')")
    session_id: str = Field(default="default_citizen", description="Citizen session ID")
    profile: UserProfile | None = None
    active_scheme_id: str | None = None

class ChatResponse(BaseModel):
    reply: str
    language: str
    suggested_schemes: list[SchemeSummary] = []
    quick_actions: list[str] = []
    source_links: list[dict[str, str]] = []

class FAQItem(BaseModel):
    question: str
    answer: str
    category: str
    scheme_id: str | None = None
