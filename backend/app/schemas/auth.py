from pydantic import BaseModel, ConfigDict, Field
import uuid

from app.models.user import RoleName


class LoginRequest(BaseModel):
    username: str
    password: str


class CounterOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class MeResponse(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str
    role: RoleName
    default_counter: CounterOut | None = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: MeResponse
