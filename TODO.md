# Active Tasks — Phase 1 MVP

Check items off as completed; add newly discovered tasks here. Append a
one-line entry to [CHANGELOG.md](CHANGELOG.md) whenever a chunk of this list
gets done.

## Backend

- [x] Multi-tenant JWT auth
- [x] Tenant CRUD endpoints. **Removed 2026-07-26** — audited while adding
      subscription tracking and found `POST`/`GET /tenants` had zero auth
      (not actually admin-gated, despite SPEC.md's stale claim) and zero
      frontend usage; replaced with `python -m app.manage_tenants` (see
      below) rather than gating unused code
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
- [x] Session lifetime extended `JWT_EXPIRE_MINUTES` 60 → 10080 (7 days —
      see DECISIONS.md); fixed the real bug this was masking (see Frontend)
- [x] Odoo connection state machine (`draft`/`active`/`error`) added to
      `tenant_odoo_credentials` — company selection (even "All companies")
      is the action that activates a draft connection; a new
      `POST .../credentials/reauthenticate` endpoint does the same field
      update as initial setup but only once active (see DECISIONS.md)
- [x] `require_active_instance()` gate applied to every Odoo-talking
      endpoint (Operation Types/Warehouses refresh+preview, Vehicle/Driver
      Odoo browse + link) — Vehicle/Driver core CRUD and unlink deliberately
      NOT gated, per the existing "locally-owned" decision (see DECISIONS.md)
- [x] Resync split into preview (dry-run diff, `{new, removed,
      unchanged_count}`, writes nothing) and confirm (the existing
      upsert-based refresh) for both Operation Types and Warehouses
- [x] `active` archive/soft-delete flag added to SyncedOperationType,
      SyncedWarehouse, Vehicle, Driver — new archive-toggle endpoints for
      the first two, reused the existing generic update endpoint for the
      other two; new `include_archived` list filter on all four; new
      DELETE endpoints for Operation Types/Warehouses (didn't exist before)
      that block with an "archive instead" message when referenced (see
      DECISIONS.md)
- [x] Destination location library (`destination_locations` table) +
      per-warehouse route sets (`warehouse_destination_locations` join,
      many-to-many — a destination can be attached to several warehouses)
      with distance computed at read time from admin-entered warehouse
      `lat`/`lng` (new nullable columns on `synced_warehouses`, **not**
      Odoo-synced) and the destination's required `lat`/`lng`. New
      `destination_locations.py` router (CRUD) plus four new endpoints on
      `warehouses.py` (set coordinates; list/add/remove a warehouse's route
      set); deleting a destination cascades out of every route set instead
      of blocking. Reuses `can_manage_warehouses` rather than a new
      permission flag (see DECISIONS.md). **Superseded the same day** — the
      flat route set below was replaced with ordered, colored Routes; the
      destination library itself and admin-entered warehouse `lat`/`lng`
      are unchanged
- [x] Replaced the flat warehouse route set with named, colored
      `warehouse_routes` + ordered `route_stops` (drops
      `warehouse_destination_locations` outright via a migration with a
      defensive empty-check guard — no real data existed yet). New
      `warehouse_routes.py` router: CRUD for routes (color auto-assigned
      from a fixed palette, avoiding a color already in use at that
      warehouse); bulk-add stops (silently skips duplicates, reports which
      were skipped); reorder (full-list replace, 400 on a mismatched set);
      remove one stop. `destination_locations.py`/`warehouses.py`'s delete
      cascades updated to clean up `route_stops` instead of the old join
      rows. New `GET .../destination-locations/picking-addresses` —
      distinct customer/address combos from the tenant's already-synced
      `SyncedPicking` rows (deduped in Python, normalized case/whitespace),
      for prefilling a new destination's name/address fields — not a live
      Odoo partner browse, since `SyncedPicking` has no partner id to key
      a proper link/unlink feature on (see DECISIONS.md)
- [x] Tenant subscription tracking, prep for SaaS/billing mode: new
      `status`/`plan_name`/`billing_email`/`expire_date`/
      `warning_period_days`/`notes` columns on `tenants`.
      `app.services.tenant_subscription` computes `warning_date` and an
      overall state (`active`/`warning`/`expired`/`suspended`/`cancelled`)
      at read time rather than storing them — `status` is a manual
      override that always wins over the date math (see DECISIONS.md).
      Not enforced anywhere yet (no login/API blocking on an expired or
      suspended tenant — tracking only, until real billing exists).
      Removed the unauthenticated, unused `POST`/`GET /tenants` HTTP
      endpoints and replaced tenant management with a new CLI,
      `python -m app.manage_tenants create|list|update` (list supports
      `--state` filtering to quickly find tenants needing attention)

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
- [x] Connection page reworked into an explicit staged flow: credentials +
      Test → Save (draft) → Load companies → select → Activate; once
      active, the credentials form is replaced by a connection summary +
      a distinct "Re-authenticate" action
- [x] Operation Types/Warehouses pages gated behind an active connection
      (with a link to the Connection page); "Resync List" now shows a
      preview (new/removed/unchanged counts) before a "Confirm" write;
      "Show archived" toggle + per-row Archive/Unarchive + Delete
- [x] Vehicles/Drivers pages: core CRUD always available regardless of
      connection state; "Link to Odoo" section shows an inline "connect
      Odoo" note instead of the picker when not active; "Show archived"
      toggle + Archive action; Drivers' "Assigned vehicle" dropdown only
      offers active (non-archived) vehicles
- [x] Fixed a real bug: an expired session (JWT) wasn't detected anywhere —
      `RequireAuth` only checked token *presence*, and every data-loading
      page's `.catch(() => {})` swallowed the resulting 401 identically to
      "nothing saved yet." Symptoms: Odoo connection appeared to vanish on
      return visits, the "Test connection" button disappeared (gated on a
      credential load that silently failed), and Save/Test showed
      "Could not validate credentials" — which was about the expired login
      session, not the Odoo API key. Fixed with a client-side `exp`-claim
      check (`hasValidSession()` in `api/client.ts`, used by
      `RequireAuth`/`NavBar`) plus a centralized 401 handler in `request()`
      that clears the session and redirects to `/login`. Verified live: the
      Odoo API key the user reported as "invalid" connected successfully
      once a valid session was used — confirming it was never actually a
      credential problem
- [x] Tailwind CSS v4 adopted as the styling approach (no component
      library — see [design.md](design.md) for the full token/component
      reference); every existing screen (Login, Connection, Operation
      Types, Warehouses, Vehicles, Drivers, Planning, NavBar) restyled
      onto seven hand-built base components
      (`frontend/src/components/ui/`: Button, Input, Select, Card, Badge,
      CapacityBar, Table) — the old hand-rolled `index.css` classes are
      gone. Planner results table is no longer "functional, not styled"
      (see the "Results view" entry above)
- [x] Load Planning board — static/read-only layout (`/load-planning`):
      `useReducer`-backed `BoardState` (unassigned pickings, per-vehicle
      FILO assignment lists, a stubbed `selectedIds` for a future
      multi-select phase); left panel groups unassigned pickings into
      collapsible sections by compass direction with a new
      `frontend/src/lib/clustering.ts` utility (distance/bearing/compass/
      cluster — ported the haversine formula from
      `backend/app/services/planning/haversine.py` for consistency, since
      no such utility existed on the frontend yet); right side is one
      `VehicleCard` per vehicle with two `CapacityBar`s (weight, volume)
      and a numbered FILO stop list; mock data lives in
      `frontend/src/loadPlanning/fixtures.ts`, swappable for a real API
      call later without touching the panels. No drag-and-drop yet — see
      TODO below.
- [x] Load Planning board: single-card drag-and-drop wired with
      `@dnd-kit/core` (`@dnd-kit/sortable` deliberately not installed —
      within-vehicle reordering is a later phase). `DndContext` wraps the
      whole board with `PointerSensor` (8px activation distance, avoids
      accidental drags on tap) + `KeyboardSensor`; each picking row is
      `useDraggable`, the unassigned panel and each vehicle `Card` are
      `useDroppable` with a `ring-2 ring-accent` drag-over state;
      `DragOverlay` shows a floating preview while the original row dims.
      New reducer action `MOVE_ITEMS` (takes `pickingIds: string[]`,
      always length 1 today, so a later multi-select phase doesn't need
      a new action type) resolves the source container from the drag
      event's `data.current.containerId` and removes/appends accordingly;
      dropping back into the same container is a no-op both at the
      component level (skips dispatch) and in the reducer (returns the
      same state reference so `useReducer` bails out of re-rendering).
      `components/ui/Card.tsx` now forwards its ref to support this.
      Capacity bars update automatically since they already derive from
      vehicle contents — confirmed, no new capacity logic needed.
- [x] Load Planning board: cluster-header drag (moves every picking in a
      compass-direction group at once, resolved from the clustered data
      rather than the rendered/collapsed DOM) and multi-select drag
      (checkbox toggles selection; plain click replaces it with just
      that card; ctrl/cmd-click toggles like the checkbox — documented
      in design.md since the task asked for an unambiguous model).
      `MOVE_ITEMS` needed no reducer-shape change (it already took
      `pickingIds: string[]`); a drag now resolves to the cluster's full
      membership, the active selection (if the dragged card is part of
      it), or just that one card, computed once in `onDragStart` and
      reused for both the "N items" `DragOverlay` badge and the eventual
      dispatch. A successful move always clears `selectedIds` as part of
      the same state update. Selected-card highlight
      (`border-accent bg-accent/5`) is deliberately not the same
      `ring-2 ring-accent` used for a droppable's drag-over state, per
      the task's "distinct from drag-over" requirement.
- [ ] Load Planning board: within-vehicle reorder (`@dnd-kit/sortable`),
      real API data instead of fixtures, capacity validation/blocking,
      backend persistence, shift-click range-select
- [x] Destination Locations page (`/destinations`, gated on
      `can_manage_warehouses`): a library CRUD section (name/address/
      lat/lng, table with Edit/Delete) plus a per-warehouse route-set
      manager (choose a warehouse, edit its lat/lng inline, list its
      attached destinations with computed distance, add from the
      unattached pool, remove per row). Nav link added next to
      "Warehouses". Built on the existing base components, no new
      design-system pattern introduced. **Reworked the same day** — the
      route-set manager moved to a new dedicated Routes page (below);
      warehouse lat/lng editing moved to the Warehouses page; added a
      "prefill from a recent delivery address" picker sourced from
      already-synced pickings
- [x] Nav reorganized into a grouped dropdown ("Setup") rather than one
      flat row of links, in anticipation of more screens being added
      (new `NavDropdown.tsx` — trigger button + panel, closes on outside
      click/Escape/picking an item; `NavBar.tsx`'s `NAV` list is now a
      union of flat links and `{kind: "group", items: [...]}` entries so
      future screens can extend either shape without touching the
      dropdown logic itself)
- [x] Warehouses page: added an inline lat/lng column + per-row
      "Edit coordinates" action (two number inputs + Save/Cancel, matching
      the existing dense-table row-action style) — moved here from the
      Destinations page, same unchanged backend endpoint
- [x] New Routes page (`/warehouse-routes`, gated `can_manage_warehouses`,
      grouped under the "Setup" nav dropdown): pick a warehouse first,
      then a Leaflet + OpenStreetMap view (new `RouteMap.tsx`) shows every
      route for that warehouse at once, each in its own color, straight
      lines only (not real road routing); a route list with
      Create/Rename-recolor/Delete; a per-route editor with an ordered
      stop table (up/down-button reorder, per-row Remove, distance shown
      per stop) and a multi-select checkbox picker over the destination
      library with a bulk "Add N selected" action. First use of a mapping
      library in this project — `leaflet` + `react-leaflet@^4` (not the
      current v5, which requires React 19; this project is on React 18) +
      `@types/leaflet`. Markers use `L.divIcon` (inline HTML/CSS), not
      Leaflet's default image-based icons, to avoid the well-known
      bundler asset-path issue and to make per-route coloring trivial

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
- [x] Connection state machine + archive/delete-guard refactor verified
      against the same real instance: the migration's backward-compat step
      correctly auto-activated the existing connection; preview correctly
      diffed real operation-type/warehouse data; confirm-refresh updated
      `last_synced_operation_types_at`/`last_synced_warehouses_at`;
      archive/unarchive round-tripped through `include_archived` list
      filtering; the warehouse delete guard blocked deleting a warehouse
      referenced by a live-created vehicle, then cleaned up correctly; and
      `reauthenticate` succeeded with the real API key, confirmed still
      working via a follow-up `test_connection` call. Frontend build (tsc +
      vite) and lint both clean, but no interactive browser click-through
      was performed in this environment — no browser automation tool was
      available, so the UI itself (as opposed to the API it calls) is
      unverified beyond the type-checked build

## Next up

- [ ] **Manage the tenant list from Odoo** — the user's stated future
      direction: for now, tenant onboarding/subscription management is a
      CLI script (`python -m app.manage_tenants`, see above), but they
      intend to eventually manage the client/tenant list from Odoo
      itself instead. No integration shape decided yet — open questions
      to resolve when this is picked up: is Odoo the system of record
      (this project's `tenants` table becomes a synced mirror, like
      `synced_warehouses`/`synced_operation_types` already are for a
      *tenant's own* Odoo data) or just a management UI that calls back
      into this project's own tenant data; which Odoo model would
      represent a tenant/subscription (a custom model, or repurposing
      `res.partner` + a subscription/contract app); and whether this
      needs its own dedicated "platform" Odoo instance separate from
      each tenant's own connected Odoo instance (today's
      `tenant_odoo_credentials` is explicitly one-per-tenant, scoped to
      that tenant's own data — a platform-level Odoo connection for
      managing tenants themselves would be a new, different concept, not
      a reuse of that table)
- [ ] Enforce tenant subscription state — today `status`/`expire_date`/
      `warning_period_days` are tracked and computed
      (`app.services.tenant_subscription`) but nothing is blocked: an
      expired or suspended tenant's users can still log in and use the
      API normally. Deliberately deferred until real billing/payment
      exists (see DECISIONS.md) — revisit alongside whatever billing
      integration eventually gets built, including what a blocked user
      should actually see (a clear "subscription expired, contact us"
      state, not a generic error)
- [x] Map visualization for route arrangement — the user asked for this
      explicitly, then confirmed and refined the requirements after
      reviewing the shipped destination-location library: ordered stops
      (not just an unordered colored group), Leaflet + OpenStreetMap (no
      paid API), straight lines only (not real road routing). Delivered as
      the `warehouse_routes`/`route_stops` model + `RouteMap.tsx` +
      `WarehouseRoutesPage.tsx` batch — see the "Replaced the flat
      warehouse route set..." entries above and DECISIONS.md
- [ ] Drag-and-drop reorder for a route's stops on the new Routes page —
      currently up/down buttons only. `@dnd-kit/core` is already a
      dependency (used by the Load Planning board) but `@dnd-kit/sortable`
      (the piece that actually gives list-reordering) is not installed;
      within-vehicle drag reorder on the Load Planning board was also
      deferred for the same reason, so this is consistent with that
      existing gap, not a new one
- [ ] True partner-id-based Odoo address linking for destinations —
      today's picking-address prefill only copies text once at creation
      time, with no live link/unlink the way Vehicles/Drivers have to
      `fleet.vehicle`/`hr.employee`. `SyncedPicking` has no stored Odoo
      `res.partner` id to key that on; the raw id is fetched and used
      transiently inside `runner.py` to join addresses, then discarded.
      Adding it is confirmed low-effort (new `partner_id` column on
      `SyncedPicking`/`Order`, threaded through `runner.py`) but out of
      scope for this batch
- [ ] `app/services/planning/runner.py::fetch_vehicles` still pulls
      `fleet.vehicle` directly from Odoo on every planning run — it does
      not use the local `vehicles` table at all. Discovered while building
      the archive/delete-guard feature: means "referenced by a planning
      run" doesn't actually apply to the local `Vehicle` entity today (see
      DECISIONS.md "Archive instead of hard delete")
- [ ] No refresh-token mechanism — at 7 days, a session still eventually
      hard-expires and the user must log in again from scratch. Fine for
      now; revisit if 7 days turns out to be too short in practice
- [ ] Real Odoo 19 instance with volume/lat-lon data to confirm those field
      mappings (see "Open questions" below) — still placeholder zeros
- [x] User management: add/edit/delete users, admin resets any user's
      password, self-service password change for any logged-in user
      (`/tenants/{id}/users/*`, `/auth/me`, `/auth/password` — see
      DECISIONS.md "User management: role vs. boolean permissions"). Two
      roles (admin/user), but `role` only gates the Users page itself —
      six independent booleans (`can_manage_connection`/`_warehouses`/
      `_operation_types`/`_fleet`, `can_run_planning`,
      `can_use_load_planning`) gate everything else, for every account
      regardless of role. Every existing router (credentials, warehouses,
      operation-types, vehicles, drivers, planning) now requires the
      matching permission on every endpoint. Frontend: Users page
      (admin-only) for CRUD + permission toggles, an Account page for
      self-service password change, nav links and routes hidden/blocked
      per the current user's permissions via a new `CurrentUserContext`
      (mirrors `OdooInstanceContext`) and `RequirePermission` guard.
      Still no invite-email flow — an admin sets the initial password
      directly and shares it out of band, same limitation the seed
      script always had
- [ ] Invite-email flow for new users (currently: admin sets an initial
      password directly, no email involved) — needs an email-sending
      capability this project doesn't have yet
- [ ] `can_use_load_planning` has no backend endpoint to actually gate
      yet (the load-planning board is still fixture data); only enforced
      via the frontend route today — revisit once it gets real API calls
- [ ] No superadmin/support-side way to recover a tenant that's down to
      zero users entirely (as opposed to zero admins, which is guarded) —
      out of scope for now, would need a platform-level operator role
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
