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
- [x] Multi-company support: `company_id`/`company_name` on the Odoo
      credential, `GET .../credentials/companies` + `PUT .../credentials/company`,
      `allowed_company_ids` context threaded through every XML-RPC read (see
      DECISIONS.md)
- [x] Planning results carry customer name, items summary, and a broken-down
      address (street1/street2/city/country/zip) per stop — pulled from
      `res.partner` + `stock.move`, not just the bare picking ID

## Frontend

- [x] Tenant login page
- [x] Password show/hide toggle on login
- [x] Add/edit Odoo connection form
- [x] Company selector (load companies from Odoo, pick one or "All companies")
- [x] "Run Planning" button + trigger flow
- [x] Results view: vehicle assignments + delivery sequence, including
      customer/items/address per stop (functional, not styled)

## Infra

- [x] `docker-compose.yml`: postgres, redis, backend, nginx
- [x] Dockerfile per service (backend/Dockerfile; nginx/Dockerfile multi-stage
      builds the React app and serves it + reverse-proxies `/api`)
- [x] GitHub Actions: lint + test on PR
- [x] GitHub Actions: build images on merge to `main`
- [x] Full stack verified locally end-to-end: `docker compose up` → migration
      runs → login → save/test Odoo credential (never leaks key) → run
      planning (fails gracefully with a real error, not a 500) → fetch result
- [x] Verified against a real, multi-company Odoo 19 instance the user
      provided (`edu-accounting-learning.odoo.com`): company listing (9
      companies), company-scoped planning run (29 pickings vs. 37 unscoped —
      confirms `allowed_company_ids` filtering actually works), and
      customer/items/address enrichment all came back correctly, including
      multi-line item summaries like `"[FURN_8888] Office Lamp x5"`

## Next up

- [ ] Real Odoo 19 instance with weight/volume/lat-lon data to confirm those
      field mappings (see "Open questions" below) — still placeholder zeros
- [ ] User invite/registration flow (currently seed-script only)
- [ ] Depot location modeling — route distance currently sums stop-to-stop
      legs only, no depot-to-first-stop leg (see SPEC.md)
- [ ] ETA computation — `RouteStop.eta` is always null; needs a depot start
      time + per-stop service time model
- [ ] Per-run company override or multi-company planning in one run — current
      design is one persisted default company per tenant (see DECISIONS.md)

## Open questions (need confirmation before implementing)

- [ ] Confirm actual Odoo 19 field names for delivery address lat/lon,
      weight, time window on `stock.picking` (see [SPEC.md](SPEC.md))
- [ ] Confirm `fleet.vehicle` capacity field names
