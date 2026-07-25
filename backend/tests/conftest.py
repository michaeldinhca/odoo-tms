import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.driver import Driver
from app.models.synced_operation_type import SyncedOperationType
from app.models.synced_picking import SyncedPicking
from app.models.synced_warehouse import SyncedWarehouse
from app.models.vehicle import Vehicle

_SYNC_MODELS = (SyncedOperationType, SyncedWarehouse, SyncedPicking)
_FLEET_MODELS = (Vehicle, Driver)


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


@pytest.fixture
def sync_db_session():
    """A real SQLAlchemy session backed by an in-memory SQLite engine,
    containing only the sync-config tables (not the full app schema — those
    other models use Postgres-specific types that don't compile under
    SQLite). Enough to exercise real upsert/query logic for
    SyncedOperationType/SyncedWarehouse/SyncedPicking without needing a
    Postgres instance in CI.
    """
    yield from _sqlite_session_with(_SYNC_MODELS)


@pytest.fixture
def fleet_db_session():
    """Same idea as sync_db_session, but for Vehicle/Driver — enough to
    exercise real CRUD/delete-guard/link logic without a Postgres instance."""
    yield from _sqlite_session_with(_FLEET_MODELS)
