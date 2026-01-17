# Product Import & Management Workflow - Frontend Specification

## Overview
This document outlines the complete frontend workflow for the Lovable-based product import and management system. The system handles product imports, attribute mapping, translation, keyword research, keyword-product mapping, and content generation.

---

## Workflow Stages

### 1. **Product Import & Parsing**
**Purpose**: Upload and parse product files with variants

**UI Components**:
- File upload interface (CSV/Excel support)
- Preview grid showing parsed products
- Validation errors display

**Features**:
- Upload product file with variants indicated
- Parent-child product relationships (via `product_id` or similar column)
- Category assignment per file/batch
- Data validation & error highlighting

**API Endpoints Needed**:
```
POST /api/v1/imports/upload/
  - Accepts: multipart/form-data (file)
  - Returns: { import_id, preview_data[], validation_errors[] }

GET /api/v1/imports/{import_id}/preview/
  - Returns: { products[], variants[], categories[] }
```

**Data Flow**:
```
CSV/Excel File → Parse → Validate → Preview Display
```

---

### 2. **Attribute & Category Mapping**
**Purpose**: Map uploaded product attributes to existing database attributes or create new ones

**UI Components**:
- Two-column mapping interface (File Columns ↔ DB Attributes)
- Dropdown selectors for existing attributes
- "Create New Attribute" inline form
- Category selector/hierarchy tree
- Bulk mapping tools

**Features**:
- Auto-suggestion for similar attribute names
- Map to existing `Attribute` records
- Create new attributes if not exists (`Attribute.code`, `Attribute.data_type`)
- Category assignment (uses `ProductType.main_category`, `ProductType.category_path`)
- Attribute value mapping/creation (`AttributeValue`)

**API Endpoints Needed**:
```
GET /api/v1/attributes/
  - Returns: List of existing attributes with types

POST /api/v1/imports/{import_id}/map-attributes/
  - Body: { mappings: [{ file_column, attribute_code, create_if_missing }] }
  - Returns: { mapped_count, created_attributes[], errors[] }

GET /api/v1/product-types/
  - Returns: List of categories with hierarchy

POST /api/v1/imports/{import_id}/assign-category/
  - Body: { product_type_code, products[] }
```

**Existing Models Used**:
- `catalog.Attribute` (code, data_type, is_value_translatable)
- `catalog.AttributeValue` (attribute, value)
- `catalog.ProductType` (code, main_category, category_path)
- `catalog.ProductAttributeValue` (product/variant, attribute, attribute_value, value_text, value_number)

---

### 3. **Translation Management**
**Purpose**: Translate product content using AI

**UI Components**:
- Locale selector (target languages)
- Translation job queue/status
- Review interface for translated content
- Edit capabilities for translations
- Batch approval/rejection

**Features**:
- Create `TranslationTask` for batch translation
- Use existing translation script (`translate_product_attribute_values.py`)
- Display translated content by locale
- Allow manual editing of translations
- Track translation status (pending/in_progress/done/failed)

**API Endpoints Needed**:
```
POST /api/v1/translations/create-task/
  - Body: { locale, scope, target_ids[], import_id }
  - Returns: { task_id, status }

GET /api/v1/translations/tasks/{task_id}/
  - Returns: { status, progress, errors }

GET /api/v1/translations/{locale}/products/{product_id}/
  - Returns: { title, description, attributes[] }

PATCH /api/v1/translations/{locale}/products/{product_id}/
  - Body: { title, description, attribute_values[] }
  - Returns: { updated }
```

**Existing Models Used**:
- `content.TranslationTask` (locale, scope, target_ids, status)
- `content.ProductI18n` (product, locale, title, description)
- `content.ProductAttributeValueI18n` (product_attribute_value, locale, value_text)
- `content.Locale` (code, name)

---

### 4. **Keyword Research (Google Ads Integration)**
**Purpose**: Fetch keywords from Google Ads Keyword Planner

**UI Components**:
- Seed keyword input (auto-populated from category)
- Additional seed words input
- Negative keywords input
- Fetch button & progress indicator
- Results table (keyword, avg_searches, competition, cpc)

**Features**:
- Auto-populate seed from `ProductType.main_category`
- Allow user to add custom seed words
- Add negative keywords
- Use existing Google Ads service (`kw.services.google_ads_keyword_planner`)
- Create `PlannerRun` and `PlannerRunKeyword` records
- Display metrics (searches, competition, CPC)

**API Endpoints Needed**:
```
POST /api/v1/keywords/planner-run/
  - Body: { 
      locale, 
      product_type_code, 
      channel_id,
      seed_terms[], 
      negative_terms[] 
    }
  - Returns: { run_id, status }

GET /api/v1/keywords/planner-run/{run_id}/
  - Returns: { 
      status, 
      keywords: [{ term, avg_searches, competition, cpc }] 
    }

POST /api/v1/keywords/planner-run/{run_id}/approve/
  - Body: { keyword_ids[] }
```

**Existing Models Used**:
- `kw.PlannerRun` (locale, product_type, channel, status)
- `kw.PlannerSeed` (locale, term, seed_type, product_type)
- `kw.Keyword` (locale, term, normalized_term)
- `kw.PlannerRunKeyword` (run, keyword, status, concept, mapped_*)
- `kw.Metric` (keyword, source, avg_searches, competition, cpc)

**Existing Service**:
- `kw.services.google_ads_keyword_planner.GoogleAdsKeywordPlanner`

---

### 5. **Keyword-Product Mapping**
**Purpose**: Map fetched keywords to products based on attributes and content

**UI Components**:
- Mapping results table
- Columns: Keyword | Products | Confidence | Matched Attributes | Actions
- Filters: confidence threshold, match type
- Bulk approve/reject tools
- Manual re-mapping interface

**Features**:
- Run existing mapper service (`kw.services.product_keyword_mapper`)
- Analyze product attributes, values, titles, descriptions
- Create `AttributeMap` (keyword → attribute/value)
- Create `ProductKeywordMap` (product → keyword)
- Display confidence scores and evidence
- Allow manual adjustments
- Validation workflow

**API Endpoints Needed**:
```
POST /api/v1/keywords/map-to-products/
  - Body: { run_id, product_ids[], min_confidence }
  - Returns: { job_id, status }

GET /api/v1/keywords/mappings/{run_id}/
  - Returns: { 
      mappings: [{ 
        keyword, 
        products[], 
        confidence, 
        matched_attrs[], 
        evidence 
      }] 
    }

PATCH /api/v1/keywords/mappings/{mapping_id}/
  - Body: { approved, product_id, keyword_id }

GET /api/v1/products/{product_id}/keywords/{run_id}/
  - Returns: { keywords: [{ term, confidence, source, matched_text }] }
```

**Existing Models Used**:
- `kw.AttributeMap` (keyword, attribute, attribute_value, confidence, status)
- `kw.ProductKeywordMap` (product, keyword, run, source, confidence, evidence)
- `kw.KeywordParse` (keyword, tokens, phrases, detected)

**Existing Service**:
- `kw.services.product_keyword_mapper.product_keywords_for_run()`

---

### 6. **Keyword Cleaning & Classification**
**Purpose**: Clean keywords, identify head/hook terms, remove noise

**UI Components**:
- Keyword list with classification tags
- Filters: Head Terms, Hook Terms, Attribute Terms
- Noise removal tools (size, marketplace names)
- Manual tag editor
- Deduplication interface

**Features**:
- Parse keywords using `parse_keywords.py` command
- Identify head terms (main category terms)
- Identify hook terms (intent/feature terms)
- Remove sizes from keywords
- Remove marketplace names
- Remove duplicate head terms
- Create `KeywordConcept` records (head_term, feature, intent, negative, brand, size)
- Classification via rules or LLM

**API Endpoints Needed**:
```
POST /api/v1/keywords/parse-and-clean/
  - Body: { run_id, remove_sizes, remove_marketplaces }
  - Returns: { job_id }

GET /api/v1/keywords/classifications/{run_id}/
  - Returns: { 
      keywords: [{ 
        term, 
        concepts: [{ type, confidence }],
        cleaned_term 
      }] 
    }

PATCH /api/v1/keywords/{keyword_id}/concepts/
  - Body: { concepts: [{ concept_type, confidence }] }
```

**Existing Models Used**:
- `kw.Concept` (code, concept_type: head_term/feature/intent/negative/brand/size)
- `kw.KeywordConcept` (keyword, concept, confidence, tagged_by)
- `kw.KeywordParse` (keyword, tokens, phrases, detected)

**Existing Command**:
- `kw.management.commands.parse_keywords`

---

### 7. **Template Management**
**Purpose**: Create content templates for product variant groups

**UI Components**:
- Variant group selector
- Template builder interface
- Variable placeholders UI ({attribute_name}, {brand}, etc.)
- Template preview with sample data
- Validation & testing tools

**Features**:
- Group products by variant family
- Create template structure for titles/descriptions
- Define variable slots (attributes, brand, model, etc.)
- Auto-generate template suggestions
- Manual template editing
- Preview with real product data
- Save as `ContentTemplate` (to be created)

**API Endpoints Needed**:
```
GET /api/v1/products/variant-groups/{product_type_code}/
  - Returns: { groups: [{ parent_product, variants[] }] }

POST /api/v1/templates/create/
  - Body: { 
      product_type_code, 
      title_template, 
      description_template,
      variables[] 
    }
  - Returns: { template_id }

POST /api/v1/templates/{template_id}/preview/
  - Body: { product_id }
  - Returns: { title, description }
```

**New Models Needed**:
```python
class ContentTemplate(models.Model):
    product_type = ForeignKey(ProductType)
    locale = ForeignKey(Locale)
    channel = ForeignKey(Channel, null=True)
    title_template = TextField()
    description_template = TextField()
    variables = JSONField()  # [{name, attribute_code, fallback}]
    is_active = BooleanField(default=True)
```

---

### 8. **Content Generation (AI)**
**Purpose**: Generate product titles and descriptions using AI

**UI Components**:
- Generation configuration panel
- Custom prompt input (additional instructions)
- Batch generation trigger
- Results review interface
- Regeneration controls (with modified prompt)
- Comparison view (before/after)
- Approval workflow

**Features**:
- Generate titles based on template + AI
- Generate descriptions with custom prompts
- Allow user to add custom instructions
- Regenerate with modified prompts
- Save to `ProductI18n` records
- Track generation metadata
- A/B testing capabilities

**API Endpoints Needed**:
```
POST /api/v1/content/generate/
  - Body: { 
      product_ids[], 
      locale, 
      template_id,
      custom_prompt,
      regenerate 
    }
  - Returns: { job_id, status }

GET /api/v1/content/generation-job/{job_id}/
  - Returns: { 
      status, 
      results: [{ 
        product_id, 
        title, 
        description, 
        metadata 
      }] 
    }

POST /api/v1/content/approve/
  - Body: { product_ids[], locale }
```

**New Service Needed**:
```python
class ContentGenerator:
    def generate_title(product, template, locale, keywords)
    def generate_description(product, locale, keywords, custom_prompt)
```

---

### 9. **Export & Publishing**
**Purpose**: Export finalized products with all translations and content

**UI Components**:
- Export configuration panel
- Format selector (CSV, Excel, JSON, API)
- Locale selector (which translations to include)
- Field selector (which data to export)
- Download interface
- Export history

**Features**:
- Export products with all translations
- Include all i18n content (titles, descriptions, attributes)
- Include keyword mappings and metrics
- Multiple export formats
- Filter by locale, category, status
- Schedule exports
- API endpoint for programmatic access

**API Endpoints Needed**:
```
POST /api/v1/exports/create/
  - Body: { 
      product_ids[], 
      locales[], 
      format,
      include_keywords,
      include_metrics 
    }
  - Returns: { export_id, download_url }

GET /api/v1/exports/{export_id}/download/
  - Returns: File download

GET /api/v1/exports/history/
  - Returns: { exports: [{ id, created_at, status, download_url }] }
```

---

## Data Models Summary

### Existing Models (Already in Django Backend)
- **catalog**: `ProductType`, `Product`, `Variant`, `Attribute`, `AttributeValue`, `ProductAttributeValue`
- **content**: `Locale`, `ProductI18n`, `ProductAttributeValueI18n`, `AttributeI18n`, `ProductTypeI18n`, `TranslationTask`
- **kw**: `Keyword`, `PlannerRun`, `PlannerRunKeyword`, `PlannerSeed`, `Metric`, `Source`, `Concept`, `KeywordConcept`, `AttributeMap`, `ProductKeywordMap`, `KeywordParse`, `Candidate`
- **pub**: `Channel`

### New Models Needed
```python
# Import tracking
class ProductImport(models.Model):
    file_name = CharField(max_length=255)
    status = CharField(choices=Status)  # pending/processing/completed/failed
    uploaded_by = CharField(max_length=100)
    row_count = IntegerField()
    processed_count = IntegerField(default=0)
    error_log = JSONField(default=dict)
    created_at = DateTimeField(auto_now_add=True)

# Content templates
class ContentTemplate(models.Model):
    product_type = ForeignKey(ProductType)
    locale = ForeignKey(Locale)
    channel = ForeignKey(Channel, null=True)
    title_template = TextField()
    description_template = TextField()
    variables = JSONField()
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)

# Content generation tracking
class ContentGenerationJob(models.Model):
    template = ForeignKey(ContentTemplate, null=True)
    locale = ForeignKey(Locale)
    custom_prompt = TextField(blank=True)
    status = CharField(choices=Status)
    product_count = IntegerField()
    completed_count = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)

# Export tracking
class ProductExport(models.Model):
    format = CharField(max_length=20)
    locales = JSONField()
    filters = JSONField()
    file_path = CharField(max_length=500)
    status = CharField(choices=Status)
    created_at = DateTimeField(auto_now_add=True)
```

---

## Frontend Pages/Views Structure

```
/dashboard
  - Overview stats
  - Recent imports, translations, exports

/imports
  /new - Upload interface
  /{id}/preview - Preview & validate
  /{id}/map-attributes - Attribute mapping
  /{id}/assign-category - Category assignment

/translations
  /tasks - List translation tasks
  /{task_id}/review - Review translations
  /{locale}/products/{product_id}/edit - Edit translation

/keywords
  /planner - Create keyword research run
  /runs/{run_id} - View run results
  /mappings/{run_id} - View/edit keyword-product mappings
  /classifications - Manage keyword concepts/tags

/templates
  /list - Template library
  /create - Template builder
  /{template_id}/edit - Edit template
  /{template_id}/preview - Preview with products

/content
  /generate - Content generation interface
  /jobs/{job_id} - Generation job status
  /review - Review generated content

/exports
  /create - Export configuration
  /history - Export history
  /{export_id}/download - Download export
```

---

## Technology Stack Recommendations

### Frontend (Lovable Platform)
- **Framework**: React + TypeScript
- **UI Library**: Tailwind CSS + shadcn/ui
- **State Management**: Zustand or React Query
- **Forms**: React Hook Form + Zod validation
- **Tables**: TanStack Table
- **File Upload**: react-dropzone
- **API Client**: Axios with interceptors

### Backend Integration
- All endpoints should follow REST conventions
- Use JWT for authentication
- WebSocket for real-time job progress
- Pagination for large datasets
- Rate limiting on AI endpoints

---

## Workflow Sequence Diagram

```
User → Upload File → Parse & Validate → Map Attributes → Assign Category
  → Translate Products → Fetch Keywords → Map Keywords to Products
  → Clean & Classify Keywords → Create Templates → Generate Content
  → Review & Edit → Export
```

---

## Next Steps

1. **Backend API Development**: Create missing API endpoints
2. **New Models**: Implement `ProductImport`, `ContentTemplate`, `ContentGenerationJob`, `ProductExport`
3. **Frontend Setup**: Initialize Lovable project with routing
4. **Component Library**: Build reusable UI components
5. **Integration Testing**: Test full workflow end-to-end

---

## Notes & Considerations

- **Permissions**: Add role-based access control (viewer/editor/admin)
- **Audit Trail**: Track all changes to products, keywords, mappings
- **Versioning**: Consider versioning for templates and content
- **Rollback**: Ability to revert imports/translations
- **Async Jobs**: Use Celery for long-running tasks
- **Caching**: Cache translations, keyword metrics
- **Error Handling**: Graceful degradation, retry mechanisms
- **Progress Tracking**: Real-time updates for batch operations
