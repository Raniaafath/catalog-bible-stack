"""Shared path for agent debug log. Works in Docker (BASE_DIR=/app) and locally."""
from pathlib import Path

from django.conf import settings

DEBUG_LOG_PATH = Path(settings.BASE_DIR) / ".cursor" / "debug.log"
