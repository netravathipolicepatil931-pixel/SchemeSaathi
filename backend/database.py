import json
import sqlite3
from pathlib import Path
from backend.config import settings

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schemes (
        id TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        color TEXT,
        icon TEXT,
        url TEXT,
        source_url TEXT,
        ministry TEXT,
        data_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        scheme_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(session_id, scheme_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS checklist_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        scheme_id TEXT NOT NULL,
        checked_indices TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(session_id, scheme_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assistant_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        user_query TEXT NOT NULL,
        response TEXT NOT NULL,
        language TEXT DEFAULT 'en',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()

    # Seed schemes if table is empty
    cursor.execute("SELECT COUNT(*) FROM schemes")
    count = cursor.fetchone()[0]
    if count == 0:
        seed_path = Path(__file__).resolve().parent / "data" / "schemes_seed.json"
        if seed_path.exists():
            with open(seed_path, "r", encoding="utf-8") as f:
                schemes_data = json.load(f)
                for s in schemes_data:
                    cursor.execute("""
                    INSERT OR REPLACE INTO schemes (id, category, color, icon, url, source_url, ministry, data_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        s["id"],
                        s["category"],
                        s.get("color", "#eaf3ec"),
                        s.get("icon", "sparkle"),
                        s.get("url", ""),
                        s.get("sourceUrl", s.get("url", "")),
                        s.get("ministry", ""),
                        json.dumps(s, ensure_ascii=False)
                    ))
            conn.commit()

    conn.close()
