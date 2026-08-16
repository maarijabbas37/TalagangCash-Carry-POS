"""
Shared pytest fixtures.

Each test gets its own fresh in-memory SQLite database (tables created
from the real SQLAlchemy models via Base.metadata, same models Alembic
migrates in production) — fast, fully isolated, no shared state between
tests. This mirrors Postgres closely enough for auth/RBAC/validation
logic; anything genuinely Postgres-specific (row locking, concurrency)
is out of scope for Phase 1's test suite and will need real-Postgres
integration tests once Phase 2 introduces concurrent stock writes.

StaticPool + check_same_thread=False keeps the same in-memory DB alive
across the multiple connections SQLAlchemy/FastAPI open during a test.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.base_class_imports  # noqa: F401 - registers all models on Base.metadata
from app.api.deps import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.user import Counter, RoleName, User


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        # Mirrors production's get_db(): production closes the session in
        # a `finally` after every request, which implicitly rolls back any
        # uncommitted work if a route raised mid-transaction. Here we keep
        # the session OPEN across the whole test (fixtures share it), but
        # still roll back on exception — otherwise a failed request's
        # flushed-but-uncommitted rows would remain visible to later
        # queries on this same session, which is not how production
        # behaves and would make atomicity tests give false negatives.
        try:
            yield db_session
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def counter1(db_session):
    counter = Counter(id=uuid.uuid4(), name="Counter 1", code="01")
    db_session.add(counter)
    db_session.commit()
    db_session.refresh(counter)
    return counter


@pytest.fixture()
def counter2(db_session):
    counter = Counter(id=uuid.uuid4(), name="Counter 2", code="02")
    db_session.add(counter)
    db_session.commit()
    db_session.refresh(counter)
    return counter


@pytest.fixture()
def inactive_counter(db_session):
    counter = Counter(id=uuid.uuid4(), name="Old Counter", code="99", is_active=False)
    db_session.add(counter)
    db_session.commit()
    db_session.refresh(counter)
    return counter


@pytest.fixture()
def owner_user(db_session, counter1):
    user = User(
        id=uuid.uuid4(),
        username="abbu",
        full_name="Abbu",
        hashed_password=hash_password("ownerpass123"),
        role=RoleName.OWNER,
        default_counter_id=counter1.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def employee_user(db_session, counter2):
    user = User(
        id=uuid.uuid4(),
        username="employee",
        full_name="Employee",
        hashed_password=hash_password("employeepass123"),
        role=RoleName.EMPLOYEE,
        default_counter_id=counter2.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def inactive_user(db_session, counter2):
    user = User(
        id=uuid.uuid4(),
        username="old_employee",
        full_name="Old Employee",
        hashed_password=hash_password("password123"),
        role=RoleName.EMPLOYEE,
        default_counter_id=counter2.id,
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def get_auth_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", data={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def owner_headers(client, owner_user):
    return get_auth_headers(client, "abbu", "ownerpass123")


@pytest.fixture()
def employee_headers(client, employee_user):
    return get_auth_headers(client, "employee", "employeepass123")


@pytest.fixture()
def product_with_stock(db_session, owner_user):
    """A product with 10 units of stock, via a real OPENING_STOCK movement
    (not a raw field write) so the ledger and current_stock start in sync."""
    from decimal import Decimal

    from app.models.inventory import InventoryMovement, MovementType
    from app.models.product import Product

    product = Product(
        id=uuid.uuid4(),
        name="Surf Excel 90g",
        barcode="123456789",
        unit="pcs",
        sale_price=Decimal("110.00"),
        reorder_level=15,
        current_stock=Decimal("10"),
    )
    db_session.add(product)
    db_session.flush()
    db_session.add(
        InventoryMovement(
            id=uuid.uuid4(),
            product_id=product.id,
            quantity=Decimal("10"),
            movement_type=MovementType.OPENING_STOCK,
            reference_type="opening_stock",
            user_id=owner_user.id,
        )
    )
    db_session.commit()
    db_session.refresh(product)
    return product
