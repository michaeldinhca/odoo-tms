from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, credentials, planning, tenants
from app.core.config import settings

app = FastAPI(title="odoo-tms API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(credentials.router)
app.include_router(planning.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
