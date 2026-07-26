"""OdooCredentialUpsert's field validators — pure schema tests, no DB
needed. Users very often copy-paste these values and pick up stray
whitespace, and Odoo usernames are case-sensitive, so trimming/format
checks live at the schema boundary rather than only the frontend."""

import pytest
from pydantic import ValidationError

from app.schemas.credentials import OdooCredentialUpsert


def _payload(**overrides) -> dict:
    defaults = {"url": "https://x.odoo.com", "db": "x", "username": "u", "api_key": "k"}
    defaults.update(overrides)
    return defaults


def test_url_is_trimmed_and_trailing_slash_stripped():
    credential = OdooCredentialUpsert(**_payload(url="  https://sky-contracting.odoo.com/  "))
    assert credential.url == "https://sky-contracting.odoo.com"


def test_username_db_api_key_are_trimmed():
    credential = OdooCredentialUpsert(
        **_payload(db=" mydb ", username=" minhd ", api_key=" secret-key \n")
    )
    assert credential.db == "mydb"
    assert credential.username == "minhd"
    assert credential.api_key == "secret-key"


def test_username_case_is_preserved_not_normalized():
    """Odoo usernames are case-sensitive — trimming must not also lowercase
    or otherwise alter case, only strip surrounding whitespace."""
    credential = OdooCredentialUpsert(**_payload(username=" Minhd "))
    assert credential.username == "Minhd"


@pytest.mark.parametrize("bad_url", ["sky-contracting.odoo.com", "ftp://x.odoo.com", "", "   "])
def test_url_without_http_scheme_is_rejected(bad_url):
    with pytest.raises(ValidationError):
        OdooCredentialUpsert(**_payload(url=bad_url))


@pytest.mark.parametrize("good_url", ["https://x.odoo.com", "http://localhost:8069"])
def test_url_with_valid_scheme_is_accepted(good_url):
    credential = OdooCredentialUpsert(**_payload(url=good_url))
    assert credential.url == good_url
