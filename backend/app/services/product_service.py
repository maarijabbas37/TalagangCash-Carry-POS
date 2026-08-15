"""
Product master business logic, including the price-history invariant:
sale_price on Product is never changed without a corresponding
ProductPriceHistory row in the SAME transaction (spec section 14).

Phase 1 fix: update_product() now requires the acting user and writes an
AuditLog entry for every field it changes (including is_active), because
this endpoint became Owner-only — see app/api/routes/products.py. The
audit entry stores field-level old/new values, not just "something
changed", so the owner can answer "what exactly changed and to what."
"""
import json
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.product import Product, ProductPriceHistory
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.audit_service import record as record_audit


def _friendly_integrity_error(exc: IntegrityError) -> HTTPException:
    # Never leak raw IntegrityError text to the client (spec section 48).
    msg = str(exc.orig).lower()
    if "barcode" in msg:
        detail = "This barcode is already assigned to another product."
    elif "internal_code" in msg:
        detail = "This internal code is already assigned to another product."
    else:
        detail = "Unable to save product due to a data conflict."
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def create_product(db: Session, data: ProductCreate, created_by: User) -> Product:
    product = Product(
        name=data.name,
        barcode=data.barcode,
        internal_code=data.internal_code,
        unit=data.unit,
        sale_price=data.sale_price,
        reorder_level=data.reorder_level,
    )
    db.add(product)
    try:
        db.flush()  # assigns product.id without committing yet
    except IntegrityError as exc:
        db.rollback()
        raise _friendly_integrity_error(exc) from exc

    record_audit(
        db,
        user=created_by,
        action="PRODUCT_CREATED",
        entity_type="product",
        entity_id=product.id,
        new_value=json.dumps({"name": product.name, "sale_price": str(product.sale_price)}, default=str),
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _friendly_integrity_error(exc) from exc
    db.refresh(product)
    return product


def update_product(db: Session, product: Product, data: ProductUpdate, changed_by: User) -> Product:
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        return product

    old_values = {field: getattr(product, field) for field in updates}
    for field, value in updates.items():
        setattr(product, field, value)

    record_audit(
        db,
        user=changed_by,
        action="PRODUCT_UPDATED",
        entity_type="product",
        entity_id=product.id,
        old_value=json.dumps(old_values, default=str),
        new_value=json.dumps(updates, default=str),
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _friendly_integrity_error(exc) from exc
    db.refresh(product)
    return product


def change_product_price(db: Session, product: Product, new_price: Decimal, changed_by: User) -> Product:
    """
    Atomically updates Product.sale_price, inserts a ProductPriceHistory
    row (product-specific price trend, used for receipts/reports later),
    AND writes a generic AuditLog entry (so price changes show up
    alongside every other sensitive action in one place, not scattered
    across domain-specific tables only).
    """
    old_price = product.sale_price
    if Decimal(str(new_price)) == Decimal(str(old_price)):
        # No-op price change: don't pollute history with a no-change row.
        return product

    history_row = ProductPriceHistory(
        id=uuid.uuid4(),
        product_id=product.id,
        old_price=old_price,
        new_price=new_price,
        changed_by_user_id=changed_by.id,
    )
    product.sale_price = new_price
    db.add(history_row)
    db.add(product)

    record_audit(
        db,
        user=changed_by,
        action="PRICE_CHANGED",
        entity_type="product",
        entity_id=product.id,
        old_value=str(old_price),
        new_value=str(new_price),
    )

    db.commit()
    db.refresh(product)
    return product
