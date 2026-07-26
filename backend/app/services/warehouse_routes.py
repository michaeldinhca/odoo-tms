"""Route-color assignment. This project previously only had a single
accent color plus a 3-color status scale (see design.md) — no categorical
palette existed for "N visually distinct things" until routes needed one."""

ROUTE_COLOR_PALETTE: list[str] = [
    "#2563EB",  # blue
    "#DC2626",  # red
    "#059669",  # green
    "#D97706",  # amber
    "#7C3AED",  # violet
    "#DB2777",  # pink
    "#0891B2",  # cyan
    "#65A30D",  # lime
]


def assign_route_color(used_colors: set[str]) -> str:
    """Picks the first palette color not already used by another route at
    the same warehouse. Deliberately not `existing_count %
    len(palette)` — that scheme hands out an already-in-use color after a
    delete-then-create (3 routes get colors 0/1/2, delete the one with
    color 1, create a new one: count-based indexing would give index 2,
    colliding with the surviving route). Falls back to cycling by count
    only once every palette color is already in use at that warehouse."""
    for color in ROUTE_COLOR_PALETTE:
        if color not in used_colors:
            return color
    return ROUTE_COLOR_PALETTE[len(used_colors) % len(ROUTE_COLOR_PALETTE)]
