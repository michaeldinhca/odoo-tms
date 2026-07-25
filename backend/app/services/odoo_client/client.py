"""Thin wrapper around Odoo's XML-RPC API.

Never log `password`/api key values — only the url/db/username, which are not
secret. See CLAUDE.md hard constraint #4.
"""

import xmlrpc.client
from typing import Any


class OdooAuthError(Exception):
    pass


class OdooClient:
    def __init__(self, url: str, db: str, username: str, api_key: str):
        self.url = url.rstrip("/")
        self.db = db
        self.username = username
        self._api_key = api_key
        self._uid: int | None = None

    def _common(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")

    def _object(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def authenticate(self) -> int:
        if self._uid is not None:
            return self._uid
        uid = self._common().authenticate(self.db, self.username, self._api_key, {})
        if not uid:
            raise OdooAuthError(f"Odoo authentication failed for db={self.db} user={self.username}")
        self._uid = uid
        return uid

    def test_connection(self) -> tuple[bool, str]:
        try:
            self.authenticate()
            return True, "Connected successfully."
        except OdooAuthError as exc:
            return False, str(exc)
        except (xmlrpc.client.Fault, ConnectionError, OSError) as exc:
            return False, f"Could not reach Odoo instance: {exc}"

    def search_read(
        self,
        model: str,
        domain: list | None = None,
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        uid = self.authenticate()
        return self._object().execute_kw(
            self.db,
            uid,
            self._api_key,
            model,
            "search_read",
            [domain or []],
            {"fields": fields or []},
        )
