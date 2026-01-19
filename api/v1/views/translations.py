from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.serializers import TranslationTaskSerializer
from catalog.models import Product, ProductAttributeValue
from content.models import Locale, ProductAttributeValueI18n, ProductI18n, TranslationTask


class TranslationTaskViewSet(viewsets.ModelViewSet):
    queryset = TranslationTask.objects.all().order_by("-id")
    serializer_class = TranslationTaskSerializer


class TranslationTaskCreateView(APIView):
    def post(self, request):
        serializer = TranslationTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = TranslationTask.objects.create(**serializer.validated_data)
        return Response(TranslationTaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TranslationTaskDetailView(APIView):
    def get(self, request, task_id: int):
        task = TranslationTask.objects.get(id=task_id)
        return Response(TranslationTaskSerializer(task).data, status=status.HTTP_200_OK)


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
