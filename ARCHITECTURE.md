# Architecture

Single Docker Compose stack on one Hetzner VPS.

```
                              Internet
                                 |
                                 v
                        +-----------------+
                        |      Nginx      |
                        |  (reverse proxy)|
                        +--------+--------+
                                 |
                +----------------+-----------------+
                |                                   |
                v                                   v
   +-------------------------+          +--------------------------+
   |   Static React build    |          |     FastAPI backend      |
   |   ( / )                 |          |     ( /api/* )           |
   +-------------------------+          +------------+-------------+
                                                      |
                             +------------------------+------------------------+
                             |                         |                       |
                             v                         v                       v
                    +----------------+       +------------------+   +--------------------+
                    |   PostgreSQL   |       |      Redis       |   |  Customer Odoo      |
                    | (tenant / job  |       | (job queue for   |   |  instances          |
                    |  data)         |       |  planning runs)  |   |  (XML-RPC, outbound |
                    +----------------+       +------------------+   |  only)              |
                                                                      +--------------------+
```

## Notes

- Nginx is the only externally exposed service; it serves the React static
  build at `/` and reverse-proxies `/api/*` to FastAPI.
- FastAPI is the only service that talks to Postgres, Redis, and outbound to
  customer Odoo instances. The frontend never calls Odoo or the DB directly.
- Postgres holds tenant records, encrypted Odoo credentials, user accounts,
  and planning run history/results.
- Redis backs the planning-run job queue (`/planning/run` enqueues a job;
  a worker — same FastAPI codebase, run as a separate process/container —
  consumes it and writes the result back to Postgres).
- All Odoo connections are outbound-only XML-RPC calls initiated by the
  backend; no customer Odoo instance ever calls into this system.
