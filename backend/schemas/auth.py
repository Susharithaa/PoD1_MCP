from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class OTPVerifyRequest(BaseModel):
    email: str
    otp: str


class OTPRequiredResponse(BaseModel):
    status: str = "otp_required"
    message: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    is_active: bool
    auth_provider: str = "local"
    created_at: str


class UpdateRoleRequest(BaseModel):
    role: str  # "user" or "admin"


class SetActiveRequest(BaseModel):
    is_active: bool
