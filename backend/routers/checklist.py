from typing import Annotated
from fastapi import APIRouter, Query
from backend.models.bookmark import ChecklistProgressItem, ChecklistProgressRequest
from backend.services.checklist_service import ChecklistService

router = APIRouter(prefix="/api/checklist", tags=["Document Checklist"])

@router.get("/progress", response_model=ChecklistProgressItem)
def get_checklist_progress(
    scheme_id: Annotated[str, Query(description="Target scheme ID")],
    session_id: Annotated[str, Query(description="Device or session identifier")] = "default_citizen",
):
    """
    Get citizen document preparation progress for a scheme (which documents are checked off).
    """
    return ChecklistService.get_progress(scheme_id=scheme_id, session_id=session_id)

@router.post("/progress", response_model=ChecklistProgressItem)
def update_checklist_progress(payload: ChecklistProgressRequest):
    """
    Update checked document items for a scheme, persisting state across sessions.
    """
    return ChecklistService.save_progress(
        scheme_id=payload.scheme_id,
        checked_indices=payload.checked_indices,
        session_id=payload.session_id,
    )
