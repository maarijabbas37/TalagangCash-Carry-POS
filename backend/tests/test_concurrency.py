"""
Phase 2 architecture review §8 (mandatory): concurrent sale tests against
REAL PostgreSQL — not SQLite. This file exists because SQLite's locking
model does not meaningfully exercise SELECT ... FOR UPDATE contention
between separate connections the way Postgres does; the guarantee this
whole architecture rests on (§4: "the database must prevent both
transactions from successfully selling the same single unit") can only
be genuinely tested against the real database engine.

These tests are skipped automatically if no Postgres test database is
reachable (set POSTGRES_TEST_URL to point at one; defaults to the local
instance used during development). They are NOT part of the fast default
loop — run them explicitly:

    POSTGRES_TEST_URL=postgresql+psycopg2://user:pass@host/db pytest tests/test_concurrency.py -v

against a real, disposable Postgres database before any deploy that
touches sale_service.py or inventory_service.py.
"""
import os
import threading
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

POSTGRES_TEST_URL = os.environ.get(
    "POSTGRES_TEST_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/talagang_test"
)


def _postgres_available() -> bool:
    try:
        engine = create_engine(POSTGRES_TEST_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"No reachable Postgres test database at {POSTGRES_TEST_URL} — concurrency tests need a real Postgres instance.",
)


@pytest.fixture()
def pg_engine():
    engine = create_engine(POSTGRES_TEST_URL, pool_size=10, max_overflow=10)
    yield engine
    engine.dispose()


@pytest.fixture()
def pg_session_factory(pg_engine):
    return sessionmaker(bind=pg_engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture()
def pg_fixtures(pg_session_factory):
    """
    Creates a real Owner user, two real Counters, and returns everything
    needed to build products against the real Postgres test DB. Cleans up
    its own rows afterward so repeated runs don't accumulate garbage
    (bill_sequence is process-wide and intentionally NOT reset — sales
    just keep incrementing across test runs, which is correct behavior,
    not a leak).
    """
    from app.core.security import hash_password
    from app.models.user import Counter, RoleName, User

    session = pg_session_factory()
    owner = User(
        id=uuid.uuid4(),
        username=f"concurrency_owner_{uuid.uuid4().hex[:8]}",
        full_name="Concurrency Test Owner",
        hashed_password=hash_password("testpass123"),
        role=RoleName.OWNER,
    )
    counter1 = Counter(id=uuid.uuid4(), name=f"Concurrency Counter 1 {uuid.uuid4().hex[:6]}", code=f"C1{uuid.uuid4().hex[:6]}")
    counter2 = Counter(id=uuid.uuid4(), name=f"Concurrency Counter 2 {uuid.uuid4().hex[:6]}", code=f"C2{uuid.uuid4().hex[:6]}")
    session.add_all([owner, counter1, counter2])
    session.commit()

    yield {"owner": owner, "counter1": counter1, "counter2": counter2}

    # Cleanup — delete everything this test created, in FK-safe order.
    from app.models.audit import AuditLog
    from app.models.inventory import InventoryMovement
    from app.models.payment import Payment
    from app.models.product import Product
    from app.models.sale import Sale, SaleItem

    cleanup = pg_session_factory()
    cleanup.query(AuditLog).filter(AuditLog.user_id == owner.id).delete()
    sale_ids = [s.id for s in cleanup.query(Sale).filter(Sale.cashier_id == owner.id).all()]
    cleanup.query(Payment).filter(Payment.sale_id.in_(sale_ids)).delete(synchronize_session=False)
    cleanup.query(SaleItem).filter(SaleItem.sale_id.in_(sale_ids)).delete(synchronize_session=False)
    cleanup.query(Sale).filter(Sale.cashier_id == owner.id).delete()
    cleanup.query(InventoryMovement).filter(InventoryMovement.user_id == owner.id).delete()
    cleanup.query(Product).filter(Product.name.like("ConcurrencyTest%")).delete()
    cleanup.query(User).filter(User.id == owner.id).delete()  # noqa: F821 (imported above via module scope)
    cleanup.query(Counter).filter(Counter.id.in_([counter1.id, counter2.id])).delete()  # noqa: F821
    cleanup.commit()
    cleanup.close()
    session.close()


def _make_product(session_factory, owner, name: str, stock: str) -> uuid.UUID:
    from app.models.inventory import InventoryMovement, MovementType
    from app.models.product import Product

    session = session_factory()
    product = Product(
        id=uuid.uuid4(), name=name, unit="pcs", sale_price=Decimal("100.00"), current_stock=Decimal(stock)
    )
    session.add(product)
    session.flush()
    session.add(
        InventoryMovement(
            id=uuid.uuid4(),
            product_id=product.id,
            quantity=Decimal(stock),
            movement_type=MovementType.OPENING_STOCK,
            user_id=owner.id,
        )
    )
    session.commit()
    product_id = product.id
    session.close()
    return product_id


def test_two_counters_cannot_both_sell_the_last_unit(pg_session_factory, pg_fixtures):
    """
    THE core guarantee (spec §4 / architecture §4): stock=1, two counters
    attempt to sell it "at the same time." Exactly one must succeed.
    """
    from app.models.user import User
    from app.schemas.sale import SaleCreate, SaleItemIn
    from app.services.sale_service import create_sale

    owner = pg_fixtures["owner"]
    counter1, counter2 = pg_fixtures["counter1"], pg_fixtures["counter2"]
    product_id = _make_product(pg_session_factory, owner, "ConcurrencyTest LastUnit", "1")

    results = {}

    def attempt(name: str, counter_id: uuid.UUID):
        session = pg_session_factory()
        try:
            cashier = session.get(User, owner.id)
            sale = create_sale(
                session,
                SaleCreate(
                    items=[SaleItemIn(product_id=product_id, quantity=Decimal("1"))],
                    payment_method="CASH",
                    amount_received=Decimal("100.00"),
                    counter_id=counter_id,
                ),
                cashier,
            )
            results[name] = ("success", sale.bill_number)
        except Exception as exc:  # HTTPException from insufficient stock, or any DB error
            results[name] = ("failed", getattr(exc, "detail", str(exc)))
        finally:
            session.close()

    t1 = threading.Thread(target=attempt, args=("counter1", counter1.id))
    t2 = threading.Thread(target=attempt, args=("counter2", counter2.id))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    outcomes = [results["counter1"][0], results["counter2"][0]]
    assert outcomes.count("success") == 1, f"Expected exactly one success, got: {results}"
    assert outcomes.count("failed") == 1, f"Expected exactly one failure, got: {results}"

    failed_key = "counter1" if results["counter1"][0] == "failed" else "counter2"
    assert "insufficient stock" in str(results[failed_key][1]).lower()

    # Final stock must be exactly 0 — never negative, never double-sold.
    verify_session = pg_session_factory()
    from app.models.product import Product

    final_product = verify_session.get(Product, product_id)
    assert Decimal(str(final_product.current_stock)) == Decimal("0")
    verify_session.close()


def test_concurrent_sales_with_overlapping_products_do_not_deadlock(pg_session_factory, pg_fixtures):
    """
    Deadlock-avoidance test (architecture §4): Sale A = [X, Y], Sale B =
    [Y, X] (reverse cart order), fired concurrently, with enough stock for
    both. The canonical ascending-product-id lock ordering in
    sale_service.create_sale means both transactions request locks in the
    SAME order regardless of cart order, so one simply waits behind the
    other instead of both waiting on each other. Both must complete
    within a short timeout — a real deadlock would hang until Postgres's
    deadlock_timeout (~1s) kills one side with an error, which this test
    would also catch (an unexpected 'failed' outcome).
    """
    from app.models.user import User
    from app.schemas.sale import SaleCreate, SaleItemIn
    from app.services.sale_service import create_sale

    owner = pg_fixtures["owner"]
    counter1, counter2 = pg_fixtures["counter1"], pg_fixtures["counter2"]
    product_x = _make_product(pg_session_factory, owner, "ConcurrencyTest ProductX", "5")
    product_y = _make_product(pg_session_factory, owner, "ConcurrencyTest ProductY", "5")

    results = {}

    def attempt(name: str, counter_id: uuid.UUID, items_order: list[uuid.UUID]):
        session = pg_session_factory()
        try:
            cashier = session.get(User, owner.id)
            sale = create_sale(
                session,
                SaleCreate(
                    items=[SaleItemIn(product_id=pid, quantity=Decimal("1")) for pid in items_order],
                    payment_method="CASH",
                    amount_received=Decimal("1000.00"),
                    counter_id=counter_id,
                ),
                cashier,
            )
            results[name] = ("success", sale.bill_number)
        except Exception as exc:
            results[name] = ("failed", getattr(exc, "detail", str(exc)))
        finally:
            session.close()

    # Sale A adds X then Y; Sale B adds Y then X — the exact scenario that
    # deadlocks without canonical lock ordering.
    t1 = threading.Thread(target=attempt, args=("sale_a", counter1.id, [product_x, product_y]))
    t2 = threading.Thread(target=attempt, args=("sale_b", counter2.id, [product_y, product_x]))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert not t1.is_alive(), "Sale A thread did not finish — likely deadlocked"
    assert not t2.is_alive(), "Sale B thread did not finish — likely deadlocked"
    assert results["sale_a"][0] == "success", results["sale_a"]
    assert results["sale_b"][0] == "success", results["sale_b"]

    verify_session = pg_session_factory()
    from app.models.product import Product

    final_x = verify_session.get(Product, product_x)
    final_y = verify_session.get(Product, product_y)
    assert Decimal(str(final_x.current_stock)) == Decimal("3")  # 5 - 1 - 1
    assert Decimal(str(final_y.current_stock)) == Decimal("3")
    verify_session.close()
