import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.destination_location import DestinationLocation, WarehouseDestinationLocation
from app.models.driver import Driver
from app.models.odoo_credential import TenantOdooCredential
from app.models.synced_operation_type import SyncedOperationType
from app.models.synced_picking import SyncedPicking
from app.models.synced_warehouse import SyncedWarehouse
from app.models.user import User
from app.models.vehicle import Vehicle

_ALL_MODELS = (
    TenantOdooCredential,
    SyncedOperationType,
    SyncedWarehouse,
    SyncedPicking,
    Vehicle,
    Driver,
    User,
    DestinationLocation,
    WarehouseDestinationLocation,
)
_SYNC_MODELS = _ALL_MODELS
_FLEET_MODELS = _ALL_MODELS


def _sqlite_session_with(models):
    engine = create_engine("sqlite:///:memory:")
    for model in models:
        model.__table__.create(bind=engine)

    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def _valid_fernet_key():
    """The default settings.fernet_key ("change-me") isn't a valid Fernet
    key, which is fine for the app (a real deployment always sets one via
    env) but breaks any test that saves Odoo credentials — encrypt_secret
    would raise. Swap in a real key for the duration of each test."""
    original = settings.fernet_key
    settings.fernet_key = Fernet.generate_key().decode()
    yield
    settings.fernet_key = original


@pytest.fixture
def sync_db_session():
    """A real SQLAlchemy session backed by an in-memory SQLite engine,
    containing every model that uses the cross-dialect `Uuid` type (not the
    full app schema — Tenant/User/PlanningRun still use Postgres-specific
    types that don't compile under SQLite). Enough to exercise real
    upsert/query/gating/cross-entity-reference logic (e.g. a warehouse
    delete guard checking both Vehicle.home_warehouse_id and SyncedPicking)
    without needing a Postgres instance in CI. `fleet_db_session` is an
    alias of the same fixture — the two names exist for readability at the
    call site, not because the table sets differ.
    """
    yield from _sqlite_session_with(_SYNC_MODELS)


@pytest.fixture
def fleet_db_session():
    yield from _sqlite_session_with(_FLEET_MODELS)
