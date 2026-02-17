from rest_framework import status, viewsets
from rest_framework.response import Response

from api.v1.serializers import LocaleSerializer
from content.models import Locale


class LocaleViewSet(viewsets.ModelViewSet):
    queryset = Locale.objects.all().order_by("code")
    serializer_class = LocaleSerializer
