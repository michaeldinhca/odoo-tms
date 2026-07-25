import uuid

from app.services.sync_config import (
    fetch_operation_types,
    fetch_warehouses,
    get_synced_operation_type_ids,
    get_warehouse_by_picking_type,
    upsert_operation_types,
    upsert_warehouses,
)

TENANT_ID = uuid.uuid4()


class FakeOdooClient:
    def __init__(self, data: dict[str, list[dict]]):
        self._data = data

    def search_read(self, model, domain=None, fields=None, company_id=None):
        return self._data.get(model, [])


def _operation_type(
    odoo_id: int, name: str, code: str = "outgoing", warehouse_id: int | None = 1
) -> dict:
    return {
        "odoo_operation_type_id": odoo_id,
        "name": name,
        "code": code,
        "warehouse_id": warehouse_id,
    }


def _warehouse(odoo_id: int = 1, name: str = "Main WH", city: str = "Toronto") -> dict:
    return {
        "odoo_warehouse_id": odoo_id,
        "name": name,
        "code": "WH",
        "street": "1 Depot Rd",
        "street2": "",
        "city": city,
        "state_id": 59,
        "state_name": "Ontario",
        "country_id": 38,
        "country_name": "Canada",
        "zip": "M5V 2T6",
    }


# --- fetch_* (Odoo-only) ---


def test_fetch_operation_types_maps_native_fields():
    client = FakeOdooClient(
        {
            "stock.picking.type": [
                {
                    "id": 10,
                    "name": "Delivery Orders",
                    "code": "outgoing",
                    "warehouse_id": [1, "WH"],
                },
                {"id": 11, "name": "Receipts", "code": "incoming", "warehouse_id": False},
            ]
        }
    )

    fetched = fetch_operation_types(client)

    assert fetched == [
        _operation_type(10, "Delivery Orders"),
        _operation_type(11, "Receipts", code="incoming", warehouse_id=None),
    ]


def test_fetch_warehouses_resolves_split_address_from_partner():
    client = FakeOdooClient(
        {
            "stock.warehouse": [
                {"id": 1, "name": "Main WH", "code": "WH", "partner_id": [5, "Main WH"]}
            ],
            "res.partner": [
                {
                    "id": 5,
                    "street": "1 Depot Rd",
                    "street2": "",
                    "city": "Toronto",
                    "state_id": [59, "Ontario"],
                    "country_id": [38, "Canada"],
                    "zip": "M5V 2T6",
                }
            ],
        }
    )

    fetched = fetch_warehouses(client)

    assert fetched == [_warehouse()]


# --- upsert_* (DB-only, real SQLite session) ---


def test_upsert_operation_types_new_rows_default_unsynced(sync_db_session):
    fetched = [_operation_type(10, "Delivery Orders")]

    rows = upsert_operation_types(sync_db_session, TENANT_ID, fetched)

    assert len(rows) == 1
    assert rows[0].is_synced is False
    assert rows[0].name == "Delivery Orders"


def test_upsert_operation_types_preserves_existing_sync_toggle_on_refresh(sync_db_session):
    fetched = [_operation_type(10, "Delivery Orders")]
    rows = upsert_operation_types(sync_db_session, TENANT_ID, fetched)
    rows[0].is_synced = True
    sync_db_session.commit()

    # Re-run "refresh" with an updated name from Odoo — simulates the user
    # renaming the operation type in Odoo between refreshes.
    refreshed = [_operation_type(10, "Delivery Orders (renamed)")]
    rows_after = upsert_operation_types(sync_db_session, TENANT_ID, refreshed)

    assert len(rows_after) == 1
    assert rows_after[0].is_synced is True  # not reset
    assert rows_after[0].name == "Delivery Orders (renamed)"  # still updated


def test_upsert_operation_types_new_type_found_on_refresh_defaults_unsynced(sync_db_session):
    upsert_operation_types(sync_db_session, TENANT_ID, [_operation_type(10, "Delivery Orders")])
    rows = upsert_operation_types(sync_db_session, TENANT_ID, [])
    rows[0].is_synced = True
    sync_db_session.commit()

    # A second operation type shows up in Odoo on a later refresh.
    rows_after = upsert_operation_types(
        sync_db_session,
        TENANT_ID,
        [_operation_type(10, "Delivery Orders"), _operation_type(20, "Receipts", code="incoming")],
    )

    by_odoo_id = {r.odoo_operation_type_id: r for r in rows_after}
    assert by_odoo_id[10].is_synced is True  # existing toggle preserved
    assert by_odoo_id[20].is_synced is False  # new one defaults off


def test_upsert_warehouses_preserves_existing_sync_toggle_on_refresh(sync_db_session):
    fetched = [_warehouse()]
    rows = upsert_warehouses(sync_db_session, TENANT_ID, fetched)
    rows[0].is_synced = True
    sync_db_session.commit()

    fetched = [_warehouse(city="Mississauga")]  # address changed in Odoo
    rows_after = upsert_warehouses(sync_db_session, TENANT_ID, fetched)

    assert rows_after[0].is_synced is True  # not reset
    assert rows_after[0].city == "Mississauga"  # still updated


# --- planning-side lookup helpers ---


def test_get_synced_operation_type_ids_only_returns_synced(sync_db_session):
    fetched = [_operation_type(10, "A"), _operation_type(20, "B", code="incoming")]
    rows = upsert_operation_types(sync_db_session, TENANT_ID, fetched)
    rows[0].is_synced = True
    sync_db_session.commit()

    assert get_synced_operation_type_ids(sync_db_session, TENANT_ID) == {10}


def test_get_warehouse_by_picking_type_joins_operation_type_and_warehouse(sync_db_session):
    upsert_operation_types(sync_db_session, TENANT_ID, [_operation_type(10, "Delivery")])
    upsert_warehouses(sync_db_session, TENANT_ID, [_warehouse()])

    result = get_warehouse_by_picking_type(sync_db_session, TENANT_ID)

    assert result == {10: {"warehouse_id": 1, "warehouse_name": "Main WH"}}
