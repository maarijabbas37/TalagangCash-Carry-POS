"""
Product master business logic, including the price-history invariant:
sale_price on Product is never changed without a corresponding
ProductPriceHistory row in the SAME transaction (spec section 14).
"""
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.product import Product, ProductPriceHistory
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate


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


def create_product(db: Session, data: ProductCreate) -> Product:
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
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _friendly_integrity_error(exc) from exc
    db.refresh(product)
    return product


def update_product(db: Session, product: Product, data: ProductUpdate) -> Product:
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(product, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _friendly_integrity_error(exc) from exc
    db.refresh(product)
    return product


def change_product_price(db: Session, product: Product, new_price: Decimal, changed_by: User) -> Product:
    """
    Atomically updates Product.sale_price and inserts a ProductPriceHistory
    row. Both happen in one DB transaction so it's impossible for the
    current price to drift from the audit trail explaining it.
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
    db.commit()
    db.refresh(product)
    return product
