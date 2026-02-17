from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.v1 import views


router = DefaultRouter()
router.register("locales", views.LocaleViewSet, basename="locales")
router.register("product-types", views.ProductTypeViewSet, basename="product-types")
router.register("products", views.ProductViewSet, basename="products")
router.register("variants", views.VariantViewSet, basename="variants")
router.register("attributes", views.AttributeViewSet, basename="attributes")
router.register("attributes-translatable", views.TranslatableAttributesViewSet, basename="attributes-translatable")
router.register("attribute-values", views.AttributeValueViewSet, basename="attribute-values")
router.register("channels", views.ChannelViewSet, basename="channels")
router.register("channel-policy-sets", views.ChannelPolicySetViewSet, basename="channel-policy-sets")
router.register("channel-locale-policies", views.ChannelLocalePolicyViewSet, basename="channel-locale-policies")
router.register("channel-listings", views.ChannelListingViewSet, basename="channel-listings")
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
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/signup/", views.SignupView.as_view(), name="auth-signup"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("imports/upload/", views.ImportUploadView.as_view(), name="import-upload"),
    path("imports/<int:import_id>/preview/", views.ImportPreviewView.as_view(), name="import-preview"),
    path("imports/<int:import_id>/assign-category/", views.ImportAssignCategoryView.as_view(), name="import-assign-category"),
    path("imports/<int:import_id>/map-attributes/", views.ImportMapAttributesView.as_view(), name="import-map-attributes"),
    path("imports/<int:import_id>/process/", views.ImportProcessView.as_view(), name="import-process"),
    path("translations/create-task/", views.TranslationTaskCreateView.as_view(), name="translation-task-create"),
    path("translations/tasks/<int:task_id>/", views.TranslationTaskDetailView.as_view(), name="translation-task-detail"),
    path(
        "translations/status/<str:locale_code>/",
        views.TranslationStatusView.as_view(),
        name="translation-status",
    ),
    path(
        "translations/<str:scope>/<int:translation_id>/",
        views.UpdateTranslationView.as_view(),
        name="update-translation",
    ),
    path(
        "translations/export/<int:task_id>/",
        views.ExportTranslationsView.as_view(),
        name="export-translations",
    ),
    path(
        "translations/export-translated-products-csv/",
        views.ExportTranslatedProductsCsvView.as_view(),
        name="export-translated-products-csv",
    ),
    path(
        "translations/<str:locale_code>/products/<int:product_id>/",
        views.ProductTranslationView.as_view(),
        name="product-translation",
    ),
    path("keywords/planner-run/", views.KeywordPlannerRunCreateView.as_view(), name="keywords-planner-run"),
    path(
        "keywords/planner-run/import-csv/",
        views.KeywordPlannerRunImportCsvView.as_view(),
        name="keywords-planner-run-import-csv",
    ),
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
    path(
        "keywords/planner-run/<int:run_id>/map/",
        views.KeywordPlannerRunMapView.as_view(),
        name="keywords-planner-run-map",
    ),
    path(
        "keywords/planner-run/<int:run_id>/mappings/",
        views.KeywordPlannerRunMappingsView.as_view(),
        name="keywords-planner-run-mappings",
    ),
    path(
        "keywords/planner-run/mappings/<int:attribute_map_id>/",
        views.KeywordPlannerRunMappingDetailView.as_view(),
        name="keywords-planner-run-mapping-detail",
    ),
    path(
        "keywords/planner-run/<int:run_id>/persist-mappings/",
        views.KeywordPlannerRunPersistMappingsView.as_view(),
        name="keywords-planner-run-persist-mappings",
    ),
    path(
        "keywords/planner-run/<int:run_id>/suggested-terms/",
        views.KeywordPlannerRunSuggestedTermsView.as_view(),
        name="keywords-planner-run-suggested-terms",
    ),
    path(
        "keywords/planner-run/<int:run_id>/product-maps/",
        views.KeywordPlannerRunProductMapsView.as_view(),
        name="keywords-planner-run-product-maps",
    ),
    path(
        "keywords/planner-run/<int:run_id>/product-maps/<int:map_id>/",
        views.KeywordPlannerRunProductMapDetailView.as_view(),
        name="keywords-planner-run-product-map-detail",
    ),
    path(
        "keywords/saved-terms/",
        views.SavedTermsView.as_view(),
        name="keywords-saved-terms",
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
    # Channel Listings (Groups) - custom actions
    path(
        "channel-listings/<int:listing_id>/move-variants/",
        views.ChannelListingMoveVariantsView.as_view(),
        name="channel-listing-move-variants",
    ),
    path(
        "channel-listings/<int:listing_id>/remove-variants/",
        views.ChannelListingRemoveVariantsView.as_view(),
        name="channel-listing-remove-variants",
    ),
    path(
        "channel-listings/<int:listing_id>/available-variants/",
        views.ChannelListingAvailableVariantsView.as_view(),
        name="channel-listing-available-variants",
    ),
    path(
        "channel-listings/<int:listing_id>/differences/",
        views.ChannelListingDifferencesView.as_view(),
        name="channel-listing-differences",
    ),
    path(
        "channel-listings/<int:listing_id>/axes/",
        views.ChannelListingAxesView.as_view(),
        name="channel-listing-axes",
    ),
    path(
        "channel-listings/<int:listing_id>/available-templates/",
        views.ChannelListingAvailableTemplatesView.as_view(),
        name="channel-listing-available-templates",
    ),
    path(
        "channel-listings/<int:listing_id>/create-default-template/",
        views.ChannelListingCreateDefaultTemplateView.as_view(),
        name="channel-listing-create-default-template",
    ),
    path(
        "channel-listings/<int:listing_id>/generate-titles/",
        views.ChannelListingGenerateTitlesView.as_view(),
        name="channel-listing-generate-titles",
    ),
    path(
        "channel-listings/<int:listing_id>/generated-titles/",
        views.ChannelListingGeneratedTitlesView.as_view(),
        name="channel-listing-generated-titles",
    ),
    path(
        "channel-listings/<int:listing_id>/generated-titles/<int:variant_id>/",
        views.ChannelListingGeneratedTitleUpdateView.as_view(),
        name="channel-listing-generated-title-update",
    ),
    path(
        "products/<int:product_id>/head-selection/",
        views.ProductHeadSelectionView.as_view(),
        name="product-head-selection",
    ),
    path(
        "variants/<int:variant_id>/attribute-details/",
        views.VariantAttributeDetailsView.as_view(),
        name="variant-attribute-details",
    ),
    path(
        "generated-titles/",
        views.AllGeneratedTitlesView.as_view(),
        name="all-generated-titles",
    ),
    path("", include(router.urls)),
]
