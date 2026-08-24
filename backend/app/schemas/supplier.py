import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    address_notes: str | None = Field(default=None, max_length=2000)


class SupplierOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: str | None
    address_notes: str | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
