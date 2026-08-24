import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PurchaseItemIn(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class PurchaseCreate(BaseModel):
    supplier_id: uuid.UUID
    items: list[PurchaseItemIn] = Field(min_length=1)
    invoice_number: str | None = Field(default=None, max_length=100)
    invoice_date: date | None = None
    invoice_total: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)
    # Approved decision: any nonzero difference between computed_total and
    # invoice_total is a hard 409 unless the caller explicitly acknowledges
    # it here — this is a backend-enforced gate, not just a UI warning.
    mismatch_acknowledged: bool = False


class PurchaseItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    quantity: Decimal
    unit_cost: Decimal
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class PurchasePaymentIn(BaseModel):
    amount: Decimal = Field(gt=0)
    notes: str | None = Field(default=None, max_length=500)


class PurchasePaymentOut(BaseModel):
    id: uuid.UUID
    amount: Decimal
    user_id: uuid.UUID
    paid_at: datetime
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class PurchaseOut(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    invoice_number: str | None
    invoice_date: date | None
    invoice_total: Decimal | None
    computed_total: Decimal
    mismatch_acknowledged: bool
    received_by_user_id: uuid.UUID
    notes: str | None
    items: list[PurchaseItemOut]
    payments: list[PurchasePaymentOut]
    amount_paid: Decimal
    outstanding: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
