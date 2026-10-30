import json
import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet

from backend.config import settings

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA secure_delete = ON")

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "User" (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        verified INTEGER NOT NULL DEFAULT 0,
        "createdAt" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "OTP" (
        id TEXT PRIMARY KEY,
        "userId" TEXT NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
        otp TEXT NOT NULL,
        purpose TEXT NOT NULL CHECK (purpose IN ('login', 'registration')),
        "expiresAt" TIMESTAMP NOT NULL,
        "usedAt" TIMESTAMP,
        attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 5),
        "createdAt" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS otp_user_created_idx
    ON "OTP" ("userId", "createdAt" DESC);
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "LoginHistory" (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        "userId" TEXT NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
        email TEXT NOT NULL,
        "loginTime" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "ipAddress" TEXT,
        "userAgent" TEXT,
        device TEXT,
        location TEXT
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_documents (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
        document_type TEXT NOT NULL CHECK (
            document_type IN (
                'aadhaar', 'pan_card', 'bank_passbook',
                'class_10_marksheet', 'disability_certificate'
            )
        ),
        encrypted_filename BLOB NOT NULL,
        media_type TEXT NOT NULL CHECK (
            media_type IN ('application/pdf', 'image/jpeg')
        ),
        size_bytes INTEGER NOT NULL CHECK (size_bytes BETWEEN 1 AND 2097152),
        encrypted_content BLOB NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    document_columns = {
        row["name"]
        for row in cursor.execute("PRAGMA table_info(user_documents)").fetchall()
    }
    if "encrypted_filename" not in document_columns:
        cursor.execute(
            "ALTER TABLE user_documents ADD COLUMN encrypted_filename BLOB"
        )
    if "original_filename" in document_columns:
        legacy_names = cursor.execute(
            """
            SELECT id, original_filename, encrypted_filename
            FROM user_documents
            WHERE original_filename != '' AND encrypted_filename IS NULL
            """
        ).fetchall()
        if legacy_names:
            if not settings.document_encryption_key:
                raise RuntimeError(
                    "DOCUMENT_ENCRYPTION_KEY is required to encrypt existing "
                    "document filenames."
                )
            fernet = Fernet(settings.document_encryption_key.encode("ascii"))
            for row in legacy_names:
                encrypted_filename = fernet.encrypt(
                    row["original_filename"].encode("utf-8")
                )
                cursor.execute(
                    """
                    UPDATE user_documents SET encrypted_filename = ?
                    WHERE id = ?
                    """,
                    (encrypted_filename, row["id"]),
                )
        cursor.execute(
            "ALTER TABLE user_documents DROP COLUMN original_filename"
        )
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS user_documents_owner_created_idx
    ON user_documents (user_id, created_at DESC);
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS login_history_user_time_idx
    ON "LoginHistory" ("userId", "loginTime" DESC);
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS revoked_tokens (
        token_id TEXT PRIMARY KEY,
        expires_at TIMESTAMP NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auth_rate_limits (
        bucket_key TEXT PRIMARY KEY,
        window_started_at TEXT NOT NULL,
        attempts INTEGER NOT NULL CHECK (attempts >= 0)
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
