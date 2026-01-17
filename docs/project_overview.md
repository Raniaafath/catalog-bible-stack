# Project Overview (evidence-based)

## Entrypoints
- `manage.py` sets `DJANGO_SETTINGS_MODULE=core.settings` and runs management commands. (manage.py:L7-L18)
- ASGI entrypoint is `core.asgi.application`. (core/asgi.py:L10-L16)
- WSGI entrypoint is `core.wsgi.application`. (core/wsgi.py:L10-L16)

## Settings and environment
- Environment variables are loaded with `load_dotenv()`. (core/settings.py:L1-L6)
- `INSTALLED_APPS` includes `rest_framework`, `catalog`, `content`, `kw`, and `pub`. (core/settings.py:L18-L32)
- Root URL config uses `core.urls`. (core/settings.py:L45-L45)
- Database engine is PostgreSQL. (core/settings.py:L66-L69)
- Static files are collected to `staticfiles/` and use WhiteNoise storage. (core/settings.py:L93-L98)
- REST framework defaults define auth classes, permissions, pagination, and filter backends. (core/settings.py:L102-L115)

## Routing
- Root routes include `/admin/` and `/api/v1/`. (core/urls.py:L20-L23)
- API routes are defined in `api/v1/urls.py`. (api/v1/urls.py:L1-L41)

## Models by app
- `catalog`: `ProductType`, `Product`, `Variant`, `Attribute`, `AttributeValue`, and related models. (catalog/models.py:L6-L265)
- `content`: `Locale`, `ProductI18n`, `ProductTypeI18n`, `ProductTypeSynonym`, `AttributeValueSynonym`, `TranslationTask`, and related models. (content/models.py:L7-L300)
- `kw`: `Keyword`, `PlannerSeed`, `PlannerRun`, `PlannerRunKeyword`, `Metric`, `AttributeMap`, `Candidate`, and related models. (kw/models.py:L28-L458)
- `pub`: `Channel`, `Template`, `TemplatePart`, `GenerationRun`, `GenerationOutput`, `Approval`, `ContentSet`, `ExportProfile`, `ExportJob`, and related models. (pub/models.py:L4-L821)

## Management commands (modules)
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
- Tests exist in `catalog/tests.py` and `pub/tests/test_title_policies.py`. (catalog/tests.py:L1-L3, pub/tests/test_title_policies.py:L1-L91)

## Docker
- Docker image is defined in `Dockerfile`. (Dockerfile:L1-L10)
- Entrypoint waits for Postgres, runs migrations and collectstatic, then starts Gunicorn. (entrypoint.sh:L4-L11)
