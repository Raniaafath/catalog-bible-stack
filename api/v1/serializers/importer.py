from rest_framework import serializers

from catalog.models import Attribute
from importer.models import ImportColumnMapping, CategoryBatch, ImportRow, ProductImport


class ProductImportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImport
        fields = [
            "id",
            "created_by",
            "created_at",
            "original_filename",
            "file_type",
            "status",
            "row_count",
            "error_count",
            "parse_error_message",
            "group_by_product_key",
            "category",
        ]


class ImportRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRow
        fields = ["id", "row_number", "raw", "normalized", "errors", "is_valid"]


class CategoryBatchSerializer(serializers.ModelSerializer):
    product_import_id = serializers.PrimaryKeyRelatedField(
        source="product_import",
        queryset=ProductImport.objects.all(),
    )

    class Meta:
        model = CategoryBatch
        fields = [
            "id",
            "product_import_id",
            "category",
            "status",
            "product_count",
            "variant_count",
            "created_at",
        ]


class ImportColumnMappingSerializer(serializers.ModelSerializer):
    category_batch_id = serializers.PrimaryKeyRelatedField(
        source="category_batch",
        queryset=CategoryBatch.objects.all(),
    )
    target_attribute_id = serializers.PrimaryKeyRelatedField(
        source="target_attribute",
        queryset=Attribute.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = ImportColumnMapping
        fields = [
            "id",
            "category_batch_id",
            "source_attr_name",
            "target_attribute_id",
            "strategy",
            "notes",
            "confidence",
            "created_at",
        ]


# Backward-compatibility alias.
AttributeMappingSerializer = ImportColumnMappingSerializer
