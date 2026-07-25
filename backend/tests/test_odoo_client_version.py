from unittest.mock import MagicMock

from app.services.odoo_client.client import OdooClient, _parse_major_version


def _client_with_fake_common(version_response: dict) -> OdooClient:
    client = OdooClient(url="https://example.com", db="db", username="user", api_key="key")
    fake_common = MagicMock()
    fake_common.version.return_value = version_response
    client._common = MagicMock(return_value=fake_common)  # type: ignore[method-assign]
    return client


def test_get_version_info_uses_server_version_info_when_present():
    client = _client_with_fake_common(
        {
            "server_version": "17.0",
            "server_version_info": [17, 0, 0, "final", 0, ""],
            "server_serie": "17.0",
            "protocol_version": 1,
        }
    )

    info = client.get_version_info()

    assert info == {
        "server_version": "17.0",
        "server_version_major": 17,
        "server_serie": "17.0",
        "protocol_version": 1,
    }


def test_get_version_info_falls_back_to_parsing_serie_when_version_info_missing():
    # Odoo Online / SaaS instances sometimes report a "saas~X.Y" serie
    # without a server_version_info list.
    client = _client_with_fake_common(
        {"server_version": "saas~17.2", "server_serie": "saas~17.2", "protocol_version": 1}
    )

    info = client.get_version_info()

    assert info["server_version_major"] == 17


def test_get_version_info_does_not_authenticate():
    """common.version() is public — no auth call should happen."""
    client = _client_with_fake_common(
        {"server_version": "17.0", "server_version_info": [17, 0], "protocol_version": 1}
    )

    client.get_version_info()

    assert client._uid is None


def test_parse_major_version_handles_on_prem_format():
    assert _parse_major_version("17.0") == 17


def test_parse_major_version_handles_saas_format():
    assert _parse_major_version("saas~17.2") == 17


def test_parse_major_version_handles_missing_value():
    assert _parse_major_version("") is None
    assert _parse_major_version(None) is None
