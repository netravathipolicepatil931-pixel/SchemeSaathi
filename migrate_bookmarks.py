
from backend.database import get_db_connection
from backend.supabase_client import supabase_admin

# Read existing SQLite bookmarks
conn = get_db_connection()

try:
    rows = conn.execute(
        "SELECT session_id, scheme_id FROM bookmarks"
    ).fetchall()

    bookmarks = [dict(row) for row in rows]

finally:
    conn.close()

print("SQLite bookmarks found:", len(bookmarks))

if not bookmarks:
    print("Nothing to migrate.")

else:
    # Check that each scheme exists in Supabase
    scheme_response = (
        supabase_admin.table("schemes")
        .select("id")
        .execute()
    )

    valid_ids = {
        row["id"] for row in scheme_response.data
    }

    valid_bookmarks = [
        bookmark for bookmark in bookmarks
        if bookmark["scheme_id"] in valid_ids
    ]

    skipped = [
        bookmark["scheme_id"]
        for bookmark in bookmarks
        if bookmark["scheme_id"] not in valid_ids
    ]

    print("Bookmarks ready to migrate:", len(valid_bookmarks))
    print("Missing schemes skipped:", skipped)

    if valid_bookmarks:
        response = (
            supabase_admin.table("bookmarks")
            .upsert(
                valid_bookmarks,
                on_conflict="session_id,scheme_id"
            )
            .execute()
        )

        print("Migration completed.")
        print("Bookmarks transferred:", len(response.data or []))

