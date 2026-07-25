"""Orchestrates a single planning run: pull open pickings/vehicles from a
tenant's Odoo, run FFD assignment, then FILO sequencing per vehicle.

MVP runs synchronously within the `/planning/run` request — Redis is
provisioned in the stack (see ARCHITECTURE.md) but not yet used as an async
job queue; that's a Phase 2 concern once run volume/duration warrants it.
"""

from typing import Any

from app.services.odoo_client import OdooClient
from app.services.planning.ffd import Address, Order, Vehicle, assign_orders_ffd
from app.services.planning.filo import sequence_filo
from app.services.planning.haversine import estimate_duration_min, haversine_distance_km


def _rel_id(value: Any) -> int | None:
    """Odoo many2one fields come back as `[id, display_name]`, or `False`
    when unset."""
    return value[0] if value else None


def _rel_name(value: Any, default: str = "") -> str:
    return value[1] if value else default


def fetch_open_orders(client: OdooClient, company_id: int | None = None) -> list[Order]:
    # TODO: confirm real Odoo 19 field names — see SPEC.md "Odoo field mappings".
    picking_records = client.search_read(
        "stock.picking",
        domain=[["state", "=", "assigned"]],
        fields=["id", "partner_id"],
        company_id=company_id,
    )
    if not picking_records:
        return []

    picking_ids = [rec["id"] for rec in picking_records]
    partner_ids = sorted(
        {_rel_id(rec.get("partner_id")) for rec in picking_records if rec.get("partner_id")}
    )

    partner_by_id: dict[int, dict] = {}
    if partner_ids:
        partner_records = client.search_read(
            "res.partner",
            domain=[["id", "in", partner_ids]],
            fields=["id", "street", "street2", "city", "zip", "country_id"],
            company_id=company_id,
        )
        partner_by_id = {p["id"]: p for p in partner_records}

    # TODO: confirm the real Odoo 19 model/field names for a picking's item
    # lines — see SPEC.md "Odoo field mappings". stock.move is the most
    # standard candidate; some setups may need stock.move.line instead.
    items_by_picking: dict[int, list[str]] = {}
    move_records = client.search_read(
        "stock.move",
        domain=[["picking_id", "in", picking_ids]],
        fields=["picking_id", "product_id", "product_uom_qty"],
        company_id=company_id,
    )
    for move in move_records:
        picking_id = _rel_id(move.get("picking_id"))
        if picking_id is None:
            continue
        product_name = _rel_name(move.get("product_id"), default="Unknown item")
        qty = move.get("product_uom_qty") or 0
        items_by_picking.setdefault(picking_id, []).append(f"{product_name} x{qty:g}")

    orders: list[Order] = []
    for rec in picking_records:
        partner_id = _rel_id(rec.get("partner_id"))
        partner = partner_by_id.get(partner_id) if partner_id is not None else None

        orders.append(
            Order(
                picking_id=rec["id"],
                weight_kg=0.0,  # TODO: source field not yet confirmed
                volume_m3=0.0,  # TODO: source field not yet confirmed
                lat=0.0,  # TODO: source field not yet confirmed
                lon=0.0,  # TODO: source field not yet confirmed
                customer_name=_rel_name(rec.get("partner_id")),
                items_summary="; ".join(items_by_picking.get(rec["id"], [])),
                address=Address(
                    street1=(partner or {}).get("street") or "",
                    street2=(partner or {}).get("street2") or "",
                    city=(partner or {}).get("city") or "",
                    country=_rel_name((partner or {}).get("country_id")),
                    zip=(partner or {}).get("zip") or "",
                ),
            )
        )
    return orders


def fetch_vehicles(client: OdooClient, company_id: int | None = None) -> list[Vehicle]:
    # TODO: confirm real Odoo 19 field names — see SPEC.md "Odoo field mappings".
    records = client.search_read(
        "fleet.vehicle",
        domain=[],
        fields=["id"],
        company_id=company_id,
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
        {
            "stop_order": i + 1,
            "picking_id": order.picking_id,
            "customer_name": order.customer_name,
            "items_summary": order.items_summary,
            "address": {
                "street1": order.address.street1,
                "street2": order.address.street2,
                "city": order.address.city,
                "country": order.address.country,
                "zip": order.address.zip,
            },
        }
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


def run_planning_sync(client: OdooClient, company_id: int | None = None) -> dict:
    """Runs the full pull -> FFD -> FILO pipeline and returns a plain dict
    matching the `PlanningRunResult.routes` / `unassigned_picking_ids` shape
    (see app.schemas.planning).
    """
    orders = fetch_open_orders(client, company_id=company_id)
    vehicles = fetch_vehicles(client, company_id=company_id)

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
