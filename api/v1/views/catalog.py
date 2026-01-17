from rest_framework import viewsets

from api.v1.serializers import (
    AttributeSerializer,
    AttributeValueSerializer,
    ProductSerializer,
    ProductTypeSerializer,
    VariantSerializer,
)
from api.v1.views.mixins import IntegrityErrorTo409Mixin
from catalog.models import Attribute, AttributeValue, Product, ProductType, Variant


class ProductTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductType.objects.all().order_by("code")
    serializer_class = ProductTypeSerializer


class ProductViewSet(IntegrityErrorTo409Mixin, viewsets.ModelViewSet):
    queryset = Product.objects.select_related("product_type").order_by("-id")
    serializer_class = ProductSerializer


class VariantViewSet(IntegrityErrorTo409Mixin, viewsets.ModelViewSet):
    queryset = Variant.objects.select_related("product").order_by("-id")
    serializer_class = VariantSerializer


class AttributeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Attribute.objects.all().order_by("code")
    serializer_class = AttributeSerializer


class AttributeValueViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AttributeValue.objects.select_related("attribute").order_by("attribute_id", "sort_order", "id")
    serializer_class = AttributeValueSerializer
