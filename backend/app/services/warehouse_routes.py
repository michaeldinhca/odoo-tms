"""Route-color assignment. This project previously only had a single
accent color plus a 3-color status scale (see design.md) — no categorical
palette existed for "N visually distinct things" until routes needed one."""

ROUTE_COLOR_PALETTE: list[str] = [
    "#DC2626",  # red
    "#EA580C",  # orange
    "#CA8A04",  # yellow
    "#65A30D",  # lime
    "#16A34A",  # green
    "#059669",  # emerald
    "#0891B2",  # cyan
    "#2563EB",  # blue
    "#4F46E5",  # indigo
    "#7C3AED",  # violet
    "#C026D3",  # fuchsia
    "#DB2777",  # pink
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
