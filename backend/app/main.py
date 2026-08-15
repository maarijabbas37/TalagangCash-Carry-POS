from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, products, users, counters, audit
from app.core.config import settings

app = FastAPI(
    title=f"{settings.STORE_NAME} POS API",
    version="0.1.0",
    description="Phase 1: authentication, roles, counters, product master.",
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


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "store": settings.STORE_NAME}
