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
