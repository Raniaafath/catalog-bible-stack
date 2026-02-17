# Documentation Index

## ⭐ Simple Grouping Workflow (Recommended)

**Simple, user-controlled product grouping:**

1. **[SIMPLE_GROUPING_WORKFLOW.md](SIMPLE_GROUPING_WORKFLOW.md)** - Complete guide (START HERE!)
2. **[examples/manual_grouping_example.py](examples/manual_grouping_example.py)** - Runnable example

**How it works:**
- Choose category → Import CSV → Create variants (standalone)
- User selects variants → Choose marketplace → System shows differences
- User picks variation axes → Create product group

---

## 🚀 Quick Start Guides (Original Auto-Grouping)

**Using the automatic PRODUCT_KEY grouping:**

1. **[START_HERE.md](START_HERE.md)** - Overview and quick links
2. **[QUICK_START.md](QUICK_START.md)** - Step-by-step tutorial
3. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick reference card

## 📘 User Guides

### Import System
- **[FRONTEND_MAPPING_GUIDE.md](FRONTEND_MAPPING_GUIDE.md)** - How to use the mapping UI
- **[CSV_STRUCTURE_EXAMPLES.md](CSV_STRUCTURE_EXAMPLES.md)** - CSV format options
- **[VISUAL_IMPORT_FLOW.md](VISUAL_IMPORT_FLOW.md)** - Visual diagrams
- **[WHAT_IMPORT_DOES.md](WHAT_IMPORT_DOES.md)** - Technical details

### Example Files
- **[examples/products_import_example.csv](examples/products_import_example.csv)** - Sample data (all variants)
- **[examples/products_import_parent_variant.csv](examples/products_import_parent_variant.csv)** - Sample data (parent + variants)
- **[examples/README.md](examples/README.md)** - Example file explanations

## 📚 Technical Documentation

### Architecture
- **[GROUPING_AND_MARKETPLACE_AXES.md](GROUPING_AND_MARKETPLACE_AXES.md)** - Product family vs listing group, and how variation axes are resolved (catalog vs marketplace)

### Development
- **[API_GUIDE.md](API_GUIDE.md)** - API endpoints and usage
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment instructions
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
- **[project_overview.md](project_overview.md)** - Project architecture

### Updates
- **[IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)** - Feature checklist
- **[NEW_MODELS.md](NEW_MODELS.md)** - Database model documentation

## 🎯 Choose Your Path

### I want to import products NOW
→ Go to [QUICK_START.md](QUICK_START.md)

### I want to understand the UI
→ Go to [FRONTEND_MAPPING_GUIDE.md](FRONTEND_MAPPING_GUIDE.md)

### I want to see CSV examples
→ Go to [CSV_STRUCTURE_EXAMPLES.md](CSV_STRUCTURE_EXAMPLES.md)

### I want technical details
→ Go to [WHAT_IMPORT_DOES.md](WHAT_IMPORT_DOES.md)

### I want a quick reference
→ Go to [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

---

## 📖 Documentation Overview

This import system handles **parent-variant products** (products with multiple variations like color/size):

1. **Upload CSV** with product and variant data
2. **Assign category** to group imports
3. **Map columns** to database fields/attributes
4. **Auto-detect** variation axes (color, size, etc.)
5. **Store** products, variants, and axes
6. **Generate titles** later using stored axes

**Key Feature:** The frontend now has **search functionality** instead of auto-suggestions for accurate mapping.

---

## 🔄 Two Workflows: Auto vs Manual Grouping

### Manual Grouping (NEW - Recommended)

**When to use:**
- You want full control over grouping
- Different channels need different axes
- You want to review variants before grouping

**How it works:**
```
CSV Import → Variants Created (standalone) → User Reviews → 
User Selects Variants → System Shows Differences → 
User Picks Axes → Product Group Created
```

**Key setting:** `group_by_product_key: false` (default)

**API:** `POST /api/v1/variants/compare/` + `POST /api/v1/variants/group-with-axes/`

📖 **Read:** [SIMPLE_GROUPING_WORKFLOW.md](SIMPLE_GROUPING_WORKFLOW.md)

---

### Auto Grouping (Original)

**When to use:**
- Your CSV has a `PRODUCT_KEY` column
- Variants are pre-grouped in your data
- You want automatic, immediate grouping

**How it works:**
```
CSV Import → System Groups by PRODUCT_KEY → 
Products Created → Variants Attached → Axes Detected
```

**Key setting:** `group_by_product_key: true` (set explicitly)

**CSV Column:** `PRODUCT_KEY` (or `parent_id`, `model`, etc.)

📖 **Read:** [QUICK_START.md](QUICK_START.md) for auto-grouping workflow

---

## 📊 Workflow Comparison

| Feature | Manual Grouping | Auto Grouping |
|---------|----------------|---------------|
| **Control** | Full user control | Automatic |
| **Timing** | After import | During import |
| **Flexibility** | Regroup anytime | Fixed at import |
| **Channel-specific axes** | ✅ Yes | ⚠️ Limited |
| **Review before grouping** | ✅ Yes | ❌ No |
| **Best for** | Multiple channels | Single channel |
| **CSV requirement** | SKU only | PRODUCT_KEY needed |

**Recommendation:** Use **Manual Grouping** for maximum flexibility.
