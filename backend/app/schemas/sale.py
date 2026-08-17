import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.sale import PaymentMethod


class SaleItemIn(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(gt=0)


class SaleCreate(BaseModel):
    items: list[SaleItemIn] = Field(min_length=1)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    payment_method: PaymentMethod
    amount_received: Decimal | None = Field(default=None, ge=0)  # CASH only
    payment_reference: str | None = Field(default=None, max_length=100)  # QR only, optional
    counter_id: uuid.UUID | None = None  # defaults to cashier's default counter

    @model_validator(mode="after")
    def cash_requires_amount_received(self) -> "SaleCreate":
        if self.payment_method == PaymentMethod.CASH and self.amount_received is None:
            raise ValueError("amount_received is required for cash payments.")
        return self


class SaleItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    unit_price: Decimal
    quantity: Decimal
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class PaymentOut(BaseModel):
    id: uuid.UUID
    payment_method: PaymentMethod
    amount: Decimal
    amount_received: Decimal | None
    change_amount: Decimal
    payment_reference: str | None
    user_id: uuid.UUID
    counter_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SaleOut(BaseModel):
    id: uuid.UUID
    bill_number: int
    counter_id: uuid.UUID
    cashier_id: uuid.UUID
    cashier_name: str
    subtotal: Decimal
    discount_amount: Decimal
    discount_user_id: uuid.UUID | None
    net_total: Decimal
    items: list[SaleItemOut]
    payments: list[PaymentOut]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
