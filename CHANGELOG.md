# Changelog

One line per significant chunk of work, newest first.

- 2026-07-24: Initial MVP scaffold — repo, context docs (CLAUDE/PLAN/SPEC/ARCHITECTURE/DECISIONS/TODO), FastAPI backend (auth, tenant CRUD, Fernet-encrypted Odoo credentials, XML-RPC client, FFD + Haversine + FILO planning pipeline, Alembic), React dispatcher UI (login, connection, planning), Docker Compose + CI. Verified end-to-end locally via `docker compose up` (migration, login, credential storage, planning-run error handling all confirmed working); fixed a passlib/bcrypt incompatibility and a missing error handler for Odoo connection failures found during that verification.
