# Design System

This document is the reference for the visual design system introduced
2026-07-25: Tailwind CSS (utility classes on our own markup, no component
library) plus a small set of hand-built base components. See
[DECISIONS.md](DECISIONS.md) for the architectural record of *why* Tailwind
was chosen over a component library — this file covers the *what* (tokens,
components, rationale) and is meant to be kept current as the design
evolves.

## Where things live

| What | File |
|---|---|
| Tailwind install/config | `frontend/package.json` (`tailwindcss`, `@tailwindcss/vite`), `frontend/vite.config.ts` (plugin registration) |
| Design tokens | `frontend/src/index.css` — CSS-first `@theme` block (Tailwind v4 convention; there is no `tailwind.config.ts` in this project) |
| Base components | `frontend/src/components/ui/` — `Button.tsx`, `Input.tsx`, `Select.tsx`, `Card.tsx`, `Badge.tsx`, `CapacityBar.tsx`, `Table.tsx`, plus `cn.ts` (tiny className-join helper) and `index.ts` (barrel export) |

Tailwind v4 was confirmed as current at setup time (`npm install
tailwindcss @tailwindcss/vite` resolved `^4.3.3`); v4 moved config into CSS
via `@theme` instead of a JS/TS config file and content-scanning is
automatic (no `content: []` glob to maintain).

## Color tokens

All defined in `frontend/src/index.css`'s `@theme` block as `--color-*`
custom properties, which Tailwind automatically turns into `bg-*`/`text-*`/
`border-*` utilities (e.g. `--color-accent` → `bg-accent`, `text-accent`,
`border-accent`, and opacity-modified forms like `bg-accent/10`).

| Token | Hex | Purpose | Contrast (as text, on white) |
|---|---|---|---|
| `bg` | `#F1F5F9` | Page background — sits behind elevated surfaces | — (not used as text) |
| `surface` | `#FFFFFF` | Cards, panels, inputs, table rows | — |
| `text` | `#0F172A` | Primary text | 17.85:1 |
| `text-muted` | `#475569` | Secondary text, field labels, table headers, timestamps | 7.58:1 |
| `border` | `#94A3B8` | Card/input/table borders and row dividers (single token, used everywhere) | 2.56:1 (see note below) |
| `accent` | `#1D4ED8` | Primary actions, active nav, links, focus rings | 6.70:1 (both as text-on-white and white-on-accent) |
| `status-ok` | `#15803D` | Capacity/status: normal | 5.02:1 |
| `status-warning` | `#B45309` | Capacity/status: approaching limit | 5.02:1 |
| `status-full` | `#B91C1C` | Capacity/status: at/over limit, errors | 6.47:1 |

Every value above is a specific, named stop from Tailwind's own palette
(slate/blue/green/amber/red) rather than an invented hex — reusing
well-tested values, just giving them semantic names instead of scale
numbers.

**Contrast note on `border`:** measured at 2.56:1 against white, short of
the 3:1 WCAG 1.4.11 non-text-contrast guideline for meaningful UI
boundaries. This is a deliberate choice, not an oversight: a border strong
enough to hit 3:1 on its own (Tailwind's slate-500, ~4.76:1) reads as a
heavy grid line, which is exactly the "hairline-rule broadsheet" look this
system is trying to avoid. Table/card structure instead leans on padding,
row-hover highlighting (`hover:bg-bg/60`), and a tinted header row
(`bg-bg` on `<thead>`) to carry scanability, with the border as a light
assist rather than the sole boundary cue. The place non-text contrast
actually matters most — the focus indicator on an interactive element —
is the `accent` ring at 6.70:1, well clear of 3:1.

## Type scale

No custom sizes were added — every size below is an out-of-the-box
Tailwind class. This is the mapping from use case to class, for
consistency across pages:

| Use case | Class | Size |
|---|---|---|
| Page title (`<h1>`) | `text-2xl font-semibold` | 24px |
| Section heading (`<h2>`, `Card`'s `heading` prop) | `text-lg font-semibold` | 18px |
| Body text | `text-sm` | 14px |
| Data label (table headers, field labels, badge text) | `text-xs font-medium uppercase tracking-wide` | 12px |

Body defaults to `text-sm` (14px) rather than Tailwind's `text-base`
(16px) — a deliberate density choice for a tool whose primary content is
tables and forms read at a glance, not paragraphs.

## Spacing

Tailwind's default spacing scale, unmodified. No custom spacing values
were added to the theme — there was no case in this pass that needed
anything off-scale.

## Radius and shadow

One radius token, one shadow token, used everywhere without exception:

- **Radius:** `rounded-md` (6px) — buttons, inputs, selects, cards, badges,
  table container, capacity bar track/fill. Badges deliberately use
  `rounded-md` rather than a fully-rounded pill shape, so there's exactly
  one radius in the whole system rather than a "pill exception."
- **Shadow:** `shadow-sm` — applied only to `Card` (the one elevated
  surface in this system). Nothing else uses a shadow; buttons, inputs,
  and table rows stay flat.

## Base components (`frontend/src/components/ui/`)

| Component | File | Notes |
|---|---|---|
| `Button` | `Button.tsx` | `variant`: `primary` (solid accent) / `secondary` (bordered). `size`: `default` / `sm` / `icon`. |
| `Input` | `Input.tsx` | Optional `label` prop renders the label+field as one unit; omit it for a bare input (e.g. inline table-row filters). |
| `Select` | `Select.tsx` | Same `label` pattern as `Input`. |
| `Card` | `Card.tsx` | Optional `heading` prop (named to avoid colliding with the native `title` HTML attribute). Forwards its ref (`forwardRef<HTMLDivElement, CardProps>`) so it composes with `useDroppable`/`useDraggable` and similar. Basis for panels, and for the Load Planning page's vehicle/unassigned drop targets. |
| `Badge` | `Badge.tsx` | `variant`: `neutral` / `accent` / `ok` / `warning` / `full`. Used for connection state, sync/link status, and vehicle/driver status today. |
| `CapacityBar` | `CapacityBar.tsx` | Takes `value`/`max` (any shared unit), computes a 0–100% fill and picks `ok`/`warning`/`full` at 85%/100% thresholds. Real `role="progressbar"` semantics. Used on the Load Planning page's vehicle cards (`frontend/src/loadPlanning/VehicleCard.tsx`) — one bar for weight, one for volume, since a vehicle can be full on one axis and empty on the other. |
| `Table` / `TableHead` / `TableBody` / `TableRow` / `Th` / `Td` | `Table.tsx` | Composable primitives mirroring plain HTML table structure, not one generic data-grid — there's no sorting/virtualization need yet. Used for every table in the app today (Operation Types, Warehouses, Vehicles, Drivers, Planning results) and will be the basis for the dense unassigned-pickings list later. |
| `cn` | `cn.ts` | Zero-dependency `classes.filter(Boolean).join(" ")` helper — the only "utility" pulled in for className composition (no `clsx`/`cva`). |

Applied to every existing screen: `LoginPage`, `ConnectionPage`,
`OperationTypesPage`, `WarehousesPage`, `VehiclesPage`, `DriversPage`,
`PlanningPage`, and the `NavBar`. All of `frontend/src/index.css`'s old
hand-rolled classes (`.page`, `.navbar`, `.route-table`, `.hint`, `.error`,
etc.) were removed — nothing in the app references them anymore.

## Rationale

This is an internal, high-frequency tool a dispatcher uses standing at a
warehouse workstation or on a tablet, glancing between a picking list and
a vehicle's remaining capacity dozens of times a shift — not a marketing
site or a consumer app someone spends leisure time in. Every choice above
was made against that brief specifically:

- **Cool neutral gray, not warm cream or near-black.** A warm
  cream/terracotta pairing reads as editorial/consumer; a near-black
  surface with a neon accent reads as a dev-tool/dashboard flex. Neither
  fits a tool whose job is to be read quickly and correctly under
  fluorescent warehouse lighting. Cool slate grays are neutral and
  don't compete with the status colors doing the actual communicating.
- **A single, restrained blue accent**, not a saturated/neon one — used
  sparingly (primary actions, active nav, links, focus), so it stays
  meaningful instead of becoming visual noise across a page with a lot of
  buttons and badges.
- **A real status scale, not a repurposed accent.** Capacity state
  (ok/warning/full) is the one piece of information a dispatcher needs to
  register instantly and unambiguously — it gets its own three colors,
  chosen to be clearly distinct from the blue accent and from each other
  (traffic-light green/amber/red), not "accent but a bit different."
- **Density over whitespace.** Body text at 14px, `sm`-sized buttons
  available everywhere in tables, borders present but light (see the
  contrast note above) rather than absent — optimized for scanning many
  rows, not for generous marketing-page breathing room.
- **One radius, one shadow, applied everywhere.** A tool used all day
  should look like one coherent surface, not a collage of components each
  making their own rounding/elevation decision — which is also why this
  explicitly isn't a hairline-rule "broadsheet" layout: structure comes
  from consistent spacing and a light, uniform border, not decorative
  rules.

## Known gaps / not done in this pass

- No interactive browser verification was performed — this environment
  has no browser automation tool available. Verification here is
  `tsc -b` (type-check) + `vite build` (production build) + `eslint`, all
  clean, plus a manually computed WCAG contrast check for every color
  pairing above (see the table). The actual rendered UI has not been
  visually confirmed in a browser.
- No drag-and-drop, vehicle-box layout, clustering UI, or state
  management — explicitly out of scope for this pass.

## Load planning board (2026-07-25)

The Load Planning page (`frontend/src/pages/LoadPlanningPage.tsx`,
`/load-planning`) is the first consumer of `CapacityBar` and the first
non-trivial `useReducer`-backed page. Its supporting code lives in
`frontend/src/loadPlanning/` (`types.ts`, `reducer.ts`, `fixtures.ts`,
`UnassignedPanel.tsx`, `VehicleCard.tsx`) and `frontend/src/lib/
clustering.ts` (`getDistanceKm`/`getBearing`/`getCompassDirection`/
`clusterDestinations` — pure geo math, no React/domain coupling, ported
from `backend/app/services/planning/haversine.py`'s formula so on-screen
distances agree with the backend's).

**Drag-and-drop (2026-07-25, follow-up):** `@dnd-kit/core` wires a single
picking card at a time between the unassigned panel and vehicle cards —
`@dnd-kit/utilities` was skipped (not needed: the original card is just
dimmed via `isDragging` rather than transform-followed, and `DragOverlay`
positions its own floating copy without help), and `@dnd-kit/sortable`
is intentionally not installed yet (within-vehicle reordering is a later
phase). `Card` (`components/ui/Card.tsx`) now forwards its ref so
`useDroppable`/`useDraggable` can attach to it directly. The "drag over"
state on a droppable `Card` is a `ring-2 ring-accent` rather than a
second `border-*`/`bg-*` utility layered on top of Card's own — this
project doesn't use `tailwind-merge`, so two utilities touching the same
CSS property (e.g. `border-border` from Card plus a conditional
`border-accent`) have an unpredictable winner based on Tailwind's
generated stylesheet order, not DOM class order. A ring uses `box-shadow`
instead, which doesn't collide with either. The reducer's `MOVE_ITEMS`
action takes `pickingIds: string[]` (always length 1 today) rather than
a single-id shape, so a later multi-select phase can move several
pickings in one dispatch without a new action type or a breaking rename.

This phase is drag-only — no within-vehicle reordering, no multi-select,
no capacity-overfill blocking, no backend persistence. See DECISIONS.md
if a future reordering phase adds new architectural choices worth
logging there.

**Cluster-drag and multi-select (2026-07-25, follow-up):** `MOVE_ITEMS`
already took `pickingIds: string[]`, so no reducer-shape change was
needed to generalize beyond a single card — only the drag handlers
needed to resolve a bigger array in more cases.

- Each compass-direction cluster header in `UnassignedPanel` has its own
  small drag handle (`ClusterDragHandle`, a six-dot grip glyph),
  separate from the header's existing collapse/expand button — dragging
  it carries every id in `cluster.items` (from `clusterDestinations`'s
  *output*, i.e. the underlying data), so a collapsed cluster still
  drags its full membership correctly.
- **Selection interaction model** (documented here since the task asked
  for it to be unambiguous): a checkbox on each card toggles that card's
  membership in `selectedIds` without touching the rest of the
  selection; a plain click anywhere else on the card *replaces* the
  selection with just that card; ctrl/cmd-click on the card body toggles
  it the same way the checkbox does. This mirrors the common
  file-manager convention (checkbox = toggle, click = select-only-this,
  modifier-click = toggle) and was chosen over picking a single
  mechanism because the board is explicitly a desktop-and-tablet tool —
  ctrl/cmd-click doesn't exist on touch, so the checkbox is the
  affordance that always works. Shift-click range-select was skipped as
  the task allowed.
- Selected cards get `border-accent bg-accent/5` — deliberately not a
  ring, since `ring-2 ring-accent` is already the *droppable-container*
  "drag over" indicator (on the panel/vehicle `Card`), and the task
  asked for the two states to read as visually distinct. Card-level
  selection styling swaps the border/background classes outright
  (`isSelected ? "border-accent bg-accent/5" : "border-border bg-surface
  hover:bg-bg"`) rather than layering a conditional class on top of the
  row's own base classes, for the same Tailwind-without-`tailwind-merge`
  override-order reason `Card`'s drag-over ring avoids stacking
  `border-*`/`bg-*` utilities (see above).
- Dragging a card that's part of the current selection carries the
  whole selection; dragging one that isn't carries just itself (stale
  selections elsewhere are ignored) — resolved once in `onDragStart` and
  reused for both the `DragOverlay` content and the eventual dispatch.
  `DragOverlay` shows a `Badge`-based "N items" preview instead of a
  single card whenever more than one id is being dragged (cluster *or*
  multi-select).
- A successful `MOVE_ITEMS` now always clears `selectedIds` as part of
  the same state update, not a second dispatch — simpler than requiring
  every call site to remember to clear it, and there's no case where
  leaving a stale selection after a move would be desirable.

## Decisions log

### 2026-07-25 — Adopt Tailwind CSS v4, no component library; cool-neutral/blue-accent direction

**Decision:** Installed `tailwindcss` + `@tailwindcss/vite` (v4, confirmed
current — CSS-first `@theme` config, no `tailwind.config.ts`, automatic
content scanning). Built seven hand-written base components
(`Button`/`Input`/`Select`/`Card`/`Badge`/`CapacityBar`/`Table`) in
`frontend/src/components/ui/` rather than adopting shadcn or any other
component library — every component's markup and behavior is ours,
Tailwind only supplies the utility classes. Chose a cool slate-gray
neutral palette with a single restrained blue accent (`#1D4ED8`) and a
traffic-light status scale (`#15803D`/`#B45309`/`#B91C1C`) kept visually
and hue-distinct from the accent. One radius (`rounded-md`) and one shadow
(`shadow-sm`) used everywhere, no exceptions (including badges, which
conventionally get a pill shape elsewhere but use the same radius token
here). Body text defaults to 14px (`text-sm`), not Tailwind's 16px
default, for density. Applied the new system to every existing screen
(Login, Connection, Operation Types, Warehouses, Vehicles, Drivers,
Planning, NavBar) rather than building a separate style-guide page, since
real screens already existed to restyle.

**Why:** this is a high-frequency operational tool for warehouse
dispatchers, not a marketing surface — scanability and data density were
prioritized over decorative flourish per the brief, and the specific
palette/radius/shadow choices were made to avoid three identified
"AI-generated look" clichés (cream+terracotta, near-black+neon,
hairline-rule broadsheet) while still landing somewhere deliberate rather
than generically safe. Full reasoning for each token is in the
"Rationale" section above.

**Open items for a future entry:** `CapacityBar` is unused pending real
capacity data from a load-planning phase; the `border` token's contrast
tradeoff (documented above) should be revisited if this ever needs a
formal accessibility audit rather than the manual WCAG spot-check done
here; no browser-based visual QA has been performed on any of this.
