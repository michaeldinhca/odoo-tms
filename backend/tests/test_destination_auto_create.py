"""auto_create_destinations_from_orders — called after every planning run's
pickings are synced (see app.api.planning). Tenant/DestinationLocation
setup only, no Odoo/planning-run machinery needed."""

import uuid

from app.api.deps import CurrentUser
from app.api.destination_locations import create_destination_location
from app.models.destination_location import DestinationLocation
from app.models.synced_warehouse import SyncedWarehouse
from app.schemas.destination_location import DestinationLocationCreate
from app.services.destination_locations import auto_create_destinations_from_orders, distance_km
from app.services.planning.ffd import Address, Order

TENANT_ID = uuid.uuid4()
USER = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_ID)


def _order(picking_id: int, customer_name: str, **address_overrides) -> Order:
    address_fields = {
        "street": "1 Main St",
        "street2": "",
        "city": "Toronto",
        "state_name": "Ontario",
        "country_name": "Canada",
        "zip": "M1M 1M1",
    }
    address_fields.update(address_overrides)
    return Order(
        picking_id=picking_id,
        weight_kg=0.0,
        volume_m3=0.0,
        lat=0.0,
        lon=0.0,
        customer_name=customer_name,
        address=Address(**address_fields),
    )


def test_creates_a_destination_for_a_new_address(sync_db_session):
    created = auto_create_destinations_from_orders(
        sync_db_session, TENANT_ID, [_order(1, "Acme Corp")]
    )
    sync_db_session.commit()

    assert len(created) == 1
    assert created[0].name == "Acme Corp"
    assert created[0].city == "Toronto"
    assert created[0].lat is None
    assert created[0].lng is None


def test_skips_orders_that_already_match_an_existing_destination(sync_db_session):
    create_destination_location(
        TENANT_ID,
        DestinationLocationCreate(
            name="Acme Corp",
            street="1 Main St",
            city="Toronto",
            state="Ontario",
            country="Canada",
            zip="M1M 1M1",
            lat=43.7,
            lng=-79.4,
        ),
        sync_db_session,
        USER,
    )

    created = auto_create_destinations_from_orders(
        sync_db_session, TENANT_ID, [_order(1, "Acme Corp")]
    )

    assert created == []


def test_matching_ignores_case_and_whitespace(sync_db_session):
    create_destination_location(
        TENANT_ID,
        DestinationLocationCreate(name="Acme Corp", city="Toronto", lat=43.7, lng=-79.4),
        sync_db_session,
        USER,
    )

    created = auto_create_destinations_from_orders(
        sync_db_session,
        TENANT_ID,
        [
            _order(
                1,
                "  ACME CORP  ",
                city="TORONTO",
                street="",
                zip="",
                state_name="",
                country_name="",
            )
        ],
    )

    assert created == []


def test_skips_orders_with_no_customer_name(sync_db_session):
    created = auto_create_destinations_from_orders(sync_db_session, TENANT_ID, [_order(1, "   ")])

    assert created == []


def test_deduplicates_within_the_same_batch(sync_db_session):
    orders = [_order(1, "Acme Corp"), _order(2, "Acme Corp")]

    created = auto_create_destinations_from_orders(sync_db_session, TENANT_ID, orders)
    sync_db_session.commit()

    assert len(created) == 1


def test_different_addresses_each_get_their_own_destination(sync_db_session):
    orders = [_order(1, "Acme Corp", city="Toronto"), _order(2, "Beta Inc", city="Ottawa")]

    created = auto_create_destinations_from_orders(sync_db_session, TENANT_ID, orders)
    sync_db_session.commit()

    assert {d.name for d in created} == {"Acme Corp", "Beta Inc"}
    assert sync_db_session.query(DestinationLocation).filter_by(tenant_id=TENANT_ID).count() == 2


def test_distance_is_null_when_an_auto_created_destination_has_no_coordinates():
    """An auto-created destination (see above) has null lat/lng until an
    admin fills them in — distance must degrade gracefully, not error."""
    warehouse = SyncedWarehouse(tenant_id=TENANT_ID, odoo_warehouse_id=1, lat=43.65, lng=-79.38)
    destination = DestinationLocation(tenant_id=TENANT_ID, name="Acme Corp", lat=None, lng=None)

    assert distance_km(warehouse, destination) is None
