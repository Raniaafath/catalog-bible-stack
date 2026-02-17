from rest_framework import serializers

from content.models import Locale


class LocaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Locale
        fields = ["id", "code", "name"]
        read_only_fields = ["id"]

    def validate_code(self, value):
        """Validate locale code format (should be lowercase, 2-5 characters typically)."""
        if not value:
            raise serializers.ValidationError("Locale code is required.")
        value = value.lower().strip()
        if len(value) < 2 or len(value) > 15:
            raise serializers.ValidationError("Locale code must be between 2 and 15 characters.")
        return value
