import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.inventory import MovementType


class OpeningStockIn(BaseModel):
    """
    Owner-only, one-time-per-product initialization — NOT a recurring
    stock-entry mechanism. See app/services/inventory_service.py
    docstring for the guardrails (Phase 2 architecture review amendment 2).
    """
    product_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    notes: str | None = Field(default=None, max_length=500)


class InventoryMovementOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal
    movement_type: MovementType
    reference_type: str | None
    reference_id: uuid.UUID | None
    user_id: uuid.UUID
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockDiscrepancy(BaseModel):
    """One row of a reconciliation report — a product where the ledger
    (sum of inventory_movements) disagrees with products.current_stock."""
    product_id: uuid.UUID
    product_name: str
    current_stock: Decimal
    ledger_stock: Decimal
    difference: Decimal


class ReconciliationReport(BaseModel):
    checked_at: datetime
    products_checked: int
    discrepancies: list[StockDiscrepancy]
