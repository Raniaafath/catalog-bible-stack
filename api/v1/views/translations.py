import logging
import threading

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.serializers import TranslationTaskSerializer
from api.v1.serializers.translations import (
    AttributeI18nSerializer,
    AttributeValueI18nSerializer,
    ProductTypeI18nSerializer,
)
from catalog.models import Attribute, AttributeValue, Product, ProductAttributeValue, ProductType
from content.models import (
    AttributeI18n,
    AttributeValueI18n,
    Locale,
    ProductAttributeValueI18n,
    ProductI18n,
    ProductTypeI18n,
    TranslationTask,
)
from content.services.translation_processor import process_translation_task

logger = logging.getLogger(__name__)


def _start_translation_in_background(task_id: int):
    """Start translation processing in a background thread."""
    def run_translation():
        try:
            logger.info(f"Starting background translation for task {task_id}")
            process_translation_task(task_id)
            logger.info(f"Background translation completed for task {task_id}")
        except Exception as e:
            logger.error(f"Background translation failed for task {task_id}: {e}")
    
    thread = threading.Thread(target=run_translation, daemon=True)
    thread.start()


class TranslationTaskViewSet(viewsets.ModelViewSet):
    queryset = TranslationTask.objects.all().order_by("-id")
    serializer_class = TranslationTaskSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a translation task and automatically start processing."""
        response = super().create(request, *args, **kwargs)
        
        # Start processing in background thread
        task_id = response.data.get("id")
        if task_id:
            _start_translation_in_background(task_id)
        
        return response
    
    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """Retry a failed translation task."""
        task = self.get_object()
        
        if task.status not in [TranslationTask.Status.FAILED, TranslationTask.Status.DONE]:
            return Response(
                {"error": "Can only retry failed or completed tasks"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset task status
        task.status = TranslationTask.Status.PENDING
        task.error = ""
        task.items_completed = 0
        task.started_at = None
        task.finished_at = None
        task.save()
        
        # Start processing in background
        _start_translation_in_background(task.id)
        
        return Response(TranslationTaskSerializer(task).data)
    
    @action(detail=True, methods=["get"])
    def results(self, request, pk=None):
        """Get the translated items for a task."""
        task = self.get_object()
        
        try:
            locale = Locale.objects.get(code=task.locale)
        except Locale.DoesNotExist:
            return Response(
                {"error": f"Locale {task.locale} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if task.scope == "attribute":
            # Get translated attribute names
            if task.target_ids:
                queryset = AttributeI18n.objects.filter(
                    attribute_id__in=task.target_ids,
                    locale=locale
                ).select_related("attribute")
            else:
                # All translatable attributes
                translatable_attrs = Attribute.objects.filter(is_value_translatable=True)
                queryset = AttributeI18n.objects.filter(
                    attribute__in=translatable_attrs,
                    locale=locale
                ).select_related("attribute")
            
            items = []
            for i18n in queryset:
                items.append({
                    "id": i18n.id,
                    "source_id": i18n.attribute_id,
                    "source_code": i18n.attribute.code,
                    "source_value": i18n.attribute.code,  # Original is the code
                    "translated_value": i18n.label,
                })
            
            return Response({
                "scope": task.scope,
                "locale": task.locale,
                "count": len(items),
                "items": items,
            })
        
        elif task.scope == "attribute_value":
            # Get translated attribute values
            if task.target_ids:
                queryset = AttributeValueI18n.objects.filter(
                    attribute_value_id__in=task.target_ids,
                    locale=locale
                ).select_related("attribute_value", "attribute_value__attribute")
            else:
                queryset = AttributeValueI18n.objects.filter(
                    locale=locale
                ).select_related("attribute_value", "attribute_value__attribute")
            
            items = []
            for i18n in queryset:
                items.append({
                    "id": i18n.id,
                    "source_id": i18n.attribute_value_id,
                    "source_code": i18n.attribute_value.code,
                    "attribute_code": i18n.attribute_value.attribute.code,
                    "source_value": i18n.attribute_value.code,
                    "translated_value": i18n.label,
                })
            
            return Response({
                "scope": task.scope,
                "locale": task.locale,
                "count": len(items),
                "items": items,
            })
        
        elif task.scope == "product_type":
            # Get translated product types
            if task.target_ids:
                queryset = ProductTypeI18n.objects.filter(
                    product_type_id__in=task.target_ids,
                    locale=locale
                ).select_related("product_type")
            else:
                queryset = ProductTypeI18n.objects.filter(
                    locale=locale
                ).select_related("product_type")
            
            items = []
            for i18n in queryset:
                items.append({
                    "id": i18n.id,
                    "source_id": i18n.product_type_id,
                    "source_code": i18n.product_type.code,
                    "source_value": i18n.product_type.default_label or i18n.product_type.code,
                    "translated_value": i18n.label,
                    "main_category": i18n.main_category,
                })
            
            return Response({
                "scope": task.scope,
                "locale": task.locale,
                "count": len(items),
                "items": items,
            })
        
        elif task.scope == "product_attribute_value":
            # Get translated product attribute values
            from catalog.models import ProductAttributeValue as PAV
            
            if task.target_ids:
                # target_ids are attribute IDs, not PAV IDs
                queryset = ProductAttributeValueI18n.objects.filter(
                    product_attribute_value__attribute_id__in=task.target_ids,
                    locale=locale
                ).select_related("product_attribute_value", "product_attribute_value__attribute")
            else:
                # All translatable attributes
                translatable_attrs = Attribute.objects.filter(is_value_translatable=True)
                queryset = ProductAttributeValueI18n.objects.filter(
                    product_attribute_value__attribute__in=translatable_attrs,
                    locale=locale
                ).select_related("product_attribute_value", "product_attribute_value__attribute")
            
            items = []
            for i18n in queryset[:100]:  # Limit to first 100 for performance
                pav = i18n.product_attribute_value
                source_value = pav.value_text or (pav.attribute_value.code if pav.attribute_value else "")
                items.append({
                    "id": i18n.id,
                    "source_id": pav.id,
                    "attribute_code": pav.attribute.code,
                    "source_value": source_value,
                    "translated_value": i18n.value_text,
                })
            
            return Response({
                "scope": task.scope,
                "locale": task.locale,
                "count": queryset.count(),
                "items": items,
                "truncated": queryset.count() > 100,
            })
        
        return Response(
            {"error": f"Unknown scope: {task.scope}"},
            status=status.HTTP_400_BAD_REQUEST
        )


class TranslationTaskCreateView(APIView):
    def post(self, request):
        serializer = TranslationTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = TranslationTask.objects.create(**serializer.validated_data)
        
        # Start processing in background thread
        _start_translation_in_background(task.id)
        
        return Response(TranslationTaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TranslationTaskDetailView(APIView):
    def get(self, request, task_id: int):
        task = TranslationTask.objects.get(id=task_id)
        return Response(TranslationTaskSerializer(task).data, status=status.HTTP_200_OK)


class UpdateTranslationView(APIView):
    """Update a single translation."""
    
    def patch(self, request, scope: str, translation_id: int):
        """
        Update a translation by scope and ID.
        
        Body: { "translated_value": "new value", "main_category": "optional for product_type" }
        """
        translated_value = request.data.get("translated_value")
        if translated_value is None:
            return Response(
                {"error": "translated_value is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if scope == "attribute":
                obj = AttributeI18n.objects.select_related("attribute").get(id=translation_id)
                obj.label = translated_value
                obj.save(update_fields=["label"])
                return Response({
                    "id": obj.id,
                    "source_id": obj.attribute_id,
                    "source_code": obj.attribute.code,
                    "source_value": obj.attribute.code,
                    "translated_value": obj.label,
                })
                
            elif scope == "attribute_value":
                obj = AttributeValueI18n.objects.select_related(
                    "attribute_value", "attribute_value__attribute"
                ).get(id=translation_id)
                obj.label = translated_value
                obj.save(update_fields=["label"])
                return Response({
                    "id": obj.id,
                    "source_id": obj.attribute_value_id,
                    "source_code": obj.attribute_value.code,
                    "attribute_code": obj.attribute_value.attribute.code,
                    "source_value": obj.attribute_value.code,
                    "translated_value": obj.label,
                })
                
            elif scope == "product_type":
                obj = ProductTypeI18n.objects.select_related("product_type").get(id=translation_id)
                obj.label = translated_value
                # Optionally update main_category if provided
                if "main_category" in request.data:
                    obj.main_category = request.data["main_category"]
                    obj.save(update_fields=["label", "main_category"])
                else:
                    obj.save(update_fields=["label"])
                return Response({
                    "id": obj.id,
                    "source_id": obj.product_type_id,
                    "source_code": obj.product_type.code,
                    "source_value": obj.product_type.default_label or obj.product_type.code,
                    "translated_value": obj.label,
                    "main_category": obj.main_category,
                })
                
            elif scope == "product_attribute_value":
                obj = ProductAttributeValueI18n.objects.select_related(
                    "product_attribute_value", "product_attribute_value__attribute"
                ).get(id=translation_id)
                obj.value_text = translated_value
                obj.save(update_fields=["value_text"])
                pav = obj.product_attribute_value
                source_value = pav.value_text or (pav.attribute_value.code if pav.attribute_value else "")
                return Response({
                    "id": obj.id,
                    "source_id": pav.id,
                    "attribute_code": pav.attribute.code,
                    "source_value": source_value,
                    "translated_value": obj.value_text,
                })
            else:
                return Response(
                    {"error": f"Unknown scope: {scope}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except (AttributeI18n.DoesNotExist, AttributeValueI18n.DoesNotExist, 
                ProductTypeI18n.DoesNotExist, ProductAttributeValueI18n.DoesNotExist):
            return Response(
                {"error": "Translation not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class TranslationStatusView(APIView):
    """Get counts of what needs translation for a given locale."""
    
    def get(self, request, locale_code: str):
        try:
            locale = Locale.objects.get(code=locale_code)
        except Locale.DoesNotExist:
            # Locale doesn't exist yet, so nothing is translated
            locale = None
        
        # Count translatable attributes
        translatable_attrs = Attribute.objects.filter(is_value_translatable=True)
        total_attributes = translatable_attrs.count()
        
        if locale:
            translated_attributes = AttributeI18n.objects.filter(
                attribute__in=translatable_attrs,
                locale=locale
            ).count()
        else:
            translated_attributes = 0
        
        # Count attribute values (enum options)
        total_attribute_values = AttributeValue.objects.count()
        if locale:
            translated_attribute_values = AttributeValueI18n.objects.filter(
                locale=locale
            ).count()
        else:
            translated_attribute_values = 0
        
        # Count product types
        total_product_types = ProductType.objects.count()
        if locale:
            translated_product_types = ProductTypeI18n.objects.filter(
                locale=locale
            ).count()
        else:
            translated_product_types = 0
        
        # Count product attribute values (only for translatable attributes)
        # Include both: text values (value_text) AND enum values (attribute_value FK)
        from django.db.models import Q
        from catalog.models import ProductAttributeValue as PAV
        
        # Count PAVs that have either a text value OR an enum value
        total_pav = PAV.objects.filter(
            attribute__in=translatable_attrs
        ).filter(
            Q(value_text__isnull=False) & ~Q(value_text='') |  # Has text value
            Q(attribute_value__isnull=False)  # Has enum value
        ).count()
        
        if locale:
            translated_pav = ProductAttributeValueI18n.objects.filter(
                product_attribute_value__attribute__in=translatable_attrs,
                locale=locale
            ).count()
        else:
            translated_pav = 0
        
        return Response({
            "locale": locale_code,
            "attributes": {
                "total": total_attributes,
                "translated": translated_attributes,
                "untranslated": total_attributes - translated_attributes,
            },
            "attribute_values": {
                "total": total_attribute_values,
                "translated": translated_attribute_values,
                "untranslated": total_attribute_values - translated_attribute_values,
            },
            "product_types": {
                "total": total_product_types,
                "translated": translated_product_types,
                "untranslated": total_product_types - translated_product_types,
            },
            "product_attribute_values": {
                "total": total_pav,
                "translated": translated_pav,
                "untranslated": total_pav - translated_pav,
            },
        })


class ProductTranslationView(APIView):
    def get(self, request, locale_code: str, product_id: int):
        locale = Locale.objects.get(code=locale_code)
        product = Product.objects.get(id=product_id)
        product_i18n, _ = ProductI18n.objects.get_or_create(product=product, locale=locale)

        pavs = ProductAttributeValue.objects.filter(product=product).select_related("attribute", "attribute_value")
        pav_i18n = ProductAttributeValueI18n.objects.filter(
            product_attribute_value__in=pavs,
            locale=locale,
        )
        pav_i18n_map = {item.product_attribute_value_id: item for item in pav_i18n}

        attributes = []
        for pav in pavs:
            i18n = pav_i18n_map.get(pav.id)
            if pav.attribute_value_id:
                source_value = pav.attribute_value.code
            elif pav.value_text is not None:
                source_value = pav.value_text
            elif pav.value_number is not None:
                source_value = str(pav.value_number)
            elif pav.value_bool is not None:
                source_value = str(pav.value_bool)
            else:
                source_value = ""
            attributes.append(
                {
                    "product_attribute_value_id": pav.id,
                    "attribute_id": pav.attribute_id,
                    "attribute_code": pav.attribute.code,
                    "source_value": source_value,
                    "translated_value": i18n.value_text if i18n else "",
                }
            )

        response = {
            "product_id": product.id,
            "locale": locale.code,
            "title": product_i18n.title,
            "description": product_i18n.description,
            "meta_title": product_i18n.meta_title,
            "meta_description": product_i18n.meta_description,
            "slug": product_i18n.slug,
            "attributes": attributes,
        }
        return Response(response, status=status.HTTP_200_OK)

    def patch(self, request, locale_code: str, product_id: int):
        locale = Locale.objects.get(code=locale_code)
        product = Product.objects.get(id=product_id)
        product_i18n, _ = ProductI18n.objects.get_or_create(product=product, locale=locale)

        for field in ["title", "description", "meta_title", "meta_description", "slug"]:
            if field in request.data:
                setattr(product_i18n, field, request.data[field] or "")
        product_i18n.save()

        for item in request.data.get("attribute_values", []):
            pav_id = item.get("product_attribute_value_id")
            if not pav_id:
                continue
            pav = ProductAttributeValue.objects.get(id=pav_id, product=product)
            value_text = item.get("value_text", "")
            pav_i18n, _ = ProductAttributeValueI18n.objects.get_or_create(
                product_attribute_value=pav,
                locale=locale,
            )
            pav_i18n.value_text = value_text
            pav_i18n.save()

        return Response({"updated": True}, status=status.HTTP_200_OK)
