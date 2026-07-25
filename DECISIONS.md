# Architecture Decision Log

Format: date, decision, why. Newest entries at the bottom. Ask the user before
overriding or reversing any entry here — don't just re-litigate it in code.

---

## 2026-07-24 — Rejected zone-based routing

**Decision:** Routing assignment is purely location/time-based (nearest
feasible stop given capacity and time windows). No pre-assigned delivery
zones/territories.

**Why:** Daily order distribution varies too much for static zones to stay
efficient — zones would need constant manual rebalancing and would leave
capacity stranded on light days and overloaded on heavy days.

---

## 2026-07-24 — Shared DB + `tenant_id` over per-tenant databases

**Decision:** Multi-tenancy is implemented as one shared PostgreSQL database
with a `tenant_id` column on tenant-scoped tables, not a separate database (or
schema) per tenant.

**Why:** Simpler migrations, connection pooling, and backups for an MVP with
one operator and a single VPS. Revisit if/when a tenant needs hard data
isolation guarantees or the shared DB becomes a scaling bottleneck.

---

## 2026-07-24 — FFD algorithm + Haversine distance for MVP load planning

**Decision:** Use First Fit Decreasing (FFD) bin-packing for assigning orders
to vehicle capacity, and Haversine great-circle distance for
distance/time estimation between stops.

**Why:** Both are simple, dependency-free, and good enough for MVP-scale
routing decisions without needing a paid routing/matrix API. Revisit if
real road-network distance/time accuracy becomes a blocker.

---

## 2026-07-24 — Deferred Traccar / live tracking to Phase 2

**Decision:** No live GPS tracking integration in the MVP.

**Why:** MVP planning is batch (manual "Run Planning" trigger against a
snapshot of open orders); live position data isn't needed until real-time
re-optimization is in scope, which is a Phase 2 concern. See [PLAN.md](PLAN.md).

---

## 2026-07-25 — Multi-company handled as one selectable default company per tenant credential

**Decision:** A single Odoo connection (`tenant_odoo_credentials` row) can
belong to an Odoo instance with multiple `res.company` records. Rather than
modeling each company as its own tenant, or letting a tenant plan across all
companies at once, each tenant's Odoo credential gets an optional
`company_id`/`company_name` (nullable = "all companies the API user can see,
unfiltered"). The dispatcher picks the company from a list fetched live from
Odoo (`res.company` via XML-RPC) on the Connection page, and that selection
is stored and reused for every planning run until changed. All XML-RPC reads
(`stock.picking`, `fleet.vehicle`, `res.partner`, `stock.move`) pass Odoo's
`allowed_company_ids` context key when a company is selected, which is Odoo's
own mechanism for scoping records to a company.

**Why:** Matches the existing "single depot" MVP scope boundary (CLAUDE.md) —
one tenant plans for one company at a time, not a cross-company merge, which
would also break FFD/FILO's single-vehicle-pool assumption if two companies'
fleets got mixed. Keeping the selection persisted (not a per-run parameter)
keeps the Run Planning page a one-click action, matching the "manual trigger
only" MVP scope. A per-run company override, or planning across multiple
companies in one run, is deferred — see TODO.md "Next up" if that's needed
later.

---

## 2026-07-25 — No custom fields on Odoo; this system is the source of truth for anything Odoo doesn't natively provide

**Decision:** We never add custom (`x_`) fields to a tenant's Odoo instance,
and never write back to Odoo (this batch is read/sync only — no write-back
of any kind yet, planning results included). Every XML-RPC read uses only
Odoo's native standard fields (`res.partner`, `stock.picking`,
`stock.picking.type`, `stock.warehouse`, `stock.move`, `res.company`, ...).
Anything the TMS needs that Odoo doesn't natively provide is built and
stored on our own system (local Postgres) instead.

**Why:** We don't own the tenant's Odoo instance and have no business
mutating its schema — a customer's Odoo is a system we integrate with, not
one we get to reshape. This also keeps the integration portable across
however a given tenant's Odoo happens to be configured (which modules are
installed, which fields exist) rather than depending on a customization we'd
have to install per-tenant.

---

## 2026-07-25 — Address/company/country names resolved and cached at sync time, not looked up live at display time

**Decision:** When we pull a many2one relational field from Odoo (e.g.
`res.partner.state_id`, `country_id`), we store both the Odoo id and the
resolved display name at sync time (`state_id` + `state_name`, `country_id`
+ `country_name`, same pattern for warehouse name on a picking). Display
code reads the cached name directly; it never re-queries Odoo to resolve an
id to a name.

**Why:** Odoo's XML-RPC `search_read` already returns `[id, display_name]`
for every many2one field for free — there's no extra round trip to capture
the name alongside the id, so caching it is strictly cheaper than a live
lookup. It also means the planner results table and synced-picking records
stay readable even if Odoo is briefly unreachable when displaying a past
run. Trade-off: a renamed state/country in Odoo won't retroactively update
already-synced rows until the next sync touches that record — acceptable
for reference data that essentially never changes.

---

## 2026-07-25 — Operation-type sync gating: empty selection means sync nothing, not sync everything

**Decision:** `fetch_open_orders` takes a `synced_operation_type_ids` set.
An empty set returns zero pickings (no Odoo call at all) — it is not treated
as "no filter configured, fetch everything." Only `None` skips the filter
(used by tests/callers that don't care about operation-type config).

**Why:** The operation-type sync screen's whole point is opt-in: a new
tenant with zero configured operation types should sync nothing until they
explicitly choose which operation types they want, not silently pull every
open picking (which is what happened before this batch, and would be a
surprising amount of data — Receipts, Manufacturing, etc. — for a tenant who
hasn't set anything up yet).

---

## 2026-07-25 — `synced_pickings` populated as a side effect of `/planning/run`, not a separate sync trigger

**Decision:** There is no standalone "sync pickings now" action. The
existing `/planning/run` pipeline (`fetch_open_orders` → FFD → FILO) is
"the stock.picking sync" — every `Order` it fetches (assigned to a route or
not) gets upserted into `synced_pickings` as part of that same request, via
`app.services.picking_sync`. Operation types and warehouses, by contrast,
each got their own explicit "Resync List" action (per the spec) since
there's no other trigger that would naturally refresh them.

**Why:** The request described this batch as "sync work," which read as
introducing a persistent local mirror of picking data — but it also
explicitly scoped this batch to no new API surface beyond what the described
UI needs, and asked for the *existing* planner results table to surface the
enriched fields. Reusing the existing planning-run pull as the sync trigger
satisfies both without inventing an unrequested second pipeline. Revisit if
a decoupled "sync pickings without running a plan" action turns out to be
needed.
