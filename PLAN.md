# Roadmap

## >>> CURRENT PHASE: Phase 1 — MVP <<<

Internal fleet management, single-tenant testing, but built ready to go
multi-tenant. Manual planning runs only.

Scope:
- Multi-tenant data model from day one (`tenant_id` columns), even though we
  will only actively test with one tenant during MVP.
- Connect to one customer Odoo instance via XML-RPC, pull open `stock.picking`
  records.
- Run FFD (First Fit Decreasing) bin-packing for load assignment across
  available `fleet.vehicle` capacity.
- Run FILO sequencing within each vehicle's assigned load.
- Return a planning result as JSON via `/planning/run` — no write-back to Odoo
  yet.
- Minimal React dispatcher UI: log in, manage one Odoo connection, trigger a
  planning run, view the result.
- Single Docker Compose stack, single Hetzner VPS.

Out of scope for Phase 1 (see below): live GPS, driver app, real-time
re-optimization, multi-depot.

## Phase 2 — Full multi-tenant SaaS

- Onboard multiple tenants concurrently; harden tenant isolation.
- Live tracking via Traccar integration.
- Driver mobile app.
- Real-time re-optimization as new orders/exceptions arrive mid-route.
- Multi-depot support.
- Write planning results back into Odoo (e.g. `fleet.vehicle` assignment,
  delivery sequence on `stock.picking`).

## Non-goals (either phase, unless revisited in DECISIONS.md)

- Zone-based routing.
- Paid SaaS dependencies beyond free tiers.
- Per-tenant database instances.
