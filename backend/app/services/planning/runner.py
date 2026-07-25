"""Orchestrates a single planning run: pull open pickings/vehicles from a
tenant's Odoo, run FFD assignment, then FILO sequencing per vehicle.

MVP runs synchronously within the `/planning/run` request — Redis is
provisioned in the stack (see ARCHITECTURE.md) but not yet used as an async
job queue; that's a Phase 2 concern once run volume/duration warrants it.
"""

from app.services.odoo_client import OdooClient
from app.services.planning.ffd import Order, Vehicle, assign_orders_ffd
from app.services.planning.filo import sequence_filo
from app.services.planning.haversine import estimate_duration_min, haversine_distance_km


def fetch_open_orders(client: OdooClient) -> list[Order]:
    # TODO: confirm real Odoo 19 field names — see SPEC.md "Odoo field mappings".
    records = client.search_read(
        "stock.picking",
        domain=[["state", "=", "assigned"]],
        fields=["id", "partner_id"],
    )
    orders: list[Order] = []
    for rec in records:
        orders.append(
            Order(
                picking_id=rec["id"],
                weight_kg=0.0,  # TODO: source field not yet confirmed
                volume_m3=0.0,  # TODO: source field not yet confirmed
                lat=0.0,  # TODO: source field not yet confirmed
                lon=0.0,  # TODO: source field not yet confirmed
            )
        )
    return orders


def fetch_vehicles(client: OdooClient) -> list[Vehicle]:
    # TODO: confirm real Odoo 19 field names — see SPEC.md "Odoo field mappings".
    records = client.search_read(
        "fleet.vehicle",
        domain=[],
        fields=["id"],
    )
    vehicles: list[Vehicle] = []
    for rec in records:
        vehicles.append(
            Vehicle(
                vehicle_id=rec["id"],
                capacity_weight_kg=0.0,  # TODO: source field not yet confirmed
                capacity_volume_m3=0.0,  # TODO: source field not yet confirmed
            )
        )
    return vehicles


def build_route(vehicle_id: int, sequenced_orders: list[Order]) -> dict:
    stops = [
        {"stop_order": i + 1, "picking_id": order.picking_id}
        for i, order in enumerate(sequenced_orders)
    ]

    total_distance_km = 0.0
    for prev_order, next_order in zip(sequenced_orders, sequenced_orders[1:]):
        total_distance_km += haversine_distance_km(
            prev_order.lat, prev_order.lon, next_order.lat, next_order.lon
        )

    return {
        "vehicle_id": vehicle_id,
        "sequence": stops,
        "estimated_distance_km": round(total_distance_km, 3),
        "estimated_duration_min": round(estimate_duration_min(total_distance_km), 1),
    }


def run_planning_sync(client: OdooClient) -> dict:
    """Runs the full pull -> FFD -> FILO pipeline and returns a plain dict
    matching the `PlanningRunResult.routes` / `unassigned_picking_ids` shape
    (see app.schemas.planning).
    """
    orders = fetch_open_orders(client)
    vehicles = fetch_vehicles(client)

    assignments, unassigned = assign_orders_ffd(orders, vehicles)

    routes = []
    for assignment in assignments:
        if not assignment.assigned_orders:
            continue
        sequenced = sequence_filo(assignment.assigned_orders)
        routes.append(build_route(assignment.vehicle_id, sequenced))

    return {
        "routes": routes,
        "unassigned_picking_ids": [o.picking_id for o in unassigned],
    }
