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
- [x] Address fields restructured to `street`/`street2`/`city`/`state_id`+
      `state_name`/`country_id`+`country_name`/`zip` (one shared shape reused
      for both picking addresses and warehouse addresses — see DECISIONS.md)
- [x] Operation-type sync config: `synced_operation_types` table,
      refresh/toggle endpoints, refresh preserves existing `is_synced` on
      re-run (unit-tested against a real SQLite session, not mocked)
- [x] Warehouse sync config: `synced_warehouses` table, same refresh/toggle
      pattern, same address shape as picking addresses
- [x] Stock.picking sync now only fetches pickings whose `picking_type_id` is
      marked synced — an empty sync selection means zero pickings, not "all"
      (see DECISIONS.md "Operation-type sync gating")
- [x] Picking sync enriched with state, scheduled_date, resolved warehouse
      (via operation type → synced_warehouses), origin, native `weight`,
      optional `shipping_weight` (graceful `null` when the `delivery` module
      isn't installed — checked via `fields_get`, never errors), and note;
      persisted locally to `synced_pickings` as a side effect of every
      `/planning/run` call
- [x] `vehicles` / `drivers` tables — locally-owned, no Odoo link required to
      exist; CRUD + delete guards (vehicle: blocked if a driver references
      it; driver: blocked while active — see DECISIONS.md)
- [x] Optional Odoo `fleet.vehicle`/`hr.employee` browse + link/unlink —
      browse-only (never auto-creates locally), linking never overwrites
      local fields, gracefully returns `available:false` when the Fleet/HR
      module isn't installed (checked via `model_exists`, no error)
- [x] Stale Odoo link detection: linked vehicles/drivers get flagged `stale`
      (not silently unlinked, reference kept) when they disappear from a
      later Odoo browse; self-heals back to `linked` if they reappear (see
      DECISIONS.md "Stale Odoo links, not silent unlinking")
- [x] Odoo version detection: `common.version()` called (re-checked, not
      just once) on every `POST .../credentials/test`, persisted on the
      credential row, `version_change_detected` flagged (not silently
      overwritten) when the major version changes between checks
- [x] Version-aware field mapping registry (`app/odoo_mappings/`, one file
      per model, `resolve_field(model, logical_name, version_major)`) with a
      `"default"` fallback — every version block is currently empty (no
      real version-specific difference confirmed yet, none guessed at, per
      DECISIONS.md)
- [x] Graceful-degradation consolidated into
      `app.services.odoo_field_resolution.resolve_optional_field` (mapping
      lookup + live `fields_get()` check) — replaces the one-off
      `shipping_weight`-only check from the picking-enrichment batch
- [x] Picking enrichment, operation-type sync, warehouse sync, and
      fleet.vehicle/hr.employee lookup all now resolve Odoo-side field names
      through the mapping registry instead of hardcoded strings (behavior
      unchanged today since every default equals what was hardcoded before
      — confirmed by the full existing test suite passing unmodified)

## Frontend

- [x] Tenant login page
- [x] Password show/hide toggle on login
- [x] Add/edit Odoo connection form
- [x] Company selector (load companies from Odoo, pick one or "All companies")
- [x] "Run Planning" button + trigger flow
- [x] Results view: vehicle assignments + delivery sequence, including
      customer/items/address per stop (functional, not styled)
- [x] Operation Types screen: checkbox per row + "Resync List"
- [x] Warehouses screen: checkbox per row + "Resync List"
- [x] Planner results table: added status, scheduled date, source document,
      warehouse columns
- [x] Vehicles screen: list + create/edit form + Odoo fleet.vehicle link picker
- [x] Drivers screen: list + create/edit form + Odoo hr.employee link picker
- [x] Connection page shows detected Odoo version ("Connected — Odoo 17.0")
      and a warning when a version change was detected on the last check

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
- [x] Batch 2 re-verified against the same real instance: 86 operation types
      refreshed across 9 warehouses; toggling one operation type + warehouse
      on and re-running planning correctly narrowed results to just that
      operation type; `state`/`scheduled_date`/`origin`/`weight`/
      `shipping_weight` all came back with real values (this instance has
      the `delivery` module installed); warehouse resolution via the
      operation-type join confirmed correct on every stop
- [x] Vehicle/driver management verified against the same real instance:
      both Fleet and HR modules installed and browsable (6 real fleet
      vehicles, 29 real employees with phone numbers); linked a local
      vehicle + driver to real Odoo records; delete guards blocked deleting
      a vehicle referenced by a driver and blocked deleting an active
      driver; stale-link detection flagged a link to a nonexistent Odoo id
      as `stale` on the next browse, then self-healed back to `linked` once
      re-linked to a real id — full round trip confirmed live, not just
      unit-tested
- [x] Odoo version detection verified against the same real instance:
      `common.version()` correctly reports Odoo 19.0+e; simulated a stale
      stored version via direct DB update and confirmed
      `version_change_detected` flips `True` on the next test-connection,
      then settles back to `False` afterward; operation-type refresh and a
      full planning run both re-verified working end-to-end through the new
      field-resolution wiring (not just passing in isolation against a fake
      client)

## Next up

- [ ] Real Odoo 19 instance with volume/lat-lon data to confirm those field
      mappings (see "Open questions" below) — still placeholder zeros
- [ ] User invite/registration flow (currently seed-script only)
- [ ] Depot location modeling — route distance currently sums stop-to-stop
      legs only, no depot-to-first-stop leg (see SPEC.md)
- [ ] ETA computation — `RouteStop.eta` is always null; needs a depot start
      time + per-stop service time model
- [ ] Per-run company override or multi-company planning in one run — current
      design is one persisted default company per tenant (see DECISIONS.md)
- [ ] A decoupled "sync pickings" action independent of running a plan —
      today `synced_pickings` only updates when `/planning/run` is called
      (see DECISIONS.md)
- [ ] Stale/removed operation types or warehouses (deleted in Odoo, no longer
      returned by refresh) aren't pruned or flagged locally — `last_seen_at`
      just stops advancing; no UI surfaces that yet (vehicles/drivers now
      have this exact pattern via `odoo_link_status="stale"` — could unify)
- [ ] Cost log per vehicle — explicitly deferred, not built this batch;
      belongs in a later batch once there's a real usage pattern to design
      against
- [ ] Real trip/assignment-history table — would let the driver delete guard
      check actual current assignments instead of the `status="active"`
      stand-in (see DECISIONS.md), and would let the vehicle delete guard
      check more than just `driver.assigned_vehicle_id`
- [ ] No create/browse UI exists yet for `synced_warehouses`-less tenants to
      pick a vehicle's `home_warehouse_id` before any warehouse sync has run
      — the dropdown is just empty until Warehouses are refreshed
- [ ] `stock.move` (items_summary) and `res.company` (company selection)
      aren't wired to the version-aware mapping registry yet — deliberately
      out of this batch's scope (see DECISIONS.md), still hardcoded
- [ ] Every version block in `app/odoo_mappings/` is currently empty — no
      access yet to an Odoo instance running an older major version (13,
      15, 16) to confirm whether any real field-name differences exist to
      map. The registry is ready for them; nothing has been verified to
      actually differ
- [ ] `version_change_detected` has no "acknowledge/dismiss" action — it
      just gets recomputed fresh on each test-connection call (true = the
      *last* check saw a change). No historical log of past changes is kept
      beyond that one flag

## Open questions (need confirmation before implementing)

- [ ] Confirm actual Odoo 19 field names for delivery address lat/lon,
      volume on `stock.picking` (see [SPEC.md](SPEC.md))
- [ ] Confirm `fleet.vehicle` capacity field names — now more visibly needed
      since `weight_kg` is real (no longer a 0.0 placeholder): with vehicle
      capacity still hardcoded to 0.0, FFD only assigns orders that happen to
      weigh exactly 0, so most real orders come back unassigned until this is
      fixed
