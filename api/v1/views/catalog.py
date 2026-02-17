from django.db import models, transaction
from django.db.models import Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from api.v1.serializers import (
    AttributeSerializer,
    AttributeValueSerializer,
    ProductSerializer,
    ProductTypeSerializer,
    VariantSerializer,
)
from api.v1.serializers.catalog import (
    CreateAttributeWithProductTypeSerializer,
    ProductTypeAttributeSerializer,
    TranslatableAttributeSerializer,
    VariantCreateSerializer,
    VariantAttributeValueWriteSerializer,
)
from api.v1.views.mixins import IntegrityErrorTo409Mixin
from catalog.models import (
    Attribute,
    AttributeValue,
    ChannelVariantAxis,
    Product,
    ProductAttributeValue,
    ProductType,
    ProductTypeAttribute,
    Variant,
)
from content.models import Locale, ProductHookTerm, ProductTypeI18n, ProductTypeSynonym, SynonymStatus
from pub.models import Channel


class ProductTypeViewSet(viewsets.ModelViewSet):
    queryset = ProductType.objects.all().order_by("code")
    serializer_class = ProductTypeSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=["get"], url_path="attributes")
    def attributes(self, request, pk=None):
        """Get all attributes for a specific product type"""
        product_type = self.get_object()
        type_attributes = ProductTypeAttribute.objects.filter(product_type=product_type).select_related(
            "attribute"
        ).prefetch_related("attribute__values")
        serializer = ProductTypeAttributeSerializer(type_attributes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="link-attribute")
    def link_attribute(self, request, pk=None):
        """Link an existing attribute to this product type"""
        product_type = self.get_object()
        attribute_id = request.data.get("attribute_id")
        required = request.data.get("required", False)
        filterable = request.data.get("filterable", False)
        variant_level = request.data.get("variant_level", False)

        if not attribute_id:
            return Response({"error": "attribute_id is required"}, status=400)

        try:
            attribute = Attribute.objects.get(id=attribute_id)
            product_type_attribute, created = ProductTypeAttribute.objects.get_or_create(
                product_type=product_type,
                attribute=attribute,
                defaults={
                    "required": required,
                    "filterable": filterable,
                    "variant_level": variant_level,
                }
            )

            if not created:
                # Update if it already exists
                product_type_attribute.required = required
                product_type_attribute.filterable = filterable
                product_type_attribute.variant_level = variant_level
                product_type_attribute.save()

            serializer = ProductTypeAttributeSerializer(product_type_attribute)
            return Response(serializer.data, status=201 if created else 200)
        except Attribute.DoesNotExist:
            return Response({"error": "Attribute not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=["get", "post"], url_path="head-terms")
    def head_terms(self, request, pk=None):
        """
        GET: List head terms for this product type (used in title generation).
             Query params: locale_id (required), channel_id (optional).
        POST: Add a head term. Body: { "locale_id", "channel_id"?, "term" }.
        """
        product_type = self.get_object()
        if request.method == "POST":
            locale_id = request.data.get("locale_id")
            if not locale_id:
                return Response({"detail": "locale_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                locale = Locale.objects.get(id=locale_id)
            except Locale.DoesNotExist:
                return Response({"detail": "Locale not found"}, status=status.HTTP_404_NOT_FOUND)
            channel_id = request.data.get("channel_id")
            channel = Channel.objects.filter(id=channel_id).first() if channel_id else None
            term = (request.data.get("term") or "").strip()
            if not term:
                return Response({"detail": "term is required"}, status=status.HTTP_400_BAD_REQUEST)
            syn, created = ProductTypeSynonym.objects.get_or_create(
                product_type=product_type,
                locale=locale,
                channel=channel,
                term=term,
                defaults={"status": SynonymStatus.APPROVED, "is_active": True},
            )
            if not created:
                syn.status = SynonymStatus.APPROVED
                syn.is_active = True
                syn.save()
            return Response(
                {"id": syn.id, "term": syn.term, "locale_id": syn.locale_id, "channel_id": syn.channel_id},
                status=status.HTTP_201_CREATED if created else 200,
            )

        locale_id = request.query_params.get("locale_id")
        if not locale_id:
            return Response({"detail": "locale_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            locale = Locale.objects.get(id=locale_id)
        except Locale.DoesNotExist:
            return Response({"detail": "Locale not found"}, status=status.HTTP_404_NOT_FOUND)
        channel_id = request.query_params.get("channel_id")
        channel = Channel.objects.filter(id=channel_id).first() if channel_id else None

        terms = []
        pti18n = ProductTypeI18n.objects.filter(product_type=product_type, locale=locale).first()
        if pti18n and pti18n.label:
            terms.append({"term": pti18n.label, "source": "label", "id": None})

        syn_qs = ProductTypeSynonym.objects.filter(
            product_type=product_type,
            locale=locale,
            status=SynonymStatus.APPROVED,
            is_active=True,
        ).order_by("-priority", "id")
        if channel:
            syn_qs = syn_qs.filter(models.Q(channel=channel) | models.Q(channel__isnull=True))
        for syn in syn_qs:
            terms.append({"term": syn.term, "source": "synonym", "id": syn.id})
        return Response({"terms": terms})

    @action(detail=True, methods=["delete"], url_path="head-terms/(?P<synonym_id>[^/.]+)")
    def remove_head_term(self, request, pk=None, synonym_id=None):
        """Remove a head term (synonym) by id. Only synonyms are removable; label is from ProductTypeI18n."""
        product_type = self.get_object()
        try:
            syn = ProductTypeSynonym.objects.get(id=synonym_id, product_type=product_type)
        except ProductTypeSynonym.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        syn.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductViewSet(IntegrityErrorTo409Mixin, viewsets.ModelViewSet):
    queryset = (
        Product.objects.select_related("product_type")
        .annotate(variant_count=Count("variants"))
        .order_by("-id")
    )
    serializer_class = ProductSerializer

    @action(detail=True, methods=["get", "post"], url_path="variants")
    def variants(self, request, pk=None):
        """
        GET: List variants for this product
        POST: Create a variant attached to this product
        """
        product = self.get_object()

        if request.method.lower() == "get":
            qs = Variant.objects.filter(product=product).order_by("-id")
            return Response(VariantSerializer(qs, many=True).data)

        # POST: create a variant under this product
        serializer = VariantCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        variant = Variant.objects.create(product=product, **serializer.validated_data)
        return Response(VariantSerializer(variant).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="group-variants")
    def group_variants(self, request, pk=None):
        """
        Attach existing variants to this product (grouping/regrouping).
        Body: { "variant_ids": [1,2,3] }
        """
        target = self.get_object()
        variant_ids = request.data.get("variant_ids") or []
        
        if not isinstance(variant_ids, list) or not variant_ids:
            return Response(
                {"detail": "variant_ids must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            qs = Variant.objects.select_for_update().filter(id__in=variant_ids)
            found = qs.count()
            unique_ids = len(set(variant_ids))
            
            if found != unique_ids:
                return Response(
                    {
                        "detail": "Some variants do not exist",
                        "found": found,
                        "requested": unique_ids,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            qs.update(product=target)

        return Response({
            "detail": "ok",
            "product_id": target.id,
            "moved_variants": unique_ids,
        })

    @action(detail=True, methods=["get"], url_path="attribute-values")
    def attribute_values(self, request, pk=None):
        """Get all attribute values for a specific product"""
        product = self.get_object()
        attribute_values = ProductAttributeValue.objects.filter(product=product).select_related(
            "attribute", "attribute_value"
        )
        
        data = []
        for pav in attribute_values:
            data.append({
                "id": pav.id,
                "product_id": product.id,
                "attribute_id": pav.attribute.id,
                "attribute_code": pav.attribute.code,
                "value_text": pav.value_text,
                "value_number": pav.value_number,
                "value_bool": pav.value_bool,
                "attribute_value_id": pav.attribute_value_id,
            })
        
        return Response(data)

    @action(detail=True, methods=["get", "post"], url_path="hook-terms")
    def hook_terms(self, request, pk=None):
        """
        GET: List hook terms for this product (group of variants). Query: locale_id (required), channel_id (optional).
        POST: Add a hook term. Body: { "locale_id", "channel_id"?, "term", "priority"?: int }.
        """
        product = self.get_object()
        if request.method == "POST":
            locale_id = request.data.get("locale_id")
            if not locale_id:
                return Response({"detail": "locale_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                locale = Locale.objects.get(id=locale_id)
            except Locale.DoesNotExist:
                return Response({"detail": "Locale not found"}, status=status.HTTP_404_NOT_FOUND)
            channel_id = request.data.get("channel_id")
            channel = Channel.objects.filter(id=channel_id).first() if channel_id else None
            term = (request.data.get("term") or "").strip()
            if not term:
                return Response({"detail": "term is required"}, status=status.HTTP_400_BAD_REQUEST)
            priority = request.data.get("priority")
            if priority is None:
                priority = 0
            try:
                priority = int(priority)
            except (TypeError, ValueError):
                priority = 0
            hook_term, created = ProductHookTerm.objects.update_or_create(
                product=product,
                locale=locale,
                channel=channel,
                term=term,
                defaults={"priority": priority},
            )
            return Response(
                {
                    "id": hook_term.id,
                    "term": hook_term.term,
                    "locale_id": hook_term.locale_id,
                    "channel_id": hook_term.channel_id,
                    "priority": hook_term.priority,
                },
                status=status.HTTP_201_CREATED if created else 200,
            )

        locale_id = request.query_params.get("locale_id")
        if not locale_id:
            return Response({"detail": "locale_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        channel_id = request.query_params.get("channel_id")
        qs = ProductHookTerm.objects.filter(product=product, locale_id=locale_id).select_related("locale", "channel")
        if channel_id:
            qs = qs.filter(models.Q(channel_id=channel_id) | models.Q(channel__isnull=True))
        qs = qs.order_by("-priority", "id")
        data = [
            {
                "id": h.id,
                "term": h.term,
                "locale_id": h.locale_id,
                "channel_id": h.channel_id,
                "priority": h.priority,
            }
            for h in qs
        ]
        return Response({"terms": data})

    @action(detail=True, methods=["delete"], url_path="hook-terms/(?P<hook_term_id>[^/.]+)")
    def remove_hook_term(self, request, pk=None, hook_term_id=None):
        """Remove a hook term by id."""
        product = self.get_object()
        try:
            hook_term = ProductHookTerm.objects.get(id=hook_term_id, product=product)
        except ProductHookTerm.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        hook_term.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post", "delete"], url_path="channel-axes")
    def channel_axes(self, request, pk=None):
        """
        GET: Get variation axes for this product + channel
        POST: Set variation axes for this product + channel
        DELETE: Remove all axes for this product + channel
        
        Query params: ?channel_id=1
        POST body: {
            "channel_id": 1,
            "axes": [
                {"attribute_id": 5, "position": 0},
                {"attribute_id": 6, "position": 1}
            ]
        }
        """
        product = self.get_object()
        channel_id = request.query_params.get("channel_id") or request.data.get("channel_id")
        
        if not channel_id:
            return Response(
                {"detail": "channel_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            channel = Channel.objects.get(id=channel_id)
        except Channel.DoesNotExist:
            return Response(
                {"detail": "Channel not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if request.method == "GET":
            axes = ChannelVariantAxis.objects.filter(
                product=product,
                channel=channel
            ).select_related("attribute").order_by("position")
            
            data = {
                "product_id": product.id,
                "product_code": product.code,
                "channel": {
                    "id": channel.id,
                    "code": channel.code,
                    "name": channel.name,
                },
                "axes": [
                    {
                        "id": axis.id,
                        "attribute": {
                            "id": axis.attribute.id,
                            "code": axis.attribute.code,
                            "data_type": axis.attribute.data_type,
                        },
                        "position": axis.position,
                        "label_override": axis.label_override,
                    }
                    for axis in axes
                ],
            }
            return Response(data)
        
        elif request.method == "POST":
            axes_data = request.data.get("axes", [])
            
            if not isinstance(axes_data, list):
                return Response(
                    {"detail": "axes must be a list"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                # Delete existing axes for this product+channel
                ChannelVariantAxis.objects.filter(product=product, channel=channel).delete()
                
                # Create new axes
                created_axes = []
                for idx, axis_item in enumerate(axes_data):
                    attribute_id = axis_item.get("attribute_id")
                    position = axis_item.get("position", idx)
                    label_override = axis_item.get("label_override")
                    
                    if not attribute_id:
                        continue
                    
                    try:
                        attribute = Attribute.objects.get(id=attribute_id)
                        axis = ChannelVariantAxis.objects.create(
                            product=product,
                            channel=channel,
                            attribute=attribute,
                            position=position,
                            label_override=label_override or None,
                        )
                        created_axes.append({
                            "id": axis.id,
                            "attribute_id": attribute.id,
                            "attribute_code": attribute.code,
                            "position": axis.position,
                        })
                    except Attribute.DoesNotExist:
                        continue
                
                return Response({
                    "detail": "ok",
                    "product_id": product.id,
                    "channel_id": channel.id,
                    "axes": created_axes,
                }, status=status.HTTP_201_CREATED)
        
        elif request.method == "DELETE":
            deleted_count, _ = ChannelVariantAxis.objects.filter(
                product=product,
                channel=channel
            ).delete()
            
            return Response({
                "detail": "ok",
                "deleted_count": deleted_count,
            })


class VariantViewSet(IntegrityErrorTo409Mixin, viewsets.ModelViewSet):
    queryset = Variant.objects.select_related("product").order_by("-id")
    serializer_class = VariantSerializer

    def perform_destroy(self, instance):
        product = instance.product
        instance.delete()
        # Keep things simple: no product without variants
        if product.variants.count() == 0:
            product.delete()

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by product_id
        product_id = self.request.query_params.get("product_id")
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        return queryset

    @action(detail=True, methods=["get", "post"], url_path="attribute-values")
    def attribute_values(self, request, pk=None):
        """
        GET: list raw ProductAttributeValue records for this variant.
        POST: create or update a ProductAttributeValue for this variant.
        """
        variant = self.get_object()

        if request.method == "GET":
            attribute_values = ProductAttributeValue.objects.filter(variant=variant).select_related(
                "attribute", "attribute_value"
            )

            data = []
            for pav in attribute_values:
                data.append(
                    {
                        "id": pav.id,
                        "variant_id": variant.id,
                        "attribute_id": pav.attribute.id,
                        "attribute_code": pav.attribute.code,
                        "value_text": pav.value_text,
                        "value_number": pav.value_number,
                        "value_bool": pav.value_bool,
                        "attribute_value_id": pav.attribute_value_id,
                    }
                )

            return Response(data)

        serializer = VariantAttributeValueWriteSerializer(
            data=request.data,
            context={"variant": variant},
        )
        serializer.is_valid(raise_exception=True)
        pav = serializer.save()
        return Response({"id": pav.id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch", "delete"], url_path="attribute-values/(?P<pav_id>[^/.]+)")
    def attribute_value_detail(self, request, pk=None, pav_id=None):
        """
        PATCH: update a single ProductAttributeValue belonging to this variant.
        DELETE: delete a single ProductAttributeValue belonging to this variant.
        """
        variant = self.get_object()
        try:
            pav = ProductAttributeValue.objects.get(id=pav_id, variant=variant)
        except ProductAttributeValue.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.method == "DELETE":
            pav.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = VariantAttributeValueWriteSerializer(
            pav,
            data=request.data,
            partial=True,
            context={"variant": variant},
        )
        serializer.is_valid(raise_exception=True)
        pav = serializer.save()
        return Response({"id": pav.id})

    @action(detail=True, methods=["post"], url_path="move-to-product")
    def move_to_product(self, request, pk=None):
        """
        Move a single variant to another product.
        Body: { "product_id": 123 }
        """
        variant = self.get_object()
        product_id = request.data.get("product_id")
        
        if not product_id:
            return Response(
                {"detail": "product_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"detail": "Target product not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        variant.product = target
        variant.save(update_fields=["product"])
        return Response(VariantSerializer(variant).data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=["post"], url_path="compare")
    def compare(self, request):
        """
        Compare multiple variants to find attribute differences.
        
        This is used to help users identify variation axes when grouping variants.
        
        Body: {
            "variant_ids": [1, 2, 3, 4, 5]
        }
        
        Returns: {
            "variants": [...],
            "differences": [
                {
                    "attribute_id": 10,
                    "attribute_code": "color",
                    "variant_values": {
                        "1": {"display": "red", ...},
                        "2": {"display": "blue", ...}
                    },
                    "unique_values": ["red", "blue"],
                    "is_candidate_axis": true
                }
            ],
            "common_attributes": [...]
        }
        """
        from catalog.services.variant_grouping import compare_variants
        
        variant_ids = request.data.get("variant_ids", [])
        
        if not isinstance(variant_ids, list) or len(variant_ids) < 2:
            return Response(
                {"detail": "variant_ids must be a list with at least 2 IDs"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = compare_variants(variant_ids)
        
        if "error" in result:
            return Response(
                {"detail": result["error"]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(result)
    
    @action(detail=False, methods=["post"], url_path="group-with-axes")
    def group_with_axes(self, request):
        """
        Group variants under a product and set variation axes for a channel.
        
        This is the all-in-one endpoint for manual grouping workflow:
        1. User selects variants
        2. User selects channel/marketplace
        3. User selects variation axes (from compare results)
        4. This endpoint creates/updates product and sets axes
        
        Body: {
            "variant_ids": [1, 2, 3],
            "channel_id": 5,
            "variation_axes": [
                {"attribute_id": 10, "position": 0},  # e.g., color
                {"attribute_id": 11, "position": 1}   # e.g., size
            ],
            "create_new_product": true,  # or false to use existing
            "product_code": "my-product-group",  # optional, for new product
            "product_type_id": 2,  # optional, for new product
            "target_product_id": 123  # required if create_new_product=false
        }
        
        Returns: {
            "product": {"id": 123, "code": "...", "created": true},
            "channel": {"id": 5, "code": "shopify"},
            "variants_grouped": 3,
            "axes": [...]
        }
        """
        from catalog.services.variant_grouping import group_variants_with_axes
        
        variant_ids = request.data.get("variant_ids", [])
        channel_id = request.data.get("channel_id")
        variation_axes = request.data.get("variation_axes", [])
        create_new_product = request.data.get("create_new_product", True)
        product_code = request.data.get("product_code")
        product_type_id = request.data.get("product_type_id")
        target_product_id = request.data.get("target_product_id")
        
        # Validation
        if not variant_ids or not isinstance(variant_ids, list):
            return Response(
                {"detail": "variant_ids must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not channel_id:
            return Response(
                {"detail": "channel_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not create_new_product and not target_product_id:
            return Response(
                {"detail": "target_product_id is required when create_new_product is false"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = group_variants_with_axes(
                variant_ids=variant_ids,
                channel_id=channel_id,
                variation_axes=variation_axes,
                product_code=product_code,
                product_type_id=product_type_id,
                create_new_product=create_new_product,
                target_product_id=target_product_id,
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": f"Error grouping variants: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], url_path="ungroup")
    def ungroup(self, request):
        """
        Ungroup variants by moving each to its own individual placeholder product.
        
        This is the opposite of grouping - it breaks apart a group so that each 
        variant becomes standalone again. Useful when you want to re-organize
        variants into different groups.
        
        Body: {
            "variant_ids": [1, 2, 3]
        }
        
        Returns: {
            "ungrouped_count": 3,
            "variants": [
                {
                    "id": 1,
                    "sku": "TSH-BLK-S",
                    "old_product_id": 10,
                    "old_product_code": "tshirt-group",
                    "new_product_id": 50,
                    "new_product_code": "variant-tsh-blk-s"
                },
                ...
            ],
            "orphaned_products_deleted": 1
        }
        """
        from catalog.services.variant_grouping import ungroup_variants
        
        variant_ids = request.data.get("variant_ids", [])
        
        if not variant_ids or not isinstance(variant_ids, list):
            return Response(
                {"detail": "variant_ids must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = ungroup_variants(variant_ids)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": f"Error ungrouping variants: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AttributeViewSet(viewsets.ModelViewSet):
    queryset = Attribute.objects.all().order_by("code")
    serializer_class = AttributeSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"], url_path="create-with-product-type")
    def create_with_product_type(self, request):
        """Create an Attribute and associate it with a ProductType in one call"""
        serializer = CreateAttributeWithProductTypeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response({
            "attribute": AttributeSerializer(result["attribute"]).data,
            "product_type_attribute": ProductTypeAttributeSerializer(result["product_type_attribute"]).data,
            "attribute_created": result["created"],
            "association_created": result["associated"],
        }, status=201)

    @action(detail=False, methods=["patch"], url_path="bulk-update")
    def bulk_update(self, request):
        """Bulk update attributes, primarily for toggling is_value_translatable"""
        attribute_ids = request.data.get("ids", [])
        updates = request.data.get("updates", {})

        if not attribute_ids:
            return Response({"error": "ids array is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not updates:
            return Response({"error": "updates object is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            updated_count = Attribute.objects.filter(id__in=attribute_ids).update(**updates)
            return Response({
                "updated_count": updated_count,
                "message": f"Successfully updated {updated_count} attribute(s)"
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AttributeValueViewSet(viewsets.ModelViewSet):
    queryset = AttributeValue.objects.select_related("attribute").order_by("attribute_id", "sort_order", "id")
    serializer_class = AttributeValueSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"], url_path="add-to-attribute")
    def add_to_attribute(self, request):
        """Add a new value to an existing enum attribute"""
        attribute_id = request.data.get("attribute_id")
        code = request.data.get("code")
        sort_order = request.data.get("sort_order", 0)

        if not attribute_id or not code:
            return Response(
                {"error": "attribute_id and code are required"},
                status=400
            )

        try:
            attribute = Attribute.objects.get(id=attribute_id)
            if attribute.data_type != Attribute.DataType.ENUM:
                return Response(
                    {"error": "Can only add values to enum attributes"},
                    status=400
                )

            # Create or get the attribute value
            attr_value, created = AttributeValue.objects.get_or_create(
                attribute=attribute,
                code=code,
                defaults={"sort_order": sort_order}
            )

            if not created:
                # Update sort_order if it changed
                if attr_value.sort_order != sort_order:
                    attr_value.sort_order = sort_order
                    attr_value.save(update_fields=["sort_order"])

            serializer = AttributeValueSerializer(attr_value)
            return Response(serializer.data, status=201 if created else 200)
        except Attribute.DoesNotExist:
            return Response({"error": "Attribute not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class TranslatableAttributesViewSet(viewsets.ReadOnlyModelViewSet):
    """List attributes that have translatable values"""
    queryset = Attribute.objects.filter(is_value_translatable=True).prefetch_related(
        "product_types__product_type"
    ).order_by("code")
    serializer_class = TranslatableAttributeSerializer
    permission_classes = [AllowAny]
    
    def list(self, request, *args, **kwargs):
        # #region agent log
        from core.debug_utils import DEBUG_LOG_PATH
        import json
        try:
            with open(DEBUG_LOG_PATH, 'a') as f:
                f.write(json.dumps({"id":"log_list_entry","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:619","message":"TranslatableAttributesViewSet.list entry","data":{"request_path":request.path},"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + '\n')
        except: pass
        # #endregion
        try:
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json.dumps({"id":"log_before_queryset","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:625","message":"Before queryset evaluation","data":{},"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + '\n')
            except: pass
            # #endregion
            queryset = self.filter_queryset(self.get_queryset())
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json.dumps({"id":"log_after_queryset","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:630","message":"After queryset evaluation","data":{"queryset_count":queryset.count()},"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + '\n')
            except: pass
            # #endregion
            page = self.paginate_queryset(queryset)
            if page is not None:
                # #region agent log
                try:
                    with open(DEBUG_LOG_PATH, 'a') as f:
                        f.write(json.dumps({"id":"log_before_serialize","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:636","message":"Before serialization","data":{"page_size":len(page) if page else 0},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + '\n')
                except: pass
                # #endregion
                serializer = self.get_serializer(page, many=True)
                # #region agent log
                try:
                    with open(DEBUG_LOG_PATH, 'a') as f:
                        f.write(json.dumps({"id":"log_after_serialize","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:641","message":"After serialization","data":{},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + '\n')
                except: pass
                # #endregion
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a') as f:
                    f.write(json.dumps({"id":"log_list_exception","timestamp":int(__import__('time').time()*1000),"location":"catalog.py:650","message":"Exception in list method","data":{"error_type":type(e).__name__,"error_message":str(e)},"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL"}) + '\n')
            except: pass
            # #endregion
            raise
