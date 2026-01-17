# Catalog Bible Stack (Django)

## Overview
- Django project with local apps `catalog`, `content`, `kw`, `pub`, and `rest_framework` enabled. (core/settings.py:L18-L32)
- Root routing includes `/admin/` and `/api/v1/`. (core/urls.py:L20-L23)

## Entrypoints
- `manage.py` sets `DJANGO_SETTINGS_MODULE=core.settings` and runs Django management commands. (manage.py:L7-L18)
- ASGI entrypoint is `core.asgi.application`. (core/asgi.py:L10-L16)
- WSGI entrypoint is `core.wsgi.application`. (core/wsgi.py:L10-L16)

## Settings and environment
- Environment variables are loaded via `python-dotenv` (`load_dotenv()`). (core/settings.py:L1-L6)
- Required env keys used in settings:
  - `DJANGO_SECRET_KEY`. (core/settings.py:L10-L10)
  - `DJANGO_DEBUG`. (core/settings.py:L11-L11)
  - `DJANGO_CSRF_TRUSTED_ORIGINS`. (core/settings.py:L14-L16)
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`. (core/settings.py:L66-L74)
  - `DEFAULT_LOCALE_CODE`. (core/settings.py:L90-L91)
- Database engine is PostgreSQL (`django.db.backends.postgresql`). (core/settings.py:L66-L69)
- Static files are collected to `staticfiles/` and served with WhiteNoise storage. (core/settings.py:L93-L98)
- REST framework defaults:
  - Auth classes: SessionAuthentication and BasicAuthentication. (core/settings.py:L102-L106)
  - Permissions: IsAdminUser. (core/settings.py:L107-L109)
  - Pagination: PageNumberPagination with `PAGE_SIZE=50`. (core/settings.py:L110-L111)
  - Filter backends: OrderingFilter, SearchFilter. (core/settings.py:L112-L115)

## Apps and models
- `catalog` models include `ProductType`, `Product`, `Variant`, `Attribute`, `AttributeValue`. (catalog/models.py:L6-L118)
- `content` models include `Locale`, `ProductI18n`, `ProductTypeI18n`, `ProductTypeSynonym`, `AttributeValueSynonym`, `TranslationTask`. (content/models.py:L7-L255)
- `kw` models include `Keyword`, `PlannerSeed`, `PlannerRun`, `PlannerRunKeyword`, `Metric`, `AttributeMap`, `Candidate`. (kw/models.py:L28-L458)
- `pub` models include `Channel`, `Template`, `TemplatePart`, `GenerationRun`, `GenerationOutput`, `Approval`, `ContentSet`, `ExportProfile`, `ExportJob`. (pub/models.py:L4-L795)

## API routing
Base prefix: `/api/v1/` from root URL config. (core/urls.py:L20-L23)

Router endpoints:
- `locales` -> `LocaleViewSet` (ReadOnlyModelViewSet). (api/v1/urls.py:L7-L13, api/v1/views/content.py:L7-L9)
- `product-types` -> `ProductTypeViewSet` (ReadOnlyModelViewSet). (api/v1/urls.py:L8-L10, api/v1/views/catalog.py:L14-L16)
- `products` -> `ProductViewSet` (ModelViewSet). (api/v1/urls.py:L9-L11, api/v1/views/catalog.py:L19-L22)
- `variants` -> `VariantViewSet` (ModelViewSet). (api/v1/urls.py:L10-L12, api/v1/views/catalog.py:L24-L26)
- `attributes` -> `AttributeViewSet` (ReadOnlyModelViewSet). (api/v1/urls.py:L11-L13, api/v1/views/catalog.py:L29-L31)
- `attribute-values` -> `AttributeValueViewSet` (ReadOnlyModelViewSet). (api/v1/urls.py:L12-L13, api/v1/views/catalog.py:L34-L36)
- `templates` -> `TemplateViewSet` (ModelViewSet). (api/v1/urls.py:L14-L15, api/v1/views/pub.py:L46-L49)
- `template-parts` -> `TemplatePartViewSet` (ModelViewSet). (api/v1/urls.py:L15-L15, api/v1/views/pub.py:L51-L54)
- `generation-runs` -> `GenerationRunViewSet` (ReadOnlyModelViewSet). (api/v1/urls.py:L16-L16, api/v1/views/pub.py:L56-L64)
- `content-sets` -> `ContentSetViewSet` (ModelViewSet). (api/v1/urls.py:L17-L17, api/v1/views/pub.py:L67-L70)
- `generation-batches` -> `GenerationBatchViewSet` (ReadOnlyModelViewSet). (api/v1/urls.py:L18-L18, api/v1/views/pub.py:L72-L75)
- `export-profiles` -> `ExportProfileViewSet` (ModelViewSet). (api/v1/urls.py:L19-L19, api/v1/views/pub.py:L77-L80)
- `export-jobs` -> `ExportJobViewSet` (ReadOnlyModelViewSet). (api/v1/urls.py:L20-L20, api/v1/views/pub.py:L82-L85)

Non-router endpoints and methods:
- `POST titles/generate/` -> `TitleGenerateView.post`. (api/v1/urls.py:L23-L24, api/v1/views/pub.py:L87-L89)
- `GET titles/suggestions/` -> `TitleSuggestionsView.get`. (api/v1/urls.py:L24-L24, api/v1/views/pub.py:L265-L267)
- `POST content/preview/` -> `ContentPreviewView.post`. (api/v1/urls.py:L25-L25, api/v1/views/pub.py:L127-L129)
- `POST content/generate/` -> `ContentGenerateView.post`. (api/v1/urls.py:L26-L26, api/v1/views/pub.py:L151-L153)
- `POST content-sets/<set_id>/items/` -> `ContentSetItemView.post`. (api/v1/urls.py:L27-L31, api/v1/views/pub.py:L198-L201)
- `DELETE content-sets/<set_id>/items/<item_id>/` -> `ContentSetItemView.delete`. (api/v1/urls.py:L28-L31, api/v1/views/pub.py:L210-L212)
- `POST generation-batches/create/` -> `GenerationBatchCreateView.post`. (api/v1/urls.py:L33-L33, api/v1/views/pub.py:L215-L218)
- `GET generation-batches/<batch_id>/items/` -> `GenerationBatchItemView.get`. (api/v1/urls.py:L35-L37, api/v1/views/pub.py:L245-L248)
- `POST exports/create/` -> `ExportJobCreateView.post`. (api/v1/urls.py:L39-L39, api/v1/views/pub.py:L252-L255)

## Management commands
Command modules present:
- `core/management/commands/run_pipeline.py`. (core/management/commands/run_pipeline.py:L15-L15)
- `content/management/commands/enqueue_missing_translations.py`. (content/management/commands/enqueue_missing_translations.py:L14-L14)
- `content/management/commands/run_translation_tasks.py`. (content/management/commands/run_translation_tasks.py:L19-L19)
- `content/management/commands/seed_minimal_reference.py`. (content/management/commands/seed_minimal_reference.py:L23-L23)
- `content/management/commands/translate_product_attribute_values.py`. (content/management/commands/translate_product_attribute_values.py:L13-L13)
- `kw/management/commands/refresh_planner_seeds.py`. (kw/management/commands/refresh_planner_seeds.py:L11-L11)
- `kw/management/commands/fetch_keyword_ideas.py`. (kw/management/commands/fetch_keyword_ideas.py:L22-L22)
- `kw/management/commands/kw_import_ads_keywords.py`. (kw/management/commands/kw_import_ads_keywords.py:L13-L13)
- `kw/management/commands/kw_classify_rules.py`. (kw/management/commands/kw_classify_rules.py:L12-L12)
- `kw/management/commands/kw_refresh_value_synonyms.py`. (kw/management/commands/kw_refresh_value_synonyms.py:L8-L8)
- `kw/management/commands/map_keywords.py`. (kw/management/commands/map_keywords.py:L365-L365)
- `kw/management/commands/parse_keywords.py`. (kw/management/commands/parse_keywords.py:L138-L138)
- `kw/management/commands/select_candidates.py`. (kw/management/commands/select_candidates.py:L19-L19)
- `kw/management/commands/select_head_candidates.py`. (kw/management/commands/select_head_candidates.py:L50-L50)
- `kw/management/commands/promote_am_synonyms.py`. (kw/management/commands/promote_am_synonyms.py:L280-L280)
- `kw/management/commands/add_pt_synonym.py`. (kw/management/commands/add_pt_synonym.py:L10-L10)
- `kw/management/commands/persist_product_keyword_maps.py`. (kw/management/commands/persist_product_keyword_maps.py:L16-L16)
- `pub/management/commands/generate_titles.py`. (pub/management/commands/generate_titles.py:L11-L11)
- `pub/management/commands/import_export_products_xlsx.py`. (pub/management/commands/import_export_products_xlsx.py:L50-L50)
- `pub/management/commands/export_translated_titles.py`. (pub/management/commands/export_translated_titles.py:L14-L14)
- `pub/management/commands/clone_title_template_locale.py`. (pub/management/commands/clone_title_template_locale.py:L8-L8)
- `pub/management/commands/seed_fr_sample_titles.py`. (pub/management/commands/seed_fr_sample_titles.py:L22-L22)

## Tests
- Test modules present at `catalog/tests.py` and `pub/tests/test_title_policies.py`. (catalog/tests.py:L1-L3, pub/tests/test_title_policies.py:L1-L91)

## Docker
- Dockerfile installs system deps and Python requirements and copies the app to `/app`. (Dockerfile:L1-L9)
- Entrypoint waits for Postgres, runs `migrate` and `collectstatic`, then starts Gunicorn (`core.wsgi:application`). (entrypoint.sh:L4-L11)
