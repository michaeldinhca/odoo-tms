from app.services.planning.ffd import Order


def sequence_filo(assigned_orders: list[Order]) -> list[Order]:
    """FILO delivery sequencing: last loaded = first delivered.

    `assigned_orders` is assumed to already be in load order (the order items
    were assigned/loaded onto the vehicle). This is a hard constraint, not an
    optimization — see CLAUDE.md hard constraint #2.
    """
    return list(reversed(assigned_orders))
