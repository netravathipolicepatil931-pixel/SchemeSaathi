from uuid import uuid4

import bcrypt
import pytest
from fastapi import HTTPException, Request
from pydantic import ValidationError

from backend import auth_store
from backend.config import settings
from backend.database import init_db
from backend.models.auth import AuthenticatedUser, LoginRequest, OTPVerificationRequest
from backend.services import auth_service


@pytest.fixture
def auth_database(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "auth-test.db"))
    init_db()
    return auth_store


def _request(ip="127.0.0.1"):
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/login",
            "headers": [(b"user-agent", b"Mozilla/5.0 (Windows NT 10.0)")],
            "client": (ip, 12345),
        }
    )


def test_credentials_normalize_email():
    credentials = LoginRequest(
        email="  Citizen@Example.COM ", password="safe-pass-123"
    )
    assert credentials.email == "citizen@example.com"


def test_credentials_reject_invalid_email_and_oversized_utf8_password():
    with pytest.raises(ValidationError):
        LoginRequest(email="not-an-email", password="safe-pass-123")
    with pytest.raises(ValidationError):
        LoginRequest(email="citizen@example.com", password="é" * 37)


def test_otp_requires_six_digits():
    with pytest.raises(ValidationError):
        OTPVerificationRequest(email="citizen@example.com", otp="12345")


@pytest.mark.parametrize(
    ("agent", "expected"),
    [
        ("Mozilla/5.0 (iPhone; CPU iPhone OS)", "mobile"),
        ("Mozilla/5.0 (iPad; CPU OS)", "tablet"),
        ("Mozilla/5.0 (Windows NT 10.0)", "desktop"),
        ("", "unknown"),
    ],
)
def test_device_type(agent, expected):
    assert auth_service._device_type(agent) == expected


def test_rate_limit_returns_after_limit(auth_database, monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "s" * 32)
    auth_service._check_rate_limit("login:test", 2, 900)
    auth_service._check_rate_limit("login:test", 2, 900)
    with pytest.raises(HTTPException) as error:
        auth_service._check_rate_limit("login:test", 2, 900)
    assert error.value.status_code == 429
    assert int(error.value.headers["Retry-After"]) > 0


def test_registration_allows_more_than_three_users_from_same_ip(
    auth_database, monkeypatch
):
    monkeypatch.setattr(settings, "jwt_secret_key", "s" * 32)
    monkeypatch.setattr(auth_service, "_create_otp", lambda *_args: None)
    request = _request()
    for _ in range(3):
        auth_service._check_rate_limit("register:127.0.0.1", 3, 3600)

    for user_number in range(4):
        response = auth_service.register(
            f"citizen{user_number}@example.com", "safe-pass-123", request
        )
        assert "verification code" in response["message"].lower()


def test_login_history_only_allows_the_authenticated_user():
    current_user = AuthenticatedUser(
        id=str(uuid4()),
        email="citizen@example.com",
        token_id="token-id",
        token_expires_at=1,
    )
    with pytest.raises(HTTPException) as error:
        auth_service.get_login_history(str(uuid4()), current_user)
    assert error.value.status_code == 403


def test_login_rejects_users_with_missing_password_hash(auth_database, monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "s" * 32)
    auth_database.create_user("missing@example.com", bcrypt.hashpw(b"safe-pass-123", bcrypt.gensalt()).decode())
    with auth_database._connect() as connection:
        connection.execute(
            'UPDATE "User" SET password = ? WHERE email = ?',
            (b"not-a-bcrypt-hash", "missing@example.com"),
        )
    with pytest.raises(HTTPException) as error:
        auth_service.login("missing@example.com", "safe-pass-123", _request())
    assert error.value.status_code == 401


def test_registration_login_otp_and_logout_flow(auth_database, monkeypatch):
    sent_codes = []
    monkeypatch.setattr(settings, "jwt_secret_key", "s" * 32)
    monkeypatch.setattr(settings, "debug", True)
    monkeypatch.setattr(settings, "auth_dev_otp", True)
    monkeypatch.setattr(
        auth_service,
        "_send_otp_email",
        lambda _email, code, _purpose, _allow_dev_otp: (
            sent_codes.append(code) or True
        ),
    )
    request = _request()

    auth_service.register("citizen@example.com", "safe-pass-123", request)
    registration = auth_service.verify_otp(
        "citizen@example.com", sent_codes[-1], request
    )
    assert registration["verified"] is True

    auth_service.login("citizen@example.com", "safe-pass-123", request)
    result = auth_service.verify_otp("citizen@example.com", sent_codes[-1], request)
    assert result["token_type"] == "bearer"
    user_id = auth_database.get_user("citizen@example.com")["id"]
    assert len(auth_database.get_login_history(user_id)) == 1

    token = result["access_token"]
    user = auth_service.authenticate_token(f"Bearer {token}")
    auth_service.logout(user)
    with pytest.raises(HTTPException) as error:
        auth_service.authenticate_token(f"Bearer {token}")
    assert error.value.status_code == 401


def test_local_development_otp_is_only_returned_for_loopback_requests(
    auth_database, monkeypatch
):
    monkeypatch.setattr(settings, "jwt_secret_key", "s" * 32)
    monkeypatch.setattr(settings, "debug", True)
    monkeypatch.setattr(settings, "auth_dev_otp", True)
    monkeypatch.setattr(settings, "smtp_user", None)
    monkeypatch.setattr(settings, "smtp_password", None)

    response = auth_service.register(
        "local@example.com", "safe-pass-123", _request("127.0.0.1")
    )
    assert response["development_otp"].isdigit()
    assert len(response["development_otp"]) == 6
    stored_otp = auth_database.get_latest_otp(
        auth_database.get_user("local@example.com")["id"]
    )["otp"]
    assert stored_otp.startswith(("$2a$", "$2b$", "$2y$"))


def test_development_otp_is_never_returned_to_non_loopback_request(
    auth_database, monkeypatch
):
    monkeypatch.setattr(settings, "jwt_secret_key", "s" * 32)
    monkeypatch.setattr(settings, "debug", True)
    monkeypatch.setattr(settings, "auth_dev_otp", True)
    monkeypatch.setattr(settings, "smtp_user", None)
    monkeypatch.setattr(settings, "smtp_password", None)
    with pytest.raises(HTTPException) as error:
        auth_service.register(
            "remote@example.com", "safe-pass-123", _request("192.0.2.10")
        )
    assert error.value.status_code == 503
    assert "SMTP_USER" in error.value.detail
