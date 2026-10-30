import bcrypt
import hashlib
import hmac
import ipaddress
import jwt
import logging
import re
import secrets
import smtplib
import ssl
import sqlite3
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request, status

from backend.config import settings
from backend import auth_store
from backend.models.auth import AuthenticatedUser

logger = logging.getLogger(__name__)
OTP_LIFETIME = timedelta(minutes=5)
JWT_ALGORITHM = "HS256"
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(
    b"not-a-real-password", bcrypt.gensalt(rounds=12)
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _check_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    if not settings.jwt_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        )
    bucket = hmac.new(
        settings.jwt_secret_key.encode(), key.encode(), hashlib.sha256
    ).hexdigest()
    try:
        allowed, retry_after = auth_store.consume_rate_limit(
            bucket, limit, window_seconds
        )
    except Exception as error:
        raise _database_unavailable(error) from error

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host[:100]
    return "unknown"


def _device_type(user_agent: str) -> str:
    agent = user_agent.lower()
    if re.search(r"ipad|tablet|kindle|silk", agent):
        return "tablet"
    if re.search(r"mobile|iphone|ipod|android", agent):
        return "mobile"
    if not agent:
        return "unknown"
    return "desktop"


def _database_unavailable(error: Exception) -> HTTPException:
    logger.error(
        "Authentication database operation failed",
        exc_info=(type(error), error, error.__traceback__),
    )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authentication is temporarily unavailable.",
    )


def _send_otp_email(
    email: str, otp: str, purpose: str, allow_dev_otp: bool = False
) -> bool:
    if not settings.smtp_user or not settings.smtp_password:
        if allow_dev_otp:
            return False
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Email delivery is not configured. Set SMTP_USER and "
                "SMTP_PASSWORD in .env to send verification codes."
            ),
        )

    message = EmailMessage()
    message["Subject"] = "Your SchemeSaathi verification code"
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = email
    action = "verify your email address" if purpose == "registration" else "sign in"
    message.set_content(
        f"Your code to {action} to SchemeSaathi is {otp}.\n\n"
        "This code expires in 5 minutes. If you did not request it, you can "
        "ignore this email."
    )

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
            return True
    except (OSError, smtplib.SMTPException):
        logger.exception("Failed to deliver a verification email")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="We could not send the verification email. Please try again later.",
        ) from None


def _create_otp(
    user_id: str,
    email: str,
    purpose: str,
    allow_dev_otp: bool = False,
) -> str | None:
    code = f"{secrets.randbelow(1_000_000):06d}"
    now = _now()
    try:
        otp_id = auth_store.create_otp(
            user_id,
            bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode(),
            purpose,
            _iso(now + OTP_LIFETIME),
            _iso(now),
        )
    except Exception as error:
        raise _database_unavailable(error) from error

    try:
        if _send_otp_email(email, code, purpose, allow_dev_otp):
            return None
        return code
    except HTTPException:
        try:
            auth_store.invalidate_otp(otp_id, _iso(_now()))
        except Exception:
            logger.exception("Failed to invalidate undelivered OTP")
        raise


def _allow_local_development_otp(request: Request) -> bool:
    if not settings.debug or not settings.auth_dev_otp:
        return False
    if not request.client or not request.client.host:
        return False
    try:
        return ipaddress.ip_address(request.client.host).is_loopback
    except ValueError:
        return False


def register(email: str, password: str, request: Request) -> dict[str, str]:
    ip_address = _client_ip(request)
    _check_rate_limit(f"register:v2:ip:{ip_address}", 10, 3600)
    _check_rate_limit(f"register:v2:email:{email}", 5, 3600)
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
    try:
        existing_user = auth_store.get_user(email)
        if existing_user:
            if not existing_user["verified"]:
                auth_store.update_unverified_password(
                    existing_user["id"], password_hash
                )
                code = _create_otp(
                    existing_user["id"],
                    email,
                    "registration",
                    _allow_local_development_otp(request),
                )
                response = {
                    "message": "A verification code has been sent to your email."
                    if code is None
                    else "Local development mode: use the displayed code to verify your email."
                }
                if code is not None:
                    response["development_otp"] = code
                return response
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        user = auth_store.create_user(email, password_hash)
    except HTTPException:
        raise
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error
    except Exception as error:
        raise _database_unavailable(error) from error

    code = _create_otp(
        user["id"],
        email,
        "registration",
        _allow_local_development_otp(request),
    )
    response = {
        "message": "A verification code has been sent to your email."
        if code is None
        else "Local development mode: use the displayed code to verify your email."
    }
    if code is not None:
        response["development_otp"] = code
    return response


def login(email: str, password: str, request: Request) -> dict[str, str]:
    ip_address = _client_ip(request)
    _check_rate_limit(f"login:ip:{ip_address}", 20, 900)
    _check_rate_limit(f"login:email:{email}", 8, 900)
    try:
        user = auth_store.get_user(email)
    except Exception as error:
        raise _database_unavailable(error) from error

    stored_hash = user.get("password", "").encode() if user else _DUMMY_PASSWORD_HASH
    try:
        password_matches = bcrypt.checkpw(password.encode(), stored_hash)
    except (ValueError, TypeError):
        password_matches = False
    if not user or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.get("verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email address before signing in.",
        )

    code = _create_otp(
        user["id"],
        email,
        "login",
        _allow_local_development_otp(request),
    )
    response = {
        "message": "A verification code has been sent to your email."
        if code is None
        else "Local development mode: use the displayed code to sign in."
    }
    if code is not None:
        response["development_otp"] = code
    return response


def _create_jwt(user_id: str, email: str) -> tuple[str, int]:
    if not settings.jwt_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        )
    issued_at = _now()
    expires_at = issued_at + timedelta(minutes=settings.jwt_expiry_minutes)
    token_id = secrets.token_urlsafe(24)
    token = jwt.encode(
        {
            "sub": user_id,
            "email": email,
            "jti": token_id,
            "iat": issued_at,
            "exp": expires_at,
        },
        settings.jwt_secret_key,
        algorithm=JWT_ALGORITHM,
    )
    return token, int(expires_at.timestamp())


def verify_otp(email: str, otp: str, request: Request) -> dict[str, Any]:
    _check_rate_limit(f"verify:ip:{_client_ip(request)}", 20, 300)
    _check_rate_limit(f"verify:email:{email}", 8, 300)
    try:
        user = auth_store.get_user(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The verification code is invalid or expired.",
            )
        otp_row = auth_store.get_latest_otp(user["id"])
    except HTTPException:
        raise
    except Exception as error:
        raise _database_unavailable(error) from error

    if not otp_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The verification code is invalid or expired.",
        )

    try:
        code_matches = bcrypt.checkpw(otp.encode(), otp_row["otp"].encode())
    except (ValueError, TypeError):
        code_matches = False
    if not code_matches:
        try:
            auth_store.increment_otp_attempt(otp_row["id"])
        except Exception as error:
            raise _database_unavailable(error) from error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The verification code is invalid or expired.",
        )

    now = _now()
    try:
        consumed = auth_store.consume_otp(otp_row["id"], _iso(now))
        if not consumed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The verification code is invalid or expired.",
            )
        if otp_row["purpose"] == "registration":
            auth_store.set_user_verified(user["id"])
            return {"verified": True, "message": "Email verified. You can now sign in."}

        if not user["verified"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Verify your email address before signing in.",
            )
        user_agent = request.headers.get("user-agent", "")[:2000]
        login_time = _iso(now)
        auth_store.create_login_history(
            user["id"],
            user["email"],
            login_time,
            _client_ip(request),
            user_agent,
            _device_type(user_agent),
        )
    except HTTPException:
        raise
    except Exception as error:
        raise _database_unavailable(error) from error

    token, expires_at = _create_jwt(user["id"], user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "user": {"id": user["id"], "email": user["email"]},
    }


def authenticate_token(authorization: str | None) -> AuthenticatedUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not settings.jwt_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        )
    token = authorization[7:].strip()
    try:
        claims = jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
        user = AuthenticatedUser(
            id=str(UUID(claims["sub"])),
            email=claims["email"],
            token_id=claims["jti"],
            token_expires_at=int(claims["exp"]),
        )
        revoked = auth_store.is_token_revoked(user.token_id)
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except Exception as error:
        raise _database_unavailable(error) from error
    if revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This session has been logged out.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def logout(user: AuthenticatedUser) -> dict[str, str]:
    try:
        auth_store.revoke_token(
            user.token_id,
            datetime.fromtimestamp(
                user.token_expires_at, timezone.utc
            ).isoformat(),
        )
    except Exception as error:
        raise _database_unavailable(error) from error
    return {"message": "You have been logged out."}


def get_login_history(
    user_id: str, current_user: AuthenticatedUser
) -> list[dict[str, Any]]:
    try:
        requested_id = str(UUID(user_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user ID.",
        ) from None
    if requested_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only view your own login history.",
        )
    try:
        return auth_store.get_login_history(requested_id)
    except Exception as error:
        raise _database_unavailable(error) from error


def get_current_user(user: AuthenticatedUser) -> dict[str, str]:
    return {"id": user.id, "email": user.email}
