# Listing Group Workflow - Current Status

## ✅ What's Already Working

### 1. Create Listing Group
- **Location:** `/groups` → "New Listing Group" button
- **What it does:**
  - Select Product
  - Select Channel/Marketplace
  - Optional: Add a name
  - Creates empty listing group
- **Status:** ✅ **WORKING**

### 2. Add Variants to Listing Group
- **Location:** `/groups/{id}` → "Variants" tab → "Add Variants" button
- **What it does:**
  - Shows all variants from the same product
  - Select which variants to add
  - Moves variants to this listing group
  - Removes them from any other listing on the same channel
- **Status:** ✅ **WORKING**

### 3. Detect Variation Axes
- **Location:** `/groups/{id}` → "Variation Axes" tab
- **What it does:**
  - Automatically analyzes variants in the listing
  - Shows which attributes differ between variants
  - Suggests good candidates for variation axes (2-10 unique values, no missing data)
  - Shows common attributes (same across all variants)
- **Status:** ✅ **WORKING**

### 4. Set Variation Axes
- **Location:** `/groups/{id}` → "Variation Axes" tab
- **What it does:**
  - Check/uncheck attributes to use as axes
  - Order matters (first axis = position 0)
  - Saves axes to `ChannelListingAxis` table
- **Status:** ✅ **WORKING**

### 5. Generate Titles for Listing Group
- **Location:** ❌ **NOT IMPLEMENTED**
- **What it should do:**
  - Generate titles for ALL variants in the listing
  - Use the listing's specific axes (`ChannelListingAxis`)
  - Generate titles based on marketplace + locale
- **Status:** ❌ **MISSING**

---

## Current Workflow (What You Can Do Now)

```
1. Create Listing Group
   └─> Select Product + Channel
   
2. Add Variants
   └─> Go to listing detail page
   └─> Click "Add Variants"
   └─> Select variants to group
   
3. Detect & Set Axes
   └─> Go to "Variation Axes" tab
   └─> System shows detected differences
   └─> Check attributes you want as axes
   └─> Click "Save Axes"
   
4. Generate Titles ❌
   └─> NOT YET AVAILABLE
   └─> Need to use individual variant title generation
```

---

## What Needs to Be Added

### 1. Update Title Renderer to Use Listing Axes

**File:** `pub/services/title_renderer.py`

**Current behavior:**
- Uses `ProductVariantAxis` (global axes) only

**Needed:**
- Check if variant belongs to a `ChannelListing`
- Use `ChannelListingAxis` if available (highest priority)
- Fall back to `ChannelVariantAxis` (product+channel)
- Fall back to `ProductVariantAxis` (global)

**Priority resolution:**
```
1. ChannelListingAxis (listing-specific) ← Highest
2. ChannelVariantAxis (product+channel) ← Middle
3. ProductVariantAxis (global) ← Lowest
```

### 2. Add API Endpoint for Listing Group Title Generation

**New endpoint:** `POST /api/v1/channel-listings/{id}/generate-titles/`

**Request:**
```json
{
  "locale_code": "en",
  "planner_run_id": 123,  // optional
  "include_descriptions": false
}
```

**Response:**
```json
{
  "status": "completed",
  "listing_id": 1,
  "variant_count": 5,
  "outputs": [
    {
      "variant_id": 557,
      "title": "Mountain Bike Pro - Red Medium",
      "status": "generated"
    },
    ...
  ]
}
```

### 3. Add UI Button in GroupDetail Page

**Location:** `frontend/src/pages/groups/GroupDetail.tsx`

**Add:**
- "Generate Titles" button in the listing detail page
- Dialog to select locale
- Show progress/results after generation
- Display generated titles for each variant

---

## Example Workflow (Once Complete)

```
1. Create Listing Group
   Product: "BIKE-001"
   Channel: "eBay"
   Name: "Red variants only"
   
2. Add Variants
   - BIKE-001-RED-S
   - BIKE-001-RED-M
   - BIKE-001-RED-L
   
3. Detect Axes
   System detects:
   - color: Red (same, not an axis)
   - size: S, M, L (different, good axis!)
   
4. Set Axes
   ✅ size (position 0)
   
5. Generate Titles
   Locale: "en"
   Results:
   - BIKE-001-RED-S → "Mountain Bike Pro - Small"
   - BIKE-001-RED-M → "Mountain Bike Pro - Medium"
   - BIKE-001-RED-L → "Mountain Bike Pro - Large"
```

---

## Database Tables Used

1. **`pub_channellisting`** - The listing group
2. **`pub_channellistingmap`** - Variant → Listing mapping
3. **`catalog_channellistingaxis`** - Axes for this listing
4. **`pub_generationoutput`** - Generated titles (when implemented)

---

## Summary

**✅ Working:**
- Create listing groups
- Add/remove variants
- Detect variation axes
- Set variation axes

**❌ Missing:**
- Generate titles for listing group (needs API endpoint + UI)
- Title renderer using listing axes (needs code update)

The foundation is solid! Just need to add title generation functionality that uses the listing's axes.
