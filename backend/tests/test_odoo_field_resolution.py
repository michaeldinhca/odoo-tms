from app.services.odoo_field_resolution import resolve_optional_field, resolve_required_field


class FakeOdooClient:
    def __init__(self, present_fields: set[str]):
        self._present_fields = present_fields

    def has_field(self, model, field_name):
        return field_name in self._present_fields


def test_resolve_required_field_is_a_pure_mapping_lookup_no_client_needed():
    assert resolve_required_field("stock.picking", "state", version_major=None) == "state"


def test_resolve_optional_field_returns_the_field_name_when_present():
    client = FakeOdooClient(present_fields={"shipping_weight"})

    result = resolve_optional_field(client, "stock.picking", "shipping_weight", version_major=None)

    assert result == "shipping_weight"


def test_resolve_optional_field_returns_none_when_absent():
    client = FakeOdooClient(present_fields=set())

    result = resolve_optional_field(client, "stock.picking", "shipping_weight", version_major=None)

    assert result is None
