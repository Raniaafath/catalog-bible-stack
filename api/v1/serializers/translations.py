from rest_framework import serializers

from content.models import ProductAttributeValueI18n, ProductI18n, TranslationTask


class TranslationTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranslationTask
        fields = [
            "id",
            "locale",
            "scope",
            "target_ids",
            "status",
            "error",
            "created_at",
            "updated_at",
        ]


class ProductI18nSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductI18n
        fields = [
            "id",
            "product_id",
            "locale_id",
            "title",
            "description",
            "meta_title",
            "meta_description",
            "slug",
            "is_locked",
        ]


class ProductAttributeValueI18nSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttributeValueI18n
        fields = [
            "id",
            "product_attribute_value_id",
            "locale_id",
            "value_text",
            "is_locked",
        ]
