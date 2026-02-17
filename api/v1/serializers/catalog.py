from rest_framework import serializers

from catalog.models import (
    Attribute,
    AttributeValue,
    Product,
    ProductAttributeValue,
    ProductType,
    ProductTypeAttribute,
    Variant,
)
from django.db.models import Count, Q


class AttributeDetailSerializer(serializers.ModelSerializer):
    """Serializer for attribute with possible values"""

    values = serializers.SerializerMethodField()

    class Meta:
        model = Attribute
        fields = ["id", "code", "data_type", "unit", "is_multi", "is_value_translatable", "values"]

    def get_values(self, obj):
        """Return available values for enum attributes"""
        if obj.data_type == "enum":
            return list(obj.values.values("id", "code", "sort_order"))
        return []


class ProductTypeAttributeSerializer(serializers.ModelSerializer):
    """Serializer for product type attributes with full attribute details"""

    attribute = AttributeDetailSerializer()

    class Meta:
        model = ProductTypeAttribute
        fields = ["id", "attribute", "required", "filterable", "variant_level"]


class ProductTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = ["id", "code", "default_label", "parent_id", "main_category", "category_path", "is_active"]


class ProductSerializer(serializers.ModelSerializer):
    product_type_id = serializers.PrimaryKeyRelatedField(
        source="product_type",
        queryset=ProductType.objects.all(),
    )
    attributes = serializers.JSONField(write_only=True, required=False)
    variant_count = serializers.IntegerField(read_only=True, default=0)

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
            "variant_count",
            "attributes",
        ]

    def create(self, validated_data):
        attributes_data = validated_data.pop("attributes", {})
        product = super().create(validated_data)

        # Create attribute values
        for attr_code, value_data in attributes_data.items():
            try:
                attribute = Attribute.objects.get(code=attr_code)
                self._create_attribute_value(product, attribute, value_data)
            except Attribute.DoesNotExist:
                pass  # Skip invalid attributes

        return product

    def update(self, instance, validated_data):
        attributes_data = validated_data.pop("attributes", {})
        product = super().update(instance, validated_data)

        # Update or create attribute values
        for attr_code, value_data in attributes_data.items():
            try:
                attribute = Attribute.objects.get(code=attr_code)
                # Delete existing attribute value for this attribute
                ProductAttributeValue.objects.filter(product=product, attribute=attribute).delete()
                # Create new one
                if value_data not in [None, '', []]:  # Only create if there's a value
                    self._create_attribute_value(product, attribute, value_data)
            except Attribute.DoesNotExist:
                pass  # Skip invalid attributes

        return product

    def _create_attribute_value(self, product, attribute, value_data):
        """Create a product attribute value based on data type"""
        kwargs = {
            "product": product,
            "attribute": attribute,
        }

        # Handle different data types
        if attribute.data_type == "enum":
            # Value is either an AttributeValue ID or code
            if isinstance(value_data, int):
                kwargs["attribute_value_id"] = value_data
            elif isinstance(value_data, str):
                try:
                    attr_value = AttributeValue.objects.get(attribute=attribute, code=value_data)
                    kwargs["attribute_value"] = attr_value
                except AttributeValue.DoesNotExist:
                    return
        elif attribute.data_type == "text":
            kwargs["value_text"] = str(value_data)
        elif attribute.data_type == "number":
            try:
                kwargs["value_number"] = float(value_data)
            except (ValueError, TypeError):
                return
        elif attribute.data_type == "bool":
            kwargs["value_bool"] = bool(value_data)
        elif attribute.data_type == "json":
            kwargs["value_json"] = value_data

        ProductAttributeValue.objects.create(**kwargs)


class ProductMinimalSerializer(serializers.ModelSerializer):
    """Minimal product for embedding in variant list/detail."""

    class Meta:
        model = Product
        fields = ["id", "code", "default_label", "product_type_id"]


class VariantSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product = ProductMinimalSerializer(read_only=True)
    attributes = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = Variant
        fields = [
            "id",
            "product_id",
            "product",
            "sku",
            "barcode",
            "mpn",
            "internal_sku",
            "axis_signature",
            "created_at",
            # Source fields (from import/supplier)
            "source_title",
            "source_description",
            "source_sku",
            "source_supplier",
            "source_locale",
            "attributes",
        ]
        read_only_fields = ["id", "product_id", "internal_sku", "axis_signature", "created_at"]

    def update(self, instance, validated_data):
        attributes_data = validated_data.pop("attributes", {})
        instance = super().update(instance, validated_data)

        # Update variant attribute values
        for attr_code, value_data in attributes_data.items():
            try:
                attribute = Attribute.objects.get(code=attr_code)
                # Delete existing attribute value for this variant+attribute
                ProductAttributeValue.objects.filter(
                    variant=instance, attribute=attribute
                ).delete()
                # Create new one
                self._create_attribute_value(instance, attribute, value_data, is_variant=True)
            except Attribute.DoesNotExist:
                pass

        return instance

    def _create_attribute_value(self, variant_or_product, attribute, value_data, is_variant=False):
        """Helper to create attribute value (same logic as ProductSerializer)"""
        kwargs = {"attribute": attribute}
        if is_variant:
            kwargs["variant"] = variant_or_product
        else:
            kwargs["product"] = variant_or_product

        if attribute.data_type == "enum" and isinstance(value_data, int):
            kwargs["attribute_value_id"] = value_data
        elif attribute.data_type == "text":
            kwargs["value_text"] = str(value_data)
        elif attribute.data_type == "number":
            kwargs["value_number"] = value_data
        elif attribute.data_type == "bool":
            kwargs["value_bool"] = bool(value_data)
        elif attribute.data_type == "json":
            kwargs["value_json"] = value_data

        ProductAttributeValue.objects.create(**kwargs)


class VariantCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating variants (product_id is set from URL, not payload)"""
    attributes = serializers.JSONField(write_only=True, required=False)
    
    class Meta:
        model = Variant
        fields = [
            "sku",
            "barcode",
            "mpn",
            "source_title",
            "source_description",
            "source_sku",
            "source_supplier",
            "source_locale",
            "attributes",
        ]

    def create(self, validated_data):
        attributes_data = validated_data.pop("attributes", {})
        variant = super().create(validated_data)

        # Create variant attribute values
        for attr_code, value_data in attributes_data.items():
            try:
                attribute = Attribute.objects.get(code=attr_code)
                self._create_attribute_value(variant, attribute, value_data)
            except Attribute.DoesNotExist:
                pass

        return variant

    def _create_attribute_value(self, variant, attribute, value_data):
        """Helper to create attribute value"""
        kwargs = {"variant": variant, "attribute": attribute}

        if attribute.data_type == "enum" and isinstance(value_data, int):
            kwargs["attribute_value_id"] = value_data
        elif attribute.data_type == "text":
            kwargs["value_text"] = str(value_data)
        elif attribute.data_type == "number":
            kwargs["value_number"] = value_data
        elif attribute.data_type == "bool":
            kwargs["value_bool"] = bool(value_data)
        elif attribute.data_type == "json":
            kwargs["value_json"] = value_data

        ProductAttributeValue.objects.create(**kwargs)


class VariantAttributeDetailsSerializer(serializers.Serializer):
    """Read-only representation of a variant's attribute values with i18n info."""

    attribute_id = serializers.IntegerField()
    attribute_code = serializers.CharField()
    attribute_label = serializers.CharField(allow_null=True, required=False)
    data_type = serializers.CharField()
    is_variant_level = serializers.BooleanField()
    product_attribute_value_id = serializers.IntegerField()
    raw_value = serializers.CharField(allow_null=True)
    translated_value = serializers.CharField(allow_null=True)
    source = serializers.CharField()


class VariantAttributeValueWriteSerializer(serializers.Serializer):
    """
    Write serializer for creating/updating ProductAttributeValue records
    attached to a specific variant.
    """

    # For create; on update the attribute is taken from the instance
    attribute_id = serializers.IntegerField(required=False)

    # Type-specific value fields – exactly one must be provided
    attribute_value_id = serializers.IntegerField(required=False, allow_null=True)
    value_text = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    value_number = serializers.FloatField(required=False, allow_null=True)
    value_bool = serializers.BooleanField(required=False)

    def _get_variant(self):
        variant = self.context.get("variant")
        if variant is None:
            raise serializers.ValidationError("Variant context is required.")
        return variant

    def _get_attribute(self, attrs):
        # On update, always use the instance's attribute
        if self.instance is not None:
            return self.instance.attribute

        attribute_id = attrs.get("attribute_id")
        if not attribute_id:
            raise serializers.ValidationError({"attribute_id": "This field is required."})

        try:
            return Attribute.objects.get(id=attribute_id)
        except Attribute.DoesNotExist:
            raise serializers.ValidationError({"attribute_id": "Invalid attribute_id."})

    def validate(self, attrs):
        variant = self._get_variant()
        attribute = self._get_attribute(attrs)

        # Ensure attribute is allowed as variant-level for this product type
        product_type = variant.product.product_type
        if not ProductTypeAttribute.objects.filter(
            product_type=product_type, attribute=attribute, variant_level=True
        ).exists():
            raise serializers.ValidationError(
                {"attribute_id": "Attribute is not configured as variant-level for this product type."}
            )

        # Require exactly one concrete value field
        provided = {}
        for key in ("attribute_value_id", "value_text", "value_number", "value_bool"):
            if key in attrs and attrs.get(key) not in (None, ""):
                provided[key] = attrs[key]

        if not provided:
            raise serializers.ValidationError("Provide a value for the attribute.")
        if len(provided) > 1:
            raise serializers.ValidationError("Provide only one type-specific value field.")

        # Data-type specific checks
        data_type = attribute.data_type

        if data_type == "enum":
            attr_value_id = attrs.get("attribute_value_id")
            if not attr_value_id:
                raise serializers.ValidationError(
                    {"attribute_value_id": "attribute_value_id is required for enum attributes."}
                )
            if not AttributeValue.objects.filter(id=attr_value_id, attribute=attribute).exists():
                raise serializers.ValidationError(
                    {"attribute_value_id": "attribute_value_id does not belong to this attribute."}
                )
        elif data_type == "text":
            if not attrs.get("value_text"):
                raise serializers.ValidationError({"value_text": "value_text is required for text attributes."})
        elif data_type == "number":
            if attrs.get("value_number") is None:
                raise serializers.ValidationError(
                    {"value_number": "value_number is required for number attributes."}
                )
        elif data_type == "bool":
            if "value_bool" not in attrs:
                raise serializers.ValidationError({"value_bool": "value_bool is required for bool attributes."})

        # Attach attribute for use in create/update
        attrs["attribute"] = attribute
        return attrs

    def _apply_defaults(self, instance, validated_data):
        """
        Apply the validated value fields to the instance, clearing incompatible ones.
        """
        # Reset all basic value fields; JSON is not handled here
        instance.attribute_value_id = None
        instance.value_text = None
        instance.value_number = None
        instance.value_bool = None

        if "attribute_value_id" in validated_data:
            instance.attribute_value_id = validated_data["attribute_value_id"]
        if "value_text" in validated_data:
            instance.value_text = validated_data["value_text"]
        if "value_number" in validated_data:
            instance.value_number = validated_data["value_number"]
        if "value_bool" in validated_data:
            instance.value_bool = validated_data["value_bool"]

        instance.save()
        return instance

    def create(self, validated_data):
        variant = self._get_variant()
        attribute = validated_data.pop("attribute")

        # Enforce a single ProductAttributeValue per (variant, attribute)
        pav, _created = ProductAttributeValue.objects.get_or_create(
            variant=variant,
            attribute=attribute,
        )
        return self._apply_defaults(pav, validated_data)

    def update(self, instance, validated_data):
        # Attribute and variant are fixed on the instance
        validated_data.pop("attribute", None)
        return self._apply_defaults(instance, validated_data)


class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ["id", "code", "data_type", "unit", "is_multi", "is_value_translatable", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_code(self, value):
        """Ensure code is unique (except for current instance on update)"""
        if self.instance and self.instance.code == value:
            return value
        if Attribute.objects.filter(code=value).exists():
            raise serializers.ValidationError("An attribute with this code already exists.")
        return value


class CreateAttributeWithProductTypeSerializer(serializers.Serializer):
    """Serializer to create an Attribute and associate it with a ProductType"""
    code = serializers.SlugField(required=True)
    data_type = serializers.ChoiceField(choices=Attribute.DataType.choices, required=True)
    unit = serializers.CharField(max_length=50, required=False, allow_blank=True)
    is_multi = serializers.BooleanField(default=False)
    is_value_translatable = serializers.BooleanField(default=False)
    product_type_id = serializers.IntegerField(required=True)
    required = serializers.BooleanField(default=False)
    filterable = serializers.BooleanField(default=False)
    variant_level = serializers.BooleanField(default=False)

    def create(self, validated_data):
        product_type_id = validated_data.pop("product_type_id")
        required = validated_data.pop("required", False)
        filterable = validated_data.pop("filterable", False)
        variant_level = validated_data.pop("variant_level", False)

        # Create or get the attribute
        attribute, created = Attribute.objects.get_or_create(
            code=validated_data["code"],
            defaults=validated_data
        )

        # Associate with ProductType
        product_type = ProductType.objects.get(id=product_type_id)
        product_type_attribute, pta_created = ProductTypeAttribute.objects.get_or_create(
            product_type=product_type,
            attribute=attribute,
            defaults={
                "required": required,
                "filterable": filterable,
                "variant_level": variant_level,
            }
        )

        return {
            "attribute": attribute,
            "product_type_attribute": product_type_attribute,
            "created": created,
            "associated": pta_created,
        }


class AttributeValueSerializer(serializers.ModelSerializer):
    attribute_id = serializers.PrimaryKeyRelatedField(
        source="attribute",
        queryset=Attribute.objects.all(),
    )

    class Meta:
        model = AttributeValue
        fields = ["id", "attribute_id", "code", "sort_order"]


class TranslatableAttributeSerializer(serializers.ModelSerializer):
    """Serializer for translatable attributes with product type associations"""
    
    product_types = serializers.SerializerMethodField()
    translatable_value_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Attribute
        fields = ["id", "code", "data_type", "is_value_translatable", "product_types", "translatable_value_count"]
    
    def get_product_types(self, obj):
        """Return associated product types"""
        # #region agent log
        import json
        try:
            from core.debug_utils import DEBUG_LOG_PATH
            with open(DEBUG_LOG_PATH, 'a') as f:
                f.write(json.dumps({"id":"log_get_product_types_entry","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:254","message":"get_product_types entry","data":{"attribute_id":obj.id,"attribute_code":obj.code},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + '\n')
        except: pass
        # #endregion
        try:
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json.dumps({"id":"log_before_query","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:260","message":"Before product_type_attributes query","data":{},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + '\n')
            except: pass
            # #endregion
            product_type_attrs = obj.product_types.select_related("product_type").all()
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json.dumps({"id":"log_after_query","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:265","message":"After product_type_attributes query","data":{"count":product_type_attrs.count() if hasattr(product_type_attrs, 'count') else len(list(product_type_attrs))},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + '\n')
            except: pass
            # #endregion
            result = [
                {
                    "id": pta.product_type.id,
                    "code": pta.product_type.code,
                    "default_label": pta.product_type.default_label,
                    "variant_level": pta.variant_level,
                }
                for pta in product_type_attrs
            ]
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json.dumps({"id":"log_get_product_types_exit","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:275","message":"get_product_types exit","data":{"result_count":len(result)},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + '\n')
            except: pass
            # #endregion
            return result
        except Exception as e:
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json.dumps({"id":"log_get_product_types_exception","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:280","message":"Exception in get_product_types","data":{"error_type":type(e).__name__,"error_message":str(e)},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + '\n')
            except: pass
            # #endregion
            raise
    
    def get_translatable_value_count(self, obj):
        """Return count of translatable ProductAttributeValue records"""
        # #region agent log
        import json
        try:
            from core.debug_utils import DEBUG_LOG_PATH
            with open(DEBUG_LOG_PATH, 'a') as f:
                f.write(json.dumps({"id":"log_get_count_entry","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:267","message":"get_translatable_value_count entry","data":{"attribute_id":obj.id,"data_type":str(obj.data_type),"is_value_translatable":obj.is_value_translatable},"sessionId":"debug-session","runId":"run1","hypothesisId":"E"}) + '\n')
        except: pass
        # #endregion
        try:
            # Skip if not translatable or if it's a true enum attribute (not text using enum values)
            if not obj.is_value_translatable:
                return 0
            
            # For true enum attributes, they're translated via AttributeValueI18n, not ProductAttributeValue
            if obj.data_type == "enum":
                return 0
            
            # For text-type attributes, count both:
            # 1. Text values stored directly in value_text
            # 2. Enum values (when text-type attributes use enum AttributeValue objects)
            text_count = ProductAttributeValue.objects.filter(
                attribute=obj,
                attribute_value__isnull=True  # Direct text values
            ).exclude(
                Q(value_text__isnull=True) | Q(value_text="")
            ).count()
            
            # Count enum values used by text-type attributes (like color:blanc, material:cuir-synthetique)
            enum_count = ProductAttributeValue.objects.filter(
                attribute=obj,
                attribute_value__isnull=False  # Enum values
            ).count()
            
            result = text_count + enum_count
            
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json.dumps({"id":"log_get_count_exit","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:283","message":"get_translatable_value_count exit","data":{"count":result,"text_count":text_count,"enum_count":enum_count},"sessionId":"debug-session","runId":"run1","hypothesisId":"E"}) + '\n')
            except: pass
            # #endregion
            return result
        except Exception as e:
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json.dumps({"id":"log_get_count_exception","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:288","message":"Exception in get_translatable_value_count","data":{"error_type":type(e).__name__,"error_message":str(e)},"sessionId":"debug-session","runId":"run1","hypothesisId":"E"}) + '\n')
            except: pass
            # #endregion
            raise
