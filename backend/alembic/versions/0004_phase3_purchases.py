"""Phase 3: suppliers, purchases, purchase items, purchase payments

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- suppliers ---
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("address_notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_suppliers_name", "suppliers", ["name"])

    # --- products: last_purchase_cost + preferred_supplier_id ---
    op.add_column("products", sa.Column("last_purchase_cost", sa.Numeric(12, 2), nullable=True))
    op.add_column(
        "products",
        sa.Column("preferred_supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id"), nullable=True),
    )

    # --- purchases ---
    op.create_table(
        "purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("invoice_number", sa.String(length=100), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("invoice_total", sa.Numeric(12, 2), nullable=True),
        sa.Column("computed_total", sa.Numeric(12, 2), nullable=False),
        # Approved decision: any nonzero mismatch is a hard backend gate.
        # This column records whether that gate was explicitly cleared,
        # so "was this discrepancy actually reviewed" is answerable later.
        sa.Column("mismatch_acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("received_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_purchases_supplier_id", "purchases", ["supplier_id"])

    # --- purchase_items ---
    op.create_table(
        "purchase_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchases.id"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_purchase_items_purchase_id", "purchase_items", ["purchase_id"])

    # --- purchase_payments ---
    # No UNIQUE(purchase_id) — 1:N, same reasoning as Payment being 1:N
    # from Sale (Phase 2): usually one full cash payment, but "we do not
    # normally pay advances" leaves room for a partial-payment exception.
    op.create_table(
        "purchase_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchases.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_purchase_payments_purchase_id", "purchase_payments", ["purchase_id"])


def downgrade() -> None:
    op.drop_index("ix_purchase_payments_purchase_id", table_name="purchase_payments")
    op.drop_table("purchase_payments")

    op.drop_index("ix_purchase_items_purchase_id", table_name="purchase_items")
    op.drop_table("purchase_items")

    op.drop_index("ix_purchases_supplier_id", table_name="purchases")
    op.drop_table("purchases")

    op.drop_column("products", "preferred_supplier_id")
    op.drop_column("products", "last_purchase_cost")

    op.drop_index("ix_suppliers_name", table_name="suppliers")
    op.drop_table("suppliers")
