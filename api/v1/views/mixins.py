from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response


class IntegrityErrorTo409Mixin:
    """Mixin to convert IntegrityError exceptions to 409 Conflict responses."""
    
    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError as exc:
            return Response(
                {"detail": "Conflict: unique constraint violated.", "error": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
