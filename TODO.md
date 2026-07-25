# Active Tasks — Phase 1 MVP

Check items off as completed; add newly discovered tasks here. Append a
one-line entry to [CHANGELOG.md](CHANGELOG.md) whenever a chunk of this list
gets done.

## Backend

- [x] Multi-tenant JWT auth
- [x] Tenant CRUD endpoints
- [x] Encrypted Odoo credential storage (Fernet) — store/update/never-return-plaintext
- [x] Odoo XML-RPC client wrapper + test-connection endpoint
- [x] FFD bin-packing module (capacity-based, no zones)
- [x] Haversine distance/time estimation module
- [x] FILO sequencing module
- [x] `/planning/run` endpoint: pull open `stock.picking` from tenant's Odoo,
      run FFD + FILO, return JSON assignment result (no write-back to Odoo yet)
- [x] Alembic migrations set up from the start (hand-written initial migration,
      verified against a real Postgres via `docker compose up`)
- [x] Dev seed script (`app/seed.py`) — MVP has no self-registration/invite
      endpoint (not in SPEC.md's endpoint list), so this is the only way to
      get a first tenant + login user

## Frontend

- [x] Tenant login page
- [x] Add/edit Odoo connection form
- [x] "Run Planning" button + trigger flow
- [x] Results view: vehicle assignments + delivery sequence (functional, not styled)

## Infra

- [x] `docker-compose.yml`: postgres, redis, backend, nginx
- [x] Dockerfile per service (backend/Dockerfile; nginx/Dockerfile multi-stage
      builds the React app and serves it + reverse-proxies `/api`)
- [x] GitHub Actions: lint + test on PR
- [x] GitHub Actions: build images on merge to `main`
- [x] Full stack verified locally end-to-end: `docker compose up` → migration
      runs → login → save/test Odoo credential (never leaks key) → run
      planning (fails gracefully with a real error, not a 500) → fetch result

## Next up

- [ ] Real Odoo 19 instance to confirm field mappings (see "Open questions"
      below) — `runner.py`'s `fetch_open_orders`/`fetch_vehicles` currently
      return zeroed weight/volume/lat/lon placeholders
- [ ] User invite/registration flow (currently seed-script only)
- [ ] Depot location modeling — route distance currently sums stop-to-stop
      legs only, no depot-to-first-stop leg (see SPEC.md)

## Open questions (need confirmation before implementing)

- [ ] Confirm actual Odoo 19 field names for delivery address lat/lon,
      weight, time window on `stock.picking` (see [SPEC.md](SPEC.md))
- [ ] Confirm `fleet.vehicle` capacity field names
