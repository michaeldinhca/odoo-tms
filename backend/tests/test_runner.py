from app.services.planning.runner import fetch_open_orders


class FakeOdooClient:
    """Duck-types app.services.odoo_client.OdooClient's search_read, backed
    by canned per-model data instead of a real XML-RPC call."""

    def __init__(self, data: dict[str, list[dict]]):
        self._data = data
        self.calls: list[tuple[str, list, int | None]] = []

    def search_read(self, model, domain=None, fields=None, company_id=None):
        self.calls.append((model, domain or [], company_id))
        return self._data.get(model, [])


def test_fetch_open_orders_enriches_customer_address_and_items():
    client = FakeOdooClient(
        {
            "stock.picking": [
                {"id": 101, "partner_id": [7, "Acme Corp"]},
                {"id": 102, "partner_id": False},
            ],
            "res.partner": [
                {
                    "id": 7,
                    "street": "123 Main St",
                    "street2": "Suite 4",
                    "city": "Toronto",
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
    assert acme_order.address.street1 == "123 Main St"
    assert acme_order.address.street2 == "Suite 4"
    assert acme_order.address.city == "Toronto"
    assert acme_order.address.country == "Canada"
    assert acme_order.address.zip == "M5V 2T6"

    no_partner_order = next(o for o in orders if o.picking_id == 102)
    assert no_partner_order.customer_name == ""
    assert no_partner_order.items_summary == ""
    assert no_partner_order.address.street1 == ""


def test_fetch_open_orders_passes_company_id_through_to_every_call():
    client = FakeOdooClient(
        {
            "stock.picking": [{"id": 1, "partner_id": [1, "X"]}],
            "res.partner": [
                {"id": 1, "street": "", "street2": "", "city": "", "zip": "", "country_id": False}
            ],
            "stock.move": [],
        }
    )

    fetch_open_orders(client, company_id=5)

    assert all(company_id == 5 for _, _, company_id in client.calls)


def test_fetch_open_orders_returns_empty_without_extra_calls_when_no_pickings():
    client = FakeOdooClient({"stock.picking": []})

    orders = fetch_open_orders(client)

    assert orders == []
    assert [call[0] for call in client.calls] == ["stock.picking"]
