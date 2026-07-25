"""Thin wrapper around Odoo's XML-RPC API.

Never log `password`/api key values — only the url/db/username, which are not
secret. See CLAUDE.md hard constraint #4.
"""

import re
import xmlrpc.client
from typing import Any


class OdooAuthError(Exception):
    pass


def _parse_major_version(version_str: str) -> int | None:
    """Extracts the leading integer from an Odoo version string. Handles
    both on-prem style ("17.0") and Odoo Online/SaaS style ("saas~17.2")."""
    match = re.search(r"\d+", version_str or "")
    return int(match.group()) if match else None


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

    def get_version_info(self) -> dict[str, Any]:
        """Calls Odoo's public `common.version()` — no authentication
        required, works before login. Used to detect which major version a
        tenant's Odoo instance runs, since native field names/availability
        can differ across versions (see app.odoo_mappings)."""
        result = self._common().version()
        server_version = str(result.get("server_version", ""))
        server_serie = str(result.get("server_serie", server_version))
        version_info = result.get("server_version_info")
        if isinstance(version_info, (list, tuple)) and version_info:
            major = int(version_info[0])
        else:
            major = _parse_major_version(server_serie or server_version)
        protocol_version = result.get("protocol_version")
        return {
            "server_version": server_version,
            "server_version_major": major,
            "server_serie": server_serie,
            "protocol_version": int(protocol_version) if protocol_version is not None else None,
        }

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
        company_id: int | None = None,
    ) -> list[dict[str, Any]]:
        uid = self.authenticate()
        options: dict[str, Any] = {"fields": fields or []}
        if company_id is not None:
            # Odoo's own multi-company scoping mechanism — restricts the
            # search to records visible under this company.
            options["context"] = {"allowed_company_ids": [company_id]}
        return self._object().execute_kw(
            self.db,
            uid,
            self._api_key,
            model,
            "search_read",
            [domain or []],
            options,
        )

    def list_companies(self) -> list[dict[str, Any]]:
        return self.search_read("res.company", domain=[], fields=["id", "name"])

    def has_field(self, model: str, field_name: str) -> bool:
        """Whether `field_name` exists on `model` — e.g. `shipping_weight` on
        `stock.picking` only exists when the optional `delivery` module is
        installed. Used to build an optional-field's `fields` list entry
        without guessing and retrying on a Fault."""
        uid = self.authenticate()
        fields_meta = self._object().execute_kw(
            self.db, uid, self._api_key, model, "fields_get", [], {"attributes": []}
        )
        return field_name in fields_meta

    def model_exists(self, model: str) -> bool:
        """Whether `model` exists at all on this Odoo instance — e.g.
        `fleet.vehicle` only exists when the Fleet module is installed."""
        try:
            uid = self.authenticate()
            self._object().execute_kw(
                self.db, uid, self._api_key, model, "fields_get", [], {"attributes": []}
            )
            return True
        except xmlrpc.client.Fault:
            return False
