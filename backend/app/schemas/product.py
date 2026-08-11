import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    barcode: str | None = Field(default=None, max_length=64)
    internal_code: str | None = Field(default=None, max_length=20)
    unit: str = Field(default="pcs", max_length=20)
    sale_price: Decimal = Field(gt=0)
    reorder_level: int = Field(default=15, ge=0)

    @field_validator("barcode", "internal_code")
    @classmethod
    def blank_to_none(cls, v: str | None) -> str | None:
        # An empty string from a form field should behave like "not provided",
        # not collide with every other blank-barcode product on the unique index.
        if v is not None and v.strip() == "":
            return None
        return v


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    barcode: str | None = None
    internal_code: str | None = None
    unit: str | None = None
    reorder_level: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    # sale_price is intentionally NOT editable here — changing price goes
    # through PriceUpdate below so a history row is always created (spec 14).


class PriceUpdate(BaseModel):
    new_price: Decimal = Field(gt=0)


class ProductOut(BaseModel):
    id: uuid.UUID
    name: str
    barcode: str | None
    internal_code: str | None
    unit: str
    sale_price: Decimal
    reorder_level: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PriceHistoryOut(BaseModel):
    id: uuid.UUID
    old_price: Decimal | None
    new_price: Decimal
    changed_by_user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
