import pytest
from backend.database import init_db
from backend.routers.bookmarks import (
    add_bookmark,
    get_user_bookmarks,
    check_bookmark_status,
    remove_bookmark,
)
from backend.routers.checklist import get_checklist_progress, update_checklist_progress
from backend.models.bookmark import BookmarkRequest, ChecklistProgressRequest

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_bookmark_lifecycle():
    session_id = "test_user_session_1"

    # 1. Add bookmark
    add_res = add_bookmark(BookmarkRequest(scheme_id="pm-kisan", session_id=session_id))
    assert add_res["status"] == "success"

    # 2. Check status
    status_res = check_bookmark_status(scheme_id="pm-kisan", session_id=session_id)
    assert status_res["bookmarked"] is True

    # 3. List bookmarks
    bookmarks = get_user_bookmarks(session_id=session_id, language="en")
    assert len(bookmarks) == 1
    assert bookmarks[0].id == "pm-kisan"

    # 4. Remove bookmark
    del_res = remove_bookmark(scheme_id="pm-kisan", session_id=session_id)
    assert del_res["removed"] is True

    # 5. Verify empty
    bookmarks_after = get_user_bookmarks(session_id=session_id, language="en")
    assert len(bookmarks_after) == 0

def test_checklist_progress():
    session_id = "test_user_checklist_1"

    # Update progress
    res = update_checklist_progress(
        ChecklistProgressRequest(
            scheme_id="ayushman-bharat",
            checked_indices=[0, 1],
            session_id=session_id,
        )
    )
    assert res.scheme_id == "ayushman-bharat"
    assert res.checked_indices == [0, 1]
    assert res.progress_percentage > 0

    # Retrieve progress
    prog = get_checklist_progress(scheme_id="ayushman-bharat", session_id=session_id)
    assert prog.checked_indices == [0, 1]
