# Contributing to PickleSphere

Thanks for helping make PickleSphere production-ready! This document covers
the workflow and standards used in this repository.

## Development setup

```bash
git clone https://github.com/kairu15/pickleball.git
cd pickleball
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env        # SQLite defaults are fine for development
python manage.py migrate
python manage.py runserver
```

## Branching & commits

- Work on feature branches off `main` (e.g. `fix/booking-integrity`,
  `feat/scoring-ui`). Do not commit directly to `main`.
- Use [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `build:`, `ci:`.
  Keep each commit small and focused; the subject explains the *why*.
- **Never rewrite history** on shared branches — no force-push, no rebase of
  commits others may have pulled. Local squashes before pushing are fine.
- Migrations must be additive and reversible; never edit a migration that has
  been pushed (add a follow-up migration instead).

## Tests are not optional

Every change ships with tests:

```bash
pytest -q                                   # must be green before you push
pytest --cov=reservations --cov=payments --cov=scoring   # money path coverage
python manage.py makemigrations --check --dry-run        # no drift allowed
```

- Concurrency-sensitive logic (booking, payments, equipment stock) belongs in
  `reservations/services.py` / service modules and gets service-level tests,
  not just view tests.
- Use the fast hasher in auth-heavy tests:
  `@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])`.
- Views that touch slot availability must go through the shared gates in
  `reservations/services.py` — do not hand-roll overlap queries.

## Lint & types

```bash
pre-commit install          # one-time
pre-commit run --all-files  # ruff + black + hooks
mypy .                      # configured in pyproject.toml
```

Style: ruff (E/F/W/I/B/UP/DJ) + black at 100 columns. The lint job in CI is
non-blocking until the existing baseline is clean — do not add new violations.

## Pull requests

1. Rebase/merge the latest `main` into your branch.
2. CI must pass (tests, migration check; lint is advisory for now).
3. Describe the *why*, list behavior changes, and note any new env vars or
   migrations in the PR description.
4. One approval required; the maintainer merges (no self-merge).

## Security issues

Do not open a public issue for security vulnerabilities. Report privately to
the repository owner (kairu15) or via GitHub's "Report a vulnerability"
flow on this repository.

## License

By contributing you agree that your contributions are licensed under the
Apache-2.0 license (see `LICENSE`).
