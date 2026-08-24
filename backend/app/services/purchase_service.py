"""
Purchase creation — stock receiving from a supplier.

Mirrors sale_service.create_sale()'s shape deliberately (same reviewed,
approved architecture, applied to the inbound direction):
  validate → compute totals → gate on business rules → create rows
  → mutate stock via adjust_stock() → audit → one commit.

The one genuinely new piece versus Phase 2: the invoice-mismatch gate
(approved decision — any nonzero difference between computed_total and
invoice_total is a hard 409 unless explicitly acknowledged). Everything
else re-uses existing, already-tested machinery.
"""
import json
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.inventory import MovementType
from app.models.purchase import Purchase, PurchaseItem, PurchasePayment
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.purchase import PurchaseCreate, PurchasePaymentIn
from app.services.audit_service import record as record_audit
from app.services.inventory_service import adjust_stock


def create_purchase(db: Session, data: PurchaseCreate, received_by: User) -> Purchase:
    if not data.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase must include at least one item.")

    product_ids = [item.product_id for item in data.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate product in purchase. Combine quantities into a single line.",
        )

    supplier = db.get(Supplier, data.supplier_id)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")

    # --- compute totals purely from the request — no DB IO needed yet,
    # so a mismatch is caught before any row is locked or mutated ---
    computed_total = Decimal("0.00")
    for item in data.items:
        line_total = (item.quantity * item.unit_cost).quantize(Decimal("0.01"))
        computed_total += line_total

    # --- approved decision: any nonzero mismatch is a hard gate, not a
    # passive warning. No tolerance. ---
    mismatch_amount = None
    if data.invoice_total is not None:
        difference = (computed_total - data.invoice_total).quantize(Decimal("0.01"))
        if difference != 0:
            mismatch_amount = difference
            if not data.mismatch_acknowledged:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Purchase total (Rs. {computed_total}) does not match invoice total "
                        f"(Rs. {data.invoice_total}). Difference: Rs. {difference}. "
                        "Review the discrepancy and resubmit with mismatch_acknowledged=true if correct."
                    ),
                )

    purchase = Purchase(
        id=uuid.uuid4(),
        supplier_id=supplier.id,
        invoice_number=data.invoice_number,
        invoice_date=data.invoice_date,
        invoice_total=data.invoice_total,
        computed_total=computed_total,
        mismatch_acknowledged=data.mismatch_acknowledged,
        received_by_user_id=received_by.id,
        notes=data.notes,
    )
    db.add(purchase)
    db.flush()  # assigns purchase.id for use as movement reference below

    # --- lock/mutate products in CANONICAL ASCENDING product_id ORDER —
    # not request order — same deadlock-avoidance rule as sale_service,
    # applied here so a purchase and a sale touching overlapping products
    # concurrently can never deadlock each other (they always acquire
    # locks in the same global order). ---
    items_sorted = sorted(data.items, key=lambda item: str(item.product_id))

    for item in items_sorted:
        line_total = (item.quantity * item.unit_cost).quantize(Decimal("0.01"))

        product = adjust_stock(
            db,
            product_id=item.product_id,
            quantity_delta=item.quantity,
            movement_type=MovementType.PURCHASE,
            user=received_by,
            reference_type="purchase",
            reference_id=purchase.id,
        )

        db.add(
            PurchaseItem(
                id=uuid.uuid4(),
                purchase_id=purchase.id,
                product_id=product.id,
                product_name=product.name,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                line_total=line_total,
            )
        )

        # last_purchase_cost: fast-read cache, informational only (spec:
        # never authoritative — purchase_items ledger is).
        product.last_purchase_cost = item.unit_cost

        # preferred_supplier_id: only SET when currently null. Never
        # silently overwritten by a later purchase from a different
        # supplier — a product may genuinely have multiple suppliers.
        if product.preferred_supplier_id is None:
            old_value = {"preferred_supplier_id": None}
            product.preferred_supplier_id = supplier.id
            db.add(
                AuditLog(
                    id=uuid.uuid4(),
                    user_id=received_by.id,
                    action="PRODUCT_UPDATED",
                    entity_type="product",
                    entity_id=product.id,
                    old_value=json.dumps(old_value, default=str),
                    new_value=json.dumps({"preferred_supplier_id": str(supplier.id)}, default=str),
                    notes="Preferred supplier auto-set from first purchase received.",
                )
            )

        db.add(product)

    record_audit(
        db,
        user=received_by,
        action="PURCHASE_RECORDED",
        entity_type="purchase",
        entity_id=purchase.id,
        new_value=json.dumps(
            {"supplier": supplier.name, "computed_total": str(computed_total)}, default=str
        ),
        notes=(
            f"Invoice total mismatch: system Rs.{computed_total}, invoice Rs.{data.invoice_total}, "
            f"difference Rs.{mismatch_amount}, acknowledged={data.mismatch_acknowledged}"
            if mismatch_amount is not None
            else None
        ),
    )

    db.commit()
    db.refresh(purchase)
    return purchase


def record_purchase_payment(db: Session, purchase_id: uuid.UUID, data: PurchasePaymentIn, user: User) -> PurchasePayment:
    purchase = get_purchase(db, purchase_id)

    if data.amount > purchase.outstanding:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount exceeds outstanding balance. Outstanding: Rs. {purchase.outstanding}.",
        )

    payment = PurchasePayment(
        id=uuid.uuid4(),
        purchase_id=purchase.id,
        amount=data.amount,
        user_id=user.id,
        notes=data.notes,
    )
    db.add(payment)

    record_audit(
        db,
        user=user,
        action="SUPPLIER_PAYMENT_RECORDED",
        entity_type="purchase",
        entity_id=purchase.id,
        new_value=str(data.amount),
        notes=data.notes,
    )

    db.commit()
    db.refresh(payment)
    return payment


def get_purchase(db: Session, purchase_id: uuid.UUID) -> Purchase:
    purchase = db.get(Purchase, purchase_id)
    if purchase is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found.")
    return purchase
