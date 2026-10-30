import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from backend.config import settings


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(settings.db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _as_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def consume_rate_limit(
    bucket: str, limit: int, window_seconds: int
) -> tuple[bool, int]:
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT window_started_at, attempts
            FROM auth_rate_limits
            WHERE bucket_key = ?
            """,
            (bucket,),
        ).fetchone()
        if row is None:
            connection.execute(
                """
                INSERT INTO auth_rate_limits (bucket_key, window_started_at, attempts)
                VALUES (?, ?, 1)
                """,
                (bucket, now_text),
            )
            return True, 0
        started = datetime.fromisoformat(row["window_started_at"])
        if started + timedelta(seconds=window_seconds) <= now:
            connection.execute(
                """
                UPDATE auth_rate_limits
                SET window_started_at = ?, attempts = 1
                WHERE bucket_key = ?
                """,
                (now_text, bucket),
            )
            return True, 0
        if row["attempts"] >= limit:
            remaining = started + timedelta(seconds=window_seconds) - now
            return False, max(1, int(remaining.total_seconds()))
        connection.execute(
            "UPDATE auth_rate_limits SET attempts = attempts + 1 WHERE bucket_key = ?",
            (bucket,),
        )
        return True, 0


def get_user(email: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            'SELECT id, email, password, verified FROM "User" WHERE email = ?',
            (email,),
        ).fetchone()
        return _as_dict(row)


def create_user(email: str, password_hash: str) -> dict[str, Any]:
    with _connect() as connection:
        user_id = str(uuid4())
        connection.execute(
            'INSERT INTO "User" (id, email, password) VALUES (?, ?, ?)',
            (user_id, email, password_hash),
        )
        row = connection.execute(
            'SELECT id, email, password, verified FROM "User" WHERE id = ?',
            (user_id,),
        ).fetchone()
        result = _as_dict(row)
        if result is None:
            raise RuntimeError("The user record was not returned after registration.")
        return result


def update_unverified_password(user_id: int, password_hash: str) -> None:
    with _connect() as connection:
        connection.execute(
            'UPDATE "User" SET password = ? WHERE id = ? AND verified = 0',
            (password_hash, user_id),
        )


def create_otp(
    user_id: str, otp_hash: str, purpose: str, expires_at: str, created_at: str
) -> str:
    with _connect() as connection:
        connection.execute(
            'UPDATE "OTP" SET "usedAt" = ? WHERE "userId" = ? AND purpose = ? AND "usedAt" IS NULL',
            (created_at, user_id, purpose),
        )
        otp_id = str(uuid4())
        connection.execute(
            """
            INSERT INTO "OTP" (id, "userId", otp, purpose, "expiresAt", attempts, "createdAt")
            VALUES (?, ?, ?, ?, ?, 0, ?)
            """,
            (otp_id, user_id, otp_hash, purpose, expires_at, created_at),
        )
        return otp_id


def get_latest_otp(user_id: str) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT id, otp, purpose, "expiresAt", "usedAt", attempts
            FROM "OTP"
            WHERE "userId" = ? AND "usedAt" IS NULL
                AND "expiresAt" > ? AND attempts < 5
            ORDER BY "createdAt" DESC
            LIMIT 1
            """,
            (user_id, now),
        ).fetchone()
        return _as_dict(row)


def increment_otp_attempt(otp_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as connection:
        connection.execute(
            """
            UPDATE "OTP" SET attempts = attempts + 1
            WHERE id = ? AND "usedAt" IS NULL AND "expiresAt" > ? AND attempts < 5
            """,
            (otp_id, now),
        )


def invalidate_otp(otp_id: str, used_at: str) -> None:
    with _connect() as connection:
        connection.execute(
            'UPDATE "OTP" SET "usedAt" = ? WHERE id = ? AND "usedAt" IS NULL',
            (used_at, otp_id),
        )


def consume_otp(otp_id: str, used_at: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as connection:
        cursor = connection.execute(
            """
            UPDATE "OTP" SET "usedAt" = ?
            WHERE id = ? AND "usedAt" IS NULL AND "expiresAt" > ? AND attempts < 5
            """,
            (used_at, otp_id, now),
        )
        return cursor.rowcount == 1


def set_user_verified(user_id: str) -> None:
    with _connect() as connection:
        connection.execute(
            'UPDATE "User" SET verified = 1 WHERE id = ?', (user_id,)
        )


def create_login_history(
    user_id: str,
    email: str,
    login_time: str,
    ip_address: str,
    user_agent: str,
    device: str,
) -> None:
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO "LoginHistory"
                ("userId", email, "loginTime", "ipAddress", "userAgent", device)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, email, login_time, ip_address, user_agent, device),
        )


def is_token_revoked(token_id: str) -> bool:
    with _connect() as connection:
        return (
            connection.execute(
                "SELECT 1 FROM revoked_tokens WHERE token_id = ? LIMIT 1",
                (token_id,),
            ).fetchone()
            is not None
        )


def revoke_token(token_id: str, expires_at: str) -> None:
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO revoked_tokens (token_id, expires_at) VALUES (?, ?)
            ON CONFLICT(token_id) DO NOTHING
            """,
            (token_id, expires_at),
        )


def get_login_history(user_id: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, "userId", email, "loginTime", "ipAddress",
                "userAgent", device, location
            FROM "LoginHistory"
            WHERE "userId" = ?
            ORDER BY "loginTime" DESC
            LIMIT 100
            """,
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]
