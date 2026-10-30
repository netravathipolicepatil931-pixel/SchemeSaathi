from .schemes import router as schemes_router
from .bookmarks import router as bookmarks_router
from .checklist import router as checklist_router
from .assistant import router as assistant_router
from .translations import router as translations_router
from .auth import router as auth_router
from .documents import router as documents_router

__all__ = [
    "schemes_router",
    "bookmarks_router",
    "checklist_router",
    "assistant_router",
    "translations_router",
    "auth_router",
    "documents_router",
]
