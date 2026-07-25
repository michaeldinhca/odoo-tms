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
| company_id     | integer, nullable | selected Odoo `res.company` id; NULL = all companies the API user can see, unfiltered (see DECISIONS.md "Multi-company") |
| company_name   | text, nullable | cached display name of `company_id`, for the UI  |
| created_at     | timestamptz |                                                    |

One tenant may eventually have more than one Odoo connection (Phase 2,
multi-depot); MVP assumes one active credential row per tenant. Within that
one connection, an Odoo instance may have several companies — `company_id`
picks which one planning runs are scoped to (via Odoo's own
`allowed_company_ids` XML-RPC context key), rather than modeling companies as
separate tenants.

### `users` (dispatcher/operator accounts)

| column        | type        | notes                             |
|---------------|-------------|-------------------------------------|
| id            | UUID (PK)   |                                      |
| tenant_id     | UUID (FK)   | references `tenants.id`             |
| email         | text        | unique                              |
| password_hash | text        |                                      |
| created_at    | timestamptz |                                      |

### `planning_runs`

| column        | type        | notes                                       |
|---------------|-------------|-----------------------------------------------|
| id            | UUID (PK)   |                                                 |
| tenant_id     | UUID (FK)   |                                                 |
| status        | text        | `pending` / `running` / `done` / `failed`      |
| result_json   | jsonb       | see "Planning result shape" below              |
| created_at    | timestamptz |                                                 |
| completed_at  | timestamptz | nullable                                       |

## Core planning flow — data shapes

### Input: order / `stock.picking` (pulled from tenant's Odoo)

This is `app.services.planning.ffd.Order` — implemented, not just planned.
Customer name, items summary, and address are populated from real Odoo
queries (`res.partner`, `stock.move`); weight/volume/lat/lon are still
placeholder zeros pending field confirmation (see "Odoo field mappings").

```jsonc
{
  "picking_id": 0,            // stock.picking.id
  "customer_name": "",        // stock.picking.partner_id's display name
  "items_summary": "",        // joined "<product> x<qty>" from stock.move, e.g. "Widget x2; Gadget x1"
  "address": {                // from res.partner, looked up via stock.picking.partner_id
    "street1": "",
    "street2": "",
    "city": "",
    "country": "",
    "zip": ""
  },
  "weight_kg": 0.0,            // TODO: stock.picking / move line weight field — still a placeholder
  "volume_m3": 0.0,            // TODO: placeholder, may not exist on stock.picking directly
  "lat": 0.0,                  // TODO: source field — partner geo or custom field
  "lon": 0.0
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
      "address": { "street1": "", "street2": "", "city": "", "country": "", "zip": "" },
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
| GET    | `/tenants`                           | list tenants (admin)                               | implemented |
| POST   | `/tenants`                           | create tenant                                      | implemented |
| GET    | `/tenants/{id}/credentials`          | get Odoo connection status (never returns key)     | implemented |
| PUT    | `/tenants/{id}/credentials`          | set/update Odoo connection (Fernet-encrypts key)   | implemented |
| POST   | `/tenants/{id}/credentials/test`     | test XML-RPC connection                            | implemented |
| GET    | `/tenants/{id}/credentials/companies`| live-list the Odoo instance's `res.company` records | implemented |
| PUT    | `/tenants/{id}/credentials/company`  | select (or clear) the company planning is scoped to | implemented |
| POST   | `/planning/run`                      | trigger a planning run for a tenant                | implemented |
| GET    | `/planning/results/{id}`             | fetch a planning run's result                      | implemented |

No user self-registration/invite endpoint exists — see TODO.md.

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

### `stock.picking`

| our field          | odoo field                                              | status                        |
|--------------------|-----------------------------------------------------------|--------------------------------|
| customer_name       | `partner_id` (display name half of the m2o tuple)         | confirmed against real instance |
| delivery_address    | via `res.partner` lookup on `partner_id` (see below)       | confirmed against real instance |
| items_summary        | via `stock.move` lookup on `picking_id`, joining `product_id` + `product_uom_qty` | confirmed against real instance |
| weight_kg           | ?                                                          | TODO: confirm (move lines?)   |
| volume_m3           | ?                                                          | TODO: confirm                 |
| lat / lon           | `partner_id`'s geo fields or a custom field                | TODO: confirm                 |
| time_window          | `scheduled_date` +/- ?                                     | TODO: confirm — not modeled yet |

### `res.partner` (for `address`)

| our field   | odoo field    | status                          |
|-------------|---------------|-----------------------------------|
| street1     | `street`      | confirmed against real instance   |
| street2     | `street2`     | confirmed against real instance   |
| city        | `city`        | confirmed against real instance   |
| zip         | `zip`         | confirmed against real instance   |
| country     | `country_id` (display name half of the m2o tuple) | confirmed against real instance |

### `stock.move` (for `items_summary`)

| our field       | odoo field         | status       |
|-----------------|---------------------|---------------|
| product name     | `product_id` (display name half of the m2o tuple) | confirmed against real instance |
| quantity         | `product_uom_qty`  | confirmed against real instance |

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
