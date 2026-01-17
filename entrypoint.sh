#!/usr/bin/env bash
set -euo pipefail

until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; do
  sleep 1
done

python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60
