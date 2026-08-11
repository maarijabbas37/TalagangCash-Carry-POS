"""
Users, roles, and counters — Phase 1 identity/access model.

Design notes (deliberate decisions, documented per spec section 72):
- Role is a small fixed enum-backed table (OWNER, EMPLOYEE) rather than a
  free-form permissions table. The spec defines exactly two practical roles
  today; a full RBAC permission-matrix table would be premature complexity
  for a two-role store system. Section-4 permissions are enforced in code
  (see app/api/deps.py) keyed off this role, not stored per-permission in
  the DB. If a third role or granular per-user overrides are ever needed,
  this is the seam to extend.
- Counter is a separate lookup table (not a raw string) because sales,
  users' default counters, and future multi-counter reporting all need a
  stable FK, and the store may add a Counter 3 later without a migration
  that touches every table that references "counter name".
- User.default_counter_id is nullable: a login doesn't have to be pinned to
  a counter at the account level if the store ever wants a user to float
  between counters, though today Abbu = Counter 1, Employee = Counter 2.
"""
import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class RoleName(str, enum.Enum):
    OWNER = "OWNER"
    EMPLOYEE = "EMPLOYEE"


class Counter(Base, TimestampMixin):
    __tablename__ = "counters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # "Counter 1"
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)  # "01"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Counter {self.name}>"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleName] = mapped_column(Enum(RoleName, name="role_name"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    default_counter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counters.id"), nullable=True
    )
    default_counter: Mapped["Counter | None"] = relationship("Counter")

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"
