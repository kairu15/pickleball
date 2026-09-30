# PickleSphere 🎾

Pickleball facility & game management system built with Django: court
reservations with race-safe booking, online payments (Stripe + local
gateways), live match scoring over WebSockets, tournaments, equipment rental,
waitlists, maintenance scheduling, and a full staff/admin dashboard.

## Feature highlights

- **Race-safe booking** — availability is re-checked under a court row lock
  (`reservations/services.py`) so concurrent checkouts cannot double-book; on
  PostgreSQL the same checks can be backed by an `EXCLUDE` constraint
  (see `AUDIT.md` §6).
- **Payments** — Stripe Checkout for cards (webhooks are idempotent, refunds
  are mirrored from `charge.refunded`), plus GCash / Maya / bank / cash flows
  with proof-of-payment uploads.
- **Waitlist** — join a fully booked slot and get notified when it frees up.
- **Maintenance blocks & closures** — staff schedule per-court windows;
  overlapped reservations are auto-cancelled, equipment returned, owners
  notified, and upcoming blocks are shown on the public court page.
- **Live scoring** — Django Channels over WebSockets with access control and
  a score audit log.
- **Background jobs** — Celery worker + beat expire unpaid holds (30 min) and
  send 24 h reminders; runs eagerly in dev with no broker needed.
- **Notifications** — in-app center with 16 categories, e-mail via console /
  SMTP / Elastic Email (Anymail).

## Tech stack

Django 4.2 (also runs on 5.x), PostgreSQL (or SQLite for dev), Redis for
cache/Celery/channel layers, Channels + Daphne, WhiteNoise, django-axes,
Stripe, Celery.

## Quickstart (Docker)

```bash
cp .env.example .env           # then set SECRET_KEY (see below)
docker compose up --build      # web + postgres + redis + celery worker/beat
```

Generate a secret key and paste it into `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

The app is on http://localhost:8000, health check at `/health/`.
Websockets (live scoring, notifications) work out of the box — the web
service runs Daphne, not plain WSGI.

## Quickstart (local, without Docker)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                                 # defaults work for SQLite dev
python manage.py migrate
python manage.py runserver
```

Celery is optional in development: tasks run inline (`CELERY_TASK_ALWAYS_EAGER`)
and caches fall back to local memory, so no Redis is required.

## Settings & environments

Settings live in `picklesphere/settings/`:

| Module      | When it's used                                   |
|-------------|--------------------------------------------------|
| `base.py`   | All shared, env-driven configuration             |
| `dev.py`    | Default. Debug conveniences (ngrok hosts, finder static, eager Celery) |
| `prod.py`   | Hardened: re-derives security flags from `DEBUG=False` and **fails fast** on placeholder `SECRET_KEY`, wildcard `ALLOWED_HOSTS`, SQLite, or missing `REDIS_URL` |

Selection: `DJANGO_ENV=dev|prod` (default `dev`), or point
`DJANGO_SETTINGS_MODULE` at a specific module, e.g.
`DJANGO_SETTINGS_MODULE=picklesphere.settings.prod`.

Everything is configured via environment variables (see `.env.example`):
`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `SITE_URL`, `DB_ENGINE` + `DB_*`,
`REDIS_URL`, `CACHE_BACKEND=redis`, `STRIPE_*`, `EMAIL_*` /
`ELASTICEMAIL_API_KEY`, `CHANNEL_LAYER_BACKEND`, cookie/SSL flags.

## Testing & quality

```bash
pytest -q                                   # full suite
pytest --cov=reservations --cov=payments --cov=scoring   # coverage on the money path
python manage.py makemigrations --check --dry-run        # no model change without a migration
pre-commit run --all-files                  # ruff, black, hooks (see .pre-commit-config.yaml)
```

CI (`.github/workflows/django-tests.yml`) runs checks, the migration check,
the full suite with coverage artifact, and a non-blocking `pip-audit`.

## Background jobs

Beat schedule (see `picklesphere/settings/base.py`):
- `expire-unpaid-reservations` — every 5 min, cancels holds older than 30 min
- `send-reservation-reminders` — hourly, for bookings ~24 h out

Run manually:

```bash
python manage.py expire_unpaid_reservations --minutes 30
python manage.py send_reservation_reminders --hours 24
```

## Project layout

```
accounts/       users, roles (user/staff/super_admin), auth backends
courts/         courts, sites, availability, maintenance blocks
reservations/   booking domain services, waitlist, cancellation flows
payments/       Stripe, GCash/Maya/bank/cash, refunds, webhook idempotency
scoring/        matches, live scoring, audit log
tournaments/    brackets, registration
equipment/      inventory + per-reservation rentals
notifications/  in-app center, e-mail service, broadcast
dashboard/      staff/admin dashboards, CMS
```

## Deployment notes

- Use `DJANGO_ENV=prod` (or `picklesphere.settings.prod`) — it refuses to
  boot insecurely instead of leaking dev settings.
- Serve with Daphne (ASGI) so websocket scoring works; `docker compose` does
  this by default.
- `python manage.py collectstatic` is required in production; WhiteNoise
  serves hashed files with 1-year cache headers.
- Set `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, and a real
  `SITE_URL` behind HTTPS. Set `SECURE_SSL_REDIRECT=False` only if TLS
  terminates in front of the app.
- Migrations are additive and reversible; run `python manage.py migrate`
  (the Docker entrypoint does this automatically on the web service).
- PostgreSQL is strongly recommended in production — see `AUDIT.md` §6 for
  the database-level booking-overlap constraint this enables.

## License

Apache-2.0 — see [LICENSE](LICENSE).
