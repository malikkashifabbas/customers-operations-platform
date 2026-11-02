"""Request and response shapes for login and tokens."""

from uuid import UUID

from ninja import Field, Schema
from pydantic import EmailStr


class CustomerLoginIn(Schema):
    tenant_public_id: UUID  # phone is unique per company only: the same number can be a customer of two companies
    phone: str = Field(min_length=7, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class CustomerSignupIn(Schema):
    tenant_public_id: UUID
    full_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=7, max_length=32)
    email: EmailStr | None = None
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordIn(Schema):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


class ResetPasswordIn(Schema):
    new_password: str = Field(min_length=1, max_length=128)


class LogoutIn(Schema):
    refresh_token: str | None = None


class StaffLoginIn(Schema):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(Schema):
    refresh_token: str = Field(min_length=1)


class TokensOut(Schema):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class AccessTokenOut(Schema):
    access_token: str
    token_type: str
    expires_in: int


class MeOut(Schema):
    role: str
    name: str
    tenant_public_id: UUID
    customer_public_id: UUID | None = None
    staff_public_id: UUID | None = None
