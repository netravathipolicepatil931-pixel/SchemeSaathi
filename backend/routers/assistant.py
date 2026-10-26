from typing import Annotated
from fastapi import APIRouter, Query
from backend.models.chat import ChatRequest, ChatResponse, FAQItem
from backend.services.ai_assistant import AIAssistantService

router = APIRouter(prefix="/api/assistant", tags=["AI Citizen Assistant"])

@router.post("/chat", response_model=ChatResponse)
def chat_with_assistant(payload: ChatRequest):
    """
    Conversational AI Citizen Assistant:
    Accepts queries in English, Kannada, or Hindi regarding welfare schemes, eligibility rules,
    document requirements, and application procedures.
    """
    return AIAssistantService.answer_query(payload)

@router.get("/faq", response_model=list[FAQItem])
def get_faqs(
    language: Annotated[str, Query(description="Language code: en, kn, hi")] = "en"
):
    """
    Frequently asked questions about government scheme eligibility and portal verification.
    """
    return AIAssistantService.get_faqs(language)
