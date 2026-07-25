# odoo-tms — AI Context

Read this file first in every session. Then read [PLAN.md](PLAN.md) (current phase)
and [TODO.md](TODO.md) (active tasks). Treat CLAUDE.md + PLAN.md + TODO.md as
sufficient context to orient — only open source files when a specific task needs
them. Consult [DECISIONS.md](DECISIONS.md) before questioning any architectural
choice already recorded there; ask the user instead of overriding it.

## Project purpose

A multi-tenant Transportation Management System (TMS). It connects to multiple
customers' Odoo instances via XML-RPC to pull open deliveries and produce
optimized vehicle load plans and delivery routes. Each tenant's Odoo connection
(url, db, username, API key) is stored Fernet-encrypted per tenant.

## Stack

- Backend: FastAPI + PostgreSQL + Redis
- Frontend: React
- Reverse proxy: Nginx
- Deployment: single Docker Compose stack on one Hetzner VPS

## Hard constraints — never violate without asking first

1. **Routing is purely location/time-based.** No pre-assigned zones, ever.
2. **FILO sequencing** (last loaded = first delivered) is a hard constraint on
   route sequencing, not an optimization nice-to-have.
3. **Multi-tenant via shared DB + `tenant_id` column** on tenant-scoped tables,
   not separate databases per tenant.
4. **Odoo credentials are always Fernet-encrypted at rest** and never logged in
   plaintext (including in exception messages/stack traces).
5. **Cost-conscious**: single VPS, no paid SaaS dependencies beyond free tiers.

## MVP scope boundary

- Manual "Run Planning" trigger only — no live GPS, no driver mobile app.
- Single depot only.
- No real-time re-optimization once a plan is generated.

See [PLAN.md](PLAN.md) for what's explicitly deferred to Phase 2.

## Working agreement

- After any significant chunk of work: update [TODO.md](TODO.md) (check off
  done items, add newly discovered ones) and append a one-line entry to
  [CHANGELOG.md](CHANGELOG.md) so state is recoverable without re-reading the
  whole codebase.
- Ask before making any architectural choice not already covered in
  [DECISIONS.md](DECISIONS.md).
