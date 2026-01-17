from rest_framework import serializers

from content.models import Locale


class LocaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Locale
        fields = ["id", "code", "name"]
