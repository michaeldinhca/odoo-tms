"""Detects and persists a tenant's Odoo server version (see DECISIONS.md
"Odoo version detection"). Called on every test-connection, not just once —
a tenant's Odoo instance can be upgraded after the connection was first
configured, and field mappings may need to change accordingly."""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.odoo_credential import TenantOdooCredential
from app.services.odoo_client import OdooClient

logger = logging.getLogger(__name__)


def detect_and_store_version(
    db: Session, credential: TenantOdooCredential, client: OdooClient
) -> dict:
    info = client.get_version_info()
    previous_major = credential.server_version_major
    new_major = info["server_version_major"]

    changed = (
        previous_major is not None and new_major is not None and previous_major != new_major
    )
    if changed:
        logger.warning(
            "Odoo major version change detected for tenant_odoo_credentials %s: %s -> %s",
            credential.id,
            previous_major,
            new_major,
        )

    credential.server_version = info["server_version"]
    credential.server_version_major = new_major
    credential.server_serie = info["server_serie"]
    credential.protocol_version = info["protocol_version"]
    credential.version_checked_at = datetime.now(UTC)
    credential.version_change_detected = changed
    db.commit()
    db.refresh(credential)
    return info
