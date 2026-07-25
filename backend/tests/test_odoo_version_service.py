import uuid

from app.models.odoo_credential import TenantOdooCredential
from app.services.odoo_version import detect_and_store_version


class FakeSession:
    """detect_and_store_version only calls commit()/refresh() — no querying
    — so a real Session isn't needed, avoiding the Postgres-only UUID type
    on TenantOdooCredential (see tests/conftest.py's note on that)."""

    def commit(self):
        pass

    def refresh(self, obj):
        pass


class FakeOdooClient:
    def __init__(self, version_info: dict):
        self._version_info = version_info

    def get_version_info(self):
        return self._version_info


def _credential(**overrides) -> TenantOdooCredential:
    credential = TenantOdooCredential(
        tenant_id=uuid.uuid4(), url="https://x.odoo.com", db="x", username="u", encrypted_key="k"
    )
    for key, value in overrides.items():
        setattr(credential, key, value)
    return credential


def _v17_client(server_version: str = "17.0") -> FakeOdooClient:
    return FakeOdooClient(
        {
            "server_version": server_version,
            "server_version_major": 17,
            "server_serie": "17.0",
            "protocol_version": 1,
        }
    )


def test_first_ever_check_does_not_flag_a_change():
    credential = _credential()  # server_version_major starts as None

    detect_and_store_version(FakeSession(), credential, _v17_client())

    assert credential.server_version_major == 17
    assert credential.version_change_detected is False


def test_same_major_version_on_recheck_does_not_flag_a_change():
    credential = _credential(server_version_major=17)

    detect_and_store_version(FakeSession(), credential, _v17_client())

    assert credential.version_change_detected is False


def test_different_major_version_on_recheck_flags_a_change():
    credential = _credential(server_version_major=16)

    detect_and_store_version(FakeSession(), credential, _v17_client())

    assert credential.server_version_major == 17  # updated to the new value
    assert credential.version_change_detected is True  # but the change is flagged, not silent


def test_stores_full_version_info():
    credential = _credential()

    detect_and_store_version(FakeSession(), credential, _v17_client(server_version="17.0+e"))

    assert credential.server_version == "17.0+e"
    assert credential.server_serie == "17.0"
    assert credential.protocol_version == 1
    assert credential.version_checked_at is not None
