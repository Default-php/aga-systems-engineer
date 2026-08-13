# Portfolio — Alfonso González Arellano

Systems-engineer portfolio built with Django: a fast, themeable showcase site with
admin-managed content (projects, skills, experience, certifications), a blog, a
contact form, SEO/sitemap support, and production-ready Docker infrastructure. The
project doubles as a working example of Django 6 development with CI, containerized
deployment, and an AI-assistant integration.

## Stack

- Python 3.12 / Django 6.0
- Django templates + Tailwind CSS v4 (CSS-first) + GSAP (frontend animations)
- SQLite in development; PostgreSQL in production (via `DATABASE_URL`)
- Docker / Docker Compose (multi-stage build, Postgres, healthchecks)
- GitHub Actions CI
- OpenRouter AI integration (RAG chat assistant, Phase 4.5)

## Local setup

```bash
python -m venv .venv
.venv/bin/pip install -r requirements/base.txt
cp .env.example .env        # then set a real SECRET_KEY
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Then visit http://127.0.0.1:8000/. To seed content, create an admin user with
`.venv/bin/python manage.py createsuperuser` and use the `/admin/` interface
(see `temp/PLAN.md` for the recommended population order).

## Environment variables

Copy [`.env.example`](.env.example) to `.env` and fill in real values. `.env` is
gitignored — never commit it.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key (required) |
| `DEBUG` | `True` in development; production forces `False` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `DEFAULT_FROM_EMAIL` | From-address for contact emails |
| `CONTACT_RECIPIENT_EMAIL` | Where contact-form messages are delivered |
| `SITE_DESCRIPTION` | Default meta/OG description |
| `SECURE_PROXY_SSL_HEADER_ENABLED` | `True` when behind a TLS-terminating proxy |
| `POSTGRES_PASSWORD` | Required for `docker compose up` (no default) |
| `OPENROUTER_API_KEY` | Optional — forwarded to the AI widget; empty enables demo mode |
| `OPENROUTER_MODEL` | OpenRouter model to use (default `openrouter/auto:free`) |

`DATABASE_URL` is only read by the `production` settings module; local development
uses SQLite automatically.

## Docker / deployment

The image is built from a multi-stage `Dockerfile`:

1. `js-builder` (Node 22) — `npm ci` + Tailwind CSS build (templates are bundled so
   the compiled CSS includes the site's classes).
2. `python-builder` (Python 3.12 slim) — installs runtime dependencies and runs
   `collectstatic`, so static files are baked into the image (served by WhiteNoise).
3. `runtime` — slim Python image, non-root user, gunicorn entrypoint.

`entrypoint.sh` runs `collectstatic --noinput` then `migrate --noinput` before
executing gunicorn; it fails fast if `SECRET_KEY` or `DATABASE_URL` are missing.

To run the full stack:

```bash
cp .env.example .env
# set POSTGRES_PASSWORD, SECRET_KEY, ALLOWED_HOSTS, OPENROUTER_API_KEY
docker compose up --build
```

Compose starts `db` (Postgres 16 with a healthcheck) and `web` (the Django app,
which waits for the database, then serves on port 8000). Healthchecks keep the
services observable; the web service checks `/` via curl.

Useful commands:

```bash
docker compose logs web
docker compose exec web python manage.py shell
docker compose exec web python manage.py createsuperuser
```

## Cloud notes

The image runs on any Docker host: Fly.io, Render, a plain VPS, or ECS. Put a
TLS-terminating reverse proxy (nginx, Caddy, or Traefik) in front of port 8000.
Production requires these environment variables:

- `DATABASE_URL` — e.g. `postgres://user:pass@host:5432/portfolio`
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `OPENROUTER_API_KEY` (for the AI widget; demo mode runs without)

## Project layout

- `config/` — Django project: settings split into `base` / `development` / `production`, URLconf, WSGI/ASGI
- `apps/` — Django apps: `core`, `projects`, `skills`, `experience`, `certifications`, `blog`, `contact`, `ai_assistant`
- `templates/`, `static/`, `media/` — frontend assets
- `requirements/` — `base.txt` (dev + shared), `production.txt` (runtime extras)
- `.github/workflows/ci.yml` — GitHub Actions: checks, tests, JS tests, informational lint

## CI

GitHub Actions runs the Django system check, the full test suite, the JS tests,
and an informational lint pass on every push to `main` and the `phase*` branches,
and on pull requests against `main`.
