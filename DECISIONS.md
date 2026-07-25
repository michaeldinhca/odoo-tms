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
