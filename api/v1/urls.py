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
router.register("channels", views.ChannelViewSet, basename="channels")
router.register("imports", views.ProductImportViewSet, basename="imports")
router.register("category-batches", views.CategoryBatchViewSet, basename="category-batches")
router.register("translation-tasks", views.TranslationTaskViewSet, basename="translation-tasks")
router.register("templates", views.TemplateViewSet, basename="templates")
router.register("template-parts", views.TemplatePartViewSet, basename="template-parts")
router.register("generation-runs", views.GenerationRunViewSet, basename="generation-runs")
router.register("content-sets", views.ContentSetViewSet, basename="content-sets")
router.register("generation-batches", views.GenerationBatchViewSet, basename="generation-batches")
router.register("export-profiles", views.ExportProfileViewSet, basename="export-profiles")
router.register("export-jobs", views.ExportJobViewSet, basename="export-jobs")
router.register("planner-runs", views.PlannerRunViewSet, basename="planner-runs")
router.register("planner-run-keywords", views.PlannerRunKeywordViewSet, basename="planner-run-keywords")
router.register("planner-seeds", views.PlannerSeedViewSet, basename="planner-seeds")
router.register("keywords", views.KeywordViewSet, basename="keywords")
router.register("metrics", views.MetricViewSet, basename="metrics")

urlpatterns = [
    path("imports/upload/", views.ImportUploadView.as_view(), name="import-upload"),
    path("imports/<int:import_id>/preview/", views.ImportPreviewView.as_view(), name="import-preview"),
    path("imports/<int:import_id>/assign-category/", views.ImportAssignCategoryView.as_view(), name="import-assign-category"),
    path("imports/<int:import_id>/map-attributes/", views.ImportMapAttributesView.as_view(), name="import-map-attributes"),
    path("translations/create-task/", views.TranslationTaskCreateView.as_view(), name="translation-task-create"),
    path("translations/tasks/<int:task_id>/", views.TranslationTaskDetailView.as_view(), name="translation-task-detail"),
    path(
        "translations/<str:locale_code>/products/<int:product_id>/",
        views.ProductTranslationView.as_view(),
        name="product-translation",
    ),
    path("keywords/planner-run/", views.KeywordPlannerRunCreateView.as_view(), name="keywords-planner-run"),
    path(
        "keywords/planner-run/<int:run_id>/",
        views.KeywordPlannerRunDetailView.as_view(),
        name="keywords-planner-run-detail",
    ),
    path(
        "keywords/planner-run/<int:run_id>/approve/",
        views.KeywordPlannerRunApproveView.as_view(),
        name="keywords-planner-run-approve",
    ),
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
