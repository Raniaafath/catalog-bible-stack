# Quick Reference Card - Import Mapping

## 🚀 Quick Start (30 seconds)

1. Upload CSV with parent-variant structure
2. Assign category to this import batch
3. Map columns using search (no auto-suggestions)
4. Click "Complete Import"

---

## 🔑 Essential Mappings

| CSV Column Contains | Map To | Notes |
|-------------------|--------|-------|
| Parent/Group ID | `🔑 Parent Product ID` | Groups variants together |
| Variant unique ID | `Variant SKU` | Each variant must have unique ID |
| Brand name | `Product Brand` | Same across all variants |
| Product title | `Product Source Title` | Same across all variants |
| Color, Size, Material | Search for attribute | Will be variation axes |
| Price, Stock, Barcode | Search for attribute | Variant-specific data |

---

## 🔍 How to Use Search

### In the Mapping Dropdown:
1. Click dropdown for a column
2. See search box at top: `🔎 Search attributes...`
3. Type attribute name (e.g., "color", "size")
4. List filters as you type
5. Select from filtered results

### Search Tips:
- **Partial match works**: Type "col" to find "color"
- **Case insensitive**: "SIZE" = "size"
- **Per-column search**: Each column has own search
- **Clear search**: Delete text to see all again

---

## ✅ What Gets Auto-Detected?

### Variation Axes (Automatic)
System detects attributes that:
- Have 2-20 unique values
- Differ between variants of same product
- Are used consistently

**Example:**
- `color`: Red, Blue, Green → ✓ Detected
- `size`: S, M, L, XL → ✓ Detected
- `price`: 100 different values → ✗ Not detected (too many)

### Priority Order (Automatic)
System assigns priority 1-5:
1. First variation axis (often color)
2. Second variation axis (often size)
3. Third variation axis
4. Fourth variation axis
5. Fifth variation axis

---

## 📊 Table Columns Explained

| Column | What It Shows | Action |
|--------|--------------|--------|
| **File Column** | CSV column name | Read only |
| **Sample Data** | Preview from file | Review to verify |
| **Mapping** | Where to map this column | **SELECT HERE** |
| **Create New** | Create new attribute? | Check if attribute doesn't exist |
| **Variation Axis** | Will this be a variation axis? | Auto-detected (read only) |

---

## ⚠️ Common Mistakes to Avoid

| ❌ Don't Do This | ✅ Do This Instead |
|----------------|------------------|
| Skip Parent Product ID | Always map parent_id column |
| Map to wrong attribute type | Use search to find exact match |
| Forget Variant SKU | Each variant needs unique SKU |
| Create duplicate attributes | Search first, create only if missing |
| Ignore variation axis column | Review it to verify detection |

---

## 🎯 Verification Checklist

Before clicking "Complete Import":

- [ ] Parent Product ID mapped (if column exists)
- [ ] Variant SKU mapped
- [ ] Product fields (brand, title) mapped
- [ ] Variant attributes searched and mapped
- [ ] Variation axis column shows correct axes
- [ ] No unmapped columns (or intentionally skipped)
- [ ] Sample data looks correct

---

## 🔧 Field Types Quick Reference

### Product Fields (Same for all variants)
- Product Code
- Product Brand
- Product Model
- Product Series
- Product Source Title
- Product Source Description
- Product Status
- Product Source Supplier

### Variant Fields (Different per variant)
- Variant SKU ← **REQUIRED**
- Variant Barcode
- Variant MPN

### Special Fields
- 🔑 Parent Product ID ← Groups variants
- Any attribute (color, size, etc.) ← Via search

---

## 💡 Pro Tips

1. **Parent ID is optional** but recommended
   - With parent_id: Explicit grouping
   - Without parent_id: System groups by shared fields

2. **Use consistent naming**
   - All SKUs should follow same pattern
   - Makes variant grouping more reliable

3. **Review sample data**
   - Check if values look correct
   - Verify variation axes make sense

4. **Start simple**
   - Test with 1-2 products first
   - Then import full catalog

5. **Create new attributes carefully**
   - Check if attribute exists first
   - Use consistent data types (text, choice, etc.)

---

## 🚨 Troubleshooting

### "I can't find my attribute"
→ Use search box, type partial name
→ Check if attribute exists in system
→ Create new if truly missing

### "Wrong columns marked as variation axes"
→ This is auto-detected from data patterns
→ Verify data has 2-20 unique values
→ Adjust after import if needed

### "Variants not grouping correctly"
→ Check Parent Product ID mapping
→ Verify same parent_id for all variants
→ Review sample data

### "Search not working"
→ Make sure you're typing in the search box
→ Check spelling
→ Try shorter/partial terms

---

## 📚 More Help

- [Frontend Mapping Guide](FRONTEND_MAPPING_GUIDE.md) - Complete UI guide
- [CSV Examples](CSV_STRUCTURE_EXAMPLES.md) - File format options
- [Visual Flow](VISUAL_IMPORT_FLOW.md) - Step-by-step diagrams
- [Quick Start](QUICK_START.md) - Full tutorial

---

## 🎓 Example Mapping

```
CSV Columns:
  parent_id  → 🔑 Parent Product ID
  sku        → Variant SKU
  brand      → Product Brand
  title      → Product Source Title
  color      → 🔍 Search "color" → ⚡ color ✓ Variation axis
  size       → 🔍 Search "size"  → ⚡ size  ✓ Variation axis
  price      → 🔍 Search "price" → ⚡ price
  stock      → 🔍 Search "stock" → ⚡ stock
```

**Result:**
- 1 Product with multiple variants
- 2 Variation axes (color, size)
- Ready for title generation later

