# Product Content Generation Platform - Roadmap

## Vision
A complete AI-powered product catalog management system that handles:
- Product import (manual + batch)
- Multi-language translation
- Keyword research and mapping
- AI-powered title and description generation
- Export to sales channels

---

## Current Status (March 2026)

### ✅ Phase 1: Product Management (DONE)
- [x] Manual product creation with attributes
- [x] Dynamic attribute forms based on product type
- [x] Required field validation
- [x] Variant creation
- [x] Parent/variant relationships
- [x] Product list view
- [x] Batch CSV/Excel import (backend + UI)
- [x] Import preview and column mapping UI
- [x] Category assignment in import flow

### ✅ Phase 2: Translation Workflow (DONE)
- [x] TranslationTask model with progress tracking
- [x] AI translation service (OpenAI, selectable model)
- [x] API endpoints
- [x] Translation task creation page (select scope, attributes, language, AI model)
- [x] Translation task list with status and model column
- [x] Inline editing of translations
- [x] `run_translation_tasks` management command

### ✅ Phase 3: Keyword Research (DONE)
- [x] PlannerSeed, PlannerRun, PlannerRunKeyword models
- [x] Google Ads API integration (`fetch_keyword_ideas`)
- [x] Keyword metrics storage
- [x] Keyword import via CSV
- [x] Keyword list / planner run UI
- [x] Keyword-to-product mapping (AttributeMap, `map_keywords`)
- [x] Saved terms / approved terms UI
- [x] Keyword mapping review UI

### ✅ Phase 4: AI Keyword-to-Product Mapping (DONE)
- [x] AttributeMap model (keyword → attribute/value)
- [x] ProductKeywordMap (product → keyword with confidence)
- [x] AI mapping service (`product_keyword_mapper`)
- [x] `persist-mappings` API endpoint
- [x] Mapping results view in UI
- [x] AI mapping overwrites rules-based (ENUM) rows for the same keywords (AI wins)
- [x] Language-agnostic size/marketplace attribute filtering (prefix/suffix patterns, not hardcoded codes)
- [x] Smart numeric matching: bare numbers only matched when attribute has no unit (avoids `"30"` → `profondeur=30cm`)
- [x] Head/hook term AI reasons (`use_ai_reason` param on `suggested-terms` endpoint)
- [x] AI meaning generation for keywords (`use_ai_meaning` param on `suggested-terms` endpoint)

### ✅ Phase 5: Title Template System (DONE)
- [x] Template / TemplatePart models (head/hook/literal/axis/attribute parts)
- [x] Template rendering engine (`title_renderer.py`)
- [x] Template CRUD API endpoints
- [x] Template management UI
- [x] `create-default-template` endpoint for listings

### ✅ Phase 6: Title Generation (DONE)
- [x] TitleRenderer service (keyword insertion, axis handling, policy enforcement, uniqueness)
- [x] Per-listing title generation (`generate-titles` endpoint)
- [x] Generated titles review UI in listing group detail
- [x] TitleSelection / approval workflow
- [x] Axis resolution priority (listing → channel → product)

### 🔨 Phase 7: Description Generation (IN PROGRESS)
- [x] ContentSelection model (description_text, bullets_json, description_ai_enabled)
- [x] `content/preview/` API endpoint (returns features + description per variant)
- [x] `content/generate/` API endpoint
- [x] `content/save-selection/` API endpoint
- [x] DD description structure spec (`docs/DD_DESCRIPTION_STRUCTURE.md`)
- [ ] Full description generation UI
- [ ] Description editor with bullet point management
- [ ] Per-channel description output configuration

### ✅ Phase 8: Export System (DONE)
- [x] ExportProfile / ExportJob models
- [x] CSV/Excel export with channel-specific formatting
- [x] Export job create API + UI
- [x] Export job list / download UI

---

## Key Design Decisions

### 1. AI Prompt Strategy
- **One-time prompts only** (no chat memory)
- Prompts are contextual to the current task
- Not saved to database
- Each AI call is independent

### 2. Variant Handling
- Variants share keywords with parent
- Variants share title template
- Only variation axis changes (size, color, etc.)
- Description can be shared or variant-specific

### 3. Workflow State Management
- Each phase can be done independently
- Products track completion status per phase
- User can revisit and edit any phase
- Changes propagate forward (not backward)

---

## Implementation Priority

### 🔥 Active
1. Description generation UI (Phase 7)
2. Advanced per-channel description formatting
3. Bulk operations improvements

### 📅 Short-term
4. AI refinement features for titles/descriptions
5. Advanced filtering on product/variant lists
6. Scheduled/automated export

---

## Technical Notes

### AI Integration Points
1. **Translation**: `TranslationTask` → OpenAI/Claude/Gemini (selectable model)
2. **Keyword Mapping**: `product_keyword_mapper` → `pav_text_llm` source, overwrites rules-based ENUM rows
3. **Term Extraction Reasons**: `generate_term_reasons()` in `kw/services/term_extraction.py` (single call for all terms)
4. **Keyword Meaning**: `generate_keyword_meanings()` in `kw/services/term_extraction.py`
5. **Title Rendering**: Template engine (`pub/services/title_renderer.py`) — deterministic, no AI
6. **Description Generation**: `pub/services/content_generation.py` — in progress (Phase 7)

### API Design Pattern
All AI services follow same pattern:
```python
# One-time prompt, no memory
result = ai_service.run(
    context=product_data,
    user_prompt=optional_prompt,
    task_type="mapping|generation|refinement"
)
```

### Frontend State Management
- Use React Query for API state
- Form state with React Hook Form
- Toast notifications for feedback
- Loading states for AI operations
- Real-time progress for batch operations

---


## Success Metrics

- ✅ User can add 100 products in < 10 minutes (batch import)
- ✅ AI keyword mapping accuracy > 80%
- ✅ Title generation in < 5 seconds per product
- ✅ Translation quality acceptable without editing > 90%
- ✅ Export file ready in < 30 seconds for 1000 products

---

