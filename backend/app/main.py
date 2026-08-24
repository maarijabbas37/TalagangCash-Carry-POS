from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, products, users, counters, audit, sales, inventory, settings as settings_routes, suppliers, purchases
from app.core.config import settings

app = FastAPI(
    title=f"{settings.STORE_NAME} POS API",
    version="0.3.0",
    description="Phase 1: auth, roles, counters, product master. Phase 2: POS sales, inventory ledger, payments. Phase 3: suppliers, purchases, stock receiving.",
)

# Local-network LAN deployment (spec section 43) — POS clients on the same
# network hit this by IP/hostname; CORS kept permissive for LAN dev/deploy
# but should be tightened to explicit origins once client hosts are fixed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(counters.router)
app.include_router(audit.router)
app.include_router(sales.router)
app.include_router(inventory.router)
app.include_router(settings_routes.router)
app.include_router(suppliers.router)
app.include_router(purchases.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "store": settings.STORE_NAME}
