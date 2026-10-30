from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request

from backend.models.auth import (
    AuthenticatedUser,
    LoginRequest,
    OTPVerificationRequest,
    RegisterRequest,
)
from backend.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def require_user(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthenticatedUser:
    return auth_service.authenticate_token(authorization)


@router.post("/register", status_code=202)
def register(payload: RegisterRequest, request: Request) -> dict[str, str]:
    return auth_service.register(payload.email, payload.password, request)


@router.post("/login", status_code=202)
def login(payload: LoginRequest, request: Request) -> dict[str, str]:
    return auth_service.login(payload.email, payload.password, request)


@router.post("/verify-otp")
def verify_otp(
    payload: OTPVerificationRequest,
    request: Request,
) -> dict[str, Any]:
    return auth_service.verify_otp(payload.email, payload.otp, request)


@router.post("/logout")
def logout(
    current_user: Annotated[AuthenticatedUser, Depends(require_user)],
) -> dict[str, str]:
    return auth_service.logout(current_user)


@router.get("/me")
def get_current_session(
    current_user: Annotated[AuthenticatedUser, Depends(require_user)],
) -> dict[str, str]:
    return auth_service.get_current_user(current_user)


@router.get("/login-history/{user_id}")
def get_login_history(
    user_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_user)],
) -> list[dict[str, Any]]:
    return auth_service.get_login_history(user_id, current_user)
