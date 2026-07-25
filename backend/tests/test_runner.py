from app.services.planning.runner import fetch_open_orders


class FakeOdooClient:
    """Duck-types app.services.odoo_client.OdooClient's search_read/has_field,
    backed by canned per-model data instead of a real XML-RPC call."""

    def __init__(self, data: dict[str, list[dict]], missing_fields: set[str] | None = None):
        self._data = data
        self._missing_fields = missing_fields or set()
        self.calls: list[tuple[str, list, list, int | None]] = []

    def search_read(self, model, domain=None, fields=None, company_id=None):
        self.calls.append((model, domain or [], fields or [], company_id))
        return self._data.get(model, [])

    def has_field(self, model, field_name):
        return field_name not in self._missing_fields


def _picking(picking_id, partner=(7, "Acme Corp")):
    return {
        "id": picking_id,
        "partner_id": list(partner) if partner else False,
        "state": "assigned",
        "scheduled_date": "2026-07-25 08:00:00",
        "picking_type_id": [1, "Delivery Orders"],
        "origin": "SO0042",
        "weight": 12.5,
        "shipping_weight": 13.0,
        "note": "Handle with care",
    }


def test_fetch_open_orders_enriches_customer_address_and_items():
    client = FakeOdooClient(
        {
            "stock.picking": [_picking(101), _picking(102, partner=None)],
            "res.partner": [
                {
                    "id": 7,
                    "street": "123 Main St",
                    "street2": "Suite 4",
                    "city": "Toronto",
                    "state_id": [59, "Ontario"],
                    "zip": "M5V 2T6",
                    "country_id": [38, "Canada"],
                }
            ],
            "stock.move": [
                {
                    "picking_id": [101, "WH/OUT/00101"],
                    "product_id": [1, "Widget"],
                    "product_uom_qty": 2.0,
                },
                {
                    "picking_id": [101, "WH/OUT/00101"],
                    "product_id": [2, "Gadget"],
                    "product_uom_qty": 1.0,
                },
            ],
        }
    )

    orders = fetch_open_orders(client)

    assert len(orders) == 2
    acme_order = next(o for o in orders if o.picking_id == 101)
    assert acme_order.customer_name == "Acme Corp"
    assert acme_order.items_summary == "Widget x2; Gadget x1"
    assert acme_order.address.street == "123 Main St"
    assert acme_order.address.street2 == "Suite 4"
    assert acme_order.address.city == "Toronto"
    assert acme_order.address.state_id == 59
    assert acme_order.address.state_name == "Ontario"
    assert acme_order.address.country_id == 38
    assert acme_order.address.country_name == "Canada"
    assert acme_order.address.zip == "M5V 2T6"
    assert acme_order.state == "assigned"
    assert acme_order.origin == "SO0042"
    assert acme_order.weight_kg == 12.5
    assert acme_order.shipping_weight == 13.0
    assert acme_order.note == "Handle with care"
    assert acme_order.scheduled_date is not None
    assert acme_order.scheduled_date.year == 2026

    no_partner_order = next(o for o in orders if o.picking_id == 102)
    assert no_partner_order.customer_name == ""
    assert no_partner_order.items_summary == ""
    assert no_partner_order.address.street == ""


def test_fetch_open_orders_passes_company_id_through_to_every_call():
    client = FakeOdooClient(
        {
            "stock.picking": [_picking(1)],
            "res.partner": [
                {
                    "id": 7,
                    "street": "",
                    "street2": "",
                    "city": "",
                    "state_id": False,
                    "zip": "",
                    "country_id": False,
                }
            ],
            "stock.move": [],
        }
    )

    fetch_open_orders(client, company_id=5)

    assert all(company_id == 5 for _, _, _, company_id in client.calls)


def test_fetch_open_orders_returns_empty_without_extra_calls_when_no_pickings():
    client = FakeOdooClient({"stock.picking": []})

    orders = fetch_open_orders(client)

    assert orders == []
    assert [call[0] for call in client.calls] == ["stock.picking"]  # only stock.picking hit


def test_fetch_open_orders_resolves_warehouse_from_picking_type():
    client = FakeOdooClient(
        {
            "stock.picking": [_picking(1)],
            "res.partner": [
                {
                    "id": 7,
                    "street": "",
                    "street2": "",
                    "city": "",
                    "state_id": False,
                    "zip": "",
                    "country_id": False,
                }
            ],
            "stock.move": [],
        }
    )

    orders = fetch_open_orders(
        client, warehouse_by_picking_type={1: {"warehouse_id": 3, "warehouse_name": "Main WH"}}
    )

    assert orders[0].picking_type_id == 1
    assert orders[0].warehouse_id == 3
    assert orders[0].warehouse_name == "Main WH"


def test_fetch_open_orders_filters_to_synced_operation_types_only():
    client = FakeOdooClient({"stock.picking": [_picking(1)]})

    fetch_open_orders(client, synced_operation_type_ids={1, 2, 3})

    picking_call = next(call for call in client.calls if call[0] == "stock.picking")
    assert ["picking_type_id", "in", [1, 2, 3]] in picking_call[1]


def test_fetch_open_orders_skips_odoo_entirely_when_no_operation_types_synced():
    client = FakeOdooClient({"stock.picking": [_picking(1)]})

    orders = fetch_open_orders(client, synced_operation_type_ids=set())

    assert orders == []
    assert client.calls == []


def test_fetch_open_orders_handles_missing_shipping_weight_field_gracefully():
    picking = _picking(1)
    del picking["shipping_weight"]  # simulate the delivery module not being installed
    client = FakeOdooClient(
        {
            "stock.picking": [picking],
            "res.partner": [
                {
                    "id": 7,
                    "street": "",
                    "street2": "",
                    "city": "",
                    "state_id": False,
                    "zip": "",
                    "country_id": False,
                }
            ],
            "stock.move": [],
        },
        missing_fields={"shipping_weight"},
    )

    orders = fetch_open_orders(client)

    assert orders[0].shipping_weight is None
    picking_call = next(call for call in client.calls if call[0] == "stock.picking")
    fields_requested = picking_call[2]
    assert "shipping_weight" not in fields_requested  # never asked for a field we know is absent
