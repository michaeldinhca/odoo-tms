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
    created_at: datetime


class OdooCredentialTestResult(BaseModel):
    success: bool
    detail: str
