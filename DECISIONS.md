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
