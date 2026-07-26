import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

_URL_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)


class OdooCredentialUpsert(BaseModel):
    """Validated/normalized at this boundary (not just the frontend) so it
    also holds for direct API calls: users very often copy-paste these
    values and pick up stray leading/trailing whitespace, and Odoo
    usernames are case-sensitive, so a pasted-with-different-case value
    would silently fail auth rather than erroring here."""

    url: str
    db: str
    username: str
    api_key: str

    @field_validator("url")
    @classmethod
    def _normalize_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not _URL_SCHEME_RE.match(value):
            raise ValueError("Odoo URL must start with http:// or https://")
        return value

    @field_validator("db", "username", "api_key")
    @classmethod
    def _strip_whitespace(cls, value: str) -> str:
        return value.strip()


class OdooCredentialRead(BaseModel):
    """Never includes the API key, encrypted or otherwise."""

    model_config = ConfigDict(from_attributes=True)

    tenant_id: uuid.UUID
    url: str
    db: str
    username: str
    state: str = "draft"
    activated_at: datetime | None = None
    last_synced_operation_types_at: datetime | None = None
    last_synced_warehouses_at: datetime | None = None
    company_id: int | None = None
    company_name: str | None = None
    server_version: str | None = None
    server_version_major: int | None = None
    server_serie: str | None = None
    protocol_version: int | None = None
    version_checked_at: datetime | None = None
    version_change_detected: bool = False
    created_at: datetime


class OdooCredentialTestResult(BaseModel):
    success: bool
    detail: str
    server_version: str | None = None
    server_version_major: int | None = None
    version_change_detected: bool = False


class OdooCompany(BaseModel):
    id: int
    name: str


class OdooCredentialCompanySelect(BaseModel):
    """`company_id`/`company_name` both None clears the selection (plan
    across all companies the API user can see, unfiltered)."""

    company_id: int | None
    company_name: str | None
