#!/bin/sh
set -e

cd /app
: "${SECRET_KEY:?SECRET_KEY is required in production}"
: "${DATABASE_URL:?DATABASE_URL is required in production}"

python manage.py collectstatic --noinput
python manage.py migrate --noinput

exec "$@"
