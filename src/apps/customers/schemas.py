"""Request and response shapes for the customers API."""

from ninja import Field, ModelSchema, Schema
from pydantic import EmailStr

from .models import Customer


class CustomerIn(Schema):
    full_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=7, max_length=32)
    email: EmailStr | None = None


class CustomerOut(ModelSchema):
    class Meta:
        model = Customer
        fields = ["public_id", "full_name", "phone", "email", "created_at"]
