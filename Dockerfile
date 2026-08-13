# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.12
ARG NODE_VERSION=22

# Stage 1: build CSS
FROM node:${NODE_VERSION}-alpine AS js-builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY static/css/src ./static/css/src
# Tailwind v4 is CSS-first and auto-scans sources for utility classes —
# templates must be present so the generated CSS includes the site's classes.
COPY templates/ ./templates/
# Tailwind v4 is CSS-first — no JS config file to copy.
RUN npm run build   # writes static/css/dist/app.css

# Stage 2: install python deps + collect static
FROM python:${PYTHON_VERSION}-slim AS python-builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements/base.txt requirements/production.txt ./
RUN pip install --no-cache-dir -r requirements/production.txt
COPY . /app
COPY --from=js-builder /app/static/css/dist /app/static/css/dist
# collectstatic does not touch the DB; placeholder creds are only needed to
# satisfy the production settings module.
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    SECRET_KEY=collectstatic-secret-key \
    DATABASE_URL=postgres://placeholder@host:5432/db \
    python manage.py collectstatic --noinput

# Stage 3: runtime
FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash --uid 1000 app
COPY --from=python-builder /app /app
RUN chown -R app:app /app
# entrypoint copied + chmod'ed as root BEFORE switching to the non-root user
# (the app user cannot chmod a root-owned file).
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
USER app
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
