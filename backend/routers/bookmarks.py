from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, Path
from backend.models.bookmark import BookmarkRequest
from backend.models.scheme import SchemeSummary
from backend.services.bookmark_service import BookmarkService

router = APIRouter(prefix="/api/bookmarks", tags=["Bookmarks"])

@router.get("", response_model=list[SchemeSummary])
def get_user_bookmarks(
    session_id: Annotated[str, Query(description="Device or session identifier")] = "default_citizen",
    language: Annotated[str, Query(description="Preferred response language: en, kn, hi")] = "en",
):
    """
    Retrieve all schemes saved/bookmarked by the citizen on their device.
    """
    return BookmarkService.get_bookmarks(session_id=session_id, language=language)

@router.post("")
def add_bookmark(payload: BookmarkRequest):
    """
    Save / bookmark a scheme for quick access and offline reference.
    """
    success = BookmarkService.add_bookmark(
        scheme_id=payload.scheme_id, session_id=payload.session_id
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Scheme '{payload.scheme_id}' does not exist.",
        )
    return {"status": "success", "message": "Scheme bookmarked successfully."}

@router.delete("/{scheme_id}")
def remove_bookmark(
    scheme_id: Annotated[str, Path(description="Scheme ID to remove")],
    session_id: Annotated[str, Query(description="Device or session identifier")] = "default_citizen",
):
    """
    Remove a scheme from saved bookmarks.
    """
    removed = BookmarkService.remove_bookmark(scheme_id=scheme_id, session_id=session_id)
    return {
        "status": "success",
        "removed": removed,
        "message": "Bookmark updated.",
    }

@router.get("/status/{scheme_id}")
def check_bookmark_status(
    scheme_id: Annotated[str, Path(description="Scheme ID to check")],
    session_id: Annotated[str, Query(description="Device or session identifier")] = "default_citizen",
):
    """
    Check if a specific scheme is bookmarked in this session.
    """
    bookmarked = BookmarkService.is_bookmarked(scheme_id=scheme_id, session_id=session_id)
    return {"scheme_id": scheme_id, "bookmarked": bookmarked}
