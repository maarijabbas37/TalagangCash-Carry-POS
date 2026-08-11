from pydantic import BaseModel, Field
import uuid

from app.models.user import RoleName


class LoginRequest(BaseModel):
    username: str
    password: str


class CounterOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    class Config:
        from_attributes = True


class MeResponse(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str
    role: RoleName
    default_counter: CounterOut | None = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: MeResponse
