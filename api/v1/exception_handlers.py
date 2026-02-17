"""
Custom exception handler so API always returns JSON (never HTML) on errors.
"""
import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """Call DRF default handler; if it returns None (unhandled), return JSON 500."""
    response = exception_handler(exc, context)
    if response is not None:
        return response
    logger.exception("Unhandled API exception: %s", exc)
    return Response(
        {"detail": str(exc) or "Internal server error"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
