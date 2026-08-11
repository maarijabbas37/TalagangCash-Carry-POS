# Talagang Cash & Carry — POS & Inventory System

Phase 1 delivery: authentication, roles, counters, and the product master.
This is the foundation the POS, inventory ledger, purchases, and everything
else in later phases is built on.

## What's in Phase 1

- **Backend**: FastAPI + SQLAlchemy 2.x + Alembic + PostgreSQL
  - JWT-based login, Argon2 password hashing
  - `OWNER` / `EMPLOYEE` roles enforced server-side on every protected route
  - `Counter` model (Counter 1 / Counter 2) ready for Phase 2 sales to reference
  - Product master: create, search, edit, and a dedicated owner-only
    price-change endpoint that always writes to price history
  - Friendly, non-leaking error messages (e.g. duplicate barcode)
- **Frontend**: React + TypeScript + Vite + Tailwind + React Query
  - Login screen
  - Role-aware sidebar nav (owner-only items hidden from employees)
  - Products page: search, add, list — wired to the real API, no mock data
- **Docker Compose**: Postgres + backend + frontend, one command to run locally

## What's deliberately NOT in Phase 1

POS billing, barcode scanning, sales, inventory ledger, purchases,
suppliers, returns, packing, cash drawer, day-end, dashboards, and reports
are Phase 2 onward, per the phased build plan. Building them now against a
Phase 1 schema would mean redoing them once the inventory ledger design is
finalized in Phase 3.

## Decisions made and documented (from the discovery conversation)

These were explicitly settled before writing code, and are documented at
the point in the code where they matter — see the comments referenced below:

1. **Purchase entry**: available to every Employee, no per-user
   authorization flag. Flat role permission (see `app/api/routes/products.py`
   docstring — purchases arrive in Phase 3, but the same flat-role pattern
   is used here for "Add Product").
2. **Packing cost basis** (Phase 5, not built yet, but locked in now):
   weighted-average cost of the bulk stock being packed, *not* FIFO layer
   tracking. Sale-side COGS still uses FIFO — these are two different
   methods used in two different places, intentionally.
3. **QR/online payments** (Phase 2, not built yet): cashier manually
   confirms, no gateway integration, no reference-number verification.
   Accepted risk, not an oversight — revisit if fraud becomes a problem.
4. **Adding new products**: any authenticated user (owner or employee) can
   create a product, since employees add unlisted items while receiving
   purchases. Only the *owner* can change an *existing* product's price
   (`PUT /api/products/{id}/price`). If this split doesn't match how the
   store actually works, it's a one-line permission change.

## Quick start (Docker)

```bash
cp backend/.env.example backend/.env
cp .env.example .env
# edit backend/.env: set a real JWT_SECRET_KEY and DB password before
# anything beyond local testing

docker compose up --build
```

- Backend API: http://localhost:8000/docs (interactive OpenAPI docs)
- Frontend: http://localhost:5173

On first boot the backend runs migrations and seeds two accounts:

| Username | Password (seeded — CHANGE IMMEDIATELY) | Role     | Counter   |
|----------|------------------------------------------|----------|-----------|
| abbu     | value of `SEED_ADMIN_PASSWORD` in `.env`  | OWNER    | Counter 1 |
| employee | `change_me_too`                           | EMPLOYEE | Counter 2 |

## Local development (without Docker)

**Backend**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then edit DATABASE_URL to point at a local Postgres
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Testing what's here

The backend was verified with an end-to-end smoke test (login → JWT →
protected routes → role enforcement → duplicate-barcode conflict → price
history) before this was written up. A `pytest`-based automated suite
belongs in Phase 8 per the spec's phased plan, but nothing here shipped
unverified — see `backend/requirements-dev.txt` for the test tooling
already wired in (`pytest`, `httpx` for `TestClient`).

## Project layout

```
backend/
  app/
    core/       # config, JWT, password hashing
    db/         # SQLAlchemy engine/session, declarative base
    models/     # User, Role, Counter, Product, ProductPriceHistory
    schemas/    # Pydantic request/response models
    api/
      deps.py   # get_current_user, require_owner — single source of truth
                # for role enforcement
      routes/   # auth, users, products
    services/   # business logic (kept out of route handlers)
  alembic/      # migrations
  seed.py
  Dockerfile

frontend/
  src/
    api/        # axios client with auth interceptor
    hooks/      # useAuth
    routes/     # ProtectedRoute (role-gated)
    layouts/    # MainLayout (role-aware sidebar)
    pages/      # Login, Dashboard (POS placeholder), Products
```

## Next: Phase 2

POS billing screen, barcode/internal-code product entry, cart, discounts
(with authorization + audit logging), cash and QR payment, atomic sale
transactions, receipt generation/printing, and reprint — per spec sections
7–12.
