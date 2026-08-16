"""
Sale creation — the most important transaction in the system.

Sequence follows spec section 10 / the approved Phase 2 architecture flow:
  lock products → validate stock → calculate totals → validate payment
  → create sale → create sale items → update stock → create inventory
  movements → create payment → create audit entry where applicable
  → commit

Atomicity: everything from product locking through the final payment
insert happens against the SAME db Session with ONE commit at the end.
If anything raises, the exception propagates before that commit, so
SQLAlchemy's session is simply discarded — no partial stock update, no
orphaned sale row, no fake payment (spec 70.2/70.6). Printing is a
completely separate, later, read-only operation (see app/api/routes/
sales.py) — there is no code path connecting a print failure to this
transaction at all, so a print failure structurally cannot roll back an
already-committed sale.
"""
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.inventory import MovementType
from app.models.payment import Payment
from app.models.product import Product
from app.models.sale import BillSequence, PaymentMethod, Sale, SaleItem
from app.models.user import User
from app.schemas.sale import SaleCreate
from app.services.inventory_service import adjust_stock


def _next_bill_number(db: Session) -> int:
    """
    Locks the single BillSequence row for the duration of this
    transaction, incrementing it as part of the same atomic write as the
    sale. See app/models/sale.py docstring for why this is a locked
    counter table rather than a native Postgres SEQUENCE (sequences don't
    roll back with a failed transaction, which would leave gaps).

    Locked BEFORE the product rows below, so every sale transaction
    acquires locks in the same fixed order (bill_sequence, then products
    by ascending product_id) — this is half of the deadlock-avoidance
    strategy the Phase 2 architecture specifies.
    """
    seq = db.query(BillSequence).filter(BillSequence.id == 1).with_for_update().first()
    if seq is None:
        # Bootstraps itself if the seed row is somehow missing.
        seq = BillSequence(id=1, last_number=0)
        db.add(seq)
        db.flush()
    seq.last_number += 1
    return seq.last_number


def create_sale(db: Session, data: SaleCreate, cashier: User) -> Sale:
    if not data.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty.")

    # Reject duplicate product_id lines up front — merging them silently
    # would be surprising, and locking the same row twice in one
    # transaction is itself worth avoiding.
    product_ids = [item.product_id for item in data.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate product in cart. Combine quantities into a single line.",
        )

    # --- Lock ordering (deadlock avoidance): bill_sequence FIRST, then
    # product rows in ASCENDING product_id order — not cart order. Two
    # concurrent sales sharing two overlapping products but added to
    # their carts in different order would otherwise be a textbook
    # deadlock (A holds X waits for Y; B holds Y waits for X). Canonical
    # ordering means both transactions always request locks in the same
    # sequence, so one simply waits behind the other. ---
    bill_number = _next_bill_number(db)

    ordered_product_ids = sorted(product_ids, key=lambda pid: str(pid))
    products_by_id: dict[uuid.UUID, Product] = {}
    for pid in ordered_product_ids:
        product = db.query(Product).filter(Product.id == pid).with_for_update().first()
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product not found: {pid}")
        products_by_id[pid] = product

    for item in data.items:
        if item.quantity <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be greater than zero.")
        if not products_by_id[item.product_id].is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{products_by_id[item.product_id].name}' is not active and cannot be sold.",
            )

    # --- validate stock (explicit step, per the approved architecture
    # flow: lock → VALIDATE STOCK → calculate totals → validate payment
    # → ...). This runs BEFORE payment validation so an oversized cart is
    # always rejected as a stock problem, never masked by an unrelated
    # payment-amount error. The products are already locked above, so
    # this read is safe from concurrent modification for the rest of the
    # transaction — adjust_stock() re-checks at write time regardless, as
    # cheap defense-in-depth, but the authoritative rejection happens here. ---
    for item in data.items:
        available = Decimal(str(products_by_id[item.product_id].current_stock))
        if item.quantity > available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient stock for '{products_by_id[item.product_id].name}'. Available quantity: {available}.",
            )

    # --- calculate totals (snapshot prices as they are RIGHT NOW — this
    # becomes the permanent historical price on SaleItem, per spec
    # section 14/19: future price changes must never alter this) ---
    subtotal = Decimal("0.00")
    line_items: list[tuple[Product, Decimal, Decimal]] = []  # (product, qty, line_total)
    for item in data.items:
        product = products_by_id[item.product_id]
        unit_price = Decimal(str(product.sale_price))
        line_total = (unit_price * item.quantity).quantize(Decimal("0.01"))
        subtotal += line_total
        line_items.append((product, item.quantity, line_total))

    # --- discount ---
    discount_amount = data.discount_amount or Decimal("0.00")
    if discount_amount > subtotal:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount cannot exceed the subtotal.")

    net_total = (subtotal - discount_amount).quantize(Decimal("0.01"))

    # --- validate payment ---
    if data.payment_method == PaymentMethod.CASH:
        if data.amount_received is None or data.amount_received < net_total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount received is less than the total due.",
            )
        amount_received = data.amount_received
        change_amount = (amount_received - net_total).quantize(Decimal("0.01"))
    else:  # QR — cashier visually confirms, no gateway (documented accepted risk)
        amount_received = None
        change_amount = Decimal("0.00")

    counter_id = data.counter_id or cashier.default_counter_id
    if counter_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No counter specified and this user has no default counter.",
        )

    # --- create sale + items, decrement stock, all in this transaction ---
    sale = Sale(
        id=uuid.uuid4(),
        bill_number=bill_number,
        counter_id=counter_id,
        cashier_id=cashier.id,
        subtotal=subtotal,
        discount_amount=discount_amount,
        discount_user_id=cashier.id if discount_amount > 0 else None,
        net_total=net_total,
    )
    db.add(sale)
    db.flush()  # assigns sale.id for use as movement/payment reference below

    for product, quantity, line_total in line_items:
        db.add(
            SaleItem(
                id=uuid.uuid4(),
                sale_id=sale.id,
                product_id=product.id,
                product_name=product.name,
                unit_price=product.sale_price,
                quantity=quantity,
                line_total=line_total,
            )
        )
        adjust_stock(
            db,
            product_id=product.id,
            quantity_delta=-quantity,
            movement_type=MovementType.SALE,
            user=cashier,
            reference_type="sale",
            reference_id=sale.id,
        )

    db.add(
        Payment(
            id=uuid.uuid4(),
            sale_id=sale.id,
            payment_method=data.payment_method,
            amount=net_total,
            amount_received=amount_received,
            change_amount=change_amount,
            payment_reference=data.payment_reference,
            user_id=cashier.id,
            counter_id=counter_id,
        )
    )

    if discount_amount > 0:
        # Spec 70.7 / the Phase 1 audit flagged that discounts (unlike
        # price changes) had no audit trail. Every discounted sale is
        # reviewable by who/when/how much, even though both roles can
        # apply a discount without a cap (explicit business decision).
        db.add(
            AuditLog(
                id=uuid.uuid4(),
                user_id=cashier.id,
                action="DISCOUNT_APPLIED",
                entity_type="sale",
                entity_id=sale.id,
                old_value=None,
                new_value=str(discount_amount),
                notes=f"Bill #{bill_number}",
            )
        )

    # --- commit once, atomically ---
    db.commit()
    db.refresh(sale)
    return sale


def get_sale(db: Session, sale_id: uuid.UUID) -> Sale:
    """Read-only. Used for both the post-checkout response AND reprint —
    same function, so reprint cannot behave differently from the
    original view by construction (no code path here can create rows)."""
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found.")
    return sale


def get_sale_by_bill_number(db: Session, bill_number: int) -> Sale:
    sale = db.query(Sale).filter(Sale.bill_number == bill_number).first()
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found.")
    return sale
