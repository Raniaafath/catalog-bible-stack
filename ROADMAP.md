# Product Content Generation Platform - Roadmap

## Vision
A complete AI-powered product catalog management system that handles:
- Product import (manual + batch)
- Multi-language translation
- Keyword research and mapping
- AI-powered title and description generation
- Export to sales channels

---

## Current Status (January 2026)

### ✅ Phase 1: Product Management (DONE)
- [x] Manual product creation with attributes
- [x] Dynamic attribute forms based on product type
- [x] Required field validation
- [x] Variant creation
- [x] Parent/variant relationships
- [x] Product list view
- [x] Batch CSV/Excel import (backend)
- [x] Import preview and mapping UI

### 🔨 Phase 2: Translation Workflow (IN PROGRESS)

#### Backend (Existing)
- [x] TranslationTask model
- [x] TranslationItem model
- [x] AI translation service
- [x] API endpoints

#### Frontend (To Build)
- [ ] Translation task creation page
  - [ ] Select products to translate
  - [ ] Choose target language
  - [ ] Choose channel (Amazon, eBay, etc.)
  - [ ] Submit translation job
- [ ] Translation results page
  - [ ] Display translated content
  - [ ] Inline editing capability
  - [ ] Approve/reject translations
  - [ ] Save edited translations
- [ ] Translation task list
  - [ ] View all translation jobs
  - [ ] Status tracking
  - [ ] Progress indicators

### 🔨 Phase 3: Keyword Research (PARTIALLY DONE)

#### Backend (Existing)
- [x] KeywordSeed model
- [x] KeywordIdea model
- [x] Google Ads API integration
- [x] Keyword metrics storage

#### Frontend (To Build)
- [ ] Keyword import page
  - [ ] Upload keyword CSV
  - [ ] Google Ads API connector
  - [ ] Seed keyword input
  - [ ] Run keyword research
- [ ] Keyword list view
  - [ ] Display keywords with metrics
  - [ ] Filter and sort
  - [ ] Search volume display
  - [ ] Competition indicators

### ⚠️ Phase 4: AI Keyword-to-Product Mapping (NEW)

#### Backend (To Build)
- [ ] ProductKeywordMapping model
  - [ ] product_id
  - [ ] keyword_id
  - [ ] confidence_score
  - [ ] ai_reasoning (JSON)
  - [ ] status (pending/approved/rejected)
  - [ ] mapped_at
- [ ] AI mapping service
  - [ ] Analyze product attributes
  - [ ] Match with keyword intent
  - [ ] Generate reasoning
  - [ ] Return confidence scores
- [ ] Mapping API endpoints
  - [ ] POST /api/v1/keyword-mapping/run/
  - [ ] GET /api/v1/keyword-mapping/{id}/
  - [ ] PATCH /api/v1/keyword-mapping/{id}/approve/
  - [ ] PATCH /api/v1/keyword-mapping/{id}/reject/

#### Frontend (To Build)
- [ ] Keyword mapping runner page
  - [ ] Select products
  - [ ] Select keyword set
  - [ ] One-time AI prompt input (optional)
  - [ ] Run mapping button
  - [ ] Progress indicator
- [ ] Mapping results view
  - [ ] Product-keyword pairs
  - [ ] AI reasoning display
  - [ ] Confidence scores
  - [ ] Approve/reject buttons
  - [ ] Bulk approval
  - [ ] Filter by confidence

### 🔨 Phase 5: Title Template System (PARTIALLY DONE)

#### Backend (Existing)
- [x] TitleTemplate model
- [x] Template rendering logic
- [x] Variable substitution

#### Frontend (To Build)
- [ ] Template editor page
  - [ ] Template name input
  - [ ] Template text editor
  - [ ] Variable picker ({{brand}}, {{model}}, etc.)
  - [ ] Keyword slot markers
  - [ ] Preview with sample product
  - [ ] Save template
- [ ] AI template generator
  - [ ] Analyze product category
  - [ ] Generate template suggestions
  - [ ] User prompt input (one-time)
  - [ ] Display generated templates
  - [ ] Edit and save
- [ ] Template selector
  - [ ] List saved templates
  - [ ] Preview templates
  - [ ] Select for title generation

### 🔨 Phase 6: Title Generation (BACKEND DONE)

#### Backend (Existing)
- [x] TitleRenderer service
- [x] Keyword insertion
- [x] Variant axis handling
- [x] Template variable substitution

#### Frontend (To Build)
- [ ] Title generation page
  - [ ] Select products
  - [ ] Select template
  - [ ] Select mapped keywords
  - [ ] Generate titles button
  - [ ] Preview generated titles
  - [ ] AI refinement option
    - [ ] One-time prompt input
    - [ ] Refine for clarity
    - [ ] Compare before/after
  - [ ] Approve titles
- [ ] Variant title handling
  - [ ] Show all variants
  - [ ] Display variation axes
  - [ ] Consistent keyword usage
  - [ ] Variation-specific text

### ⚠️ Phase 7: Description Generation (NEW)

#### Backend (To Build)
- [ ] ProductDescription model
  - [ ] product_id
  - [ ] locale
  - [ ] description_text
  - [ ] bullet_points (JSON)
  - [ ] generated_by (ai/manual)
  - [ ] approved_at
- [ ] AI description service
  - [ ] Analyze product attributes
  - [ ] Use approved keywords
  - [ ] Generate structured content
  - [ ] Create bullet points
- [ ] Description API endpoints
  - [ ] POST /api/v1/descriptions/generate/
  - [ ] GET /api/v1/descriptions/{id}/
  - [ ] PATCH /api/v1/descriptions/{id}/

#### Frontend (To Build)
- [ ] Description generator page
  - [ ] Select products
  - [ ] Choose description style
  - [ ] One-time AI prompt (optional)
  - [ ] Generate descriptions
  - [ ] Display results
- [ ] Description editor
  - [ ] Rich text editor
  - [ ] Bullet point editor
  - [ ] Keyword highlighting
  - [ ] Character count
  - [ ] Save and approve

### ✅ Phase 8: Export System (BACKEND DONE)

#### Backend (Existing)
- [x] ExportJob model
- [x] CSV/Excel export
- [x] Channel-specific formatting

#### Frontend (To Build)
- [ ] Export page
  - [ ] Select products
  - [ ] Choose format (CSV/Excel)
  - [ ] Select channel (Amazon, eBay, etc.)
  - [ ] Select language
  - [ ] Include/exclude fields
  - [ ] Export button
- [ ] Download page
  - [ ] Export job status
  - [ ] Download link
  - [ ] Preview export data

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

### 🔥 Immediate (Next 2-3 days)
1. Translation UI (Phase 2)
2. Keyword import UI (Phase 3)
3. Template editor (Phase 5)

### 📅 Short-term (Next week)
4. AI keyword mapping (Phase 4)
5. Title generation UI (Phase 6)
6. Export UI (Phase 8)

### 📆 Medium-term (Next 2 weeks)
7. Description generation (Phase 7)
8. AI refinement features
9. Bulk operations
10. Advanced filtering

---

## Technical Notes

### AI Integration Points
1. **Translation**: Existing AI service
2. **Keyword Mapping**: New AI service needed
3. **Template Generation**: New AI service needed
4. **Title Refinement**: New AI service needed
5. **Description Generation**: New AI service needed

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

## Questions to Answer

1. **AI Model**: Which AI provider? (OpenAI, Anthropic, local model?)
2. **Keyword Volume**: How many keywords per product?
3. **Translation Languages**: Which languages to support initially?
4. **Export Channels**: Which platforms (Amazon, eBay, Shopify, etc.)?
5. **User Roles**: Single user or multi-user with permissions?
6. **Batch Size**: Max products per operation?

---

## Success Metrics

- ✅ User can add 100 products in < 10 minutes (batch import)
- ✅ AI keyword mapping accuracy > 80%
- ✅ Title generation in < 5 seconds per product
- ✅ Translation quality acceptable without editing > 90%
- ✅ Export file ready in < 30 seconds for 1000 products

---

## Next Steps

**Which phase should we start with?**
1. Complete Translation UI?
2. Build Keyword Mapping?
3. Finish Title Generation workflow?

Let me know your priority and I'll start building! 🚀
