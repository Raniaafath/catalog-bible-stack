# Catalog Bible Stack (Django)

## Overview
- Django project with apps `catalog`, `content`, `kw`, `pub`, `importer`, `core`, `rest_framework`, `rest_framework.authtoken`, `corsheaders` enabled. (core/settings.py:L40-L57)
- Root routing includes `/admin/` and `/api/v1/`. (core/urls.py:L20-L23)

## Entrypoints
- `manage.py` sets `DJANGO_SETTINGS_MODULE=core.settings` and runs Django management commands. (manage.py:L7-L18)
- ASGI entrypoint is `core.asgi.application`. (core/asgi.py:L10-L16)
- WSGI entrypoint is `core.wsgi.application`. (core/wsgi.py:L10-L16)

## Settings and environment
- Environment variables are loaded via `python-dotenv` (`load_dotenv()`). (core/settings.py:L1-L6)
- Required env keys used in settings:
  - `DJANGO_SECRET_KEY`. (core/settings.py:L10)
  - `DJANGO_DEBUG`. (core/settings.py:L11)
  - `DJANGO_CSRF_TRUSTED_ORIGINS`. (core/settings.py:L14-L16)
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`. (core/settings.py:L94-L101)
  - `DEFAULT_LOCALE_CODE` (default: `fr`). (core/settings.py:L117)
  - `TITLE_STRICT_LOCALE` (default: `true`). (core/settings.py:L122)
  - `OPENAI_API_KEY` (used by translation and content generation services).
- Database engine is PostgreSQL (`django.db.backends.postgresql`). (core/settings.py:L93)
- Static files are collected to `staticfiles/` and served with WhiteNoise storage. (core/settings.py:L127-L130)
- REST framework defaults:
  - Auth classes: TokenAuthentication, SessionAuthentication, BasicAuthentication. (core/settings.py:L137-L141)
  - Permissions: IsAdminUser. (core/settings.py:L142-L144)
  - Pagination: PageNumberPagination with `PAGE_SIZE=50`. (core/settings.py:L145-L146)
  - Filter backends: OrderingFilter, SearchFilter. (core/settings.py:L147-L150)
  - Custom exception handler: `api.v1.exception_handlers.api_exception_handler`. (core/settings.py:L151)

## Apps and models
- `catalog` — `ProductType`, `Product`, `Variant`, `Attribute`, `AttributeValue`, `ProductAttributeValue`, `ProductVariantAxis`, `ChannelVariantAxis`, `ChannelListingAxis`, `BundleComponent`. (catalog/models.py)
- `content` — `Locale`, `ProductI18n`, `ProductTypeI18n`, `ProductTypeSynonym`, `AttributeValueSynonym`, `TranslationTask`, `ContentBlock`, `ProductMedia`. (content/models.py)
- `kw` — `Keyword`, `PlannerSeed`, `PlannerRun`, `PlannerRunKeyword`, `Metric`, `AttributeMap`, `Candidate`. (kw/models.py)
- `pub` — `Channel`, `ChannelPolicySet`, `ChannelLocalePolicy`, `ChannelListing`, `ChannelListingMap`, `Template`, `TemplatePart`, `GenerationRun`, `GenerationOutput`, `TitleSelection`, `ContentSelection`, `ContentSet`, `GenerationBatch`, `GenerationBatchItem`, `ExportProfile`, `ExportJob`, `UniqueTitle`, `TermGlossary`. (pub/models.py)
- `importer` — `ProductImport`, `ImportColumnRule`, `ImportRow`, `CategoryBatch`, `AttributeMapping`. (importer/models.py)

## API routing
Base prefix: `/api/v1/` from root URL config. (core/urls.py:L20-L23)

### Router registrations (DefaultRouter)
- `locales` → `LocaleViewSet`
- `product-types` → `ProductTypeViewSet`
- `products` → `ProductViewSet`
- `variants` → `VariantViewSet`
- `attributes` → `AttributeViewSet`
- `attributes-translatable` → `TranslatableAttributesViewSet`
- `attribute-values` → `AttributeValueViewSet`
- `channels` → `ChannelViewSet`
- `channel-policy-sets` → `ChannelPolicySetViewSet`
- `channel-locale-policies` → `ChannelLocalePolicyViewSet`
- `channel-listings` → `ChannelListingViewSet`
- `imports` → `ProductImportViewSet`
- `category-batches` → `CategoryBatchViewSet`
- `translation-tasks` → `TranslationTaskViewSet`
- `templates` → `TemplateViewSet`
- `template-parts` → `TemplatePartViewSet`
- `generation-runs` → `GenerationRunViewSet`
- `content-sets` → `ContentSetViewSet`
- `generation-batches` → `GenerationBatchViewSet`
- `export-profiles` → `ExportProfileViewSet`
- `export-jobs` → `ExportJobViewSet`
- `planner-runs` → `PlannerRunViewSet`
- `planner-run-keywords` → `PlannerRunKeywordViewSet`
- `planner-seeds` → `PlannerSeedViewSet`
- `keywords` → `KeywordViewSet`
- `metrics` → `MetricViewSet`

### Non-router endpoints (api/v1/urls.py)
- Auth: `POST auth/login/`, `POST auth/signup/`, `POST auth/logout/`, `GET auth/me/`
- Import: `POST imports/upload/`, `GET imports/<id>/preview/`, `POST imports/<id>/assign-category/`, `POST imports/<id>/map-attributes/`, `POST imports/<id>/process/`
- Translations: `POST translations/create-task/`, `GET/PATCH translations/tasks/<id>/`, `GET translations/status/<locale>/`, `PATCH translations/<scope>/<id>/`, `GET translations/export/<task_id>/`, plus CSV export endpoints, `GET/PATCH translations/<locale>/products/<id>/`
- Keywords: `POST keywords/planner-run/`, `POST keywords/planner-run/import-csv/`, `GET keywords/planner-run/<id>/`, `POST keywords/planner-run/<id>/approve/`, `POST keywords/planner-run/<id>/map/`, `GET keywords/planner-run/<id>/mappings/`, `GET/PATCH keywords/planner-run/mappings/<id>/`, `POST keywords/planner-run/<id>/persist-mappings/`, `GET keywords/planner-run/<id>/suggested-terms/`, `GET keywords/planner-run/<id>/product-maps/`, `GET keywords/saved-terms/`
- Titles/Content: `POST titles/generate/`, `GET titles/suggestions/`, `POST content/preview/`, `POST content/save-selection/`, `POST content/generate/`
- Content sets: `POST/DELETE content-sets/<id>/items/`
- Batches: `POST generation-batches/create/`, `GET generation-batches/<id>/items/`
- Exports: `POST exports/create/`
- Channel listings (groups): `POST channel-listings/<id>/move-variants/`, `POST channel-listings/<id>/remove-variants/`, `GET channel-listings/<id>/available-variants/`, `GET channel-listings/<id>/differences/`, `GET/POST channel-listings/<id>/axes/`, `GET channel-listings/<id>/available-templates/`, `POST channel-listings/<id>/create-default-template/`, `POST channel-listings/<id>/generate-titles/`, `GET channel-listings/<id>/generated-titles/`, `PATCH channel-listings/<id>/generated-titles/<variant_id>/`
- `GET products/<id>/head-selection/`, `GET variants/<id>/attribute-details/`, `GET generated-titles/`

## Management commands
Command modules present:
- `core/management/commands/run_pipeline.py`
- `content/management/commands/enqueue_missing_translations.py`
- `content/management/commands/run_translation_tasks.py`
- `content/management/commands/seed_minimal_reference.py`
- `content/management/commands/translate_product_attribute_values.py`
- `kw/management/commands/refresh_planner_seeds.py`
- `kw/management/commands/fetch_keyword_ideas.py`
- `kw/management/commands/kw_import_ads_keywords.py`
- `kw/management/commands/kw_classify_rules.py`
- `kw/management/commands/kw_refresh_value_synonyms.py`
- `kw/management/commands/map_keywords.py`
- `kw/management/commands/parse_keywords.py`
- `kw/management/commands/select_candidates.py`
- `kw/management/commands/select_head_candidates.py`
- `kw/management/commands/promote_am_synonyms.py`
- `kw/management/commands/add_pt_synonym.py`
- `kw/management/commands/persist_product_keyword_maps.py`
- `pub/management/commands/generate_titles.py`
- `pub/management/commands/import_export_products_xlsx.py`
- `pub/management/commands/export_translated_titles.py`
- `pub/management/commands/clone_title_template_locale.py`
- `pub/management/commands/seed_fr_sample_titles.py`

## Tests
- Test modules present at `catalog/tests.py` and `pub/tests/test_title_policies.py`.

## Docker
- Dockerfile installs system deps and Python requirements and copies the app to `/app`. (Dockerfile:L1-L9)
- Entrypoint waits for Postgres, runs `migrate` and `collectstatic`, then starts Gunicorn (`core.wsgi:application`). (entrypoint.sh:L4-L11)
- See `DOCKER_COMMANDS.md` for common operational commands.
