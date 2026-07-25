"""Orchestrates a single planning run: pull open pickings/vehicles from a
tenant's Odoo, run FFD assignment, then FILO sequencing per vehicle.

MVP runs synchronously within the `/planning/run` request — Redis is
provisioned in the stack (see ARCHITECTURE.md) but not yet used as an async
job queue; that's a Phase 2 concern once run volume/duration warrants it.

This module stays Odoo-only / DB-free on purpose (no SQLAlchemy Session) so
it's directly unit-testable against a fake Odoo client. Anything that needs
local Postgres data (which operation types are synced, resolving a picking's
warehouse) is looked up by the caller (app.api.planning) and passed in as
plain dicts/sets — see app.services.sync_config for that side.
"""

from app.services.odoo_client import OdooClient
from app.services.odoo_relational import parse_odoo_datetime, rel_id, rel_name
from app.services.planning.ffd import Address, Order, Vehicle, assign_orders_ffd
from app.services.planning.filo import sequence_filo
from app.services.planning.haversine import estimate_duration_min, haversine_distance_km


def fetch_open_orders(
    client: OdooClient,
    company_id: int | None = None,
    synced_operation_type_ids: set[int] | None = None,
    warehouse_by_picking_type: dict[int, dict] | None = None,
) -> list[Order]:
    """Pulls open stock.picking records and enriches them with customer,
    address, items, and warehouse context.

    `synced_operation_type_ids`: when given, only pickings whose
    `picking_type_id` is in this set are fetched — an empty set means "sync
    nothing yet" (no operation type has been opted in), not "no filter".
    `None` skips the filter entirely (used by tests that don't care about
    operation-type config). See DECISIONS.md "Operation type / warehouse
    sync gating".
    """
    if synced_operation_type_ids is not None and not synced_operation_type_ids:
        return []

    domain: list = [["state", "=", "assigned"]]
    if synced_operation_type_ids is not None:
        domain.append(["picking_type_id", "in", sorted(synced_operation_type_ids)])

    has_shipping_weight = client.has_field("stock.picking", "shipping_weight")
    fields = [
        "id",
        "partner_id",
        "state",
        "scheduled_date",
        "picking_type_id",
        "origin",
        "weight",
        "note",
    ]
    if has_shipping_weight:
        fields.append("shipping_weight")

    picking_records = client.search_read(
        "stock.picking", domain=domain, fields=fields, company_id=company_id
    )
    if not picking_records:
        return []

    picking_ids = [rec["id"] for rec in picking_records]
    partner_ids = sorted(
        {rel_id(rec.get("partner_id")) for rec in picking_records if rec.get("partner_id")}
    )

    partner_by_id: dict[int, dict] = {}
    if partner_ids:
        partner_records = client.search_read(
            "res.partner",
            domain=[["id", "in", partner_ids]],
            fields=["id", "street", "street2", "city", "state_id", "country_id", "zip"],
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
        picking_id = rel_id(move.get("picking_id"))
        if picking_id is None:
            continue
        product_name = rel_name(move.get("product_id"), default="Unknown item")
        qty = move.get("product_uom_qty") or 0
        items_by_picking.setdefault(picking_id, []).append(f"{product_name} x{qty:g}")

    orders: list[Order] = []
    for rec in picking_records:
        partner_id = rel_id(rec.get("partner_id"))
        partner = partner_by_id.get(partner_id) if partner_id is not None else None

        picking_type_id = rel_id(rec.get("picking_type_id"))
        warehouse_info = (
            (warehouse_by_picking_type or {}).get(picking_type_id, {})
            if picking_type_id is not None
            else {}
        )

        orders.append(
            Order(
                picking_id=rec["id"],
                weight_kg=rec.get("weight") or 0.0,
                volume_m3=0.0,  # TODO: no native volume field confirmed yet
                lat=0.0,  # TODO: source field not yet confirmed
                lon=0.0,  # TODO: source field not yet confirmed
                customer_name=rel_name(rec.get("partner_id")),
                items_summary="; ".join(items_by_picking.get(rec["id"], [])),
                address=Address(
                    street=(partner or {}).get("street") or "",
                    street2=(partner or {}).get("street2") or "",
                    city=(partner or {}).get("city") or "",
                    state_id=rel_id((partner or {}).get("state_id")),
                    state_name=rel_name((partner or {}).get("state_id")),
                    country_id=rel_id((partner or {}).get("country_id")),
                    country_name=rel_name((partner or {}).get("country_id")),
                    zip=(partner or {}).get("zip") or "",
                ),
                state=rec.get("state") or "",
                scheduled_date=parse_odoo_datetime(rec.get("scheduled_date")),
                picking_type_id=picking_type_id,
                warehouse_id=warehouse_info.get("warehouse_id"),
                warehouse_name=warehouse_info.get("warehouse_name", ""),
                origin=rec.get("origin") or "",
                shipping_weight=(rec.get("shipping_weight") if has_shipping_weight else None),
                note=rec.get("note") or "",
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
                "street": order.address.street,
                "street2": order.address.street2,
                "city": order.address.city,
                "state_id": order.address.state_id,
                "state_name": order.address.state_name,
                "country_id": order.address.country_id,
                "country_name": order.address.country_name,
                "zip": order.address.zip,
            },
            "state": order.state,
            "scheduled_date": order.scheduled_date.isoformat() if order.scheduled_date else None,
            "origin": order.origin,
            "warehouse_name": order.warehouse_name,
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


def run_planning_sync(
    client: OdooClient,
    company_id: int | None = None,
    synced_operation_type_ids: set[int] | None = None,
    warehouse_by_picking_type: dict[int, dict] | None = None,
) -> dict:
    """Runs the full pull -> FFD -> FILO pipeline. Returns a dict with
    `routes` / `unassigned_picking_ids` (matching `PlanningRunResult`, see
    app.schemas.planning) plus an `orders` key holding every fetched Order
    (assigned or not) for the caller to persist into `synced_pickings` — see
    app.services.picking_sync. `orders` is not part of the stored
    planning_runs.result_json; the API layer pops it before saving.
    """
    orders = fetch_open_orders(
        client,
        company_id=company_id,
        synced_operation_type_ids=synced_operation_type_ids,
        warehouse_by_picking_type=warehouse_by_picking_type,
    )
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
        "orders": orders,
    }
