from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.v1 import views


router = DefaultRouter()
router.register("locales", views.LocaleViewSet, basename="locales")
router.register("product-types", views.ProductTypeViewSet, basename="product-types")
router.register("products", views.ProductViewSet, basename="products")
router.register("variants", views.VariantViewSet, basename="variants")
router.register("attributes", views.AttributeViewSet, basename="attributes")
router.register("attribute-values", views.AttributeValueViewSet, basename="attribute-values")
router.register("templates", views.TemplateViewSet, basename="templates")
router.register("template-parts", views.TemplatePartViewSet, basename="template-parts")
router.register("generation-runs", views.GenerationRunViewSet, basename="generation-runs")
router.register("content-sets", views.ContentSetViewSet, basename="content-sets")
router.register("generation-batches", views.GenerationBatchViewSet, basename="generation-batches")
router.register("export-profiles", views.ExportProfileViewSet, basename="export-profiles")
router.register("export-jobs", views.ExportJobViewSet, basename="export-jobs")

urlpatterns = [
    path("titles/generate/", views.TitleGenerateView.as_view(), name="titles-generate"),
    path("titles/suggestions/", views.TitleSuggestionsView.as_view(), name="titles-suggestions"),
    path("content/preview/", views.ContentPreviewView.as_view(), name="content-preview"),
    path("content/generate/", views.ContentGenerateView.as_view(), name="content-generate"),
    path("content-sets/<int:set_id>/items/", views.ContentSetItemView.as_view(), name="content-set-items"),
    path(
        "content-sets/<int:set_id>/items/<int:item_id>/",
        views.ContentSetItemView.as_view(),
        name="content-set-item",
    ),
    path("generation-batches/create/", views.GenerationBatchCreateView.as_view(), name="generation-batch-create"),
    path(
        "generation-batches/<int:batch_id>/items/",
        views.GenerationBatchItemView.as_view(),
        name="generation-batch-items",
    ),
    path("exports/create/", views.ExportJobCreateView.as_view(), name="export-job-create"),
    path("", include(router.urls)),
]
