import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OdooCredentialUpsert(BaseModel):
    url: str
    db: str
    username: str
    api_key: str


class OdooCredentialRead(BaseModel):
    """Never includes the API key, encrypted or otherwise."""

    model_config = ConfigDict(from_attributes=True)

    tenant_id: uuid.UUID
    url: str
    db: str
    username: str
    company_id: int | None = None
    company_name: str | None = None
    created_at: datetime


class OdooCredentialTestResult(BaseModel):
    success: bool
    detail: str


class OdooCompany(BaseModel):
    id: int
    name: str


class OdooCredentialCompanySelect(BaseModel):
    """`company_id`/`company_name` both None clears the selection (plan
    across all companies the API user can see, unfiltered)."""

    company_id: int | None
    company_name: str | None
