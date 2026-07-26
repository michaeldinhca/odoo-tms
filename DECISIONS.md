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

---

## 2026-07-25 — Vehicles and drivers are locally-owned; Odoo is an optional cross-reference only

**Decision:** `vehicles` and `drivers` are first-class tables owned by this
system. A vehicle or driver can exist with `odoo_link_status="unlinked"` and
no Odoo reference at all — e.g. a subcontracted truck that was never in
Odoo. Linking sets `odoo_fleet_vehicle_id`/`odoo_employee_id` and flips
`odoo_link_status` to `"linked"`; it never writes to or reads back any other
local field, so linking can never silently overwrite data the dispatcher
entered by hand.

**Why:** Odoo's `fleet.vehicle`/`hr.employee` don't model most of what this
system needs (payload capacity, fuel consumption, driver lock windows,
etc.), and requiring an Odoo record to exist before a vehicle/driver can be
used here would block onboarding fleets that were never in Odoo to begin
with.

---

## 2026-07-25 — Stale Odoo links, not silent unlinking

**Decision:** `odoo_link_status` has a third state, `"stale"`, alongside
`"unlinked"`/`"linked"`. Every time the Odoo fleet.vehicle or hr.employee
list is browsed (`GET .../odoo-fleet-vehicles`, `GET .../odoo-employees`),
every locally `linked`/`stale` record for that tenant is checked against the
just-fetched id set: still present → `linked`; no longer present → `stale`.
The `odoo_fleet_vehicle_id`/`odoo_employee_id` value itself is never cleared
by this check — only the status flag changes, and it self-heals back to
`linked` if the Odoo record reappears on a later browse. This check is
skipped entirely when the Odoo module itself is unavailable (`available:
false`) — that's a different signal than "this one record was deleted" and
flagging every link stale in that case would be misleading.

**Why:** A vehicle/driver deleted in Odoo after being linked here shouldn't
silently lose its local data or its link — the dispatcher should see that
something changed and decide what to do, not have it happen invisibly.

---

## 2026-07-25 — Driver delete guard: "active" status stands in for "has current assignments"

**Decision:** `DELETE .../drivers/{id}` is blocked when `driver.status ==
"active"`, full stop. There's no trip/assignment-history table yet (that's
future work — see TODO.md), so "has current assignments" isn't literally
checkable; active status is the closest real signal available today, and
the caller can always set status to `inactive` first if they're sure.
Vehicle's delete guard, by contrast, checks something that genuinely exists
today: whether any `driver.assigned_vehicle_id` points at it.

**Why:** Blocking on a concept ("current assignments") that has no backing
data would either be unimplementable or require inventing a table nobody
asked for yet. Revisit once real trip/assignment tracking exists.

---

## 2026-07-25 — Odoo version detection: re-checked on every test-connection, changes flagged not silently overwritten

**Decision:** `POST .../credentials/test` calls Odoo's public
`common.version()` (no auth required) every time it runs — not just once at
setup — and persists `server_version`/`server_version_major`/
`server_serie`/`protocol_version` on the tenant's `tenant_odoo_credentials`
row. If the newly-detected `server_version_major` differs from what was
already stored (and something was already stored — the very first check
never "changes" anything), `version_change_detected` is set `True` and a
warning is logged server-side. The value is simply overwritten with the new
version either way; nothing blocks the credential from being used. The
frontend shows the detected version and a warning banner when
`version_change_detected` is true.

**Why:** A tenant's Odoo instance can be upgraded after the connection was
first configured, and field mappings (see the next entry) are keyed on
major version — silently trusting a stale cached version number risks
resolving field names for the wrong version. Re-checking on every test
keeps this cheap (one extra unauthenticated XML-RPC call) and gives the
dispatcher a visible signal ("this changed, some things might need a
second look") instead of either erroring outright or masking the change.

---

## 2026-07-25 — Version-keyed field mapping registry with a default fallback, not per-version duplication

**Decision:** `app/odoo_mappings/` holds one file per integrated Odoo model
(`stock_picking.py`, `stock_warehouse.py`, `stock_picking_type.py`,
`fleet_vehicle.py`, `hr_employee.py`, `res_partner.py`), each a `FIELD_MAP`
dict shaped `{"default": {...}, <major_version>: {...only entries that
differ...}}`. `resolve_field(model, logical_name, version_major)` checks
the version-specific block first, falls back to `"default"` if the logical
name isn't overridden there, and falls back to `"default"` entirely for any
`version_major` with no block at all (including versions newer than
anything seen yet). As of this batch, **every** version block is empty —
no Odoo field-name difference has actually been confirmed against a real
instance of a specific version, so none is guessed at. A version block gets
added only once a real difference is verified against an actual Odoo
instance running that version — never speculatively (the task that
commissioned this batch was explicit about this, and it matches the
project's general stance against guessing at unverified Odoo behavior).

**Why default-fallback instead of a full field list duplicated per
version:** Odoo's field names are overwhelmingly stable release to release
— duplicating the full set for every supported major version would mean
one typo silently breaks a specific version's sync with no signal, and
every unrelated field addition would require touching N version blocks
instead of one default entry. A sparse override list means the *diff* from
default is the only thing that has to be correct, and an empty version
block (the common case) costs nothing.

**Scope note:** `stock.move` (used for `items_summary`) and `res.company`
(used for company selection) are deliberately **not** in the mapping
registry this batch — the task's file list and "wire existing sync code"
list both named six specific models and didn't include these two. Left as
directly-hardcoded field names for now; see TODO.md.

---

## 2026-07-25 — Graceful field-degradation consolidated into one bridge function

**Decision:** `app.services.odoo_field_resolution` has exactly two
functions: `resolve_required_field` (pure mapping lookup, no Odoo call —
for fields assumed always present) and `resolve_optional_field` (mapping
lookup + a live `fields_get()` existence check, returning `None` instead of
a field name when absent). The previous ad-hoc pattern — inline
`client.has_field("stock.picking", "shipping_weight")` only at that one
call site — is now this one reusable function, and any future
optional-field case (a new module-gated field on any of the six mapped
models) should go through it rather than growing its own inline check.

**Why:** Consolidating means there's one place that knows "how do we handle
a field that might not exist" — easier to get right once, easier to find
when auditing which fields degrade gracefully vs. which are assumed
present.

---

## 2026-07-25 — Session lifetime extended to 7 days; frontend now handles expiry explicitly

**Decision:** `JWT_EXPIRE_MINUTES` default changed from `60` to `10080`
(7 days). Separately (and this part isn't a judgment call, it's a bug fix):
the frontend now actually detects an expired/invalid session — a decoded-
client-side expiry check in `RequireAuth`/`NavBar` (`hasValidSession()` in
`app/api/client.ts`) redirects to `/login` before rendering a protected
page, and `request()`'s 401 handling clears the stale session and
redirects for any case the client-side check can't catch (e.g. the
backend restarting with a new `JWT_SECRET`).

**Why the extension:** the 60-minute default meant a dispatcher using the
app across a shift would get logged out mid-use — and worse, because nothing
detected the expiry (see the bug fix above), it silently manifested as
"my Odoo connection disappeared" and "invalid credentials" errors that were
actually about the login session, not Odoo. Reported directly by the user
after hitting exactly this. 7 days trades off a longer window of exposure
if a token leaks against not re-authenticating constantly for an internal
dispatcher tool; revisit if this system gets exposed to a less trusted user
base or needs tighter compliance requirements.

**Why the frontend fix matters independently of the extension:** even at
7 days, a token will eventually expire, and nothing about the extension
fixes the underlying gap — the app must always be able to tell "not
configured yet" apart from "you got logged out." This was a real bug, not
just tuned around.

---

## 2026-07-25 — Odoo connection state machine: draft/active/error on `TenantOdooCredential`

**Decision:** Kept the existing `TenantOdooCredential` model/table name
rather than renaming it to `OdooInstance` — added a `state` column
(`draft` → `active`, `error` reserved for future use but not yet set
anywhere) plus `activated_at`, `last_synced_operation_types_at`,
`last_synced_warehouses_at`. `PUT .../credentials` (initial setup) always
creates a `draft` row and never changes `state` on an existing row.
`PUT .../credentials/company` (selecting a company, including explicitly
choosing "All companies") is the action that transitions `draft` → `active`
and stamps `activated_at` the first time; calling it again while already
`active` just rescopes the company without resetting `activated_at`. A new
`POST .../credentials/reauthenticate` endpoint does the same field-update
work as the initial setup PUT, but only when `state == "active"` (409
otherwise) — kept as a distinct endpoint (not just a relabeled button) so
the state machine is enforced server-side, not only in the UI.

**Why keep the name:** renaming would have touched ~10 files (routers,
schemas, services, tests) for no behavior change — the state-machine fields
fit naturally onto the existing row without implying a different entity.

**Why gate on company selection, not on save:** saving credentials only
proves the URL/db/credentials are well-formed; it doesn't mean the
dispatcher has actually finished onboarding. Company selection (even
"All companies") is the last step in the UI wizard, so it's the natural
"onboarding complete" signal.

---

## 2026-07-25 — Odoo-talking endpoints gated on `state == "active"`; Vehicle/Driver core CRUD is not

**Decision:** A new `require_active_instance()` helper
(`app/services/odoo_credential_gate.py`) returns 409 unless the tenant's
connection is `active`. It gates: Operation Types/Warehouses `refresh` and
`refresh/preview`, and the Vehicle/Driver `odoo-fleet-vehicles`/
`odoo-employees` browse endpoints plus the `PUT .../odoo-link` (create a
new link) endpoints. It does **not** gate: `unlink` (removing a reference
is always safe, no Odoo call involved), or any Vehicle/Driver core CRUD
(create/edit/delete/archive) — those must keep working with zero Odoo
connection at all, per the existing "vehicles and drivers are locally-owned"
decision above. Operation Types and Warehouses, which have no standalone
value outside an Odoo sync, are fully gated behind an active connection at
the page level in the frontend too.

**Why:** the acceptance criteria for this batch asked for all four synced/
fleet screens to be gated behind an active connection, but that would have
reversed a previous, deliberate decision that a subcontracted vehicle or
driver never in Odoo must still be manageable. Surfaced this conflict to
the user directly rather than picking a side silently; they confirmed
partial gating (core CRUD always available, only the Odoo-linking
sub-feature gated) is correct.

---

## 2026-07-25 — Resync becomes preview-then-confirm; nothing writes on the first click

**Decision:** `POST .../operation-types/refresh` and `.../warehouses/refresh`
(the "confirm and apply" call, unchanged behavior — upserts via the existing
`upsert_operation_types`/`upsert_warehouses`) now have a sibling
`POST .../refresh/preview` that fetches from Odoo and diffs against the
locally stored rows by Odoo id (`preview_operation_types`/
`preview_warehouses` in `app/services/sync_config.py`), returning
`{new, removed, unchanged_count}` without writing anything. The frontend's
"Resync List" button now always calls preview first and shows the diff;
"Confirm" performs the actual write.

**Why:** "Resync List" previously wrote directly with no way to see what
would change first — a stale operation type silently vanishing, or an
unexpected new one appearing, was invisible until after the fact.

---

## 2026-07-25 — Archive (`active` flag) instead of hard delete when referenced elsewhere

**Decision:** Added an `active: bool` (default `True`) column to
`SyncedOperationType`, `SyncedWarehouse`, `Vehicle`, and `Driver` — a
soft-delete/archive flag, deliberately separate from `is_synced` (planning
opt-in) and `status` (business state like "maintenance"), matching Odoo's
own `active` field convention. New `PUT .../operation-types/{id}/archive`
and `.../warehouses/{id}/archive` endpoints toggle it; Vehicle/Driver reuse
their existing generic `PUT` update endpoint with `active` added to the
update schema, since a dedicated endpoint wasn't needed there. All four
`GET` list endpoints default to `active`-only, with a new `include_archived`
query param to see everything. New `DELETE` endpoints for Operation Types
and Warehouses (neither had one before this batch) block with a 400
("archive instead") when referenced: an operation type by a
`SyncedPicking.picking_type_id` match, a warehouse by either
`Vehicle.home_warehouse_id` or a `SyncedPicking.warehouse_id` match. The
existing Vehicle/Driver delete guards (blocked if referenced by a driver /
blocked while active) are unchanged, just with their error messages updated
to mention archiving as the alternative.

**Why archive refreshes don't touch it:** `upsert_operation_types`/
`upsert_warehouses` never set `active` on an existing row — same "don't
silently reset a toggle the user set" rule already established for
`is_synced`. An archived row that reappears in a later Odoo refresh stays
archived until the user explicitly unarchives it.

**Note — pre-existing gap, not fixed here:** `app/services/planning/
runner.py::fetch_vehicles` still pulls `fleet.vehicle` directly from Odoo
on every planning run rather than using the local `vehicles` table, so
"referenced by a planning/route record" doesn't actually apply to the
local `Vehicle` entity yet. Logged in TODO.md as a follow-up.

---

## 2026-07-25 — User management: role vs. boolean permissions

**Decision:** `User` gained a `role` column (`admin`/`user`) and six
independent `can_manage_connection`/`can_manage_warehouses`/
`can_manage_operation_types`/`can_manage_fleet`/`can_run_planning`/
`can_use_load_planning` booleans. `role` does **not** act as an
all-access bypass — it is checked in exactly one place
(`app.api.deps.require_admin`, gating `/tenants/{id}/users/*`) and
nowhere else. Every other endpoint is gated by `require_permission(flag)`,
which checks the boolean directly regardless of `role` — an admin with
`can_manage_warehouses=false` is blocked from the Warehouses page exactly
like a `user`-role account would be. New users default to `role="user"`
with `can_run_planning`/`can_use_load_planning` true and the rest false,
matching the "user can load stock pickings [i.e. run planning], use load
planning" baseline the user described; an admin creating a user can
freely override any of the six regardless of the chosen role.

**Why not let `role="admin"` bypass the booleans:** the user explicitly
asked for "functional boolean turn on/off for each function... that will
give flexibility to assign user permission." A role-bypass would silently
undermine that — turning a box off would do nothing for an admin account,
which isn't the flexibility that was asked for. Keeping `role` narrowly
scoped to "can this account reach the Users page" makes the booleans the
one real permission mechanism, consistently, for every account.

**Last-admin lockout guard:** demoting (`role` admin→user) or deleting the
last remaining `role="admin"` row for a tenant is rejected with a 400
(`app.api.users`, `_admin_count`). Without this, a tenant with a single
admin could accidentally lock itself out of its own user management —
there is no superadmin/support backdoor in this system to recover from
that.

**Fresh-DB-lookup permission checks, not JWT claims:** `get_current_user`
now queries the `users` row on every request instead of trusting anything
baked into the JWT at login time — with a 7-day token lifetime (see the
session-lifetime entry above), a permission revoked mid-session, or a
deleted user, needs to take effect on the very next request, not just
after the token eventually expires. Same reasoning applies on the
frontend: `CurrentUserContext` fetches `/auth/me` rather than decoding
the JWT for role/permissions (the JWT is only ever decoded client-side
for its `exp` claim, to detect an expired session — see
`hasValidSession()`).

**Permission mapping onto existing routers (all fully gated, not split
read/write):** `can_manage_connection` → all of `credentials.py`;
`can_manage_warehouses` → all of `warehouses.py`; `can_manage_operation_types`
→ all of `operation_types.py`; `can_manage_fleet` → all of `vehicles.py`
*and* `drivers.py` (kept together rather than split, since the user
described them as one "employee" management concern); `can_run_planning`
→ all of `planning.py`. Every route in a gated file is covered, including
plain `GET`s — a `user` role has no stated need to even view Odoo
connection details, warehouses, etc., so there was no reason to split
read from write per endpoint. `can_use_load_planning` currently has no
backend endpoint to gate (the load-planning board is still fixture data —
see design.md), so it's enforced only via the frontend route guard;
revisit once that page gets real API calls.

**No invite-email flow:** there's no email-sending capability anywhere in
this project. An admin creating a user sets the initial password directly
and shares it out of band — this was true of the original single seeded
account too (`app/seed.py`), just now available through the UI instead of
only a script. Logged as a TODO if this ever needs to scale past a
handful of manually-added accounts per tenant.

---

## 2026-07-25 — Destination location library + per-warehouse route sets

**Decision:** Added a reusable `DestinationLocation` library (name,
address, required `lat`/`lng`) that admins can attach to any number of
warehouses via a many-to-many join (`WarehouseDestinationLocation`), with
distance from each warehouse shown per association. Also added
admin-entered, nullable `lat`/`lng` columns directly on `SyncedWarehouse`.

**Why a standalone entity instead of per-warehouse locations:** the user
explicitly asked to "add destination location in several warehouse" — the
same physical destination (e.g. a large retail customer) can receive
deliveries staged from more than one warehouse, and duplicating it under
each warehouse would fragment edits (fixing a typo'd address would need
doing N times) and make "how many warehouses deliver here" unanswerable.

**Reused `can_manage_warehouses` rather than a new permission flag:** this
feature is squarely warehouse-adjacent (it exists to support route
planning around warehouses) and the existing six-boolean permission model
(see "Role vs. boolean permissions" above) was deliberately kept small;
adding a seventh flag for a feature this closely tied to warehouse
management would fragment permissions without a clear use case for
granting one without the other.

**Cascade-delete over block-delete for `DestinationLocation`:** unlike
e.g. a warehouse referenced by a vehicle's `home_warehouse_id` (see
"Archive instead of hard delete" — an entity depended on for
correctness), a `WarehouseDestinationLocation` join row is a low-stakes
reference. Deleting a destination removes it from every route set it was
in rather than blocking the delete or requiring the admin to manually
detach it from N warehouses first.

**Distance computed at read time, never stored:** `app.services.
destination_locations.distance_km` (haversine, reusing the existing
`app.services.planning.haversine.haversine_distance_km` — not the
frontend's separate `clustering.ts` port, which is client-side-only for
the Load Planning board's fixture data) is called fresh on every list
request. Either the warehouse's or the destination's coordinates can be
edited after an association exists; caching the distance on the join row
would silently go stale.

**Warehouse `lat`/`lng` are admin-entered, not Odoo-synced:** Odoo's
`res.partner` lat/lon field mapping was never confirmed (see SPEC.md
"Odoo field mappings" — still a TODO row), so rather than block this
feature on that unconfirmed mapping, warehouse coordinates are set
directly through a new `PUT .../warehouses/{id}/coordinates` endpoint.
Revisit and switch to Odoo-sourced values once that mapping is confirmed.

**Deferred, not built:** the user also asked for a map visualization when
arranging routes — each route in a distinct color, associated with a
specific warehouse. Logged as a future item in TODO.md rather than built
now; this batch is the data layer (destinations, route sets, distances)
the map would eventually render.

---

## 2026-07-26 — Replaced the flat warehouse route set with ordered, colored Routes + a map

**Decision:** The flat, unordered `WarehouseDestinationLocation` join from
the batch above (same day) was replaced with two new tables: named,
colored `WarehouseRoute` rows per warehouse, each an ordered sequence of
`RouteStop`s. A new Leaflet + OpenStreetMap view (`RouteMap.tsx`) renders
every route for a warehouse at once, each in its own color, with straight
lines (not real road routing) connecting the warehouse through its stops
in order. Warehouse lat/lng editing moved from the Destinations page to
the Warehouses page. A new destination-creation prefill sources
name/address text from the tenant's already-synced `SyncedPicking` rows.

**Why replace instead of extend:** the user reviewed the shipped flat
route-set UI and asked for something structurally different — an actual
"route" concept with order and color, matching the six-color reference
image from the original map-visualization ask, not an unordered pool of
associated destinations. Confirmed via `AskUserQuestion`: stops are
ordered (not just an unordered colored group), matching the "arrange the
route" language and the existing FILO/`RouteStop` precedent from planning
results.

**Hard-dropped `warehouse_destination_locations` rather than migrating
data:** confirmed empty live (via curl) at the point this decision was
made, and the shipped UI showed "No destinations yet" — no real user data
existed to preserve. This is the first migration in this project to hard
`DROP TABLE` a table that's actually been live (every prior `drop_table`
call lives in a `downgrade()`, reverting its own just-applied migration),
so the migration (`0009_warehouse_routes`) adds a defensive row-count
check before dropping and raises instead of silently discarding data if
that assumption turns out wrong by the time it actually runs.

**Route color palette + not-already-used-then-cycle assignment:** this
project previously had only a single `accent` color plus a 3-color status
scale — no categorical "N distinct things" palette existed. Added a fixed
8-color palette (`app.services.warehouse_routes.ROUTE_COLOR_PALETTE`).
Auto-assignment picks the first palette color not currently used by
another route *at the same warehouse*, falling back to cycling by count
only once every palette color is in use — a plain `existing_count %
len(palette)` scheme would hand out an already-in-use color after a
delete-then-create (3 routes get colors 0/1/2, delete the one with color
1, create a new one: count-based indexing would collide with the
surviving color-2 route).

**Bulk-add stops silently skips duplicates instead of 400ing:** a
different UX contract than the old single-add endpoint (which 400'd on a
duplicate) — that endpoint was one explicit action on one destination,
where an unexpected 400 is informative; bulk-add is "I selected N
destinations, give me the ones that aren't already in this route,"
where erroring the whole batch over one already-present pick would be
worse UX, not a matching one. The response still reports which ids were
skipped rather than silently discarding that information.

**Straight-line map polylines, not real road routing:** consistent with
this project's standing decision to avoid a paid routing/matrix API
(Haversine distance was chosen for the same reason). The map shows
as-the-crow-flies lines between stops in the route's stored order, not
turn-by-turn directions.

**Leaflet + OpenStreetMap over Mapbox:** no API key or billing account
required, matching the "no paid routing/matrix API" posture. `L.divIcon`
(inline HTML/CSS circle markers) is used instead of Leaflet's default
image-based `L.Icon` — sidesteps the well-known bundler/Vite asset-path
breakage with Leaflet's default marker images, and makes per-route
coloring trivial without a colored PNG per palette color.
`react-leaflet@^4` (not the current v5) was installed deliberately — v5
requires React 19, and this project is on React 18.

**Picking-address prefill, not a live Odoo partner browse:** the user
asked for destinations to link to/pull from an Odoo delivery address;
confirmed this means reusing the address `stock.picking` sync already
resolves (`SyncedPicking`'s text address fields), not a new XML-RPC
browse endpoint like Vehicles/Drivers have for `fleet.vehicle`/
`hr.employee`. `SyncedPicking` has no stored Odoo `res.partner` id (the
raw id is used transiently inside `runner.py` to join addresses, then
discarded before reaching `Order`/`SyncedPicking`) — so there's no id to
key a proper live link/unlink feature on today. The new endpoint
(`GET .../destination-locations/picking-addresses`) is a lower-fidelity
"prefill text once" feature: it dedupes already-synced pickings by
normalized (lowercased, trimmed) address text, not by any stable
identifier, since Odoo's free-text address fields aren't normalized at
sync time. Deduping happens in Python, not a dialect-specific SQL
`DISTINCT ON`, since this query needs to run against both Postgres and
the SQLite test fixture. A real partner-id-based link feature would need
a new `partner_id` column on `SyncedPicking`/`Order`, threaded through
`runner.py` (confirmed low-effort — the id is already fetched and
discarded) — logged as a future item in TODO.md, out of scope here.

**Warehouse coordinate editing moved to the Warehouses page:** it's a
warehouse property; editing it from the Destinations page (as the prior
batch shipped it) was the wrong screen. The backend endpoint
(`PUT .../warehouses/{id}/coordinates`) is unchanged — only the frontend
form's location moved.

---

## 2026-07-26 — Tenant subscription tracking + script-based tenant management

**Decision:** Added subscription/billing metadata to `Tenant`
(`status`, `plan_name`, `billing_email`, `expire_date`,
`warning_period_days`, `notes`) as prep for a future SaaS/billing mode.
Removed the existing `POST /tenants` and `GET /tenants` HTTP endpoints
entirely and replaced tenant management with a new CLI script,
`python -m app.manage_tenants` (`create`/`list`/`update`).

**Why remove the HTTP endpoints instead of gating them:** auditing them
while building this found `POST /tenants` and `GET /tenants` had **zero**
auth — `Depends(get_db)` only, no `Depends(get_current_user)` or any
permission check, despite SPEC.md's stale doc calling `GET /tenants`
"admin"-gated. Anyone with network access could create tenant shells or
list every tenant's name. A repo-wide grep confirmed the frontend never
calls either endpoint (only tenant-*scoped* `/tenants/{id}/...` routes
are used, via the JWT-derived `tenant_id`). Given the user explicitly
asked to manage tenants via script for now, gating these endpoints would
have kept an unused, no-longer-needed attack surface around for no
benefit — deleting `app/api/tenants.py`/`app/schemas/tenant.py` was
simpler and safer than adding auth to code nothing calls.

**No platform-superadmin role exists, and this batch doesn't add one:**
`require_admin` gates tenant-*scoped* admin actions (user management
within one's own tenant) — there was and still is no cross-tenant role.
`app/manage_tenants.py` runs with direct DB access (`SessionLocal`, same
pattern as the existing `app/seed.py`), not through the HTTP API, so it
doesn't need one either. `app/seed.py` itself is untouched — it stays a
one-time dev bootstrap (hardcoded `admin@example.com`, no-ops if that
email exists); `manage_tenants.py` is the general-purpose, repeatable
tool for onboarding real clients and updating their subscription state.

**`status` is a manual override, not a computed value:** `active`/
`suspended`/`cancelled`, and it always wins over date math in
`compute_subscription_state` — an operator suspending a tenant for
non-payment shouldn't be silently overridden by a still-future
`expire_date`. There's no separate `trial` status: a trial is just a
tenant with `expire_date` set to the trial's end date, which the
date-driven `warning`/`expired` states already cover without a fourth
manual value.

**`warning_date` and subscription state are computed, not stored:** same
reasoning as every other derived value in this project this week
(destination-to-warehouse distance, route stop distances) — either
`expire_date` or `warning_period_days` can change after the fact, and a
cached value would silently go stale. `app.services.tenant_subscription`
computes both at read time.

**No enforcement yet — deliberately:** an expired or suspended tenant's
users are **not** blocked from logging in or using the API. There's no
billing/payment integration behind these fields yet, and no
dispute/grace-period process — flipping on a hard block now risks
locking out a real client over a date field with nothing to appeal to.
Revisit once real billing exists. Logged as a TODO.

**Ready-to-use fields chosen, and what was deliberately left out:**
included `plan_name` (free-text, no separate plans table — no pricing
model exists yet to normalize against), `billing_email` (a contact
distinct from operational user accounts, for when invoicing/warning
emails eventually get built), and `notes` (free-text, for the operator's
own renewal/exception tracking). Deliberately did **not** add: seat/usage
limits, a real plans/pricing table, payment-provider fields (Stripe
customer id, etc.), or an audit-log/history table for subscription
changes — none of these have a concrete near-term use yet, and adding
them now would be speculative scaffolding with no consumer.

**Future direction, not built now:** the user's stated intent is to
eventually manage the tenant list from Odoo instead of this CLI script
(e.g., Odoo as the system of record for clients/subscriptions, syncing
into or replacing this `tenants` table). Logged as a "Next up" item in
TODO.md — no integration shape decided yet.
