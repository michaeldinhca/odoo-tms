import pytest

import app.odoo_mappings as mappings


def test_resolve_field_default_mapping_when_no_version_given():
    assert mappings.resolve_field("res.partner", "street", version_major=None) == "street"


def test_resolve_field_default_mapping_for_a_version_with_no_override(monkeypatch):
    monkeypatch.setitem(
        mappings._MODEL_MAPS, "res.partner", {"default": {"street": "street"}, 13: {}}
    )

    assert mappings.resolve_field("res.partner", "street", version_major=17) == "street"


def test_resolve_field_returns_version_specific_override_when_present(monkeypatch):
    monkeypatch.setitem(
        mappings._MODEL_MAPS,
        "res.partner",
        {"default": {"street": "street"}, 13: {"street": "street_name_legacy"}},
    )

    assert mappings.resolve_field("res.partner", "street", version_major=13) == "street_name_legacy"
    # a different version with no override still gets the default
    assert mappings.resolve_field("res.partner", "street", version_major=17) == "street"


def test_resolve_field_unknown_future_version_major_falls_back_to_default(monkeypatch):
    monkeypatch.setitem(
        mappings._MODEL_MAPS,
        "res.partner",
        {"default": {"street": "street"}, 13: {"street": "street_name_legacy"}},
    )

    # version 99 has never been seen — no KeyError, just the default
    assert mappings.resolve_field("res.partner", "street", version_major=99) == "street"


def test_resolve_field_unknown_model_raises_key_error():
    with pytest.raises(KeyError):
        mappings.resolve_field("not.a.real.model", "x", version_major=17)


def test_resolve_field_unknown_logical_name_raises_key_error():
    with pytest.raises(KeyError):
        mappings.resolve_field("res.partner", "not_a_real_logical_field", version_major=17)


@pytest.mark.parametrize(
    ("model", "logical_name", "expected"),
    [
        ("stock.picking", "state", "state"),
        ("stock.picking", "shipping_weight", "shipping_weight"),
        ("stock.warehouse", "partner_id", "partner_id"),
        ("stock.picking.type", "warehouse_id", "warehouse_id"),
        ("fleet.vehicle", "license_plate", "license_plate"),
        ("hr.employee", "mobile_phone", "mobile_phone"),
        ("res.partner", "country_id", "country_id"),
    ],
)
def test_real_registry_defaults_are_identity_mappings_today(model, logical_name, expected):
    """No version-specific overrides have been confirmed yet for any model
    (see DECISIONS.md) — every logical field should currently resolve to
    the same name it always hardcoded to, regardless of version_major."""
    assert mappings.resolve_field(model, logical_name, version_major=None) == expected
    assert mappings.resolve_field(model, logical_name, version_major=13) == expected
    assert mappings.resolve_field(model, logical_name, version_major=18) == expected
