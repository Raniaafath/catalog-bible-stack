# Frontend Interface Requirements

This document provides detailed UI/UX specifications for the Lovable frontend.

---

## Design System

### Colors
```css
--primary: #3b82f6 (blue-500)
--primary-dark: #2563eb (blue-600)
--success: #10b981 (green-500)
--warning: #f59e0b (amber-500)
--danger: #ef4444 (red-500)
--neutral-50: #f9fafb
--neutral-100: #f3f4f6
--neutral-200: #e5e7eb
--neutral-800: #1f2937
--neutral-900: #111827
```

### Typography
- **Font**: Inter, system-ui, sans-serif
- **Headings**: font-weight: 600
- **Body**: font-weight: 400

---

## Page Layouts

### 1. Dashboard (`/dashboard`)

**Components:**
- **Header**: Logo, user menu, notifications
- **Stats Cards**: 
  - Total Products
  - Active Imports
  - Pending Translations
  - Keyword Runs
- **Recent Activity Timeline**
- **Quick Actions**: New Import, New Translation, New Keyword Run

**Wireframe:**
```
┌─────────────────────────────────────────────────┐
│ Logo                    [User] [Notifications]  │
├─────────────────────────────────────────────────┤
│                                                  │
│  [📦 Products]  [⬆ Imports]  [🌐 Translations] │
│    1,234           3             12 pending     │
│                                                  │
│  Recent Activity                Quick Actions   │
│  ┌──────────────┐              ┌──────────────┐│
│  │ • Import...  │              │ + New Import ││
│  │ • Transl...  │              │ + Keywords   ││
│  │ • Export...  │              │ + Export     ││
│  └──────────────┘              └──────────────┘│
└─────────────────────────────────────────────────┘
```

---

### 2. Product Import Flow

#### 2.1 Upload Page (`/imports/new`)

**Components:**
- **File Upload Dropzone**: Drag & drop or click to upload
- **File Format Info**: Supported formats, example template download
- **Optional Fields**: Source supplier, source locale

**UI Elements:**
```tsx
<FileUpload 
  accept=".csv,.xlsx,.xls"
  maxSize={10 * 1024 * 1024} // 10MB
  onUpload={handleUpload}
/>

<TemplateDownload 
  formats={['CSV', 'Excel']}
/>
```

**Wireframe:**
```
┌─────────────────────────────────────────────────┐
│ ← Back to Imports                               │
├─────────────────────────────────────────────────┤
│                                                  │
│         Upload Product File                      │
│                                                  │
│  ┌────────────────────────────────────────────┐│
│  │                                             ││
│  │        📁 Drag & drop file here            ││
│  │           or click to browse               ││
│  │                                             ││
│  │     Supported: CSV, Excel                  ││
│  │     Max size: 10MB                         ││
│  │                                             ││
│  └────────────────────────────────────────────┘│
│                                                  │
│  [Download Template ▼]                          │
│                                                  │
│  Optional Settings:                              │
│  Source Supplier: [____________]                │
│  Source Locale:   [en ▼]                       │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

#### 2.2 Preview & Validate (`/imports/{id}/preview`)

**Components:**
- **File Info**: Name, size, rows detected
- **Data Preview Table**: First 10 rows
- **Validation Errors Panel**: Errors with row numbers
- **Column Detection**: Auto-detected columns with confidence
- **Action Buttons**: Continue, Re-upload, Cancel

**Table Features:**
- Sortable columns
- Sticky header
- Error highlighting (red background)
- Warning highlighting (yellow background)

**Wireframe:**
```
┌─────────────────────────────────────────────────┐
│ ← Back                                           │
├─────────────────────────────────────────────────┤
│ Import Preview: products.csv                     │
│ 1,500 rows • 2.3 MB • 12 columns detected       │
├─────────────────────────────────────────────────┤
│                                                  │
│ ⚠ 3 validation errors found                     │
│ • Row 15: Invalid barcode format                │
│ • Row 42: Missing required field 'sku'          │
│ • Row 128: Duplicate SKU                        │
│                                                  │
├─────────────────────────────────────────────────┤
│ Preview Data (first 10 rows)                    │
│                                                  │
│ ┌─────┬───────┬──────┬─────┬──────┬─────────┐ │
│ │ Row │ Code  │ Brand│ ... │ SKU  │ Status  │ │
│ ├─────┼───────┼──────┼─────┼──────┼─────────┤ │
│ │ 1   │ P001  │ Appl │ ... │ A001 │ ✓       │ │
│ │ 2   │ P002  │ Sam  │ ... │ A002 │ ✓       │ │
│ │ ... │       │      │     │      │         │ │
│ └─────┴───────┴──────┴─────┴──────┴─────────┘ │
│                                                  │
│              [Re-upload]  [Continue →]          │
└─────────────────────────────────────────────────┘
```

---

#### 2.3 Attribute Mapping (`/imports/{id}/map-attributes`)

**Components:**
- **Two-Column Mapper**: File columns on left, DB attributes on right
- **Auto-Match Suggestions**: ML-suggested mappings with confidence
- **Create New Attribute Form**: Inline creation
- **Mapping Summary**: Shows mapped/unmapped counts

**Interactive Elements:**
```tsx
<AttributeMapper
  fileColumns={['color', 'size', 'weight']}
  dbAttributes={existingAttributes}
  onMap={handleMapping}
  onCreateNew={handleCreateAttribute}
/>
```

**Wireframe:**
```
┌─────────────────────────────────────────────────┐
│ ← Back          Map Attributes          [3/3]   │
├─────────────────────────────────────────────────┤
│                                                  │
│ Map import columns to database attributes       │
│ 12 columns • 8 auto-matched • 4 unmapped        │
│                                                  │
│ ┌──────────────────┬──────────────────────────┐│
│ │ File Column      │ → Database Attribute     ││
│ ├──────────────────┼──────────────────────────┤│
│ │ color           │ [color ▼] ✓ 98%         ││
│ │ size            │ [size ▼] ✓ 95%          ││
│ │ screen_size     │ [Create new... +]        ││
│ │ weight_kg       │ [weight ▼] ⚠ 75%        ││
│ │ ...             │                          ││
│ └──────────────────┴──────────────────────────┘│
│                                                  │
│ [+ Create New Attribute]                         │
│                                                  │
│              [← Back]  [Continue →]             │
└─────────────────────────────────────────────────┘
```

**Create New Attribute Modal:**
```
┌─────────────────────────────────────────┐
│ Create New Attribute                    │
├─────────────────────────────────────────┤
│                                          │
│ Code*: [screen_size_____________]       │
│                                          │
│ Data Type*: [Number ▼]                  │
│                                          │
│ □ Value is translatable                 │
│                                          │
│ Slot (order): [5____]                   │
│                                          │
│              [Cancel]  [Create]         │
└─────────────────────────────────────────┘
```

---

#### 2.4 Category Assignment (`/imports/{id}/assign-category`)

**Components:**
- **Category Tree Selector**: Hierarchical category browser
- **Search**: Quick category search
- **Preview**: Shows how many products will be assigned
- **Batch Assignment**: Option to split by category

**Wireframe:**
```
┌─────────────────────────────────────────────────┐
│ ← Back       Assign Category            [4/4]   │
├─────────────────────────────────────────────────┤
│                                                  │
│ Select a category for these products            │
│                                                  │
│ Search: [____________🔍]                        │
│                                                  │
│ ┌────────────────────────────────────────────┐ │
│ │ ▼ Electronics                              │ │
│ │   ▼ Phones                                 │ │
│ │     • Smartphones            [Select →]   │ │
│ │     • Feature Phones         [Select →]   │ │
│ │   ▶ Tablets                                │ │
│ │   ▶ Accessories                            │ │
│ │ ▶ Home & Garden                            │ │
│ │ ▶ Sports & Outdoors                        │ │
│ └────────────────────────────────────────────┘ │
│                                                  │
│ Selected: Electronics > Phones > Smartphones    │
│ Will assign to: 1,500 products                  │
│                                                  │
│              [← Back]  [Confirm Import]         │
└─────────────────────────────────────────────────┘
```

---

### 3. Translation Management

#### 3.1 Translation Tasks List (`/translations/tasks`)

**Components:**
- **Task Cards**: Status, locale, progress
- **Filters**: Status, locale, date range
- **Create New Button**: Launch translation task
- **Progress Indicators**: Real-time updates

**Wireframe:**
```
┌─────────────────────────────────────────────────┐
│ Translations                [+ New Task]         │
├─────────────────────────────────────────────────┤
│                                                  │
│ Filters: [All Statuses ▼] [All Locales ▼]      │
│                                                  │
│ ┌────────────────────────────────────────────┐ │
│ │ 🇫🇷 French Translation - Products          │ │
│ │ Status: In Progress  ████████░░ 80%        │ │
│ │ 800/1000 completed  • Started 2h ago      │ │
│ │                        [View Details →]    │ │
│ └────────────────────────────────────────────┘ │
│                                                  │
│ ┌────────────────────────────────────────────┐ │
│ │ 🇩🇪 German Translation - Attributes        │ │
│ │ Status: Done  ████████████ 100%            │ │
│ │ 450/450 completed  • 1 day ago            │ │
│ │                        [View →]            │ │
│ └────────────────────────────────────────────┘ │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

#### 3.2 Review Translations (`/translations/{task_id}/review`)

**Components:**
- **Side-by-side View**: Source vs Translation
- **Edit Mode**: Inline editing
- **Bulk Actions**: Approve all, reject selected
- **Quality Indicators**: Flagged translations

**Wireframe:**
```
┌─────────────────────────────────────────────────┐
│ ← Back    French Translation - Review           │
├─────────────────────────────────────────────────┤
│                                                  │
│ Progress: 800/1000 ████████░░ 80%              │
│ [Approve All]  [Approve Selected]               │
│                                                  │
│ ┌──────────────────┬──────────────────────────┐│
│ │ Source (en)      │ Translation (fr)         ││
│ ├──────────────────┼──────────────────────────┤│
│ │ Premium Headset  │ Casque Premium    [✓][✗]││
│ │                  │ [Edit ✏]                ││
│ ├──────────────────┼──────────────────────────┤│
│ │ Wireless Mouse   │ Souris Sans Fil   [✓][✗]││
│ │                  │ [Edit ✏]                ││
│ ├──────────────────┼──────────────────────────┤│
│ │ ...              │ ...                      ││
│ └──────────────────┴──────────────────────────┘│
│                                                  │
│ [1] [2] [3] ... [40]        Showing 1-25 of 1K │
└─────────────────────────────────────────────────┘
```

---

### 4. Keyword Research

#### 4.1 Keyword Planner (`/keywords/planner`)

**Components:**
- **Configuration Form**: Locale, category, seeds
- **Seed Suggestions**: Auto-populated from category
- **Negative Keywords Input**: Multi-input field
- **Run Button**: Start fetching

**Wireframe:**
```
┌─────────────────────────────────────────────────┐
│ ← Back         Keyword Research                  │
├─────────────────────────────────────────────────┤
│                                                  │
│ Create New Keyword Run                           │
│                                                  │
│ Locale*: [English (US) ▼]                      │
│                                                  │
│ Category*: [Electronics > Phones > Smartphones] │
│            [Browse... 📁]                       │
│                                                  │
│ Seed Keywords:                                   │
│ ┌────────────────────────────────────────────┐ │
│ │ smartphone                        [✗]      │ │
│ │ mobile phone                      [✗]      │ │
│ │ [+ Add seed keyword]                       │ │
│ └────────────────────────────────────────────┘ │
│                                                  │
│ Negative Keywords:                               │
│ ┌────────────────────────────────────────────┐ │
│ │ broken                            [✗]      │ │
│ │ used                              [✗]      │ │
│ │ [+ Add negative keyword]                   │ │
│ └────────────────────────────────────────────┘ │
│                                                  │
│ Channel: [Google Ads ▼]                         │
│                                                  │
│              [Cancel]  [Start Research →]       │
└─────────────────────────────────────────────────┘
```

---

#### 4.2 Keyword Results (`/keywords/runs/{run_id}`)

**Components:**
- **Results Table**: Keywords with metrics
- **Filters**: Min searches, max competition, CPC range
- **Sorting**: By searches, competition, CPC
- **Bulk Selection**: Approve/reject multiple
- **Export**: Download results

**Table Columns:**
- Keyword
- Avg Searches
- Competition
- CPC
- Concepts/Tags
- Actions (Approve/Reject)

**Wireframe:**
```
┌─────────────────────────────────────────────────┐
│ ← Back    Keyword Run Results                    │
├─────────────────────────────────────────────────┤
│ Run ID: abc-123  • Completed 10m ago            │
│ 1,250 keywords found  • 450 approved            │
│                                                  │
│ Filters:                                         │
│ Min Searches: [100____] Competition: [0.5___]   │
│ [Apply Filters]  [Clear]  [Export CSV ↓]       │
│                                                  │
│ [✓ Select All]  [Approve Selected] [Reject]    │
│                                                  │
│ ┌───┬──────────────┬────────┬──────┬────┬────┐ │
│ │☐ │ Keyword      │Searches│Comp  │CPC │Tag ││
│ ├───┼──────────────┼────────┼──────┼────┼────┤ │
│ │☑ │best smartpho…│ 5,400  │ 0.42 │1.25│Head││
│ │☐ │cheap phone   │ 3,200  │ 0.65 │0.85│Inte││
│ │☐ │5g smartphone │ 2,800  │ 0.50 │1.10│Feat││
│ │   │ ...          │        │      │    │    ││
│ └───┴──────────────┴────────┴──────┴────┴────┘ │
│                                                  │
│ Showing 1-50 of 1,250          [1][2][3]...[25]│
└─────────────────────────────────────────────────┘
```

---

### 5. Keyword-Product Mapping

#### 5.1 Mapping Interface (`/keywords/mappings/{run_id}`)

**Components:**
- **Product-Keyword Matrix**: Shows mappings
- **Confidence Filter**: Slider to filter by confidence
- **Match Type Filter**: Filter by source (enum, text, etc.)
- **Evidence Viewer**: Shows why keyword matched
- **Manual Override**: Manually add/remove mappings

**Wireframe:**
```
┌─────────────────────────────────────────────────┐
│ ← Back    Keyword-Product Mappings               │
├─────────────────────────────────────────────────┤
│ Run: abc-123  • 450 approved keywords           │
│ 1,234 products  • 3,890 mappings                │
│                                                  │
│ Min Confidence: ●────────── 0.5                 │
│ Source: [All ▼] [Enum Map ▼] [Text Match ▼]    │
│                                                  │
│ ┌────────────────────────────────────────────┐ │
│ │ Keyword: "red smartphone"                  │ │
│ │ ────────────────────────────────────────── │ │
│ │ Matched Products (12):                     │ │
│ │                                             │ │
│ │ • Apple iPhone 15 - Red    📊 85% ✓       │ │
│ │   Matched: color="Red"                     │ │
│ │   [View Evidence] [Remove Mapping]         │ │
│ │                                             │ │
│ │ • Samsung Galaxy S24 - Red 📊 82% ✓       │ │
│ │   Matched: color="Red"                     │ │
│ │   [View Evidence] [Remove Mapping]         │ │
│ │                                             │ │
│ │ [+ Add Product Manually]                   │ │
│ └────────────────────────────────────────────┘ │
│                                                  │
│              [← Back]  [Validate Mappings →]    │
└─────────────────────────────────────────────────┘
```

---

### 6. Content Generation

#### 6.1 Generation Interface (`/content/generate`)

**Components:**
- **Product Selector**: Choose products or variant groups
- **Template Selector**: Choose or create template
- **Custom Prompt Input**: Additional AI instructions
- **Preview Panel**: Live preview with sample product
- **Generate Button**: Start generation

**Wireframe:**
```
┌─────────────────────────────────────────────────┐
│ ← Back       Generate Product Content            │
├─────────────────────────────────────────────────┤
│                                                  │
│ Step 1: Select Products                          │
│ ┌────────────────────────────────────────────┐ │
│ │ Category: Electronics > Smartphones        │ │
│ │ [✓] Select all (1,234 products)            │ │
│ │ [ ] Select variant groups (45 groups)      │ │
│ └────────────────────────────────────────────┘ │
│                                                  │
│ Step 2: Choose Template                          │
│ [Premium Smartphone Template ▼]                 │
│ Title: {brand} {model} - {color} {storage}      │
│ [Edit Template] [Create New]                    │
│                                                  │
│ Step 3: AI Instructions (Optional)               │
│ ┌────────────────────────────────────────────┐ │
│ │ Focus on:                                   │ │
│ │ • Premium features                          │ │
│ │ • Sustainability aspects                    │ │
│ │ • Target audience: professionals           │ │
│ │                                             │ │
│ └────────────────────────────────────────────┘ │
│                                                  │
│ Preview (Apple iPhone 15):                       │
│ ┌────────────────────────────────────────────┐ │
│ │ Title: Apple iPhone 15 - Premium Blue...  │ │
│ │ Description: Experience sustainable...     │ │
│ └────────────────────────────────────────────┘ │
│                                                  │
│              [Cancel]  [Generate Content →]     │
└─────────────────────────────────────────────────┘
```

---

#### 6.2 Review Generated Content (`/content/jobs/{job_id}`)

**Components:**
- **Status Panel**: Progress, completed count
- **Content Cards**: Each product's generated content
- **Edit Mode**: Inline editing
- **Regenerate**: For individual products
- **Bulk Actions**: Approve all, approve selected

**Wireframe:**
```
┌─────────────────────────────────────────────────┐
│ ← Back    Content Generation Results             │
├─────────────────────────────────────────────────┤
│ Job: xyz-789  • Status: Completed               │
│ 1,234/1,234 products ████████████ 100%         │
│                                                  │
│ [Approve All]  [Approve Selected]  [Export]    │
│                                                  │
│ ┌────────────────────────────────────────────┐ │
│ │ [✓] Apple iPhone 15 - Blue 128GB           │ │
│ │                                             │ │
│ │ Generated Title:                            │ │
│ │ Apple iPhone 15 - Premium Blue Smartphone  │ │
│ │ with 128GB Storage                         │ │
│ │ [Edit ✏]                                   │ │
│ │                                             │ │
│ │ Generated Description:                      │ │
│ │ Experience sustainable luxury with the...  │ │
│ │ [Edit ✏]  [Show More ▼]                   │ │
│ │                                             │ │
│ │ Tokens: 250  Time: 2.5s  Model: GPT-4     │ │
│ │                                             │ │
│ │         [Regenerate]  [Approve]  [Reject]  │ │
│ └────────────────────────────────────────────┘ │
│                                                  │
│ ┌────────────────────────────────────────────┐ │
│ │ [✓] Samsung Galaxy S24 - Black 256GB       │ │
│ │ ...                                         │ │
│ └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

---

### 7. Export

#### 7.1 Export Configuration (`/exports/create`)

**Components:**
- **Format Selector**: CSV, Excel, JSON
- **Locale Selector**: Multi-select checkboxes
- **Data Options**: Checkboxes for what to include
- **Filter Panel**: Product type, status, date range
- **Preview**: Estimated rows and columns

**Wireframe:**
```
┌─────────────────────────────────────────────────┐
│ ← Back         Export Products                   │
├─────────────────────────────────────────────────┤
│                                                  │
│ Export Format:                                   │
│ ( ) CSV  (•) Excel  ( ) JSON                    │
│                                                  │
│ Locales to Include:                              │
│ [✓] English (en)                                │
│ [✓] French (fr)                                 │
│ [✓] German (de)                                 │
│ [ ] Spanish (es)                                │
│                                                  │
│ Data to Include:                                 │
│ [✓] Product details                             │
│ [✓] Variants                                    │
│ [✓] Attributes                                  │
│ [✓] Translations                                │
│ [✓] Keywords                                    │
│ [ ] Keyword metrics                             │
│                                                  │
│ Filters:                                         │
│ Category: [All Categories ▼]                    │
│ Status:   [Active ▼]                            │
│ Brand:    [All Brands ▼]                        │
│                                                  │
│ ───────────────────────────────────────────────│
│ Estimated: 1,234 products • ~2.5 MB            │
│                                                  │
│              [Cancel]  [Create Export →]        │
└─────────────────────────────────────────────────┘
```

---

## Component Library

### Reusable Components

#### DataTable
```tsx
interface DataTableProps {
  columns: Column[]
  data: any[]
  sortable?: boolean
  filterable?: boolean
  selectable?: boolean
  onRowClick?: (row: any) => void
  onSelectionChange?: (selected: any[]) => void
}
```

#### ProgressBar
```tsx
interface ProgressBarProps {
  value: number // 0-100
  max?: number
  variant?: 'primary' | 'success' | 'warning' | 'danger'
  showLabel?: boolean
  animated?: boolean
}
```

#### FileUpload
```tsx
interface FileUploadProps {
  accept: string
  maxSize: number
  multiple?: boolean
  onUpload: (files: File[]) => void
  onError?: (error: string) => void
}
```

#### StatusBadge
```tsx
interface StatusBadgeProps {
  status: 'pending' | 'processing' | 'completed' | 'failed'
  size?: 'sm' | 'md' | 'lg'
}
```

---

## State Management

### Zustand Stores

#### Import Store
```typescript
interface ImportState {
  currentImport: ProductImport | null
  setCurrentImport: (import: ProductImport) => void
  updateStatus: (id: string, status: string) => void
}
```

#### Translation Store
```typescript
interface TranslationState {
  tasks: TranslationTask[]
  fetchTasks: () => Promise<void>
  createTask: (config: TaskConfig) => Promise<void>
}
```

#### Keyword Store
```typescript
interface KeywordState {
  runs: PlannerRun[]
  currentRun: PlannerRun | null
  keywords: Keyword[]
  fetchKeywords: (runId: string) => Promise<void>
}
```

---

## Responsive Design

### Breakpoints
```css
sm: 640px
md: 768px
lg: 1024px
xl: 1280px
2xl: 1536px
```

### Mobile Considerations
- Tables collapse to cards on mobile
- Side-by-side views stack vertically
- Sticky headers on tables
- Bottom navigation for wizards

---

## Accessibility

- **ARIA labels** on all interactive elements
- **Keyboard navigation** support
- **Focus indicators** clearly visible
- **Color contrast** WCAG AA compliant
- **Screen reader** friendly

---

## Performance

- **Lazy loading** for tables with 100+ rows
- **Virtual scrolling** for large datasets
- **Debounced search** inputs
- **Optimistic updates** for better UX
- **Cached API responses** with React Query

---

## Notifications

### Toast Notifications
```typescript
toast.success('Import completed successfully')
toast.error('Failed to generate content')
toast.warning('Some translations need review')
toast.info('Export ready for download')
```

### Real-time Updates
- WebSocket connection for job progress
- Live status updates
- Progress bar animations

---

This completes the frontend interface specifications. All components follow modern UX patterns with a focus on clarity, efficiency, and user control.
