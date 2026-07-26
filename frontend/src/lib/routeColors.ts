/** Kept in sync with `backend/app/services/warehouse_routes.py`'s
 * ROUTE_COLOR_PALETTE — 12 hues spread around the wheel so they read as
 * obviously different at small map-marker size, not just different
 * shades of the same color. Duplicated rather than shared across the
 * Python/TypeScript boundary (no existing mechanism does that in this
 * project); if you change one, change the other. */
export const ROUTE_COLOR_PALETTE: readonly string[] = [
  "#DC2626", // red
  "#EA580C", // orange
  "#CA8A04", // yellow
  "#65A30D", // lime
  "#16A34A", // green
  "#059669", // emerald
  "#0891B2", // cyan
  "#2563EB", // blue
  "#4F46E5", // indigo
  "#7C3AED", // violet
  "#C026D3", // fuchsia
  "#DB2777", // pink
];
