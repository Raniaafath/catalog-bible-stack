# Docker Commands for Catalog Bible Stack

## "Cannot reach the server" when using Docker

1. **Start the stack** (from project root, e.g. `/srv/catalog-bible-stack`):
   ```bash
   docker compose up -d
   ```
2. **Check Django is up**: `curl -s http://127.0.0.1:8000/api/v1/` should return JSON. If not, check `docker compose logs web`.
3. **Reverse proxy must forward `/api` to Django**:
   - Proxy on the **host**: use `proxy_pass http://127.0.0.1:8000;` (port 8000 is published).
   - Proxy **in Docker** on the same `proxy` network: use `proxy_pass http://web:8000;`.
4. **Frontend**: build with `VITE_API_BASE_URL=/api/v1` so the app calls the same origin; the proxy then forwards `/api` to the `web` service.

---

## Quick Reference

Since you're using Docker Compose, you need to run Django management commands inside the container.

### Service Name
- **Service**: `web`
- **Container**: `catalog-bible-web`

---

## Common Commands

### 1. Run Migrations

```bash
# From the project root (/srv/catalog-bible-stack)
docker compose exec web python manage.py migrate
```

### 2. Run Translation Tasks

```bash
# Process pending translation tasks
docker compose exec web python manage.py run_translation_tasks --locale=en --limit=10

# Process for French
docker compose exec web python manage.py run_translation_tasks --locale=fr --limit=10
```

### 3. Django Shell

```bash
# Open Django shell
docker compose exec web python manage.py shell

# Or use interactive mode
docker compose exec -it web python manage.py shell
```

### 4. Create Superuser

```bash
docker compose exec -it web python manage.py createsuperuser
```

### 5. Collect Static Files

```bash
docker compose exec web python manage.py collectstatic --noinput
```

### 6. Check Django System

```bash
docker compose exec web python manage.py check
```

### 7. View Logs

```bash
# View web service logs
docker compose logs web

# Follow logs in real-time
docker compose logs -f web

# View last 100 lines
docker compose logs --tail=100 web
```

### 8. Restart Services

```bash
# Restart web service
docker compose restart web

# Rebuild and restart
docker compose up -d --build web
```

---

## Testing the Implementation

### Test Translation Feature

1. **Create a translation task via UI:**
   - Navigate to `http://your-domain/translations/new`
   - Select attributes, language, and model
   - Click "Start Translation"

2. **Process the task:**
   ```bash
   docker compose exec web python manage.py run_translation_tasks --locale=en --limit=10
   ```

3. **Check results:**
   - Navigate to `http://your-domain/translations`
   - View task status and model used

### Test Title Generation

1. **Via UI:**
   - Navigate to `http://your-domain/groups`
   - Select a listing group
   - Click "Generate Titles" tab
   - Select locale and template
   - Click "Generate Titles"

2. **Check logs:**
   ```bash
   docker compose logs -f web
   ```

---

## Alternative: Using docker exec directly

If you prefer using `docker exec` directly:

```bash
# Get container name
docker ps | grep catalog-bible-web

# Run command
docker exec -it catalog-bible-web python manage.py migrate

# Or with container ID
docker exec -it <container-id> python manage.py migrate
```

---

## Troubleshooting

### Container not running?
```bash
docker compose ps
docker compose up -d
```

### Need to rebuild?
```bash
docker compose build web
docker compose up -d web
```

### Check environment variables
```bash
docker compose exec web env | grep DB_
```

### Access container shell
```bash
docker compose exec -it web bash
```

---

## Notes

- The `web` service automatically runs migrations on startup (see `entrypoint.sh`)
- Code changes are reflected immediately due to volume mount (`./django:/app`)
- Static files are collected automatically on container start
- Database is in a separate `db` service container
