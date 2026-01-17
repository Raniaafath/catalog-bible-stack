from rest_framework import serializers

from catalog.models import Attribute, AttributeValue, Product, ProductType, Variant


class ProductTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = ["id", "code", "default_label", "parent_id", "main_category", "category_path", "is_active"]


class ProductSerializer(serializers.ModelSerializer):
    product_type_id = serializers.PrimaryKeyRelatedField(
        source="product_type",
        queryset=ProductType.objects.all(),
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "product_type_id",
            "code",
            "status",
            "series",
            "brand",
            "model",
            "default_label",
            "source_title",
            "source_description",
            "source_locale",
            "source_supplier",
            "source_sku",
        ]


class VariantSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=Product.objects.all(),
    )

    class Meta:
        model = Variant
        fields = ["id", "product_id", "barcode", "mpn", "internal_sku", "sku", "axis_signature"]
        read_only_fields = ["internal_sku"]


class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ["id", "code", "data_type", "unit", "is_multi"]


class AttributeValueSerializer(serializers.ModelSerializer):
    attribute_id = serializers.PrimaryKeyRelatedField(
        source="attribute",
        queryset=Attribute.objects.all(),
    )

    class Meta:
        model = AttributeValue
        fields = ["id", "attribute_id", "code", "sort_order"]
