import logging

from django.utils.text import slugify
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.serializers import (
    AttributeMappingSerializer,
    CategoryBatchSerializer,
    ImportRowSerializer,
    ProductImportSerializer,
)
from catalog.models import Attribute
from importer.models import AttributeMapping, CategoryBatch, ImportRow, ProductImport
from importer.services import parse_import

logger = logging.getLogger(__name__)


class ProductImportViewSet(viewsets.ModelViewSet):
    queryset = ProductImport.objects.all().order_by("-id")
    serializer_class = ProductImportSerializer


class CategoryBatchViewSet(viewsets.ModelViewSet):
    queryset = CategoryBatch.objects.all().order_by("-id")
    serializer_class = CategoryBatchSerializer


class ImportUploadView(APIView):
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        file = request.FILES.get("file") or request.FILES.get("source_file")
        if not file:
            return Response({"detail": "Missing file upload."}, status=status.HTTP_400_BAD_REQUEST)

        original_filename = file.name or ""
        file_type = original_filename.split(".")[-1].lower() if "." in original_filename else ""
        created_by = getattr(request.user, "username", "") if request.user and request.user.is_authenticated else ""
        
        # Get group_by_product_key from form data
        group_by_product_key = request.data.get("group_by_product_key", "false").lower() in ("true", "1", "yes")

        logger.info(f"Uploading file: {original_filename} (type: {file_type}, size: {file.size} bytes)")

        product_import = ProductImport.objects.create(
            source_file=file,
            original_filename=original_filename,
            file_type=file_type,
            created_by=created_by,
            group_by_product_key=group_by_product_key,
        )
        
        logger.info(f"Created ProductImport {product_import.id}, starting parse...")
        
        try:
            result = parse_import(product_import.id)
            logger.info(f"Parse completed for import {product_import.id}: {result.total} rows, {result.ok} ok, {result.errors} errors")
        except Exception as exc:
            logger.error(f"Parse failed for import {product_import.id}: {exc}", exc_info=True)
            error_message = str(exc)
            ProductImport.objects.filter(id=product_import.id).update(
                status=ProductImport.Status.FAILED,
                parse_error_message=error_message,
            )
            return Response(
                {"detail": f"Failed to parse import: {error_message}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Refresh from database to get updated status
        product_import.refresh_from_db()
        serializer = ProductImportSerializer(product_import)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ImportPreviewView(APIView):
    def get(self, request, import_id: int):
        product_import = ProductImport.objects.get(id=import_id)
        rows = ImportRow.objects.filter(product_import=product_import).order_by("row_number")[:10]
        row_serializer = ImportRowSerializer(rows, many=True)
        column_map = getattr(product_import, "column_map", None)
        columns = []
        if column_map:
            columns = list(column_map.mapping_json.get("columns", []))
        response = {
            "import": ProductImportSerializer(product_import).data,
            "rows": row_serializer.data,
            "errors": product_import.error_count,
            "columns": columns,
        }
        return Response(response, status=status.HTTP_200_OK)


class ImportAssignCategoryView(APIView):
    def post(self, request, import_id: int):
        product_import = ProductImport.objects.get(id=import_id)
        category = request.data.get("category")
        if not category:
            return Response({"detail": "category is required."}, status=status.HTTP_400_BAD_REQUEST)
        # Store category directly on the import so process_import can use it without a join.
        product_import.category = category
        product_import.save(update_fields=["category"])
        batch = CategoryBatch.objects.create(
            product_import=product_import,
            category=category,
            product_count=request.data.get("product_count", 0) or 0,
            variant_count=request.data.get("variant_count", 0) or 0,
        )
        return Response(CategoryBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


class ImportMapAttributesView(APIView):
    def post(self, request, import_id: int):
        from importer.models import ImportColumnRule

        mappings = request.data.get("mappings", [])
        category_batch_id = request.data.get("category_batch_id")
        if not category_batch_id:
            return Response({"detail": "category_batch_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            category_batch = CategoryBatch.objects.get(
                id=category_batch_id, product_import_id=import_id
            )
        except CategoryBatch.DoesNotExist:
            return Response(
                {
                    "detail": "Import or category batch not found. It may have been deleted. Start a new import."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        product_import = category_batch.product_import
        results = []

        for mapping in mappings:
            serializer = AttributeMappingSerializer(data={**mapping, "category_batch_id": category_batch.id})
            serializer.is_valid(raise_exception=True)
            target_attribute = serializer.validated_data.get("target_attribute")
            strategy = serializer.validated_data["strategy"]
            source_attr_name = serializer.validated_data["source_attr_name"]
            
            # Extract role and field mapping from the mapping data
            role = mapping.get("role")  # e.g., "PRODUCT_KEY", "VARIANT_KEY", "ATTRIBUTE"
            field_mapping = mapping.get("field_mapping")  # e.g., "variant.sku", "product.brand", "PRODUCT_KEY"
            variant_level = mapping.get("variant_level", False)
            is_variation_axis = mapping.get("is_variation_axis", False)

            if strategy == AttributeMapping.Strategy.CREATED and target_attribute is None:
                source_name = source_attr_name or ""
                base_code = slugify(source_name) or "attribute"
                data_type = mapping.get("data_type")
                if data_type not in {choice[0] for choice in Attribute.DataType.choices}:
                    data_type = Attribute.DataType.TEXT
                code = base_code
                suffix = 2
                while Attribute.objects.filter(code=code).exists():
                    code = f"{base_code}-{suffix}"
                    suffix += 1
                target_attribute, _ = Attribute.objects.get_or_create(
                    code=code,
                    defaults={"data_type": data_type},
                )

            obj, _ = AttributeMapping.objects.update_or_create(
                category_batch=category_batch,
                source_attr_name=source_attr_name,
                defaults={
                    "target_attribute": target_attribute,
                    "strategy": strategy,
                    "notes": serializer.validated_data.get("notes", ""),
                    "confidence": serializer.validated_data.get("confidence"),
                },
            )
            results.append(AttributeMappingSerializer(obj).data)
            
            # Update ImportColumnRule with role and other settings
            # Determine the role based on field_mapping or explicit role
            column_role = ImportColumnRule.Role.ATTRIBUTE
            if role:
                # Use explicit role if provided
                if role in {choice[0] for choice in ImportColumnRule.Role.choices}:
                    column_role = role
            elif field_mapping:
                # Infer role from field mapping
                if field_mapping == "PRODUCT_KEY":
                    column_role = ImportColumnRule.Role.PRODUCT_KEY
                elif field_mapping == "variant.sku":
                    column_role = ImportColumnRule.Role.VARIANT_KEY
                elif field_mapping.startswith("product."):
                    # Product-level fields
                    field_name = field_mapping.split(".", 1)[1]
                    if field_name == "brand":
                        column_role = ImportColumnRule.Role.BRAND
                    elif field_name == "default_label":
                        column_role = ImportColumnRule.Role.TITLE
                    elif field_name == "model":
                        column_role = ImportColumnRule.Role.PRODUCT_MODEL
                    elif field_name == "series":
                        column_role = ImportColumnRule.Role.PRODUCT_SERIES
                    elif field_name == "code":
                        column_role = ImportColumnRule.Role.PRODUCT_CODE
                elif field_mapping.startswith("variant."):
                    # Variant-level fields
                    field_name = field_mapping.split(".", 1)[1]
                    if field_name == "source_title":
                        column_role = ImportColumnRule.Role.TITLE
                    elif field_name == "source_description":
                        column_role = ImportColumnRule.Role.DESCRIPTION
                    elif field_name == "barcode":
                        column_role = ImportColumnRule.Role.BARCODE
                    elif field_name == "mpn":
                        column_role = ImportColumnRule.Role.MPN
                    elif field_name == "source_sku":
                        column_role = ImportColumnRule.Role.SOURCE_SKU
                    elif field_name == "source_supplier":
                        column_role = ImportColumnRule.Role.SOURCE_SUPPLIER
                    elif field_name == "source_locale":
                        column_role = ImportColumnRule.Role.SOURCE_LOCALE
                    else:
                        # Other variant fields treated as attributes
                        column_role = ImportColumnRule.Role.ATTRIBUTE
                        variant_level = True
            
            # Update or create ImportColumnRule
            # Only set variant_level and is_variation_axis for attributes, not for field mappings
            rule_defaults = {
                "role": column_role,
                "target_attribute_code": target_attribute.code if target_attribute else "",
                "create_attribute_name": source_attr_name if strategy == AttributeMapping.Strategy.CREATED else "",
            }
            
            # Only set variant_level and is_variation_axis if this is an attribute (not a field mapping)
            if column_role == ImportColumnRule.Role.ATTRIBUTE and target_attribute:
                rule_defaults["variant_level"] = variant_level
                rule_defaults["is_variation_axis"] = is_variation_axis
            
            column_rule, _ = ImportColumnRule.objects.update_or_create(
                product_import=product_import,
                column_name=source_attr_name,
                defaults=rule_defaults
            )

        category_batch.status = CategoryBatch.Status.ATTR_MAPPED
        category_batch.save(update_fields=["status"])

        return Response({"mappings": results}, status=status.HTTP_200_OK)


class ImportProcessView(APIView):
    def post(self, request, import_id: int):
        from importer.services import process_import
        import traceback
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"Starting import processing for import_id={import_id}")
            stats = process_import(import_id)
            logger.info(f"Import processing completed successfully: {stats}")
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Import processing failed: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
