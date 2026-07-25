from app.core.crypto import decrypt_secret
from app.models.odoo_credential import TenantOdooCredential
from app.services.odoo_client import OdooClient


def build_client(credential: TenantOdooCredential) -> OdooClient:
    return OdooClient(
        url=credential.url,
        db=credential.db,
        username=credential.username,
        api_key=decrypt_secret(credential.encrypted_key),
    )
