# Attribute Research Features

## Overview
Enhanced search and research capabilities when mapping CSV columns to attributes, helping you find the right attribute quickly and understand what each attribute does.

---

## 🔍 Multi-Field Search

### Search Across 3 Fields
The search now looks in:
1. **Code** - The technical identifier (e.g., "color", "size")
2. **Name** - The display name (e.g., "Product Color", "Item Size")
3. **Description** - The full explanation of what the attribute is for

### How It Works
```
Search term: "col"

Matches:
✓ code: "color" ← Found in code
✓ name: "Product Color" ← Found in name  
✓ description: "The color of the product" ← Found in description
```

### Example Searches
| Search For | Finds Attributes With |
|-----------|----------------------|
| "col" | color, collection, collar_type |
| "size" | size, size_unit, resize_option |
| "translate" | All translatable text attributes |
| "choice" | All choice/dropdown attributes |
| "warranty" | warranty_period, warranty_type |

---

## 💡 Hover Tooltips

### See Full Details
Hover over any attribute in the dropdown to see:

1. **Full Name** - The complete display name
2. **Description** - What the attribute is used for
3. **Data Type** - text, choice, number, date, etc.
4. **Translatable** - If values can be translated to multiple languages

### Tooltip Example
```
┌────────────────────────────────────────┐
│ Product Color                          │
│                                        │
│ The color or finish of the product    │
│ variant, used for differentiation     │
│                                        │
│ ────────────────────────────────────  │
│ Type: choice                           │
│ ✓ Translatable                        │
└────────────────────────────────────────┘
```

### When to Use Tooltips
- **Unsure which attribute?** Hover to read descriptions
- **Check data type** - Ensure it matches your CSV data
- **Translatable attributes** - See which support multiple languages
- **Verify before mapping** - Read full details before selecting

---

## 🎯 Visual Indicators

### Icons
- **🔎** - Search box (type to filter)
- **⚡** - Attribute item in list
- **❓** - Help icon (hover for search tips)

### Color Coding
- **Blue ✓** - Translatable attribute
- **Gray text** - Data type indicator
- **Muted text** - No results message

---

## 📖 Research Workflow

### Step-by-Step
1. **Open the dropdown** for a CSV column
2. **Read the help icon** tooltip for search tips
3. **Type in search box** - searches code, name, description
4. **Review filtered results** - see matching attributes
5. **Hover over options** - read full details in tooltip
6. **Select the right one** - click to map

### Best Practices
- **Start broad** - Type "col" instead of "color"
- **Read descriptions** - Hover to verify it's the right attribute
- **Check data type** - Match your CSV data format
- **Look for translatable** - If you need multi-language support
- **Create if missing** - Use "Create New" if nothing matches

---

## 🚀 Advanced Search Tips

### 1. Partial Matching
Type part of a word to find all matches:
- "trans" → translatable, transparency, transport
- "prod" → product_code, production_date, producer

### 2. Search by Type
Search for data type in description:
- "choice" → Finds dropdown/select attributes
- "text" → Finds text input attributes
- "number" → Finds numeric attributes

### 3. Search by Purpose
Search for what the attribute does:
- "variation" → Attributes used for product variations
- "price" → Pricing-related attributes
- "dimension" → Size/measurement attributes

### 4. Multilingual Search
Search in any language that appears in name/description:
- "couleur" → May find "color" if description mentions it
- "taille" → May find "size" if name includes it

---

## 🔄 Search vs Create New

### When to Search
- ✅ Standard attributes (color, size, brand)
- ✅ Common product properties
- ✅ System-defined fields
- ✅ Attributes used in other imports

### When to Create New
- ✅ Custom/unique product properties
- ✅ Industry-specific attributes
- ✅ Internal-only fields
- ✅ Nothing found in search

### Decision Tree
```
Does a similar attribute exist?
├─ Yes → Use search to find it
│         └─ Exact match? → Select it
│         └─ Close match? → Read tooltip, verify
└─ No  → Check "Create New"
          └─ System will create during import
```

---

## 💪 Power User Features

### 1. Per-Column Search State
Each column remembers its own search term:
- Column "color" → Search "col"
- Column "material" → Search "mat"
- Switch between columns - searches stay active

### 2. Quick Filter Reset
- Clear search box → See all attributes
- Type new term → Instant re-filter
- No page reload needed

### 3. Keyboard Navigation
- Tab to search box
- Type to filter
- Arrow keys to navigate results
- Enter to select
- Escape to close dropdown

---

## 📊 What You Can Research

### Attribute Properties
| Property | What It Tells You | Why It Matters |
|----------|------------------|----------------|
| **Code** | Technical identifier | Must be unique, used in code |
| **Name** | Display name | Shown to users in UI |
| **Description** | Full explanation | Understand purpose/usage |
| **Data Type** | text/choice/number/etc | Must match CSV data format |
| **Translatable** | Multi-language support | Important for global products |

### Data Type Meanings
- **text** - Free text input (e.g., description)
- **choice** - Dropdown/select (e.g., color, size)
- **number** - Numeric value (e.g., price, weight)
- **date** - Date field (e.g., release_date)
- **boolean** - Yes/No (e.g., is_featured)

---

## 🎓 Examples

### Example 1: Finding Color Attribute
```
1. Column: "couleur" (French CSV)
2. Type search: "col"
3. Results:
   ⚡ color (choice)
   ⚡ collection (text)
   ⚡ collar_type (choice)
4. Hover over "color":
   "Product Color
    The color or finish of the product
    Type: choice
    ✓ Translatable"
5. Select: color ← Perfect match!
```

### Example 2: Researching Price Attributes
```
1. Column: "prix_ht" (price before tax)
2. Type search: "price"
3. Results:
   ⚡ price (number)
   ⚡ price_currency (choice)
   ⚡ price_vat_included (boolean)
4. Hover over each to see:
   - price: "Base price of the variant"
   - price_currency: "Currency code (EUR, USD, etc.)"
   - price_vat_included: "Whether price includes VAT"
5. Select: price ← Base price matches!
```

### Example 3: No Match - Create New
```
1. Column: "internal_ref_code"
2. Type search: "internal"
3. Results: No matching attributes found
4. Check "Create New" checkbox
5. System will create "internal_ref_code" attribute
```

---

## ✅ Benefits

### Before Research Features ❌
- Scroll through long lists
- Guess which attribute is right
- No attribute details visible
- Uncertain about data types
- Create duplicates by mistake

### With Research Features ✅
- **Instant filtering** - Type to find
- **Full details** - Hover to see everything
- **Confident selection** - Know what you're choosing
- **Type checking** - Verify data compatibility
- **Avoid duplicates** - Find existing attributes first

---

## 🔗 Related Documentation
- [Frontend Mapping Guide](FRONTEND_MAPPING_GUIDE.md) - Complete UI walkthrough
- [Quick Reference](QUICK_REFERENCE.md) - Cheat sheet
- [Visual Flow](VISUAL_IMPORT_FLOW.md) - Process diagrams

