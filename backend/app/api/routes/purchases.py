"""
Purchase (stock receiving) endpoints.

POST /api/purchases is open to both roles (approved: purchase entry is
a flat-role permission, matching real receiving workflow — employees
count and enter goods). POST .../payments is Owner-only (approved
decision 1: recording cash out to a supplier requires Owner
authorization, unlike sales cash which employees already handle).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_owner
from app.models.purchase import Purchase
from app.models.user import User
from app.schemas.purchase import PurchaseCreate, PurchaseOut, PurchasePaymentIn, PurchasePaymentOut
from app.services.purchase_service import create_purchase, get_purchase, record_purchase_payment

router = APIRouter(prefix="/api/purchases", tags=["purchases"])


@router.post("", response_model=PurchaseOut, status_code=201)
def receive_purchase(data: PurchaseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> PurchaseOut:
    return create_purchase(db, data, received_by=user)


@router.get("/{purchase_id}", response_model=PurchaseOut)
def get_purchase_detail(purchase_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> PurchaseOut:
    return get_purchase(db, purchase_id)


@router.get("", response_model=list[PurchaseOut])
def list_purchases(
    supplier_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=25, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[PurchaseOut]:
    query = db.query(Purchase)
    if supplier_id:
        query = query.filter(Purchase.supplier_id == supplier_id)
    return query.order_by(Purchase.created_at.desc()).limit(limit).all()


@router.post("/{purchase_id}/payments", response_model=PurchasePaymentOut, status_code=201)
def add_purchase_payment(
    purchase_id: uuid.UUID,
    data: PurchasePaymentIn,
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner),
) -> PurchasePaymentOut:
    return record_purchase_payment(db, purchase_id, data, owner)
