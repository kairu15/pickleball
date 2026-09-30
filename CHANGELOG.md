# Changelog

All notable changes to PickleSphere are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — production readiness (Steps 1–5)

**Audit**
- `AUDIT.md`: ranked security/reliability findings (critical C1–C5, high
  H1–H10, medium/low), data-model ERD, and a PostgreSQL migration
  recommendation.

**Reliability & security**
- Atomic booking: court row lock + availability re-check under lock
  (`reservations/services.py`); every checkout path uses it.
- Removed the card-payment bypass that let users confirm bookings without
  paying; cards now go through Stripe Checkout.
- Equipment rental uses `select_for_update` + atomic stock decrements with
  per-reservation line deduplication.
- Stripe webhook idempotency (`StripeWebhookEvent` dedupe), `charge.refunded`
  mirroring into `Refund`, currency/amount verification, expired-checkout
  cleanup.
- Match-level access control in scoring (owner/players/staff) and a
  `ScoreAuditLog` for every score change (view + websocket).
- `DEBUG`-scoped `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`; upload validators
  (extension allow-list + 5 MB cap) on profile, QR-code, and payment-proof
  images.
- Unpaid booking holds auto-expire after 30 minutes (equipment returned,
  payment failed, slot released to the waitlist).

**Features**
- Waitlist: join/leave per slot, automatic notification when a slot frees up,
  claim tracking (`/user/waitlist/`).
- Court maintenance blocks & closures: staff UI at
  `/admin/maintenance-blocks/`; blocks gate every booking path, overlapped
  reservations are auto-cancelled (idempotently) with equipment restock,
  payment failure, waitlist cleanup, and owner notifications; upcoming
  blocks appear on the public court page.

**Background jobs**
- Celery application with beat schedule: unpaid-hold expiry (every 5 min) and
  24 h reservation reminders (hourly). Tasks run eagerly in development.

**Platform / DevOps**
- Settings split into `picklesphere/settings/{base,dev,prod}.py`, selected by
  `DJANGO_ENV` (default `dev`); `picklesphere.settings` keeps working. Prod
  re-derives every `DEBUG`-derived value and fails fast on placeholder
  `SECRET_KEY`, wildcard hosts, SQLite, or missing `REDIS_URL`.
- Env-selectable database engine (`DB_ENGINE` + `DB_*`; PostgreSQL supported
  via psycopg 3 in `requirements-prod.txt`).
- Docker: non-root `Dockerfile` (daphne ASGI, `/health/` healthcheck,
  entrypoint waits for DB then migrates/collects static only when
  `RUN_MIGRATIONS=1`), `docker-compose.yml` with Postgres 16, Redis 7, web,
  Celery worker and beat.
- CI: GitHub Actions running system checks, migration drift check, full
  pytest suite with coverage artifact, and (non-blocking) `pip-audit` plus
  lint; pre-commit config; `requirements-dev.txt`.
- `/health/` endpoint for containers and load balancers.
- Documentation: this changelog, `README.md`, `CONTRIBUTING.md`,
  Apache-2.0 `LICENSE`.

## [0.1.0] — initial student version

- Initial PickleSphere application: courts, reservations, payments, scoring,
  tournaments, equipment, notifications, dashboards, CMS.
