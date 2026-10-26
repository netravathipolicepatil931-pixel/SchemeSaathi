
from backend.supabase_client import supabase, supabase_admin
from backend.services.scheme_service import SchemeService
from backend.services.bookmark_service import BookmarkService
from backend.services.checklist_service import ChecklistService

print("\n===== SCHEMESAATHI BACKEND TEST =====\n")

# Test 1: Government schemes
try:
    schemes = SchemeService.get_all_schemes()
    print("PASS - Government schemes:", len(schemes))
except Exception as error:
    print("FAIL - Government schemes:", error)

# Test 2: Bookmarks
try:
    bookmarks = BookmarkService.get_bookmarks()
    print("PASS - Bookmarks:", len(bookmarks))
except Exception as error:
    print("FAIL - Bookmarks:", error)

# Test 3: Document checklist
try:
    progress = ChecklistService.get_progress("pm-kisan")
    print("PASS - Checklist progress:", progress.progress_percentage)
except Exception as error:
    print("FAIL - Checklist:", error)

# Test 4: Supabase chatbot logs
try:
    response = (
        supabase_admin.table("assistant_logs")
        .select("id", count="exact")
        .execute()
    )
    print("PASS - Chatbot logs:", response.count)
except Exception as error:
    print("FAIL - Chatbot logs:", error)

print("\n===== TEST COMPLETED =====")

