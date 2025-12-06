from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Register(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 characters)")
    name: str = Field(..., min_length=3, max_length=50, description="Name (3-50 characters)")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "name": "John Doe",
                "email": "john@example.com",
                "password": "securepassword123"
            }
        }


class Login(BaseModel):
    username: Optional[str] = Field(None, description="Username or email")
    email: Optional[EmailStr] = Field(None, description="Email address")
    password: str = Field(..., description="Password")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "password": "securepassword123"
            }
        }


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")
