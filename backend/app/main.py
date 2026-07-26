from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    credentials,
    destination_locations,
    drivers,
    operation_types,
    planning,
    tenants,
    users,
    vehicles,
    warehouses,
)
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
app.include_router(users.router)
app.include_router(credentials.router)
app.include_router(operation_types.router)
app.include_router(warehouses.router)
app.include_router(destination_locations.router)
app.include_router(vehicles.router)
app.include_router(drivers.router)
app.include_router(planning.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
