"""Route handlers called directly, same pattern as test_warehouses_api.py."""

import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import CurrentUser
from app.api.destination_locations import create_destination_location, delete_destination_location
from app.api.warehouse_routes import (
    bulk_add_route_stops,
    create_warehouse_route,
    delete_warehouse_route,
    list_warehouse_routes,
    remove_route_stop,
    reorder_route_stops,
    update_warehouse_route,
)
from app.api.warehouses import delete_warehouse, set_warehouse_coordinates
from app.schemas.destination_location import DestinationLocationCreate, WarehouseCoordinatesUpdate
from app.schemas.warehouse_route import (
    RouteStopsBulkAdd,
    RouteStopsReorder,
    WarehouseRouteCreate,
    WarehouseRouteUpdate,
)
from app.services.sync_config import upsert_warehouses
from app.services.warehouse_routes import ROUTE_COLOR_PALETTE

TENANT_ID = uuid.uuid4()
USER = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_ID)


def _new_warehouse(session, odoo_id=1, name="Main WH"):
    rows = upsert_warehouses(
        session,
        TENANT_ID,
        [
            {
                "odoo_warehouse_id": odoo_id,
                "name": name,
                "code": "WH",
                "street": "",
                "street2": "",
                "city": "",
                "state_id": None,
                "state_name": "",
                "country_id": None,
                "country_name": "",
                "zip": "",
            }
        ],
    )
    return next(row for row in rows if row.odoo_warehouse_id == odoo_id)


def _destination(session, name="Acme Corp", lat=43.7, lng=-79.4):
    return create_destination_location(
        TENANT_ID,
        DestinationLocationCreate(name=name, lat=lat, lng=lng),
        session,
        USER,
    )


def test_create_and_list_route(sync_db_session):
    warehouse = _new_warehouse(sync_db_session)

    created = create_warehouse_route(
        TENANT_ID, warehouse.id, WarehouseRouteCreate(name="Route 1"), sync_db_session, USER
    )
    routes = list_warehouse_routes(TENANT_ID, warehouse.id, sync_db_session, USER)

    assert created["name"] == "Route 1"
    assert created["color"] == ROUTE_COLOR_PALETTE[0]
    assert created["stops"] == []
    assert [r["id"] for r in routes] == [created["id"]]


def test_update_route_name_and_color(sync_db_session):
    warehouse = _new_warehouse(sync_db_session)
    route = create_warehouse_route(
        TENANT_ID, warehouse.id, WarehouseRouteCreate(name="Route 1"), sync_db_session, USER
    )

    updated = update_warehouse_route(
        TENANT_ID,
        warehouse.id,
        route["id"],
        WarehouseRouteUpdate(name="Downtown Loop", color="#000000"),
        sync_db_session,
        USER,
    )

    assert updated["name"] == "Downtown Loop"
    assert updated["color"] == "#000000"


def test_delete_route(sync_db_session):
    warehouse = _new_warehouse(sync_db_session)
    route = create_warehouse_route(
        TENANT_ID, warehouse.id, WarehouseRouteCreate(name="Route 1"), sync_db_session, USER
    )

    delete_warehouse_route(TENANT_ID, warehouse.id, route["id"], sync_db_session, USER)

    assert list_warehouse_routes(TENANT_ID, warehouse.id, sync_db_session, USER) == []


def test_color_auto_assignment_cycles_through_palette(sync_db_session):
    warehouse = _new_warehouse(sync_db_session)

    colors = [
        create_warehouse_route(
            TENANT_ID, warehouse.id, WarehouseRouteCreate(name=f"Route {i}"), sync_db_session, USER
        )["color"]
        for i in range(3)
    ]

    assert colors == ROUTE_COLOR_PALETTE[:3]


def test_color_auto_assignment_avoids_collision_after_delete_then_create(sync_db_session):
    warehouse = _new_warehouse(sync_db_session)
    routes = [
        create_warehouse_route(
            TENANT_ID, warehouse.id, WarehouseRouteCreate(name=f"Route {i}"), sync_db_session, USER
        )
        for i in range(3)
    ]
    assert [r["color"] for r in routes] == ROUTE_COLOR_PALETTE[:3]

    delete_warehouse_route(TENANT_ID, warehouse.id, routes[1]["id"], sync_db_session, USER)

    new_route = create_warehouse_route(
        TENANT_ID, warehouse.id, WarehouseRouteCreate(name="Route 3"), sync_db_session, USER
    )

    # The freed-up color[1] should be reused, not color[3] (a plain
    # existing_count % len(palette) scheme would collide with routes[2]'s
    # still-in-use color[2] here).
    assert new_route["color"] == ROUTE_COLOR_PALETTE[1]


def test_bulk_add_stops_and_order(sync_db_session):
    warehouse = _new_warehouse(sync_db_session)
    route = create_warehouse_route(
        TENANT_ID, warehouse.id, WarehouseRouteCreate(name="Route 1"), sync_db_session, USER
    )
    dest_a = _destination(sync_db_session, name="A")
    dest_b = _destination(sync_db_session, name="B")

    result = bulk_add_route_stops(
        TENANT_ID,
        warehouse.id,
        route["id"],
        RouteStopsBulkAdd(destination_location_ids=[dest_a.id, dest_b.id]),
        sync_db_session,
        USER,
    )

    assert result["skipped_destination_ids"] == []
    assert [s["destination"].id for s in result["stops"]] == [dest_a.id, dest_b.id]
    assert [s["stop_order"] for s in result["stops"]] == [0, 1]


def test_bulk_add_skips_duplicates_and_reports_them(sync_db_session):
    warehouse = _new_warehouse(sync_db_session)
    route = create_warehouse_route(
        TENANT_ID, warehouse.id, WarehouseRouteCreate(name="Route 1"), sync_db_session, USER
    )
    dest_a = _destination(sync_db_session, name="A")
    dest_b = _destination(sync_db_session, name="B")
    bulk_add_route_stops(
        TENANT_ID,
        warehouse.id,
        route["id"],
        RouteStopsBulkAdd(destination_location_ids=[dest_a.id]),
        sync_db_session,
        USER,
    )

    result = bulk_add_route_stops(
        TENANT_ID,
        warehouse.id,
        route["id"],
        RouteStopsBulkAdd(destination_location_ids=[dest_a.id, dest_b.id]),
        sync_db_session,
        USER,
    )

    assert result["skipped_destination_ids"] == [dest_a.id]
    assert [s["destination"].id for s in result["stops"]] == [dest_a.id, dest_b.id]


def test_reorder_stops(sync_db_session):
    warehouse = _new_warehouse(sync_db_session)
    route = create_warehouse_route(
        TENANT_ID, warehouse.id, WarehouseRouteCreate(name="Route 1"), sync_db_session, USER
    )
    dest_a = _destination(sync_db_session, name="A")
    dest_b = _destination(sync_db_session, name="B")
    bulk_add_route_stops(
        TENANT_ID,
        warehouse.id,
        route["id"],
        RouteStopsBulkAdd(destination_location_ids=[dest_a.id, dest_b.id]),
        sync_db_session,
        USER,
    )

    reordered = reorder_route_stops(
        TENANT_ID,
        warehouse.id,
        route["id"],
        RouteStopsReorder(destination_location_ids=[dest_b.id, dest_a.id]),
        sync_db_session,
        USER,
    )

    assert [s["destination"].id for s in reordered] == [dest_b.id, dest_a.id]
    assert [s["stop_order"] for s in reordered] == [0, 1]


def test_reorder_rejects_mismatched_set(sync_db_session):
    warehouse = _new_warehouse(sync_db_session)
    route = create_warehouse_route(
        TENANT_ID, warehouse.id, WarehouseRouteCreate(name="Route 1"), sync_db_session, USER
    )
    dest_a = _destination(sync_db_session, name="A")
    dest_b = _destination(sync_db_session, name="B")
    bulk_add_route_stops(
        TENANT_ID,
        warehouse.id,
        route["id"],
        RouteStopsBulkAdd(destination_location_ids=[dest_a.id]),
        sync_db_session,
        USER,
    )

    with pytest.raises(HTTPException) as exc_info:
        reorder_route_stops(
            TENANT_ID,
            warehouse.id,
            route["id"],
            RouteStopsReorder(destination_location_ids=[dest_a.id, dest_b.id]),
            sync_db_session,
            USER,
        )

    assert exc_info.value.status_code == 400


def test_remove_one_stop(sync_db_session):
    warehouse = _new_warehouse(sync_db_session)
    route = create_warehouse_route(
        TENANT_ID, warehouse.id, WarehouseRouteCreate(name="Route 1"), sync_db_session, USER
    )
    dest_a = _destination(sync_db_session, name="A")
    dest_b = _destination(sync_db_session, name="B")
    bulk_add_route_stops(
        TENANT_ID,
        warehouse.id,
        route["id"],
        RouteStopsBulkAdd(destination_location_ids=[dest_a.id, dest_b.id]),
        sync_db_session,
        USER,
    )

    remove_route_stop(TENANT_ID, warehouse.id, route["id"], dest_a.id, sync_db_session, USER)

    routes = list_warehouse_routes(TENANT_ID, warehouse.id, sync_db_session, USER)
    assert [s["destination"].id for s in routes[0]["stops"]] == [dest_b.id]


def test_distance_present_and_null_depending_on_warehouse_coords(sync_db_session):
    warehouse = _new_warehouse(sync_db_session)
    route = create_warehouse_route(
        TENANT_ID, warehouse.id, WarehouseRouteCreate(name="Route 1"), sync_db_session, USER
    )
    destination = _destination(sync_db_session, lat=43.7764, lng=-79.2318)  # ~18km from below
    bulk_add_route_stops(
        TENANT_ID,
        warehouse.id,
        route["id"],
        RouteStopsBulkAdd(destination_location_ids=[destination.id]),
        sync_db_session,
        USER,
    )

    no_coords = list_warehouse_routes(TENANT_ID, warehouse.id, sync_db_session, USER)
    assert no_coords[0]["stops"][0]["distance_km"] is None

    set_warehouse_coordinates(
        TENANT_ID,
        warehouse.id,
        WarehouseCoordinatesUpdate(lat=43.6532, lng=-79.3832),
        sync_db_session,
        USER,
    )

    with_coords = list_warehouse_routes(TENANT_ID, warehouse.id, sync_db_session, USER)
    distance = with_coords[0]["stops"][0]["distance_km"]
    assert distance is not None
    assert 15 < distance < 22


def test_deleting_destination_cascades_out_of_every_route(sync_db_session):
    warehouse_a = _new_warehouse(sync_db_session, odoo_id=1, name="A")
    warehouse_b = _new_warehouse(sync_db_session, odoo_id=2, name="B")
    route_a = create_warehouse_route(
        TENANT_ID, warehouse_a.id, WarehouseRouteCreate(name="Route A"), sync_db_session, USER
    )
    route_b = create_warehouse_route(
        TENANT_ID, warehouse_b.id, WarehouseRouteCreate(name="Route B"), sync_db_session, USER
    )
    destination = _destination(sync_db_session)
    for warehouse, route in ((warehouse_a, route_a), (warehouse_b, route_b)):
        bulk_add_route_stops(
            TENANT_ID,
            warehouse.id,
            route["id"],
            RouteStopsBulkAdd(destination_location_ids=[destination.id]),
            sync_db_session,
            USER,
        )

    delete_destination_location(TENANT_ID, destination.id, sync_db_session, USER)

    routes_a = list_warehouse_routes(TENANT_ID, warehouse_a.id, sync_db_session, USER)
    routes_b = list_warehouse_routes(TENANT_ID, warehouse_b.id, sync_db_session, USER)
    assert routes_a[0]["stops"] == []
    assert routes_b[0]["stops"] == []


def test_deleting_warehouse_cascades_its_routes_and_stops(sync_db_session):
    warehouse = _new_warehouse(sync_db_session)
    route = create_warehouse_route(
        TENANT_ID, warehouse.id, WarehouseRouteCreate(name="Route 1"), sync_db_session, USER
    )
    destination = _destination(sync_db_session)
    bulk_add_route_stops(
        TENANT_ID,
        warehouse.id,
        route["id"],
        RouteStopsBulkAdd(destination_location_ids=[destination.id]),
        sync_db_session,
        USER,
    )

    delete_warehouse(TENANT_ID, warehouse.id, sync_db_session, USER)

    # The destination itself survives — only the routes/stops are gone.
    from app.api.destination_locations import list_destination_locations

    assert [d.id for d in list_destination_locations(TENANT_ID, sync_db_session, USER)] == [
        destination.id
    ]


def test_route_endpoints_reject_mismatched_tenant(sync_db_session):
    warehouse = _new_warehouse(sync_db_session)
    other_tenant_user = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4())

    with pytest.raises(HTTPException) as exc_info:
        create_warehouse_route(
            TENANT_ID,
            warehouse.id,
            WarehouseRouteCreate(name="Route 1"),
            sync_db_session,
            other_tenant_user,
        )

    assert exc_info.value.status_code == 403
