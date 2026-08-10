# Portfolio Web

Professional portfolio built with Django — designed as a showcase project demonstrating
Django, Docker, AI integration, cloud deployment, and infrastructure automation.


- Python 3.12 / Django 6.0
- Django templates + Tailwind CSS + GSAP (frontend)
- SQLite in development (PostgreSQL planned for production)
- Docker / Docker Compose deployment (planned)

## Local setup

```bash
python -m venv .venv
.venv/bin/pip install -r requirements/base.txt
cp .env.example .env        # then set a real SECRET_KEY
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Configuration (SECRET_KEY, DEBUG, ALLOWED_HOSTS) is read from `.env` via django-environ.
`.env` is gitignored — never commit it.

## Project layout

- `config/` — Django project settings, URLs, WSGI/ASGI
- `apps/` — Django apps (`core` now; `projects`, `skills`, `experience`, `certifications`, `blog`, `contact` planned)
- `templates/`, `static/`, `media/` — frontend assets
- `requirements/` — `base.txt` (dev), `production.txt` (planned)
