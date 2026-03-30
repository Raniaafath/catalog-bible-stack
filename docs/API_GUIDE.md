# API Guide (evidence-based)

## Base routing
- Root routes include `/api/v1/` and `/admin/`. (core/urls.py:L20-L23)
- API routes are defined in `api/v1/urls.py`.

## Authentication and permissions
- REST framework auth classes: TokenAuthentication, SessionAuthentication, BasicAuthentication. (core/settings.py:L137-L141)
- Default permissions: IsAdminUser. (core/settings.py:L142-L144)
- Token auth: include `Authorization: Token <token>` header. Obtain token via `POST auth/login/`.

## Auth endpoints
- `POST auth/login/` → `LoginView` — returns `{ token, user_id }`.
- `POST auth/signup/` → `SignupView`
- `POST auth/logout/` → `LogoutView`
- `GET  auth/me/` → `MeView` — current user info.

## Router registrations (DefaultRouter)
All produce standard list/detail/create/update/delete endpoints at `/api/v1/<prefix>/`.

| Prefix | ViewSet | Notes |
|--------|---------|-------|
| `locales` | `LocaleViewSet` | Read-only |
| `product-types` | `ProductTypeViewSet` | Read-only |
| `products` | `ProductViewSet` | Full CRUD |
| `variants` | `VariantViewSet` | Full CRUD |
| `attributes` | `AttributeViewSet` | Read-only |
| `attributes-translatable` | `TranslatableAttributesViewSet` | Attributes with `is_value_translatable=True` |
| `attribute-values` | `AttributeValueViewSet` | Read-only |
| `channels` | `ChannelViewSet` | Full CRUD |
| `channel-policy-sets` | `ChannelPolicySetViewSet` | |
| `channel-locale-policies` | `ChannelLocalePolicyViewSet` | |
| `channel-listings` | `ChannelListingViewSet` | Listing groups |
| `imports` | `ProductImportViewSet` | |
| `category-batches` | `CategoryBatchViewSet` | |
| `translation-tasks` | `TranslationTaskViewSet` | |
| `templates` | `TemplateViewSet` | Full CRUD |
| `template-parts` | `TemplatePartViewSet` | Full CRUD |
| `generation-runs` | `GenerationRunViewSet` | Read-only |
| `content-sets` | `ContentSetViewSet` | Full CRUD |
| `generation-batches` | `GenerationBatchViewSet` | Read-only |
| `export-profiles` | `ExportProfileViewSet` | Full CRUD |
| `export-jobs` | `ExportJobViewSet` | Read-only |
| `planner-runs` | `PlannerRunViewSet` | |
| `planner-run-keywords` | `PlannerRunKeywordViewSet` | |
| `planner-seeds` | `PlannerSeedViewSet` | |
| `keywords` | `KeywordViewSet` | |
| `metrics` | `MetricViewSet` | |

## Non-router endpoints

### Import workflow
- `POST imports/upload/` → `ImportUploadView` — upload CSV/Excel, returns import_id.
- `GET  imports/<import_id>/preview/` → `ImportPreviewView` — parsed rows preview.
- `POST imports/<import_id>/assign-category/` → `ImportAssignCategoryView`
- `POST imports/<import_id>/map-attributes/` → `ImportMapAttributesView`
- `POST imports/<import_id>/process/` → `ImportProcessView` — execute import.

### Translation workflow
- `POST translations/create-task/` → `TranslationTaskCreateView`
- `GET  translations/tasks/<task_id>/` → `TranslationTaskDetailView`
- `GET  translations/status/<locale_code>/` → `TranslationStatusView`
- `PATCH translations/<scope>/<translation_id>/` → `UpdateTranslationView`
- `GET  translations/export/<task_id>/` → `ExportTranslationsView`
- `GET  translations/export-translated-products-csv/` → `ExportTranslatedProductsCsvView`
- `GET  translations/export-titles-and-attributes-csv/` → `ExportTitlesAndTranslatedAttributesCsvView`
- `GET  translations/export-products-one-row-csv/` → `ExportProductsOneRowCsvView`
- `GET/PATCH translations/<locale_code>/products/<product_id>/` → `ProductTranslationView`

### Keyword research workflow
- `POST keywords/planner-run/` → `KeywordPlannerRunCreateView`
- `POST keywords/planner-run/import-csv/` → `KeywordPlannerRunImportCsvView`
- `GET  keywords/planner-run/<run_id>/` → `KeywordPlannerRunDetailView`
- `POST keywords/planner-run/<run_id>/approve/` → `KeywordPlannerRunApproveView`
- `POST keywords/planner-run/<run_id>/map/` → `KeywordPlannerRunMapView` — rules-based attribute mapping
- `GET  keywords/planner-run/<run_id>/mappings/` → `KeywordPlannerRunMappingsView`
- `GET/PATCH keywords/planner-run/mappings/<attribute_map_id>/` → `KeywordPlannerRunMappingDetailView`
- `POST keywords/planner-run/<run_id>/persist-mappings/` → `KeywordPlannerRunPersistMappingsView`
- `GET  keywords/planner-run/<run_id>/suggested-terms/` → `KeywordPlannerRunSuggestedTermsView`
- `GET  keywords/planner-run/<run_id>/product-maps/` → `KeywordPlannerRunProductMapsView`
- `GET/PATCH keywords/planner-run/<run_id>/product-maps/<map_id>/` → `KeywordPlannerRunProductMapDetailView`
- `GET  keywords/saved-terms/` → `SavedTermsView`

#### `GET keywords/planner-run/<run_id>/suggested-terms/` — query params

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `product_id` | int | — | Filter terms for a specific product |
| `use_ai_meaning` | `1`/`true` | off | Add an AI-generated meaning/explanation for each keyword |
| `use_ai_reason` | `1`/`true` | off | Add an AI-generated reason explaining *why* each term was classified as head or hook |

Response shape (per term):
```json
{
  "keyword": "table basse 120 cm",
  "vol": 1900,
  "source": "pav_text_llm",
  "reason": "Matches the product depth attribute (profondeur=120cm) found in keyword phrase",
  "meaning": "Low coffee table with 120 cm length, common search for living-room furniture"
}
```

#### `POST keywords/planner-run/<run_id>/persist-mappings/` — body params

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `use_llm` | bool | `false` | Run AI (LLM) product-keyword mapping in addition to rules |
| `skip_enum_maps` | bool | `true` | Skip rules-based enum mapping (recommended when `use_llm=true`) |
| `focus_head_terms` | bool | `false` | Bias AI to prioritise head-term keywords |
| `focus_hook_terms` | bool | `false` | Bias AI to prioritise hook/long-tail keywords |
| `focus_on` | string | — | Free-text instruction to focus AI on specific attributes or aspects |
| `ignore` | string | — | Free-text instruction telling AI to ignore certain attributes |
| `ignore_size_and_marketplace` | bool | `false` | Skip dimension and marketplace-name attributes entirely |
| `llm_model` | string | `gpt-4o-mini` | AI model to use (`gpt-4o`, `claude-sonnet-4-6`, `gemini-2.0-flash`, …) |
| `product_id` | int | — | Limit mapping to a single product |
| `min_confidence` | float | — | Minimum confidence threshold for a match to be saved |

**AI vs rules behaviour:** When `use_llm=true`, AI results (source `pav_text_llm`) automatically overwrite any existing rules-based rows (source `enum_map`) for the same `(product, keyword, run)`. Rules-based rows for keywords not handled by AI are kept as a fallback.

### Title and content generation
- `POST titles/generate/` → `TitleGenerateView`
- `GET  titles/suggestions/` → `TitleSuggestionsView`
- `POST content/preview/` → `ContentPreviewView` — preview generated content per variant.
- `POST content/save-selection/` → `ContentSaveSelectionView`
- `POST content/generate/` → `ContentGenerateView`

### Content sets
- `POST   content-sets/<set_id>/items/` → `ContentSetItemView.post`
- `DELETE content-sets/<set_id>/items/<item_id>/` → `ContentSetItemView.delete`

### Generation batches
- `POST generation-batches/create/` → `GenerationBatchCreateView`
- `GET  generation-batches/<batch_id>/items/` → `GenerationBatchItemView`

### Exports
- `POST exports/create/` → `ExportJobCreateView`

### Channel listings (listing groups) — custom actions
- `POST channel-listings/<listing_id>/move-variants/` → `ChannelListingMoveVariantsView`
- `POST channel-listings/<listing_id>/remove-variants/` → `ChannelListingRemoveVariantsView`
- `GET  channel-listings/<listing_id>/available-variants/` → `ChannelListingAvailableVariantsView`
- `GET  channel-listings/<listing_id>/differences/` → `ChannelListingDifferencesView`
- `GET/POST channel-listings/<listing_id>/axes/` → `ChannelListingAxesView`
- `GET  channel-listings/<listing_id>/available-templates/` → `ChannelListingAvailableTemplatesView`
- `POST channel-listings/<listing_id>/create-default-template/` → `ChannelListingCreateDefaultTemplateView`
- `POST channel-listings/<listing_id>/generate-titles/` → `ChannelListingGenerateTitlesView`
- `GET  channel-listings/<listing_id>/generated-titles/` → `ChannelListingGeneratedTitlesView`
- `PATCH channel-listings/<listing_id>/generated-titles/<variant_id>/` → `ChannelListingGeneratedTitleUpdateView`

#### `GET keywords/planner-run/<run_id>/propose-template/` — query params

Returns attributes ordered by total mapped keyword search volume, optionally reordered by AI with per-attribute reasons in the run's locale language.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `top` | int | `8` | Max number of attributes to return |
| `use_ai` | `1`/`true` | off | Ask AI to semantically reorder attributes and add a reason per attribute (in the run's locale language) |

Response shape:
```json
{
  "run_id": 12,
  "source": "volume",
  "proposed": [
    {
      "attribute_id": 5,
      "attribute_code": "couleur",
      "total_vol": 45000,
      "keyword_count": 12,
      "reason": null
    }
  ]
}
```

When `use_ai=true`, `source` becomes `"ai"` and each item includes a `reason` string in the run's locale language explaining the ordering decision.

### Miscellaneous
- `GET  products/<product_id>/head-selection/` → `ProductHeadSelectionView`
- `GET  variants/<variant_id>/attribute-details/` → `VariantAttributeDetailsView`
- `GET  generated-titles/` → `AllGeneratedTitlesView`
