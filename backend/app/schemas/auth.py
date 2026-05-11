"""Pydantic schemas for authentication."""

from pydantic import BaseModel, EmailStr, Field


class RegisterReq(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str


class AuthResp(BaseModel):
    access_token: str = Field(..., alias="accessToken")
    user: UserOut

    model_config = {"populate_by_name": True}
