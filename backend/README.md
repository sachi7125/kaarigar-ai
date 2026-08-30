# backend

FastAPI, stateless. Serves the mobile JSON API **and** renders the public storefront and
listing pages. AI runs in `app/workers/` behind a job queue (never inline in a request).
PostgreSQL is the single system of record.

- `app/api/`      — onboarding, listings, offers, storefront
- `app/services/` — pricing_rules, offer_validation, stock (locked decrement)
- `app/workers/`  — image / voice / pricing job consumers
- `app/web/`      — server-rendered public pages (permanent URLs)

Run (once implemented): `uvicorn app.main:app --reload` from `backend/`.
