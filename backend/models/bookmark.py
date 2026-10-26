from pydantic import BaseModel, Field

class BookmarkRequest(BaseModel):
    scheme_id: str
    session_id: str = Field(default="default_citizen", description="Device or anonymous session identifier")

class BookmarkItem(BaseModel):
    scheme_id: str
    session_id: str
    created_at: str | None = None

class ChecklistProgressRequest(BaseModel):
    scheme_id: str
    checked_indices: list[int]
    session_id: str = Field(default="default_citizen", description="Device or anonymous session identifier")

class ChecklistProgressItem(BaseModel):
    scheme_id: str
    checked_indices: list[int]
    total_items: int = 0
    progress_percentage: float = 0.0
    session_id: str
