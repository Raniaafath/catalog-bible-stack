from rest_framework import viewsets

from api.v1.serializers import LocaleSerializer
from content.models import Locale


class LocaleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Locale.objects.all().order_by("code")
    serializer_class = LocaleSerializer
