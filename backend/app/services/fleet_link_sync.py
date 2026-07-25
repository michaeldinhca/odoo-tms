"""Keeps a local Vehicle/Driver's odoo_link_status honest relative to what's
actually still in Odoo — see DECISIONS.md "Stale Odoo links, not silent
unlinking": a record that disappears from Odoo after being linked here
never gets auto-unlinked; it's flagged `stale` and self-heals back to
`linked` if it reappears on a later browse."""

import uuid

from sqlalchemy.orm import Session


def sync_link_staleness(
    db: Session,
    tenant_id: uuid.UUID,
    model: type,
    odoo_id_field: str,
    available_odoo_ids: set[int],
) -> None:
    rows = (
        db.query(model)
        .filter(model.tenant_id == tenant_id, model.odoo_link_status.in_(["linked", "stale"]))
        .all()
    )
    for row in rows:
        odoo_id = getattr(row, odoo_id_field)
        if odoo_id is None:
            continue
        new_status = "linked" if odoo_id in available_odoo_ids else "stale"
        if row.odoo_link_status != new_status:
            row.odoo_link_status = new_status
    db.commit()
