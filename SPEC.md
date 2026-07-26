# Data Models &amp; Contracts

Placeholders are marked `# TODO: fill in as we build`. This file is expected to
drift from actual model definitions during early development — treat the
source under `backend/app/models/` and `backend/app/schemas/` as ground truth
once code exists, and update this file to match after significant schema
changes.

## Core tables

### `tenants`

| column       | type        | notes                          |
|--------------|-------------|---------------------------------|
| id           | UUID (PK)   |                                  |
| name         | text        | display name                    |
| created_at   | timestamptz |                                  |

### `tenant_odoo_credentials`

| column         | type        | notes                                          |
|----------------|-------------|--------------------------------------------------|
| id             | UUID (PK)   |                                                    |
| tenant_id      | UUID (FK)   | references `tenants.id`                          |
| url            | text        | Odoo base URL                                     |
| db             | text        | Odoo database name                                |
| username       | text        |                                                    |
| encrypted_key  | text        | Fernet-encrypted Odoo API key — never plaintext   |
| state          | text        | `draft`/`active`/`error` (see DECISIONS.md "Odoo connection state machine"); `error` is reserved, not yet set anywhere |
| activated_at   | timestamptz, nullable | set the first time `state` transitions to `active` |
| last_synced_operation_types_at | timestamptz, nullable | last successful (confirm, not preview) operation-type resync |
| last_synced_warehouses_at | timestamptz, nullable | last successful (confirm, not preview) warehouse resync |
| company_id     | integer, nullable | selected Odoo `res.company` id; NULL = all companies the API user can see, unfiltered (see DECISIONS.md "Multi-company") |
| company_name   | text, nullable | cached display name of `company_id`, for the UI  |
| server_version | text, nullable | raw version string from Odoo's `common.version()`, e.g. `"17.0"` |
| server_version_major | integer, nullable | parsed major version, e.g. `17` — this is what `app.odoo_mappings.resolve_field` keys on |
| server_serie   | text, nullable | e.g. `"17.0"`                                     |
| protocol_version | integer, nullable |                                                 |
| version_checked_at | timestamptz, nullable | last time `common.version()` was called for this connection |
| version_change_detected | boolean | `True` if the most recent check found a different `server_version_major` than what was previously stored (see DECISIONS.md "Odoo version detection") |
| created_at     | timestamptz |                                                    |

One tenant may eventually have more than one Odoo connection (Phase 2,
multi-depot); MVP assumes one active credential row per tenant. Within that
one connection, an Odoo instance may have several companies — `company_id`
picks which one planning runs are scoped to (via Odoo's own
`allowed_company_ids` XML-RPC context key), rather than modeling companies as
separate tenants.

Version fields are populated/re-checked by `POST .../credentials/test`, not
just once at setup — see DECISIONS.md "Odoo version detection". Confirmed
live against the real Odoo instance (`edu-accounting-learning.odoo.com`):
`common.version()` reports `server_version="19.0+e"` (Enterprise),
`server_version_major=19`, `server_serie="19.0"` — matches the "Odoo 19"
this whole project has been built and tested against so far. Also confirmed
`version_change_detected` correctly flips `True` when the stored major
version differs from a fresh check (simulated by directly setting a
different stored value, then re-testing) and settles back to `False` on the
next unchanged check.

### `users` (dispatcher/operator accounts)

| column        | type        | notes                             |
|---------------|-------------|-------------------------------------|
| id            | UUID (PK)   |                                      |
| tenant_id     | UUID (FK)   | references `tenants.id`             |
| email         | text        | unique                              |
| password_hash | text        |                                      |
| role          | text        | `admin`/`user`, default `user` — gates *only* the Users page itself (see DECISIONS.md "Role vs. boolean permissions"); not a bypass for the columns below |
| can_manage_connection | boolean | default `false` |
| can_manage_warehouses | boolean | default `false` |
| can_manage_operation_types | boolean | default `false` |
| can_manage_fleet | boolean | default `false` — vehicles + drivers together |
| can_run_planning | boolean | default `true` |
| can_use_load_planning | boolean | default `true` |
| created_at    | timestamptz |                                      |

Every feature area other than user management is gated by its own
boolean, for every user regardless of `role` — an admin with
`can_manage_warehouses=false` is blocked from the Warehouses page exactly
like a `user`-role account would be. `role="admin"` is only checked by
the user-management endpoints (`/tenants/{id}/users/*`), and a tenant can
never end up with zero admins: demoting or deleting the last `role="admin"`
row is rejected (400).

### `planning_runs`

| column        | type        | notes                                       |
|---------------|-------------|-----------------------------------------------|
| id            | UUID (PK)   |                                                 |
| tenant_id     | UUID (FK)   |                                                 |
| status        | text        | `pending` / `running` / `done` / `failed`      |
| result_json   | jsonb       | see "Planning result shape" below              |
| created_at    | timestamptz |                                                 |
| completed_at  | timestamptz | nullable                                       |

### `synced_operation_types`

Mirrors a tenant's Odoo `stock.picking.type` records (Receipts, Delivery
Orders, Manufacturing, PoS Orders, Resupply Subcontractor, Repairs, ...).
Populated by `POST /tenants/{id}/operation-types/refresh`; only rows with
`is_synced=true` are pulled by the stock.picking sync (see "Operation
type / warehouse sync gating" in DECISIONS.md).

| column                  | type              | notes                                        |
|--------------------------|-------------------|-------------------------------------------------|
| id                       | UUID (PK)         |                                                   |
| tenant_id                | UUID (FK)         | references `tenants.id`                          |
| odoo_operation_type_id   | integer           | Odoo's `stock.picking.type.id`                   |
| name                     | text              |                                                   |
| code                     | text              | `incoming` / `outgoing` / `internal` / `mrp_operation` / ... |
| warehouse_id             | integer, nullable | Odoo warehouse id this operation type belongs to |
| is_synced                | boolean           | default `false`; refresh never resets this on existing rows |
| active                   | boolean           | default `true`; archive flag, separate from `is_synced` — refresh never resets this either (see DECISIONS.md "Archive instead of hard delete") |
| last_seen_at             | timestamptz, nullable |                                               |
| created_at               | timestamptz       |                                                   |
| updated_at                | timestamptz       |                                                   |

Unique on `(tenant_id, odoo_operation_type_id)`.

### `synced_warehouses`

Mirrors a tenant's Odoo `stock.warehouse` records, address split the same
way as everywhere else in this system (see "Address" shape below — not a
second, inconsistent structure). Populated by `POST
/tenants/{id}/warehouses/refresh`.

| column         | type              | notes                                    |
|-----------------|-------------------|---------------------------------------------|
| id              | UUID (PK)         |                                               |
| tenant_id       | UUID (FK)         | references `tenants.id`                      |
| odoo_warehouse_id | integer         | Odoo's `stock.warehouse.id`                  |
| name            | text              |                                               |
| code            | text              | Odoo's warehouse short code                  |
| street          | text              | from the warehouse's `partner_id`            |
| street2         | text              |                                               |
| city            | text              |                                               |
| state_id        | integer, nullable |                                               |
| state_name      | text              | cached display name (see DECISIONS.md)       |
| country_id      | integer, nullable |                                               |
| country_name    | text              | cached display name (see DECISIONS.md)       |
| zip             | text              |                                               |
| is_synced       | boolean           | default `false`; refresh never resets this on existing rows |
| active          | boolean           | default `true`; archive flag — see `synced_operation_types` above |
| last_seen_at    | timestamptz, nullable |                                           |
| created_at      | timestamptz       |                                               |
| updated_at      | timestamptz       |                                               |

Unique on `(tenant_id, odoo_warehouse_id)`.

### `synced_pickings`

Local mirror of a tenant's synced `stock.picking` records — only ones whose
operation type is marked `is_synced` get pulled/stored. Upserted as a side
effect of `/planning/run` (see DECISIONS.md "`synced_pickings` populated as
a side effect of `/planning/run`") — every fetched picking is stored here
regardless of whether FFD assigned it to a vehicle.

| column           | type              | notes                                       |
|-------------------|-------------------|--------------------------------------------|
| id                | UUID (PK)         |                                              |
| tenant_id         | UUID (FK)         | references `tenants.id`                     |
| odoo_picking_id   | integer           | Odoo's `stock.picking.id`                   |
| state             | text              | Odoo's native state: draft/waiting/confirmed/assigned/done/cancel |
| customer_name     | text              |                                              |
| items_summary     | text              |                                              |
| street / street2 / city / state_id / state_name / country_id / country_name / zip | — | same split-address shape as `synced_warehouses` |
| scheduled_date    | timestamptz, nullable |                                          |
| picking_type_id   | integer, nullable | Odoo's `stock.picking.picking_type_id`      |
| warehouse_id      | integer, nullable | resolved via `synced_operation_types.warehouse_id` |
| warehouse_name    | text              | resolved via `synced_warehouses`            |
| origin            | text              | Odoo's `origin` (Source Document, usually the Sales Order ref) |
| weight            | float, nullable   | Odoo's native `weight` field                |
| shipping_weight   | float, nullable   | Odoo's `shipping_weight` — only exists when the `delivery` module is installed; `null` otherwise, never errors |
| note              | text              |                                              |
| last_seen_at      | timestamptz, nullable |                                          |
| created_at        | timestamptz       |                                              |
| updated_at        | timestamptz       |                                              |

Unique on `(tenant_id, odoo_picking_id)`.

### `vehicles`

Locally-owned, system-of-record table — a vehicle can exist here with no
Odoo link at all (see DECISIONS.md "Vehicles and drivers are locally-owned").

| column                       | type              | notes                                    |
|--------------------------------|-------------------|---------------------------------------------|
| id                            | UUID (PK)         |                                               |
| tenant_id                     | UUID (FK)         | references `tenants.id`                      |
| name                          | text              | required                                     |
| license_plate                 | text, nullable    |                                               |
| vehicle_type                  | text              | `van`/`truck`/`motorbike`/`three_wheeler`/`other`, default `van` |
| payload_capacity_kg           | float, nullable   |                                               |
| volume_capacity_m3            | float, nullable   |                                               |
| fuel_consumption_per_100km    | float, nullable   |                                               |
| home_warehouse_id             | UUID (FK), nullable | references `synced_warehouses.id`          |
| status                        | text              | `active`/`inactive`/`maintenance`, default `active` |
| odoo_fleet_vehicle_id         | integer, nullable | optional cross-reference to Odoo `fleet.vehicle.id` — reference only, never a data source |
| odoo_link_status              | text              | `unlinked`/`linked`/`stale`, default `unlinked` (see DECISIONS.md "Stale Odoo links") |
| active                        | boolean           | default `true`; archive flag, orthogonal to `status` |
| created_at                    | timestamptz       |                                               |
| updated_at                    | timestamptz       |                                               |

Delete is blocked if any `driver.assigned_vehicle_id` references the vehicle
(archive instead — see DECISIONS.md "Archive instead of hard delete").

### `drivers`

Same locally-owned pattern as `vehicles`.

| column                | type              | notes                                        |
|-------------------------|-------------------|-------------------------------------------------|
| id                     | UUID (PK)         |                                                   |
| tenant_id              | UUID (FK)         | references `tenants.id`                          |
| name                   | text              | required                                         |
| phone                  | text, nullable    |                                                   |
| email                  | text, nullable    |                                                   |
| license_number         | text, nullable    |                                                   |
| id_passport_number     | text, nullable    |                                                   |
| status                 | text              | `active`/`locked`/`inactive`, default `active`   |
| locked_until           | timestamptz, nullable | used when `status="locked"` for temp-lock windows |
| assigned_vehicle_id    | UUID (FK), nullable | references `vehicles.id` — a driver's current/default vehicle, separate from any future per-trip assignment |
| odoo_employee_id       | integer, nullable | optional cross-reference to Odoo `hr.employee.id` — reference only, never a data source |
| odoo_link_status       | text              | `unlinked`/`linked`/`stale`, default `unlinked`  |
| active                 | boolean           | default `true`; archive flag, orthogonal to `status` |
| created_at             | timestamptz       |                                                   |
| updated_at             | timestamptz       |                                                   |

Delete is blocked while `status="active"` (see DECISIONS.md — a stand-in for
"has current assignments" until real assignment tracking exists); archive
instead is always available regardless of status.

## Core planning flow — data shapes

### Address (shared shape)

Used for both a picking's delivery address and a warehouse's address — one
consistent structure, not two (see DECISIONS.md). Always split, never a
concatenated string; display code composes a display string at render time.

```jsonc
{
  "street": "",
  "street2": "",
  "city": "",
  "state_id": null,       // Odoo res.country.state id, or null
  "state_name": "",       // cached display name, resolved at sync time
  "country_id": null,     // Odoo res.country id, or null
  "country_name": "",     // cached display name, resolved at sync time
  "zip": ""
}
```

### Input: order / `stock.picking` (pulled from tenant's Odoo)

This is `app.services.planning.ffd.Order` — implemented, not just planned.
Customer name, items summary, address, state, scheduled date, operation
type/warehouse, origin, weight, and note are all populated from real Odoo
queries (`res.partner`, `stock.move`, `stock.picking` itself); volume/lat/lon
are still placeholder zeros pending field confirmation (see "Odoo field
mappings"). Only pickings whose operation type is marked synced are fetched
at all — see "Operation type / warehouse sync gating" in DECISIONS.md.

```jsonc
{
  "picking_id": 0,            // stock.picking.id
  "customer_name": "",        // stock.picking.partner_id's display name
  "items_summary": "",        // joined "<product> x<qty>" from stock.move, e.g. "Widget x2; Gadget x1"
  "address": { /* see Address shape above, from res.partner via partner_id */ },
  "state": "",                 // stock.picking.state (native: draft/waiting/confirmed/assigned/done/cancel)
  "scheduled_date": null,      // stock.picking.scheduled_date
  "picking_type_id": null,     // stock.picking.picking_type_id
  "warehouse_id": null,        // resolved via synced_operation_types -> synced_warehouses
  "warehouse_name": "",
  "origin": "",                 // stock.picking.origin (Source Document)
  "weight_kg": 0.0,            // stock.picking.weight
  "volume_m3": 0.0,            // TODO: placeholder, may not exist on stock.picking directly
  "lat": 0.0,                  // TODO: source field — partner geo or custom field
  "lon": 0.0,
  "shipping_weight": null,      // stock.picking.shipping_weight — null if the `delivery` module isn't installed
  "note": ""                    // stock.picking.note
}
```

### Intermediate: FFD assignment output

```jsonc
{
  "vehicle_id": 0,             // TODO: fleet.vehicle.id
  "assigned_pickings": [0, 0], // picking_ids assigned to this vehicle
  "total_weight_kg": 0.0,
  "total_volume_m3": 0.0,
  "capacity_weight_kg": 0.0,   // TODO: fleet.vehicle capacity field
  "capacity_volume_m3": 0.0
}
```

### Output: FILO-sequenced route

`app.schemas.planning.RouteStop` — each stop carries the full customer/items/
address context needed to actually dispatch it, not just the picking ID.

```jsonc
{
  "vehicle_id": 0,
  "sequence": [
    {
      "stop_order": 1,
      "picking_id": 0,
      "customer_name": "",
      "items_summary": "",
      "address": { /* see Address shape above */ },
      "state": "",
      "scheduled_date": null,
      "origin": "",
      "warehouse_name": "",
      "eta": null            // not computed yet — TODO, needs a depot start time + per-stop service time
    }
    // last-loaded picking appears first in sequence (FILO)
  ],
  "estimated_distance_km": 0.0,
  "estimated_duration_min": 0.0
}
```

## API endpoints

| method | path                                 | purpose                                          | status |
|--------|--------------------------------------|---------------------------------------------------|--------|
| POST   | `/auth/login`                        | JWT login                                          | implemented |
| GET    | `/auth/me`                           | current user's own role/permissions (any authenticated user, not admin-gated) | implemented |
| PUT    | `/auth/password`                     | self-service password change (requires current password) | implemented |
| GET    | `/tenants`                           | list tenants (admin)                               | implemented |
| POST   | `/tenants`                           | create tenant                                      | implemented |
| GET    | `/tenants/{id}/users`                | list users (requires `role=="admin"`)              | implemented |
| POST   | `/tenants/{id}/users`                | create a user + set initial password (no invite-email flow — see TODO.md); requires `role=="admin"` | implemented |
| PUT    | `/tenants/{id}/users/{user_id}`      | update email/role/permissions (partial); blocks demoting the last admin; requires `role=="admin"` | implemented |
| DELETE | `/tenants/{id}/users/{user_id}`      | delete; blocks deleting the last admin; requires `role=="admin"` | implemented |
| PUT    | `/tenants/{id}/users/{user_id}/password` | admin resets another user's password (no current-password check); requires `role=="admin"` | implemented |
| GET    | `/tenants/{id}/credentials`          | get Odoo connection status (never returns key)     | implemented |
| PUT    | `/tenants/{id}/credentials`          | initial setup: set/update Odoo connection (Fernet-encrypts key); creates a `draft` row, never touches `state` on an existing one | implemented |
| POST   | `/tenants/{id}/credentials/reauthenticate` | same field update as the PUT above, but only when `state=="active"` (409 otherwise) — see DECISIONS.md "Odoo connection state machine" | implemented |
| POST   | `/tenants/{id}/credentials/test`     | test XML-RPC connection; also (re-)detects and persists Odoo server version | implemented |
| GET    | `/tenants/{id}/credentials/companies`| live-list the Odoo instance's `res.company` records | implemented |
| PUT    | `/tenants/{id}/credentials/company`  | select (or clear) the company planning is scoped to; transitions `state` `draft`→`active` | implemented |
| GET    | `/tenants/{id}/operation-types`      | list synced operation types (local); `?include_archived=true` to include archived rows | implemented |
| POST   | `/tenants/{id}/operation-types/refresh/preview` | dry-run diff against Odoo — `{new, removed, unchanged_count}`, writes nothing; requires `state=="active"` | implemented |
| POST   | `/tenants/{id}/operation-types/refresh` | pull `stock.picking.type` from Odoo, upsert (preserves existing `is_synced`/`active`); requires `state=="active"` | implemented |
| PUT    | `/tenants/{id}/operation-types/{row_id}/sync` | toggle `is_synced` for one operation type    | implemented |
| PUT    | `/tenants/{id}/operation-types/{row_id}/archive` | toggle `active` (archive/unarchive)         | implemented |
| DELETE | `/tenants/{id}/operation-types/{row_id}` | delete; blocked (400) if referenced by a `synced_pickings` row — archive instead | implemented |
| GET    | `/tenants/{id}/warehouses`           | list synced warehouses (local); `?include_archived=true` to include archived rows | implemented |
| POST   | `/tenants/{id}/warehouses/refresh/preview` | dry-run diff against Odoo, writes nothing; requires `state=="active"` | implemented |
| POST   | `/tenants/{id}/warehouses/refresh`   | pull `stock.warehouse` from Odoo, upsert (preserves existing `is_synced`/`active`); requires `state=="active"` | implemented |
| PUT    | `/tenants/{id}/warehouses/{row_id}/sync` | toggle `is_synced` for one warehouse            | implemented |
| PUT    | `/tenants/{id}/warehouses/{row_id}/archive` | toggle `active` (archive/unarchive)          | implemented |
| DELETE | `/tenants/{id}/warehouses/{row_id}`  | delete; blocked (400) if a vehicle's `home_warehouse_id` or a `synced_pickings` row references it — archive instead | implemented |
| GET    | `/tenants/{id}/vehicles`             | list vehicles (filter by `status_filter`, `home_warehouse_id`, `?include_archived=true`) | implemented |
| POST   | `/tenants/{id}/vehicles`             | create a vehicle                                   | implemented |
| GET    | `/tenants/{id}/vehicles/odoo-fleet-vehicles` | browse Odoo `fleet.vehicle` records (never auto-creates locally); also refreshes stale-link flags; requires `state=="active"` | implemented |
| GET    | `/tenants/{id}/vehicles/{vehicle_id}` | get one vehicle                                   | implemented |
| PUT    | `/tenants/{id}/vehicles/{vehicle_id}` | partial update (only provided fields applied, includes `active` for archiving) | implemented |
| DELETE | `/tenants/{id}/vehicles/{vehicle_id}` | delete; blocked if a driver's `assigned_vehicle_id` references it — archive instead; no Odoo connection required | implemented |
| PUT    | `/tenants/{id}/vehicles/{vehicle_id}/odoo-link` | link to an Odoo fleet.vehicle id (reference only); requires `state=="active"` | implemented |
| DELETE | `/tenants/{id}/vehicles/{vehicle_id}/odoo-link` | unlink; no active-connection requirement — pure local-state removal | implemented |
| GET    | `/tenants/{id}/drivers`              | list drivers (filter by `status_filter`, `?include_archived=true`) | implemented |
| POST   | `/tenants/{id}/drivers`              | create a driver                                    | implemented |
| GET    | `/tenants/{id}/drivers/odoo-employees` | browse Odoo `hr.employee` records (never auto-creates locally); also refreshes stale-link flags; requires `state=="active"` | implemented |
| GET    | `/tenants/{id}/drivers/{driver_id}`  | get one driver                                     | implemented |
| PUT    | `/tenants/{id}/drivers/{driver_id}`  | partial update (only provided fields applied, includes `active` for archiving) | implemented |
| DELETE | `/tenants/{id}/drivers/{driver_id}`  | delete; blocked while `status="active"` — archive instead; no Odoo connection required | implemented |
| PUT    | `/tenants/{id}/drivers/{driver_id}/odoo-link` | link to an Odoo hr.employee id (reference only); requires `state=="active"` | implemented |
| DELETE | `/tenants/{id}/drivers/{driver_id}/odoo-link` | unlink; no active-connection requirement — pure local-state removal | implemented |
| POST   | `/planning/run`                      | trigger a planning run for a tenant                | implemented |
| GET    | `/planning/results/{id}`             | fetch a planning run's result                      | implemented |

No user self-registration/invite endpoint exists — see TODO.md.

Every endpoint under `/tenants/{id}/credentials`, `/operation-types`,
`/warehouses`, `/vehicles`, and `/drivers` requires the corresponding
`can_manage_*` permission; every endpoint under `/planning` requires
`can_run_planning`. The Load Planning board has no backend endpoints of
its own yet (still fixture data — see `design.md`), so `can_use_load_planning`
is currently enforced only on the frontend route. See DECISIONS.md "Role
vs. boolean permissions" for why `role` doesn't bypass these.

## Version-aware field mapping registry

Tenants connect to Odoo instances that may run different major versions
(13, 15, 16, 17, 18, 19, ...). `backend/app/odoo_mappings/` is a config-only
package (no XML-RPC, no Odoo client) — one file per integrated model:
`stock_picking.py`, `stock_warehouse.py`, `stock_picking_type.py`,
`fleet_vehicle.py`, `hr_employee.py`, `res_partner.py`. Each defines:

```python
FIELD_MAP = {
    "default": {
        "logical_field_name": "odoo_field_name",
        # ...
    },
    # a version block is added ONLY once a real difference is confirmed —
    # never speculatively (see DECISIONS.md)
    17: {
        "logical_field_name": "different_odoo_field_name_on_v17",
    },
}
```

`resolve_field(model, logical_name, version_major)` (in
`app/odoo_mappings/__init__.py`) checks the version-specific block first,
falls back to `"default"` when the logical name isn't overridden there, and
falls back to `"default"` entirely for any `version_major` with no block at
all — including versions newer than any seen yet. As of this batch every
version block across all six files is empty; every logical name currently
resolves to the Odoo field name it always hardcoded to (see the confirmed
mappings below) — this is a scaffold for future version-specific
differences, not evidence any exist yet.

For fields that may not exist at all on a given tenant's instance (e.g.
`shipping_weight` without the `delivery` module), see
`app.services.odoo_field_resolution.resolve_optional_field(client, model,
logical_name, version_major)` — layers a live `fields_get()` existence
check on top of `resolve_field`, returning `None` instead of a field name
when absent. `resolve_required_field` is the plain-lookup counterpart for
fields assumed always present.

"Logical field name" here is *not* the same thing as this system's own
local schema column names (e.g. `SyncedPicking.weight`) — it's an
intermediate key used only for Odoo-side field resolution. The local schema
(see the table definitions above) doesn't change based on Odoo version;
only which Odoo field a given sync function reads from does.

**Not yet wired to this registry** (see DECISIONS.md "Version-keyed field
mapping..." scope note): `stock.move` (used for `items_summary`) and
`res.company` (used for company selection) — both still use hardcoded field
names directly.

## Odoo field mappings

Placeholders — confirm against a real Odoo 19 instance as we build. Verified
against a real Odoo 19 instance the user provided
(`edu-accounting-learning.odoo.com`, a multi-company instance): `stock.picking`
(state="assigned" domain works, `partner_id` resolves), `res.partner`
(street/street2/city/zip/country_id all populated — though many test pickings
had no address on their partner, which the code handles as empty strings,
not an error), `res.company` (multi-company listing + `allowed_company_ids`
scoping both confirmed — company-scoped run returned 29 pickings vs. 37
unscoped), and `stock.move` (item summaries like `"[FURN_8888] Office Lamp
x5"` came through correctly, including multi-line pickings).

Re-verified against the same instance for this batch's additions:
`stock.picking.type` (86 operation types across 9 warehouses, real `code`
values including one not originally anticipated — `repair_operation`),
`stock.warehouse` + its address, operation-type-gated picking sync (toggling
one operation type + warehouse on and running planning correctly narrowed
results to just that operation type's pickings), warehouse resolution via
the operation-type join, and `stock.picking`'s `state`/`scheduled_date`/
`origin`/`weight`/`shipping_weight`/`note` — including confirming this
instance has the `delivery` module installed (`shipping_weight` present and
populated; the absent-field fallback path is unit-tested only, since this is
the one real instance available and it has the module).

### `stock.picking`

| our field          | odoo field                                              | status                        |
|--------------------|-----------------------------------------------------------|--------------------------------|
| customer_name       | `partner_id` (display name half of the m2o tuple)         | confirmed against real instance |
| delivery_address    | via `res.partner` lookup on `partner_id` (see below)       | confirmed against real instance |
| items_summary        | via `stock.move` lookup on `picking_id`, joining `product_id` + `product_uom_qty` | confirmed against real instance |
| state                | `state`                                                    | confirmed against real instance |
| scheduled_date       | `scheduled_date`                                           | confirmed against real instance |
| picking_type_id      | `picking_type_id`                                          | confirmed against real instance |
| origin                | `origin`                                                   | confirmed against real instance (also confirmed empty-string when unset, not an error) |
| weight_kg            | `weight`                                                    | confirmed against real instance — real nonzero values (e.g. 59.4, 16.5) |
| shipping_weight       | `shipping_weight` — only present when the `delivery` module is installed; code checks via `fields_get` and stores `null` when absent, never errors | confirmed against real instance — this instance has the `delivery` module installed, field present and populated; the absent-field path is covered by a unit test (no real instance without `delivery` available to verify against) |
| note                  | `note`                                                     | confirmed field exists and is queried correctly; empty on every picking in the test dataset, so real note content unverified |
| volume_m3           | ?                                                          | TODO: confirm                 |
| lat / lon           | `partner_id`'s geo fields or a custom field                | TODO: confirm                 |

### `res.partner` (for `address` — shared shape, see "Address" above)

| our field    | odoo field    | status                          |
|--------------|---------------|-----------------------------------|
| street       | `street`      | confirmed against real instance (was named `street1` before this batch) |
| street2      | `street2`     | confirmed against real instance   |
| city         | `city`        | confirmed against real instance   |
| state_id/state_name | `state_id` (id + display name half of the m2o tuple) | confirmed against real instance (e.g. id 541 "Ontario (CA)") |
| country_id/country_name | `country_id` (id + display name half of the m2o tuple) | confirmed against real instance (id capture is new this batch) |
| zip          | `zip`         | confirmed against real instance   |

### `stock.move` (for `items_summary`)

| our field       | odoo field         | status       |
|-----------------|---------------------|---------------|
| product name     | `product_id` (display name half of the m2o tuple) | confirmed against real instance |
| quantity         | `product_uom_qty`  | confirmed against real instance |

### `stock.picking.type` (for operation type sync config)

| our field                | odoo field    | status       |
|---------------------------|---------------|---------------|
| name                      | `name`        | confirmed against real instance |
| code                      | `code`        | confirmed against real instance — observed values `incoming`/`outgoing`/`internal`/`mrp_operation`/`repair_operation` (Repairs) |
| warehouse_id              | `warehouse_id` (id half of the m2o tuple) | confirmed against real instance |

### `stock.warehouse` (for warehouse sync config)

| our field    | odoo field                              | status       |
|--------------|-------------------------------------------|---------------|
| name         | `name`                                    | confirmed against real instance |
| code         | `code`                                    | confirmed against real instance (e.g. "WH") |
| address      | via `res.partner` lookup on `partner_id`, same as picking delivery address | confirmed against real instance |

### `fleet.vehicle`

| our field           | odoo field | status       |
|---------------------|------------|---------------|
| capacity_weight_kg  | ?          | TODO: confirm |
| capacity_volume_m3  | ?          | TODO: confirm |

### `res.company` (for multi-company selection)

| our field   | odoo field | status                        |
|-------------|------------|---------------------------------|
| id          | `id`       | confirmed against real instance |
| name        | `name`     | confirmed against real instance |

### `fleet.vehicle` (for vehicle-to-Odoo linking — distinct from the planning-side capacity fields above, which are still unconfirmed)

| our field       | odoo field       | status       |
|-----------------|--------------------|---------------|
| name            | `name`             | confirmed against real instance (e.g. "Ford/F150/DYLC051") |
| license_plate   | `license_plate`    | confirmed against real instance |

Deliberately minimal — the task calling for this batch warned not to assume
fields that require the Fleet module's optional add-ons; `name` and
`license_plate` are core `fleet.vehicle` fields present regardless of which
add-ons are installed. Whether the model exists at all is checked via
`OdooClient.model_exists("fleet.vehicle")` (uses `fields_get`) before ever
calling `search_read` — if the Fleet module isn't installed, this returns
`available: false` instead of erroring.

### `hr.employee` (for driver-to-Odoo linking)

| our field       | odoo field       | status       |
|-----------------|--------------------|---------------|
| name            | `name`             | confirmed against real instance |
| work_phone      | `work_phone`       | confirmed against real instance |
| mobile_phone    | `mobile_phone`     | confirmed against real instance (e.g. "0357543504" on one test employee) |

Same `model_exists("hr.employee")` gate as `fleet.vehicle` above.
