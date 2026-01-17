# API Endpoints Specification

Complete REST API specification for the product import and management workflow.

---

## Authentication

All endpoints require JWT authentication.

```
Authorization: Bearer <token>
```

---

## 1. Import Management

### Upload Product File
```http
POST /api/v1/imports/upload/
Content-Type: multipart/form-data

Body:
  file: <binary>
  category_code: string (optional)
  source: string (optional)

Response: 201 Created
{
  "import_id": "uuid",
  "file_name": "products.csv",
  "row_count": 1500,
  "status": "pending",
  "preview": {
    "products": [...],
    "variants": [...],
    "detected_columns": [...]
  },
  "validation_errors": [
    {
      "row": 5,
      "column": "price",
      "error": "Invalid number format"
    }
  ]
}
```

### Get Import Preview
```http
GET /api/v1/imports/{import_id}/preview/

Response: 200 OK
{
  "import_id": "uuid",
  "status": "pending",
  "products": [
    {
      "row": 1,
      "code": "PROD-001",
      "brand": "BrandX",
      "model": "Model Y",
      "variants": [
        {
          "sku": "VAR-001",
          "barcode": "1234567890",
          "attributes": {
            "color": "Red",
            "size": "Large"
          }
        }
      ]
    }
  ],
  "detected_columns": ["code", "brand", "model", "sku", "color", "size"]
}
```

### Map Attributes
```http
POST /api/v1/imports/{import_id}/map-attributes/

Body:
{
  "mappings": [
    {
      "file_column": "color",
      "attribute_code": "color",
      "create_if_missing": true,
      "data_type": "text"
    },
    {
      "file_column": "size",
      "attribute_code": "size",
      "create_if_missing": false
    }
  ]
}

Response: 200 OK
{
  "mapped_count": 2,
  "created_attributes": [
    {
      "code": "color",
      "data_type": "text"
    }
  ],
  "errors": []
}
```

### Assign Category
```http
POST /api/v1/imports/{import_id}/assign-category/

Body:
{
  "product_type_code": "electronics-phones",
  "product_codes": ["PROD-001", "PROD-002"]
}

Response: 200 OK
{
  "assigned_count": 2,
  "product_type": {
    "code": "electronics-phones",
    "main_category": "Electronics",
    "category_path": "Electronics > Phones"
  }
}
```

### Confirm Import
```http
POST /api/v1/imports/{import_id}/confirm/

Body:
{
  "create_products": true,
  "create_variants": true
}

Response: 200 OK
{
  "import_id": "uuid",
  "status": "processing",
  "products_created": 0,
  "variants_created": 0
}
```

### Get Import Status
```http
GET /api/v1/imports/{import_id}/status/

Response: 200 OK
{
  "import_id": "uuid",
  "status": "completed",
  "row_count": 1500,
  "processed_count": 1500,
  "products_created": 300,
  "variants_created": 1200,
  "errors": []
}
```

---

## 2. Attribute Management

### List Attributes
```http
GET /api/v1/attributes/
  ?search=color
  &data_type=text
  &product_type=electronics

Response: 200 OK
{
  "count": 25,
  "results": [
    {
      "id": 1,
      "code": "color",
      "data_type": "text",
      "is_value_translatable": true,
      "slot": 1,
      "label": "Color"
    }
  ]
}
```

### Create Attribute
```http
POST /api/v1/attributes/

Body:
{
  "code": "screen_size",
  "data_type": "number",
  "is_value_translatable": false,
  "slot": 5
}

Response: 201 Created
{
  "id": 15,
  "code": "screen_size",
  "data_type": "number",
  "is_value_translatable": false
}
```

### List Attribute Values
```http
GET /api/v1/attributes/{attribute_id}/values/

Response: 200 OK
{
  "attribute": {
    "id": 1,
    "code": "color"
  },
  "values": [
    {
      "id": 100,
      "value": "red",
      "label": "Red"
    }
  ]
}
```

---

## 3. Product Type (Category) Management

### List Product Types
```http
GET /api/v1/product-types/
  ?search=phone
  &is_active=true

Response: 200 OK
{
  "count": 10,
  "results": [
    {
      "id": 5,
      "code": "electronics-phones",
      "main_category": "Electronics",
      "category_path": "Electronics > Phones",
      "is_active": true,
      "parent": null,
      "children": [...]
    }
  ]
}
```

### Get Product Type Hierarchy
```http
GET /api/v1/product-types/hierarchy/

Response: 200 OK
{
  "tree": [
    {
      "code": "electronics",
      "label": "Electronics",
      "children": [
        {
          "code": "electronics-phones",
          "label": "Phones",
          "children": []
        }
      ]
    }
  ]
}
```

---

## 4. Translation Management

### Create Translation Task
```http
POST /api/v1/translations/create-task/

Body:
{
  "locale": "fr",
  "scope": "product",
  "target_ids": [1, 2, 3],
  "import_id": "uuid" (optional)
}

Response: 201 Created
{
  "task_id": "uuid",
  "locale": "fr",
  "scope": "product",
  "status": "pending",
  "target_count": 3
}
```

### Get Translation Task Status
```http
GET /api/v1/translations/tasks/{task_id}/

Response: 200 OK
{
  "task_id": "uuid",
  "locale": "fr",
  "scope": "product",
  "status": "in_progress",
  "progress": {
    "total": 3,
    "completed": 1,
    "failed": 0
  },
  "errors": []
}
```

### List Translation Tasks
```http
GET /api/v1/translations/tasks/
  ?locale=fr
  &status=done

Response: 200 OK
{
  "count": 5,
  "results": [
    {
      "task_id": "uuid",
      "locale": "fr",
      "scope": "product",
      "status": "done",
      "created_at": "2026-01-15T10:00:00Z"
    }
  ]
}
```

### Get Product Translation
```http
GET /api/v1/translations/{locale}/products/{product_id}/

Response: 200 OK
{
  "product_id": 1,
  "locale": "fr",
  "title": "Téléphone intelligent",
  "description": "Un excellent téléphone...",
  "meta_title": "",
  "meta_description": "",
  "slug": "telephone-intelligent",
  "attributes": [
    {
      "attribute_code": "color",
      "value_text": "Rouge"
    }
  ]
}
```

### Update Product Translation
```http
PATCH /api/v1/translations/{locale}/products/{product_id}/

Body:
{
  "title": "Nouveau titre",
  "description": "Nouvelle description",
  "attributes": [
    {
      "attribute_code": "color",
      "value_text": "Rouge foncé"
    }
  ]
}

Response: 200 OK
{
  "product_id": 1,
  "locale": "fr",
  "updated": true
}
```

---

## 5. Keyword Research (Google Ads)

### Create Planner Run
```http
POST /api/v1/keywords/planner-run/

Body:
{
  "locale": "en",
  "product_type_code": "electronics-phones",
  "channel_id": 1,
  "seed_terms": ["smartphone", "mobile phone"],
  "negative_terms": ["broken", "used"],
  "auto_seed_from_category": true
}

Response: 201 Created
{
  "run_id": "uuid",
  "locale": "en",
  "product_type": "electronics-phones",
  "status": "pending",
  "seed_count": 2
}
```

### Get Planner Run Status
```http
GET /api/v1/keywords/planner-run/{run_id}/

Response: 200 OK
{
  "run_id": "uuid",
  "status": "completed",
  "locale": "en",
  "product_type": "electronics-phones",
  "keywords_fetched": 1250,
  "started_at": "2026-01-15T10:00:00Z",
  "completed_at": "2026-01-15T10:05:30Z"
}
```

### Get Planner Run Keywords
```http
GET /api/v1/keywords/planner-run/{run_id}/keywords/
  ?min_searches=100
  &max_competition=0.5
  &status=suggested
  &page=1
  &page_size=50

Response: 200 OK
{
  "count": 1250,
  "next": "/api/v1/keywords/planner-run/{run_id}/keywords/?page=2",
  "previous": null,
  "results": [
    {
      "keyword_id": 500,
      "term": "best smartphone 2026",
      "normalized_term": "best smartphone 2026",
      "status": "suggested",
      "metrics": {
        "avg_searches": 5400,
        "competition": 0.42,
        "cpc": 1.25
      },
      "concepts": [
        {
          "type": "head_term",
          "confidence": 0.95
        }
      ]
    }
  ]
}
```

### Approve/Reject Keywords
```http
PATCH /api/v1/keywords/planner-run/{run_id}/bulk-update/

Body:
{
  "keyword_ids": [500, 501, 502],
  "status": "approved"
}

Response: 200 OK
{
  "updated_count": 3
}
```

---

## 6. Keyword Parsing & Classification

### Parse Keywords
```http
POST /api/v1/keywords/parse-and-clean/

Body:
{
  "run_id": "uuid",
  "remove_sizes": true,
  "remove_marketplace_names": true,
  "remove_brands": false
}

Response: 202 Accepted
{
  "job_id": "uuid",
  "status": "processing"
}
```

### Get Keyword Classifications
```http
GET /api/v1/keywords/classifications/{run_id}/
  ?concept_type=head_term
  &min_confidence=0.7

Response: 200 OK
{
  "run_id": "uuid",
  "keywords": [
    {
      "keyword_id": 500,
      "term": "best smartphone 2026",
      "cleaned_term": "best smartphone",
      "concepts": [
        {
          "concept_type": "head_term",
          "concept_code": "smartphone",
          "confidence": 0.95,
          "tagged_by": "llm"
        },
        {
          "concept_type": "intent",
          "concept_code": "best",
          "confidence": 0.88,
          "tagged_by": "rule"
        }
      ],
      "parse": {
        "tokens": ["best", "smartphone", "2026"],
        "phrases": ["best smartphone", "smartphone 2026"],
        "detected": {
          "year": "2026",
          "intent": "best"
        }
      }
    }
  ]
}
```

### Update Keyword Concepts
```http
PATCH /api/v1/keywords/{keyword_id}/concepts/

Body:
{
  "concepts": [
    {
      "concept_code": "smartphone",
      "concept_type": "head_term",
      "confidence": 0.95
    }
  ]
}

Response: 200 OK
{
  "keyword_id": 500,
  "updated": true
}
```

---

## 7. Keyword-Product Mapping

### Map Keywords to Products
```http
POST /api/v1/keywords/map-to-products/

Body:
{
  "run_id": "uuid",
  "product_ids": [1, 2, 3],
  "min_confidence": 0.5
}

Response: 202 Accepted
{
  "job_id": "uuid",
  "status": "processing"
}
```

### Get Mapping Job Status
```http
GET /api/v1/keywords/mapping-job/{job_id}/

Response: 200 OK
{
  "job_id": "uuid",
  "status": "completed",
  "products_processed": 3,
  "mappings_created": 45
}
```

### Get Product-Keyword Mappings
```http
GET /api/v1/keywords/mappings/{run_id}/
  ?product_id=1
  &min_confidence=0.6
  &source=enum_map

Response: 200 OK
{
  "count": 15,
  "results": [
    {
      "mapping_id": "uuid",
      "product_id": 1,
      "keyword": {
        "id": 500,
        "term": "red smartphone"
      },
      "confidence": 0.85,
      "source": "enum_map",
      "match_kind": "attr_value_label",
      "matched_text": "Red",
      "evidence": {
        "attribute": "color",
        "attribute_value": "red"
      }
    }
  ]
}
```

### Get Product Keywords
```http
GET /api/v1/products/{product_id}/keywords/{run_id}/

Response: 200 OK
{
  "product_id": 1,
  "run_id": "uuid",
  "keywords": [
    {
      "keyword_id": 500,
      "term": "red smartphone",
      "confidence": 0.85,
      "source": "enum_map",
      "matched_text": "Red",
      "metrics": {
        "avg_searches": 2400,
        "competition": 0.35
      }
    }
  ]
}
```

### Update Mapping
```http
PATCH /api/v1/keywords/mappings/{mapping_id}/

Body:
{
  "approved": true,
  "confidence": 0.9
}

Response: 200 OK
{
  "mapping_id": "uuid",
  "updated": true
}
```

---

## 8. Template Management

### List Templates
```http
GET /api/v1/templates/
  ?product_type=electronics-phones
  &locale=en
  &is_active=true

Response: 200 OK
{
  "count": 5,
  "results": [
    {
      "template_id": 1,
      "product_type": "electronics-phones",
      "locale": "en",
      "title_template": "{brand} {model} - {color} {size}",
      "description_template": "Discover the {brand} {model}...",
      "variables": [
        {
          "name": "brand",
          "attribute_code": null,
          "source": "product.brand"
        },
        {
          "name": "color",
          "attribute_code": "color",
          "fallback": ""
        }
      ],
      "is_active": true
    }
  ]
}
```

### Create Template
```http
POST /api/v1/templates/create/

Body:
{
  "product_type_code": "electronics-phones",
  "locale": "en",
  "channel_id": 1,
  "title_template": "{brand} {model} - {color} {storage}",
  "description_template": "Experience the {brand} {model} with {storage} storage...",
  "variables": [
    {
      "name": "brand",
      "source": "product.brand"
    },
    {
      "name": "color",
      "attribute_code": "color"
    }
  ]
}

Response: 201 Created
{
  "template_id": 1,
  "created": true
}
```

### Preview Template
```http
POST /api/v1/templates/{template_id}/preview/

Body:
{
  "product_id": 1
}

Response: 200 OK
{
  "template_id": 1,
  "product_id": 1,
  "rendered": {
    "title": "Apple iPhone 15 - Blue 128GB",
    "description": "Experience the Apple iPhone 15 with 128GB storage..."
  },
  "variables_used": {
    "brand": "Apple",
    "model": "iPhone 15",
    "color": "Blue",
    "storage": "128GB"
  }
}
```

---

## 9. Content Generation

### Generate Content
```http
POST /api/v1/content/generate/

Body:
{
  "product_ids": [1, 2, 3],
  "locale": "en",
  "template_id": 1,
  "custom_prompt": "Focus on premium features and sustainability",
  "regenerate": false,
  "generate_title": true,
  "generate_description": true
}

Response: 202 Accepted
{
  "job_id": "uuid",
  "status": "processing",
  "product_count": 3
}
```

### Get Generation Job Status
```http
GET /api/v1/content/generation-job/{job_id}/

Response: 200 OK
{
  "job_id": "uuid",
  "status": "completed",
  "product_count": 3,
  "completed_count": 3,
  "failed_count": 0,
  "results": [
    {
      "product_id": 1,
      "locale": "en",
      "title": "Apple iPhone 15 - Premium Blue Smartphone",
      "description": "Experience sustainable luxury with the Apple iPhone 15...",
      "metadata": {
        "model": "gpt-4",
        "tokens_used": 250,
        "generation_time": 2.5
      }
    }
  ]
}
```

### Approve Generated Content
```http
POST /api/v1/content/approve/

Body:
{
  "product_ids": [1, 2, 3],
  "locale": "en",
  "save_to_product": true
}

Response: 200 OK
{
  "approved_count": 3
}
```

---

## 10. Export Management

### Create Export
```http
POST /api/v1/exports/create/

Body:
{
  "product_ids": [1, 2, 3],
  "locales": ["en", "fr", "de"],
  "format": "excel",
  "include_keywords": true,
  "include_metrics": true,
  "include_translations": true,
  "filters": {
    "product_type": "electronics-phones",
    "status": "active"
  }
}

Response: 202 Accepted
{
  "export_id": "uuid",
  "status": "processing"
}
```

### Get Export Status
```http
GET /api/v1/exports/{export_id}/status/

Response: 200 OK
{
  "export_id": "uuid",
  "status": "completed",
  "format": "excel",
  "file_size": 2457600,
  "row_count": 1500,
  "download_url": "/api/v1/exports/{export_id}/download/",
  "created_at": "2026-01-15T10:00:00Z",
  "expires_at": "2026-01-22T10:00:00Z"
}
```

### Download Export
```http
GET /api/v1/exports/{export_id}/download/

Response: 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="products_export_2026-01-15.xlsx"

[binary file data]
```

### List Export History
```http
GET /api/v1/exports/history/
  ?format=excel
  &from_date=2026-01-01

Response: 200 OK
{
  "count": 10,
  "results": [
    {
      "export_id": "uuid",
      "format": "excel",
      "status": "completed",
      "row_count": 1500,
      "created_at": "2026-01-15T10:00:00Z",
      "download_url": "..."
    }
  ]
}
```

---

## 11. Product Management

### List Products
```http
GET /api/v1/products/
  ?product_type=electronics-phones
  &status=active
  &search=iphone
  &page=1
  &page_size=20

Response: 200 OK
{
  "count": 150,
  "next": "...",
  "previous": null,
  "results": [
    {
      "id": 1,
      "code": "PROD-001",
      "product_type": {
        "code": "electronics-phones",
        "label": "Phones"
      },
      "brand": "Apple",
      "model": "iPhone 15",
      "status": "active",
      "variant_count": 12,
      "translations": [
        {
          "locale": "en",
          "title": "Apple iPhone 15"
        }
      ]
    }
  ]
}
```

### Get Product Details
```http
GET /api/v1/products/{product_id}/

Response: 200 OK
{
  "id": 1,
  "code": "PROD-001",
  "product_type": {...},
  "brand": "Apple",
  "model": "iPhone 15",
  "status": "active",
  "attributes": [
    {
      "attribute": {
        "code": "screen_size",
        "label": "Screen Size"
      },
      "value_number": 6.1,
      "value_unit": "inches"
    }
  ],
  "variants": [
    {
      "id": 100,
      "sku": "IPHONE15-BLU-128",
      "barcode": "1234567890123",
      "attributes": [
        {
          "attribute": "color",
          "attribute_value": {
            "id": 5,
            "value": "blue",
            "label": "Blue"
          }
        }
      ]
    }
  ],
  "translations": [
    {
      "locale": "en",
      "title": "Apple iPhone 15",
      "description": "..."
    }
  ]
}
```

### Get Variant Groups
```http
GET /api/v1/products/variant-groups/{product_type_code}/

Response: 200 OK
{
  "product_type": "electronics-phones",
  "groups": [
    {
      "parent_product": {
        "id": 1,
        "code": "PROD-001",
        "brand": "Apple",
        "model": "iPhone 15"
      },
      "variant_count": 12,
      "variants": [...]
    }
  ]
}
```

---

## Error Responses

### Standard Error Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": [
      {
        "field": "locale",
        "message": "This field is required"
      }
    ]
  }
}
```

### HTTP Status Codes
- `200 OK` - Success
- `201 Created` - Resource created
- `202 Accepted` - Async operation started
- `400 Bad Request` - Validation error
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict
- `422 Unprocessable Entity` - Semantic error
- `500 Internal Server Error` - Server error

---

## Pagination

All list endpoints support pagination:

```
?page=1&page_size=50
```

Response includes:
```json
{
  "count": 1000,
  "next": "http://api.../resource/?page=2",
  "previous": null,
  "results": [...]
}
```

---

## Filtering & Sorting

### Common Query Parameters
- `?search=keyword` - Full-text search
- `?ordering=-created_at` - Sort (prefix `-` for descending)
- `?locale=en` - Filter by locale
- `?status=active` - Filter by status

---

## Rate Limiting

- Standard endpoints: 100 requests/minute
- AI generation endpoints: 10 requests/minute
- Export endpoints: 5 requests/minute

Headers included in response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

---

## WebSocket Endpoints

### Real-time Job Progress
```
ws://api.../ws/jobs/{job_id}/

Messages:
{
  "type": "progress",
  "job_id": "uuid",
  "status": "processing",
  "progress": 45.5,
  "message": "Processing product 150/330"
}
```
