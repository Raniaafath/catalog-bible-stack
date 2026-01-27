from rest_framework import serializers

from content.models import (
    AttributeI18n,
    AttributeValueI18n,
    ProductAttributeValueI18n,
    ProductI18n,
    ProductTypeI18n,
    TranslationTask,
)


class TranslationTaskSerializer(serializers.ModelSerializer):
    channel_id = serializers.IntegerField(required=False, allow_null=True)
    
    # Progress tracking fields (read-only, computed from model properties)
    progress_percent = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = TranslationTask
        fields = [
            "id",
            "locale",
            "scope",
            "target_ids",
            "channel_id",
            "status",
            "model",
            "error",
            # Progress tracking
            "items_total",
            "items_completed",
            "progress_percent",
            "started_at",
            "finished_at",
            "duration_seconds",
            # Timestamps
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", 
            "status", 
            "error", 
            "items_total",
            "items_completed",
            "progress_percent",
            "started_at",
            "finished_at",
            "duration_seconds",
            "created_at", 
            "updated_at",
        ]
    
    def get_progress_percent(self, obj) -> int:
        """Return the progress percentage (0-100)."""
        return obj.progress_percent
    
    def get_duration_seconds(self, obj) -> int | None:
        """Return the duration in seconds."""
        return obj.duration_seconds


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


class AttributeI18nSerializer(serializers.ModelSerializer):
    attribute_code = serializers.CharField(source='attribute.code', read_only=True)
    
    class Meta:
        model = AttributeI18n
        fields = [
            "id",
            "attribute_id",
            "attribute_code",
            "locale_id",
            "label",
        ]


class AttributeValueI18nSerializer(serializers.ModelSerializer):
    attribute_value_code = serializers.CharField(source='attribute_value.code', read_only=True)
    attribute_code = serializers.CharField(source='attribute_value.attribute.code', read_only=True)
    
    class Meta:
        model = AttributeValueI18n
        fields = [
            "id",
            "attribute_value_id",
            "attribute_value_code",
            "attribute_code",
            "locale_id",
            "label",
        ]


class ProductTypeI18nSerializer(serializers.ModelSerializer):
    product_type_code = serializers.CharField(source='product_type.code', read_only=True)
    
    class Meta:
        model = ProductTypeI18n
        fields = [
            "id",
            "product_type_id",
            "product_type_code",
            "locale_id",
            "label",
            "main_category",
        ]
