from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.serializers import (
    AttributeMappingSerializer,
    CategoryBatchSerializer,
    ImportRowSerializer,
    ProductImportSerializer,
)
from importer.models import AttributeMapping, CategoryBatch, ImportRow, ProductImport


class ProductImportViewSet(viewsets.ModelViewSet):
    queryset = ProductImport.objects.all().order_by("-id")
    serializer_class = ProductImportSerializer


class CategoryBatchViewSet(viewsets.ModelViewSet):
    queryset = CategoryBatch.objects.all().order_by("-id")
    serializer_class = CategoryBatchSerializer


class ImportUploadView(APIView):
    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "Missing file upload."}, status=status.HTTP_400_BAD_REQUEST)

        original_filename = file.name or ""
        file_type = original_filename.split(".")[-1].lower() if "." in original_filename else ""
        created_by = getattr(request.user, "username", "") if request.user and request.user.is_authenticated else ""

        product_import = ProductImport.objects.create(
            source_file=file,
            original_filename=original_filename,
            file_type=file_type,
            created_by=created_by,
        )
        serializer = ProductImportSerializer(product_import)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ImportPreviewView(APIView):
    def get(self, request, import_id: int):
        product_import = ProductImport.objects.get(id=import_id)
        rows = ImportRow.objects.filter(product_import=product_import).order_by("row_number")[:10]
        row_serializer = ImportRowSerializer(rows, many=True)
        response = {
            "import": ProductImportSerializer(product_import).data,
            "rows": row_serializer.data,
            "errors": product_import.error_count,
        }
        return Response(response, status=status.HTTP_200_OK)


class ImportAssignCategoryView(APIView):
    def post(self, request, import_id: int):
        product_import = ProductImport.objects.get(id=import_id)
        category = request.data.get("category")
        if not category:
            return Response({"detail": "category is required."}, status=status.HTTP_400_BAD_REQUEST)
        batch = CategoryBatch.objects.create(
            product_import=product_import,
            category=category,
            product_count=request.data.get("product_count", 0) or 0,
            variant_count=request.data.get("variant_count", 0) or 0,
        )
        return Response(CategoryBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


class ImportMapAttributesView(APIView):
    def post(self, request, import_id: int):
        mappings = request.data.get("mappings", [])
        category_batch_id = request.data.get("category_batch_id")
        if not category_batch_id:
            return Response({"detail": "category_batch_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        category_batch = CategoryBatch.objects.get(id=category_batch_id, product_import_id=import_id)
        results = []
        for mapping in mappings:
            serializer = AttributeMappingSerializer(data={**mapping, "category_batch_id": category_batch.id})
            serializer.is_valid(raise_exception=True)
            obj, _ = AttributeMapping.objects.update_or_create(
                category_batch=category_batch,
                source_attr_name=serializer.validated_data["source_attr_name"],
                defaults={
                    "target_attribute": serializer.validated_data.get("target_attribute"),
                    "strategy": serializer.validated_data["strategy"],
                    "notes": serializer.validated_data.get("notes", ""),
                    "confidence": serializer.validated_data.get("confidence"),
                },
            )
            results.append(AttributeMappingSerializer(obj).data)

        category_batch.status = CategoryBatch.Status.ATTR_MAPPED
        category_batch.save(update_fields=["status"])

        return Response({"mappings": results}, status=status.HTTP_200_OK)
