# API Guide (evidence-based)

## Base routing
- Root routes include `/api/v1/` and `/admin/`. (core/urls.py:L20-L23)
- API routes are defined in `api/v1/urls.py`. (api/v1/urls.py:L1-L41)

## Authentication and permissions
- REST framework auth classes: SessionAuthentication and BasicAuthentication. (core/settings.py:L102-L106)
- Default permissions: IsAdminUser. (core/settings.py:L107-L109)

## Router registrations
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

## Non-router endpoints
- `POST titles/generate/` -> `TitleGenerateView.post`. (api/v1/urls.py:L23-L24, api/v1/views/pub.py:L87-L89)
- `GET titles/suggestions/` -> `TitleSuggestionsView.get`. (api/v1/urls.py:L24-L24, api/v1/views/pub.py:L265-L267)
- `POST content/preview/` -> `ContentPreviewView.post`. (api/v1/urls.py:L25-L25, api/v1/views/pub.py:L127-L129)
- `POST content/generate/` -> `ContentGenerateView.post`. (api/v1/urls.py:L26-L26, api/v1/views/pub.py:L151-L153)
- `POST content-sets/<set_id>/items/` -> `ContentSetItemView.post`. (api/v1/urls.py:L27-L31, api/v1/views/pub.py:L198-L201)
- `DELETE content-sets/<set_id>/items/<item_id>/` -> `ContentSetItemView.delete`. (api/v1/urls.py:L28-L31, api/v1/views/pub.py:L210-L212)
- `POST generation-batches/create/` -> `GenerationBatchCreateView.post`. (api/v1/urls.py:L33-L33, api/v1/views/pub.py:L215-L218)
- `GET generation-batches/<batch_id>/items/` -> `GenerationBatchItemView.get`. (api/v1/urls.py:L35-L37, api/v1/views/pub.py:L245-L248)
- `POST exports/create/` -> `ExportJobCreateView.post`. (api/v1/urls.py:L39-L39, api/v1/views/pub.py:L252-L255)
