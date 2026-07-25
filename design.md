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
| `Card` | `Card.tsx` | Optional `heading` prop (named to avoid colliding with the native `title` HTML attribute). Basis for panels now; will be the basis for vehicle boxes/cluster groups in a later phase. |
| `Badge` | `Badge.tsx` | `variant`: `neutral` / `accent` / `ok` / `warning` / `full`. Used for connection state, sync/link status, and vehicle/driver status today. |
| `CapacityBar` | `CapacityBar.tsx` | Takes `value`/`max` (any shared unit), computes a 0–100% fill and picks `ok`/`warning`/`full` at 85%/100% thresholds. Real `role="progressbar"` semantics. **Not yet used on any current screen** — none of today's API responses carry a capacity number to visualize. It exists now so the load-planner phase (explicitly out of scope here) has it ready. |
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
- `CapacityBar` has no live usage yet (see the component table above) —
  there's no capacity data in any current API response to drive it.
- No drag-and-drop, vehicle-box layout, clustering UI, or state
  management — explicitly out of scope for this pass.

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
