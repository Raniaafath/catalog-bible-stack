from django.contrib.auth import get_user_model
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ["id", "email", "full_name", "is_staff", "is_superuser"]

    def get_full_name(self, obj):
        try:
            full_name = (obj.get_full_name() or "").strip()
            if full_name:
                return full_name
            return (getattr(obj, "first_name", None) or getattr(obj, "username", None)) or ""
        except Exception:
            return ""


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    full_name = serializers.CharField(required=False, allow_blank=True)
