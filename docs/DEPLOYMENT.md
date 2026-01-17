# Deployment (evidence-based)

## Docker image
- Base image is `python:3.12-slim`. (Dockerfile:L1-L1)
- Installs `postgresql-client` and `ca-certificates`. (Dockerfile:L5-L6)
- Installs Python dependencies from `requirements.txt`. (Dockerfile:L7-L8)
- Copies the app to `/app` and makes `entrypoint.sh` executable. (Dockerfile:L9-L10)

## Entrypoint behavior
- Waits for PostgreSQL using `pg_isready` and `DB_*` env vars. (entrypoint.sh:L4-L6)
- Runs `python manage.py migrate --noinput`. (entrypoint.sh:L8-L8)
- Runs `python manage.py collectstatic --noinput`. (entrypoint.sh:L9-L9)
- Starts Gunicorn with `core.wsgi:application`, 3 workers, 60s timeout, on port 8000. (entrypoint.sh:L11-L11)

## Runtime settings
- Database engine and connection settings are configured in `core/settings.py`. (core/settings.py:L66-L74)
- Static files are collected to `staticfiles/` and use WhiteNoise storage. (core/settings.py:L93-L98)
