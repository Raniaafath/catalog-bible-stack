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
            for i18n in queryset:
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
                "count": len(items),
                "items": items,
                "truncated": False,
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


class ExportTranslationsView(APIView):
    """Export translated attribute values to Excel file."""
    
    def get(self, request, task_id: int):
        import os
        from datetime import datetime
        from collections import defaultdict
        from django.http import FileResponse
        
        try:
            from openpyxl import Workbook
        except ImportError:
            return Response(
                {"error": "openpyxl is required for Excel export"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Get the translation task
        try:
            task = TranslationTask.objects.get(id=task_id)
        except TranslationTask.DoesNotExist:
            return Response(
                {"error": f"Translation task {task_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get or create the locale
        try:
            locale = Locale.objects.get(code=task.locale)
        except Locale.DoesNotExist:
            return Response(
                {"error": f"Locale {task.locale} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get translatable attributes
        translatable_attrs = Attribute.objects.filter(
            is_value_translatable=True
        ).order_by("code")
        attr_codes = list(translatable_attrs.values_list("code", flat=True))
        attr_id_to_code = {a.id: a.code for a in translatable_attrs}
        
        # Get all translated ProductAttributeValues for this locale
        pav_i18n_qs = ProductAttributeValueI18n.objects.filter(
            locale=locale,
            product_attribute_value__attribute__in=translatable_attrs
        ).select_related(
            "product_attribute_value",
            "product_attribute_value__product",
            "product_attribute_value__variant",
            "product_attribute_value__attribute",
            "product_attribute_value__attribute_value",
        )
        
        # Also get the source PAVs to include products without translations
        pav_qs = ProductAttributeValue.objects.filter(
            attribute__in=translatable_attrs
        ).select_related(
            "product",
            "variant",
            "attribute",
            "attribute_value",
        )
        
        # Build a map of products/variants -> attribute -> translated value
        # Structure: { (product_id, variant_id): { attr_code: translated_value } }
        product_translations = defaultdict(dict)
        product_info = {}  # { (product_id, variant_id): (product_code, product_name, variant_sku) }
        
        # First, populate with source values
        for pav in pav_qs:
            product = pav.product
            variant = pav.variant
            
            # Determine the product/variant key
            if variant:
                key = (variant.product_id, variant.id)
                if key not in product_info:
                    product_info[key] = (
                        variant.product.code if variant.product else "",
                        variant.product.default_label if variant.product else "",
                        variant.internal_sku or variant.sku or "",
                    )
            elif product:
                key = (product.id, None)
                if key not in product_info:
                    product_info[key] = (product.code, product.default_label, "")
            else:
                continue
            
            # Get source value
            attr_code = attr_id_to_code.get(pav.attribute_id)
            if attr_code:
                if pav.value_text:
                    source_value = pav.value_text
                elif pav.attribute_value:
                    source_value = pav.attribute_value.code
                elif pav.value_number is not None:
                    source_value = str(pav.value_number)
                elif pav.value_bool is not None:
                    source_value = "Yes" if pav.value_bool else "No"
                else:
                    source_value = ""
                
                # Store as source (will be overwritten if translation exists)
                product_translations[key][attr_code] = source_value
        
        # Then, overlay with translated values
        for pav_i18n in pav_i18n_qs:
            pav = pav_i18n.product_attribute_value
            variant = pav.variant
            product = pav.product
            
            if variant:
                key = (variant.product_id, variant.id)
            elif product:
                key = (product.id, None)
            else:
                continue
            
            attr_code = attr_id_to_code.get(pav.attribute_id)
            if attr_code and pav_i18n.value_text:
                product_translations[key][attr_code] = pav_i18n.value_text
        
        # Create the Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = f"Translations {task.locale}"
        
        # Write header row
        headers = ["Product Code", "Product Name", "Variant SKU"] + attr_codes
        ws.append(headers)
        
        # Style the header row
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = cell.font.copy(bold=True)
        
        # Write data rows
        for key in sorted(product_info.keys()):
            product_code, product_name, variant_sku = product_info[key]
            translations = product_translations.get(key, {})
            
            row = [product_code, product_name, variant_sku]
            for attr_code in attr_codes:
                row.append(translations.get(attr_code, ""))
            
            ws.append(row)
        
        # Adjust column widths
        for col_num, header in enumerate(headers, 1):
            ws.column_dimensions[ws.cell(row=1, column=col_num).column_letter].width = max(15, len(header) + 2)
        
        # Save to file
        os.makedirs("exports", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"translations_{task.locale}_{timestamp}.xlsx"
        filepath = os.path.join("exports", filename)
        wb.save(filepath)
        
        # Return the file
        response = FileResponse(
            open(filepath, "rb"),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class ExportTranslatedProductsCsvView(APIView):
    """
    GET /translations/export-translated-products-csv/?locale_code=de-DE
    Returns CSV: locale, product_code, product_name, variant_sku, attribute_code, source_value, translated_value.
    """

    def get(self, request):
        import csv
        from io import StringIO
        from django.http import HttpResponse

        locale_code = request.query_params.get("locale_code")
        if not locale_code:
            return Response(
                {"detail": "locale_code query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            locale = Locale.objects.get(code=locale_code)
        except Locale.DoesNotExist:
            return Response(
                {"detail": f"Locale {locale_code} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        translatable_attrs = Attribute.objects.filter(is_value_translatable=True)
        qs = (
            ProductAttributeValueI18n.objects.filter(
                locale=locale,
                product_attribute_value__attribute__in=translatable_attrs,
            )
            .select_related(
                "product_attribute_value",
                "product_attribute_value__product",
                "product_attribute_value__variant",
                "product_attribute_value__attribute",
                "product_attribute_value__attribute_value",
            )
        )

        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "locale",
            "product_code",
            "product_name",
            "variant_sku",
            "attribute_code",
            "source_value",
            "translated_value",
        ])

        for pav_i18n in qs:
            pav = pav_i18n.product_attribute_value
            product = pav.product or (pav.variant.product if pav.variant else None)
            variant = pav.variant
            product_code = (product.code if product else "") or ""
            # Product has default_label, not name
            product_name = (getattr(product, "default_label", "") if product else "") or ""
            variant_sku = (variant.internal_sku or variant.sku if variant else "") or ""
            attr_code = (pav.attribute.code if pav.attribute else "") or ""
            if pav.value_text:
                source_value = pav.value_text
            elif pav.attribute_value:
                source_value = pav.attribute_value.code or ""
            elif pav.value_number is not None:
                source_value = str(pav.value_number)
            elif pav.value_bool is not None:
                source_value = "Yes" if pav.value_bool else "No"
            else:
                source_value = ""
            translated_value = (pav_i18n.value_text or "").strip()
            writer.writerow([
                locale_code,
                product_code,
                product_name,
                variant_sku,
                attr_code,
                source_value,
                translated_value,
            ])

        response = HttpResponse(buf.getvalue(), content_type="text/csv; charset=utf-8")
        safe_code = locale_code.replace("-", "_").replace(" ", "_")
        response["Content-Disposition"] = f'attachment; filename="translated_products_{safe_code}.csv"'
        return response
     return response
