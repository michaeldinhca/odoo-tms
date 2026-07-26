"""Distance from a warehouse to a destination location, computed at read
time (not stored — either side's coordinates can be edited after the
association is created, so a cached value would go stale silently)."""

from app.models.destination_location import DestinationLocation
from app.models.synced_warehouse import SyncedWarehouse
from app.services.planning.haversine import haversine_distance_km


def distance_km(warehouse: SyncedWarehouse, destination: DestinationLocation) -> float | None:
    if warehouse.lat is None or warehouse.lng is None:
        return None
    return haversine_distance_km(warehouse.lat, warehouse.lng, destination.lat, destination.lng)
