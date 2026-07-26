"""Distance from a warehouse to a destination location, computed at read
time (not stored — either side's coordinates can be edited after the
association is created, so a cached value would go stale silently)."""

import uuid

from sqlalchemy.orm import Session

from app.models.destination_location import DestinationLocation
from app.models.synced_warehouse import SyncedWarehouse
from app.services.planning.ffd import Order
from app.services.planning.haversine import haversine_distance_km


def distance_km(warehouse: SyncedWarehouse, destination: DestinationLocation) -> float | None:
    if (
        warehouse.lat is None
        or warehouse.lng is None
        or destination.lat is None
        or destination.lng is None
    ):
        return None
    return haversine_distance_km(warehouse.lat, warehouse.lng, destination.lat, destination.lng)


def normalize_address_key(
    name: str, street: str, street2: str, city: str, state: str, country: str, zip_code: str
) -> tuple[str, ...]:
    """Shared "is this the same place" comparison key — Odoo's free-text
    address fields aren't normalized at sync time, so two mentions of the
    same address can differ by case/whitespace alone. Used both to dedupe
    the picking-address prefill list and to decide whether a picking's
    address already has a matching DestinationLocation before auto-adding
    one (see app.services.picking_sync)."""
    fields = (name, street, street2, city, state, country, zip_code)
    return tuple(value.strip().lower() for value in fields)


def auto_create_destinations_from_orders(
    db: Session, tenant_id: uuid.UUID, orders: list[Order]
) -> list[DestinationLocation]:
    """Called after every planning run's pickings are synced (see
    app.api.planning) — for each order whose address doesn't already
    match an existing DestinationLocation, creates one with null
    lat/lng (an admin fills those in later; see DestinationLocation's
    docstring for why null is meaningful here, not just "not entered
    yet"). Orders with no resolved customer name are skipped — an empty
    label wouldn't be a useful library entry regardless of what address
    data came with it. Matching uses the same normalize_address_key as
    the picking-address prefill list, so "already exists" means the same
    thing in both places. Does not commit — the caller controls the
    transaction (same pattern as upsert_synced_pickings's own caller)."""
    existing = db.query(DestinationLocation).filter_by(tenant_id=tenant_id).all()
    seen_keys = {
        normalize_address_key(d.name, d.street, d.street2, d.city, d.state, d.country, d.zip)
        for d in existing
    }

    created: list[DestinationLocation] = []
    for order in orders:
        if not order.customer_name.strip():
            continue

        key = normalize_address_key(
            order.customer_name,
            order.address.street,
            order.address.street2,
            order.address.city,
            order.address.state_name,
            order.address.country_name,
            order.address.zip,
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)  # avoid duplicate creates within this same batch

        destination = DestinationLocation(
            tenant_id=tenant_id,
            name=order.customer_name,
            street=order.address.street,
            street2=order.address.street2,
            city=order.address.city,
            state=order.address.state_name,
            country=order.address.country_name,
            zip=order.address.zip,
            lat=None,
            lng=None,
        )
        db.add(destination)
        created.append(destination)

    return created
