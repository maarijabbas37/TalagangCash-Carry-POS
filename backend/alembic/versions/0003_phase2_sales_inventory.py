"""Phase 2: inventory movements, sales, sale items, payments, bill sequence

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- products.current_stock, with a DB-level non-negative guarantee ---
    # This CHECK constraint is independent of application code: even a
    # future bug in the service layer or a bypassed code path cannot make
    # current_stock negative — Postgres itself rejects the UPDATE.
    op.add_column("products", sa.Column("current_stock", sa.Numeric(12, 3), nullable=False, server_default="0"))
    op.create_check_constraint(
        "ck_products_current_stock_non_negative", "products", "current_stock >= 0"
    )

    # --- inventory_movements: the ledger (source of truth for stock) ---
    movement_type_enum = postgresql.ENUM(
        "OPENING_STOCK", "PURCHASE", "SALE", "CUSTOMER_RETURN",
        "SUPPLIER_RETURN", "STOCK_ADJUSTMENT", "PACKING_IN", "PACKING_OUT",
        name="movement_type",
    )
    movement_type_enum.create(op.get_bind(), checkfirst=True)
    movement_type_enum.create_type = False  # see migration 0001 for why

    op.create_table(
        "inventory_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("movement_type", movement_type_enum, nullable=False),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inventory_movements_product_id", "inventory_movements", ["product_id"])
    op.create_index("ix_inventory_movements_reference_id", "inventory_movements", ["reference_id"])

    # --- bill_sequence: single locked-counter row for bill numbering ---
    # Deliberately not a native Postgres SEQUENCE — see app/models/sale.py
    # docstring: a sequence's advancement survives a rolled-back
    # transaction (leaving gaps on failed sales); a locked table row does
    # not, because it's part of the same transaction as the sale itself.
    op.create_table(
        "bill_sequence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_number", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute("INSERT INTO bill_sequence (id, last_number) VALUES (1, 0)")

    # --- sales ---
    op.create_table(
        "sales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bill_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("counter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("counters.id"), nullable=False),
        sa.Column("cashier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("discount_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("net_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sales_bill_number", "sales", ["bill_number"])

    # --- sale_items ---
    op.create_table(
        "sale_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sales.id"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sale_items_sale_id", "sale_items", ["sale_id"])

    # --- payments ---
    # No UNIQUE(sale_id) — deliberately 1:N architecture. See
    # app/models/payment.py docstring (Phase 2 review amendment #5).
    payment_method_enum = postgresql.ENUM("CASH", "QR", name="payment_method")
    payment_method_enum.create(op.get_bind(), checkfirst=True)
    payment_method_enum.create_type = False  # see migration 0001 for why

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sales.id"), nullable=False),
        sa.Column("payment_method", payment_method_enum, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_received", sa.Numeric(12, 2), nullable=True),
        sa.Column("change_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("payment_reference", sa.String(length=100), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("counter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("counters.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payments_sale_id", "payments", ["sale_id"])


def downgrade() -> None:
    op.drop_index("ix_payments_sale_id", table_name="payments")
    op.drop_table("payments")
    postgresql.ENUM(name="payment_method").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_sale_items_sale_id", table_name="sale_items")
    op.drop_table("sale_items")

    op.drop_index("ix_sales_bill_number", table_name="sales")
    op.drop_table("sales")

    op.drop_table("bill_sequence")

    op.drop_index("ix_inventory_movements_reference_id", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_product_id", table_name="inventory_movements")
    op.drop_table("inventory_movements")
    postgresql.ENUM(name="movement_type").drop(op.get_bind(), checkfirst=True)

    op.drop_constraint("ck_products_current_stock_non_negative", "products", type_="check")
    op.drop_column("products", "current_stock")
