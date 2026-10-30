import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 254 or not re.fullmatch(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+",
        email,
    ):
        raise ValueError("Enter a valid email address.")
    return email


class Credentials(BaseModel):
    email: str
    password: Annotated[str, Field(min_length=8, max_length=72)]

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if "\x00" in value or len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value


class LoginRequest(Credentials):
    pass


class RegisterRequest(Credentials):
    pass


class OTPVerificationRequest(BaseModel):
    email: str
    otp: Annotated[str, Field(pattern=r"^\d{6}$")]

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class AuthenticatedUser(BaseModel):
    id: str
    email: str
    token_id: str
    token_expires_at: int
