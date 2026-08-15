import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.models.user import RoleName


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=6, max_length=255)
    role: RoleName
    default_counter_id: uuid.UUID | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str
    role: RoleName
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
