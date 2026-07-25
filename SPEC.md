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
| created_at     | timestamptz |                                                    |

One tenant may eventually have more than one Odoo connection (Phase 2,
multi-depot); MVP assumes one active credential row per tenant.

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

```jsonc
{
  "picking_id": 0,            // TODO: confirm Odoo field (stock.picking.id)
  "partner_id": 0,            // TODO: stock.picking.partner_id
  "delivery_address": {
    "lat": 0.0,                // TODO: source field — partner geo or custom field
    "lon": 0.0
  },
  "weight_kg": 0.0,            // TODO: stock.picking / move line weight field
  "volume_m3": 0.0,            // TODO: placeholder, may not exist on stock.picking directly
  "time_window": {             // TODO: confirm source (scheduled_date +/- window?)
    "start": "2026-07-24T08:00:00Z",
    "end": "2026-07-24T17:00:00Z"
  }
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

```jsonc
{
  "vehicle_id": 0,
  "sequence": [
    { "stop_order": 1, "picking_id": 0, "eta": "2026-07-24T09:00:00Z" }
    // last-loaded picking appears first in sequence (FILO)
  ],
  "estimated_distance_km": 0.0,
  "estimated_duration_min": 0.0
}
```

## API endpoints (stubbed for MVP, filled in as built)

| method | path                          | purpose                                          |
|--------|-------------------------------|---------------------------------------------------|
| POST   | `/auth/login`                 | JWT login                                          |
| GET    | `/tenants`                    | list tenants (admin)                               |
| POST   | `/tenants`                    | create tenant                                      |
| GET    | `/tenants/{id}/credentials`   | get Odoo connection status (never returns key)     |
| PUT    | `/tenants/{id}/credentials`   | set/update Odoo connection (Fernet-encrypts key)   |
| POST   | `/tenants/{id}/credentials/test` | test XML-RPC connection                         |
| POST   | `/planning/run`               | trigger a planning run for a tenant                |
| GET    | `/planning/results/{id}`      | fetch a planning run's result                      |

## Odoo field mappings

Placeholders — confirm against a real Odoo 19 instance as we build.

### `stock.picking`

| our field          | odoo field                     | status                        |
|--------------------|----------------------------------|--------------------------------|
| delivery_address   | `partner_id.partner_shareable_lat/lon` or custom field | TODO: confirm  |
| weight_kg          | ?                                 | TODO: confirm (move lines?)   |
| time_window         | `scheduled_date` +/- ?           | TODO: confirm                 |

### `fleet.vehicle`

| our field           | odoo field | status       |
|---------------------|------------|---------------|
| capacity_weight_kg  | ?          | TODO: confirm |
| capacity_volume_m3  | ?          | TODO: confirm |
