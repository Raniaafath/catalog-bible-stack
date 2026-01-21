from __future__ import annotations

import csv
import datetime as dt
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from django.conf import settings
from django.db import transaction

from importer.models import (
    AttributeMapping,
    CategoryBatch,
    ImportColumnMap,
    ImportColumnRule,
    ImportRow,
    ProductImport,
)


@dataclass
class ParseResult:
    total: int
    ok: int
    errors: int


@dataclass
class MapResult:
    mapped: int
    errors: int


def _jsonable(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _norm_col(value: str) -> str:
    normalized = (value or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")


_ROLE_ALIASES = {
    ImportColumnRule.Role.VARIANT_KEY: {
        "sku",
        "variant_sku",
        "ean",
        "barcode",
        "gtin",
        "id_variant",
        "variant_id",
    },
    ImportColumnRule.Role.PRODUCT_KEY: {
        "parent_id",
        "product_id",
        "group_id",
        "handle",
        "parent_sku",
        "model_id",
        "model",
    },
    ImportColumnRule.Role.CATEGORY: {"category", "product_type", "type", "taxonomy", "categorie", "cat"},
    ImportColumnRule.Role.BRAND: {"brand", "manufacturer", "marque", "vendor"},
    ImportColumnRule.Role.TITLE: {"title", "name", "product_name", "nom", "designation"},
    ImportColumnRule.Role.DESCRIPTION: {"description", "desc", "body_html", "details"},
}


def _guess_role(column_name: str) -> str:
    normalized = _norm_col(column_name)
    for role, aliases in _ROLE_ALIASES.items():
        if normalized in aliases:
            return role
    return ImportColumnRule.Role.ATTRIBUTE


def init_column_rules_for_import(
    product_import: ProductImport,
    columns: list[str],
    reset: bool = False,
) -> None:
    existing = {
        rule.column_name: rule
        for rule in ImportColumnRule.objects.filter(product_import=product_import)
    }
    seen = set()

    for idx, column in enumerate(columns):
        if not column:
            continue
        seen.add(column)
        defaults = {
            "position": idx,
            "role": _guess_role(column),
        }
        if reset or column not in existing:
            ImportColumnRule.objects.update_or_create(
                product_import=product_import,
                column_name=column,
                defaults=defaults,
            )
        else:
            ImportColumnRule.objects.filter(
                product_import=product_import,
                column_name=column,
            ).update(position=idx)

    ImportColumnRule.objects.filter(product_import=product_import).exclude(column_name__in=seen).delete()


def _read_csv_rows(path: Path) -> tuple[List[str], List[Dict[str, object]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        return headers, list(reader)


def _read_xlsx_rows(path: Path) -> tuple[List[str], Iterable[Dict[str, object]]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("openpyxl is required for XLSX imports.") from exc

    wb = load_workbook(path, read_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        return [], []

    headers = []
    for idx, value in enumerate(header_row):
        label = str(value).strip() if value is not None else ""
        headers.append(label or f"column_{idx + 1}")

    def _row_dicts():
        for row in rows_iter:
            values = list(row)
            payload = {
                headers[idx]: _jsonable(values[idx]) if idx < len(values) else ""
                for idx in range(len(headers))
            }
            yield payload

    return headers, _row_dicts()


def parse_import(import_id: int) -> ParseResult:
    product_import = ProductImport.objects.get(id=import_id)
    file_path = Path(product_import.source_file.path)
    file_type = (product_import.file_type or file_path.suffix.lstrip(".")).lower()

    if file_type == "xls":
        raise RuntimeError("Legacy .xls not supported. Please upload .xlsx or .csv.")
    if file_type == "xlsx":
        headers, rows = _read_xlsx_rows(file_path)
    else:
        headers, rows = _read_csv_rows(file_path)

    total = ok = errors = 0

    with transaction.atomic():
        ImportRow.objects.filter(product_import=product_import).delete()
        ImportColumnMap.objects.filter(product_import=product_import).delete()

        if headers:
            ImportColumnMap.objects.create(
                product_import=product_import,
                mapping_json={"columns": headers},
            )
            init_column_rules_for_import(product_import, headers, reset=False)

        for row_number, raw in enumerate(rows, start=2):
            if not raw or all(value in (None, "") for value in raw.values()):
                continue
            total += 1
            row_errors = {}
            is_valid = True
            if not any(raw.values()):
                row_errors["row"] = "Row is empty."
                is_valid = False

            if not is_valid:
                errors += 1
            else:
                ok += 1

            ImportRow.objects.create(
                product_import=product_import,
                row_number=row_number,
                raw=raw,
                errors=row_errors or None,
                is_valid=is_valid,
            )

        product_import.status = ProductImport.Status.PARSED
        product_import.row_count = total
        product_import.error_count = errors
        product_import.save(update_fields=["status", "row_count", "error_count"])

    source_file = product_import.source_file
    if source_file and source_file.name:
        try:
            source_file.storage.delete(source_file.name)
        except Exception:
            pass
        product_import.source_file = ""
        product_import.save(update_fields=["source_file"])

    return ParseResult(total=total, ok=ok, errors=errors)


def map_import(import_id: int) -> MapResult:
    product_import = ProductImport.objects.get(id=import_id)
    mapped = 0
    errors = 0

    batches = CategoryBatch.objects.filter(product_import=product_import)
    for batch in batches:
        mapped += AttributeMapping.objects.filter(category_batch=batch).count()

    if mapped == 0 and batches.exists():
        errors = 1

    product_import.status = ProductImport.Status.MAPPED
    product_import.save(update_fields=["status"])

    return MapResult(mapped=mapped, errors=errors)


@transaction.atomic
def process_import(import_id: int) -> dict:
    """
    Process the import by creating Product, Variant, and ProductAttributeValue records
    based on the AttributeMappings and ImportRows.
    
    Rule: 1 Excel row = 1 Variant (always)
    - Upsert Variant first (using stable unique key: internal_sku, sku, or hash)
    - Product is created/updated only as needed to attach the variant
    - Mode A (Standalone): Each variant gets its own product (default)
    - Mode B (Group-by PRODUCT_KEY): Group variants by PRODUCT_KEY column
    - Safety: Never reassign variant.product_id if variant already exists (preserve manual grouping)
    """
    from catalog.models import (
        Product, ProductType, Variant, ProductAttributeValue, 
        AttributeValue
    )
    from django.utils.text import slugify
    
    product_import = ProductImport.objects.get(id=import_id)
    
    stats = {
        "products_created": 0,
        "products_updated": 0,
        "variants_created": 0,
        "variants_updated": 0,
        "attribute_values_created": 0,
        "variation_axes_detected": 0,
        "errors": 0,
        "error_details": [],
    }
    
    # Get column rules to understand the structure
    column_rules = {
        rule.column_name: rule
        for rule in ImportColumnRule.objects.filter(product_import=product_import)
    }
    
    # Find PRODUCT_KEY and VARIANT_KEY columns
    product_key_col = None
    variant_key_col = None
    category_col = None
    row_type_col = None
    
    for col_name, rule in column_rules.items():
        if rule.role == ImportColumnRule.Role.PRODUCT_KEY:
            product_key_col = col_name
        elif rule.role == ImportColumnRule.Role.VARIANT_KEY:
            variant_key_col = col_name
        elif rule.role == ImportColumnRule.Role.CATEGORY:
            category_col = col_name
        if row_type_col is None and _norm_col(col_name) in {
            "row_type",
            "record_type",
            "record_kind",
            "row_kind",
            "line_type",
            "type",
        }:
            row_type_col = col_name
    
    # Get all valid rows
    rows = ImportRow.objects.filter(
        product_import=product_import,
        is_valid=True
    ).order_by('row_number')
    
    # Determine import mode: standalone or group-by PRODUCT_KEY
    # Respect product_import.group_by_product_key setting
    use_grouping_mode = product_import.group_by_product_key
    if use_grouping_mode and product_key_col:
        # Check if any rows have PRODUCT_KEY values
        sample_rows = rows[:10]
        has_product_key_values = False
        for sample_row in sample_rows:
            if sample_row.raw.get(product_key_col):
                has_product_key_values = True
                break
        # Only group if PRODUCT_KEY column exists AND has values
        use_grouping_mode = has_product_key_values
    else:
        # If group_by_product_key is False, always use standalone mode
        use_grouping_mode = False
    
    # Process each row: 1 row = 1 Variant
    for row in rows:
        try:
            raw_data = row.raw
            
            # Determine row type (for tracking)
            row_type_value = ""
            if row_type_col:
                row_type_value = str(raw_data.get(row_type_col, "")).strip().lower()
            is_parent = row_type_value in {
                "parent",
                "product",
                "master",
                "header",
                "p",
            }
            if row_type_value in {"variant", "child", "v"}:
                is_parent = False
            
            # STEP 1: Determine variant unique key (stable identifier)
            variant_sku = None
            variant_barcode = None
            variant_lookup_key = None
            
            if variant_key_col and raw_data.get(variant_key_col):
                variant_sku = str(raw_data[variant_key_col]).strip()
                variant_lookup_key = variant_sku
            
            if 'barcode' in raw_data and raw_data['barcode']:
                variant_barcode = str(raw_data['barcode']).strip()
                if not variant_lookup_key:
                    variant_lookup_key = variant_barcode
            
            # Fallback: use row identifier
            if not variant_lookup_key:
                variant_lookup_key = f"import-{product_import.id}-row-{row.row_number}"
            
            # STEP 2: Upsert Variant first (using stable unique key)
            # Try to find existing variant by: internal_sku (best), sku, or barcode
            existing_variant = None
            if variant_sku:
                existing_variant = Variant.objects.filter(sku=variant_sku).first()
            if not existing_variant and variant_barcode:
                existing_variant = Variant.objects.filter(barcode=variant_barcode).first()
            
            variant_is_new = existing_variant is None
            
            # STEP 3: Determine product (depends on mode and variant existence)
            target_product = None
            
            if variant_is_new:
                # New variant: create/update product based on mode
                if use_grouping_mode and product_key_col and raw_data.get(product_key_col):
                    # Mode B: Group by PRODUCT_KEY
                    parent_key = str(raw_data[product_key_col]).strip()
                    product_code = slugify(parent_key) or f"product-{row.row_number}"
                else:
                    # Mode A: Standalone (one product per variant)
                    if variant_sku:
                        product_code = slugify(variant_sku) or f"product-{row.row_number}"
                    else:
                        product_code = f"product-{row.row_number}"
                
                # Get or create product type
                product_type = None
                if category_col and raw_data.get(category_col):
                    category_code = slugify(raw_data[category_col])
                    if category_code:
                        product_type, _ = ProductType.objects.get_or_create(
                            code=category_code,
                            defaults={'default_label': raw_data[category_col]}
                        )
                
                if not product_type:
                    product_type, _ = ProductType.objects.get_or_create(
                        code='default',
                        defaults={'default_label': 'Default'}
                    )
                
                # Build product data (only update if product is new or safe to update)
                product_data = {
                    'product_type': product_type,
                    'code': product_code,
                    'status': Product.Status.DRAFT,
                }
                
                # Extract standard fields (only if product is new)
                for col_name, rule in column_rules.items():
                    value = raw_data.get(col_name)
                    if not value:
                        continue
                    
                    if rule.role == ImportColumnRule.Role.BRAND:
                        product_data['brand'] = str(value)
                    elif rule.role == ImportColumnRule.Role.TITLE:
                        # TITLE goes to product.default_label (general title for the group)
                        if not product_data.get('default_label'):
                            product_data['default_label'] = str(value)
                    elif rule.role == ImportColumnRule.Role.DESCRIPTION:
                        # Description can be product-level if shared, but usually variant-specific
                        # For now, skip (will be handled at variant level)
                        pass
                
                # Check for common field names
                if 'model' in raw_data and raw_data['model']:
                    product_data['model'] = str(raw_data['model'])
                if 'series' in raw_data and raw_data['series']:
                    product_data['series'] = str(raw_data['series'])
                
                # Create or update product (only if new, or update safe fields)
                target_product, product_created = Product.objects.update_or_create(
                    code=product_code,
                    defaults=product_data
                )
                
                if product_created:
                    stats["products_created"] += 1
                else:
                    stats["products_updated"] += 1
            else:
                # Existing variant: SAFETY RULE - don't change product_id (preserve manual grouping)
                target_product = existing_variant.product
                # Don't update product fields (may have been merged/edited manually)
            
            # Update row tracking
            row.parent_key = target_product.code if target_product else "unknown"
            row.is_parent = is_parent
            row.save(update_fields=["parent_key", "is_parent"])
            
            # STEP 4: Upsert Variant
            variant_defaults = {
                'product': target_product,
            }
            
            # Handle barcode and MPN
            if variant_barcode:
                variant_defaults['barcode'] = variant_barcode
            if 'mpn' in raw_data and raw_data['mpn']:
                variant_defaults['mpn'] = str(raw_data['mpn'])
            
            # Source fields (variant-specific, from import/supplier)
            for col_name, rule in column_rules.items():
                value = raw_data.get(col_name)
                if not value:
                    continue
                
                if rule.role == ImportColumnRule.Role.TITLE:
                    variant_defaults['source_title'] = str(value)
                elif rule.role == ImportColumnRule.Role.DESCRIPTION:
                    variant_defaults['source_description'] = str(value)
            
            # Check for common source field names
            if 'source_sku' in raw_data and raw_data['source_sku']:
                variant_defaults['source_sku'] = str(raw_data['source_sku'])
            if 'supplier' in raw_data or 'fournisseur' in raw_data:
                variant_defaults['source_supplier'] = str(raw_data.get('supplier') or raw_data.get('fournisseur', ''))
            if 'locale' in raw_data or 'language' in raw_data or 'langue' in raw_data:
                variant_defaults['source_locale'] = str(raw_data.get('locale') or raw_data.get('language') or raw_data.get('langue', ''))
            
            # No axis signature during import (user sets axes later)
            variant_defaults['axis_signature'] = None
            
            if variant_is_new:
                # Create new variant
                if variant_sku:
                    variant_defaults['sku'] = variant_sku
                
                variant = Variant.objects.create(**variant_defaults)
                stats["variants_created"] += 1
            else:
                # Update existing variant (but preserve product_id if it was manually set)
                # Only update safe fields: barcode, mpn (not product_id)
                update_fields = []
                if variant_barcode and existing_variant.barcode != variant_barcode:
                    existing_variant.barcode = variant_barcode
                    update_fields.append('barcode')
                if 'mpn' in raw_data and raw_data['mpn']:
                    mpn_val = str(raw_data['mpn'])
                    if existing_variant.mpn != mpn_val:
                        existing_variant.mpn = mpn_val
                        update_fields.append('mpn')
                
                if update_fields:
                    existing_variant.save(update_fields=update_fields)
                
                variant = existing_variant
                stats["variants_updated"] += 1
            
            # STEP 5: Create product-level attributes (only for new products)
            if variant_is_new:
                for col_name, rule in column_rules.items():
                    if rule.role != ImportColumnRule.Role.ATTRIBUTE:
                        continue
                    if rule.variant_level or rule.is_variation_axis:
                        continue

                    value = raw_data.get(col_name)
                    if not value:
                        continue

                    attribute = None
                    if rule.target_attribute_code:
                        from catalog.models import Attribute
                        try:
                            attribute = Attribute.objects.get(code=rule.target_attribute_code)
                        except Attribute.DoesNotExist:
                            pass

                    if not attribute and rule.create_attribute_name:
                        from catalog.models import Attribute
                        attr_code = slugify(rule.create_attribute_name)
                        if attr_code:
                            attribute, _ = Attribute.objects.get_or_create(
                                code=attr_code,
                                defaults={
                                    'data_type': rule.attribute_type or 'text',
                                }
                            )

                    if attribute:
                        pav_data = {
                            'attribute': attribute,
                        }
                        if attribute.data_type == 'text' or attribute.data_type == 'enum':
                            value_code = slugify(str(value))
                            if value_code:
                                attr_value, _ = AttributeValue.objects.get_or_create(
                                    attribute=attribute,
                                    code=value_code
                                )
                                pav_data['attribute_value'] = attr_value
                            else:
                                pav_data['value_text'] = str(value)
                        elif attribute.data_type == 'number':
                            try:
                                pav_data['value_number'] = Decimal(str(value))
                            except (ValueError, TypeError):
                                pav_data['value_text'] = str(value)
                        elif attribute.data_type == 'bool':
                            pav_data['value_bool'] = str(value).lower() in ('true', '1', 'yes', 'oui', 'vrai')
                        else:
                            pav_data['value_text'] = str(value)

                        pav_data['product'] = target_product
                        pav_data['variant'] = None
                        ProductAttributeValue.objects.update_or_create(
                            product=target_product,
                            attribute=attribute,
                            defaults=pav_data
                        )
                        stats["attribute_values_created"] += 1
            
            # STEP 6: Create variant-level attributes
            for col_name, rule in column_rules.items():
                if rule.role != ImportColumnRule.Role.ATTRIBUTE:
                    continue
                if not (rule.variant_level or rule.is_variation_axis):
                    continue
                
                value = raw_data.get(col_name)
                if not value:
                    continue
                
                # Get or create attribute
                attribute = None
                if rule.target_attribute_code:
                    from catalog.models import Attribute
                    try:
                        attribute = Attribute.objects.get(code=rule.target_attribute_code)
                    except Attribute.DoesNotExist:
                        pass
                
                if not attribute and rule.create_attribute_name:
                    from catalog.models import Attribute
                    attr_code = slugify(rule.create_attribute_name)
                    if attr_code:
                        attribute, _ = Attribute.objects.get_or_create(
                            code=attr_code,
                            defaults={
                                'data_type': rule.attribute_type or 'text',
                            }
                        )
                
                if attribute:
                    pav_data = {
                        'attribute': attribute,
                    }
                    
                    # Set value based on data type
                    if attribute.data_type == 'text' or attribute.data_type == 'enum':
                        value_code = slugify(str(value))
                        if value_code:
                            attr_value, _ = AttributeValue.objects.get_or_create(
                                attribute=attribute,
                                code=value_code
                            )
                            pav_data['attribute_value'] = attr_value
                        else:
                            pav_data['value_text'] = str(value)
                    elif attribute.data_type == 'number':
                        try:
                            pav_data['value_number'] = Decimal(str(value))
                        except (ValueError, TypeError):
                            pav_data['value_text'] = str(value)
                    elif attribute.data_type == 'bool':
                        pav_data['value_bool'] = str(value).lower() in ('true', '1', 'yes', 'oui', 'vrai')
                    else:
                        pav_data['value_text'] = str(value)
                    
                    # Mark as axis if it's a variation axis (for reference, but not used for grouping)
                    if rule.is_variation_axis:
                        pav_data['is_axis'] = True
                    
                    pav_data['variant'] = variant
                    pav_data['product'] = None
                    ProductAttributeValue.objects.update_or_create(
                        variant=variant,
                        attribute=attribute,
                        defaults=pav_data
                    )
                    
                    stats["attribute_values_created"] += 1
                    
        except Exception as e:
            stats["errors"] += 1
            stats["error_details"].append({
                "row_number": row.row_number,
                "product_code": product_code if 'product_code' in locals() else "unknown",
                "error": str(e)
            })
    
    # Update import status
    product_import.status = ProductImport.Status.COMPLETED
    product_import.save(update_fields=["status"])
    
    return stats


def detect_variation_axes(variant_rows: list, column_rules: dict, max_axes: int = 5) -> list:
    """
    Detect which columns represent variation axes by finding attributes that:
    1. Have different values across variants
    2. Are marked as variation axes in column rules
    3. Are commonly used for variations (size, color, etc.)
    
    Returns: List of (column_name, Attribute) tuples, up to max_axes items
    """
    from catalog.models import Attribute
    from django.utils.text import slugify
    
    if len(variant_rows) <= 1:
        return []
    
    # Collect values for each column across all variants
    column_values = defaultdict(set)
    
    for row in variant_rows:
        for col_name, value in row.raw.items():
            if value:
                column_values[col_name].add(str(value).strip())
    
    # Find columns with variation (different values) but not too many unique values
    variation_candidates = []
    
    # Common variation axis names
    common_axes = {
        'size', 'taille', 'color', 'colour', 'couleur', 'capacity', 'capacite',
        'material', 'materiau', 'style', 'finish', 'finition', 'length', 'longueur',
        'width', 'largeur', 'height', 'hauteur', 'weight', 'poids', 'voltage', 'tension'
    }
    
    for col_name, values in column_values.items():
        # Skip if only one unique value (not a variation)
        if len(values) <= 1:
            continue
        
        # Skip if too many unique values (likely not a variation axis)
        if len(values) > 20:
            continue
        
        rule = column_rules.get(col_name)
        if not rule:
            continue
        
        # Skip non-attribute columns
        if rule.role != ImportColumnRule.Role.ATTRIBUTE:
            continue
        
        # Calculate priority score
        priority_score = 0
        
        # Explicitly marked as variation axis
        if rule.is_variation_axis:
            priority_score += 1000 + rule.axis_priority
        
        # Common axis name
        col_normalized = slugify(col_name.lower())
        if any(axis in col_normalized for axis in common_axes):
            priority_score += 100
        
        # Fewer unique values = better axis (more likely to be meaningful)
        priority_score += (20 - len(values))
        
        # Get or create attribute
        attribute = None
        if rule.target_attribute_code:
            try:
                attribute = Attribute.objects.get(code=rule.target_attribute_code)
            except Attribute.DoesNotExist:
                pass
        
        if not attribute and rule.create_attribute_name:
            attr_code = slugify(rule.create_attribute_name)
            if attr_code:
                attribute, _ = Attribute.objects.get_or_create(
                    code=attr_code,
                    defaults={'data_type': rule.attribute_type or 'text'}
                )
        
        if attribute:
            variation_candidates.append((priority_score, col_name, attribute))
    
    # Sort by priority and take top max_axes
    variation_candidates.sort(reverse=True, key=lambda x: x[0])
    
    # Return column name and attribute pairs
    return [(col, attr) for score, col, attr in variation_candidates[:max_axes]]


@transaction.atomic
def process_import_old(import_id: int) -> dict:
    """
    Process the import by creating Product, Variant, and ProductAttributeValue records
    based on the AttributeMappings and ImportRows.
    """
    from catalog.models import Product, Variant, ProductAttributeValue, AttributeValue
    from django.utils.text import slugify
    
    product_import = ProductImport.objects.get(id=import_id)
    
    stats = {
        "products_created": 0,
        "products_updated": 0,
        "variants_created": 0,
        "variants_updated": 0,
        "attribute_values_created": 0,
        "errors": 0,
        "error_details": [],
    }
    
    batches = CategoryBatch.objects.filter(product_import=product_import, status=CategoryBatch.Status.ATTR_MAPPED)
    
    for batch in batches:
        # Get all mappings for this batch
        mappings = AttributeMapping.objects.filter(category_batch=batch).select_related('target_attribute')
        
        # Build mapping dictionaries
        product_field_mappings = {}  # source_col -> product field name
        variant_field_mappings = {}  # source_col -> variant field name
        attribute_mappings = {}  # source_col -> Attribute object
        
        for mapping in mappings:
            source_col = mapping.source_attr_name
            
            # Check if this is a product/variant field mapping (from frontend fieldMappings)
            # We'll need to pass this info from frontend, for now detect by attribute being None and strategy
            if mapping.target_attribute:
                attribute_mappings[source_col] = mapping.target_attribute
        
        # Get rows for this batch's product type
        rows = ImportRow.objects.filter(
            product_import=product_import,
            is_valid=True
        ).order_by('row_number')
        
        for row in rows:
            try:
                raw_data = row.raw
                
                # Extract product fields from raw data
                product_data = {
                    'product_type': batch.product_type,
                    'status': Product.Status.DRAFT,
                }
                
                variant_data = {}
                attribute_data = {}
                
                # Process each column in the row
                for col_name, col_value in raw_data.items():
                    if not col_value:
                        continue
                    
                    # Check if this column is mapped to an attribute
                    if col_name in attribute_mappings:
                        attribute_data[col_name] = {
                            'attribute': attribute_mappings[col_name],
                            'value': col_value
                        }
                
                # Try to find/generate a product code
                product_code = (
                    raw_data.get('SKU') or
                    raw_data.get('code') or
                    raw_data.get('reference') or
                    raw_data.get('sku') or
                    f"{batch.product_type.code}-{row.row_number}"
                )
                
                # Make sure code is unique
                base_code = slugify(product_code) or f"product-{row.row_number}"
                code = base_code
                suffix = 2
                while Product.objects.filter(code=code).exists():
                    # Check if it's the same product type, then update
                    existing = Product.objects.filter(code=code).first()
                    if existing and existing.product_type == batch.product_type:
                        product = existing
                        stats["products_updated"] += 1
                        break
                    code = f"{base_code}-{suffix}"
                    suffix += 1
                else:
                    # Create new product
                    product_data['code'] = code
                    
                    # Set other product fields from raw data
                    if 'brand' in raw_data or 'marque' in raw_data:
                        product_data['brand'] = raw_data.get('brand') or raw_data.get('marque')
                    if 'model' in raw_data or 'modèle' in raw_data or 'modele' in raw_data:
                        product_data['model'] = raw_data.get('model') or raw_data.get('modèle') or raw_data.get('modele')
                    if 'series' in raw_data or 'série' in raw_data or 'serie' in raw_data:
                        product_data['series'] = raw_data.get('series') or raw_data.get('série') or raw_data.get('serie')
                    
                    # Source fields
                    if 'name' in raw_data or 'title' in raw_data or 'nom' in raw_data:
                        product_data['source_title'] = raw_data.get('name') or raw_data.get('title') or raw_data.get('nom', '')
                    if 'default_label' in raw_data or 'libellé' in raw_data or 'libelle' in raw_data:
                        product_data['default_label'] = raw_data.get('default_label') or raw_data.get('libellé') or raw_data.get('libelle', '')
                    if 'description' in raw_data:
                        product_data['source_description'] = raw_data.get('description', '')
                    if 'supplier' in raw_data or 'fournisseur' in raw_data:
                        product_data['source_supplier'] = raw_data.get('supplier') or raw_data.get('fournisseur', '')
                    if 'locale' in raw_data or 'language' in raw_data or 'langue' in raw_data:
                        product_data['source_locale'] = raw_data.get('locale') or raw_data.get('language') or raw_data.get('langue', '')
                    if 'source_sku' in raw_data:
                        product_data['source_sku'] = raw_data.get('source_sku', '')
                    
                    product = Product.objects.create(**product_data)
                    stats["products_created"] += 1
                
                # Create or get variant
                variant_sku = raw_data.get('sku') or raw_data.get('SKU') or product.code
                variant, created = Variant.objects.get_or_create(
                    product=product,
                    sku=variant_sku,
                    defaults={
                        'barcode': raw_data.get('barcode') or raw_data.get('code_barre'),
                        'mpn': raw_data.get('mpn'),
                    }
                )
                
                if created:
                    stats["variants_created"] += 1
                else:
                    stats["variants_updated"] += 1
                
                # Create ProductAttributeValue records
                for col_name, attr_info in attribute_data.items():
                    attribute = attr_info['attribute']
                    value = attr_info['value']
                    
                    # Determine if this is product-level or variant-level
                    # For now, default to product-level
                    pav_data = {
                        'product': product,
                        'variant': None,
                        'attribute': attribute,
                    }
                    
                    # Set the appropriate value field based on data type
                    if attribute.data_type == 'text':
                        # Try to find or create AttributeValue
                        value_code = slugify(str(value))
                        if value_code:
                            attr_value, _ = AttributeValue.objects.get_or_create(
                                attribute=attribute,
                                code=value_code
                            )
                            pav_data['attribute_value'] = attr_value
                        else:
                            pav_data['value_text'] = str(value)
                    elif attribute.data_type == 'number':
                        try:
                            pav_data['value_number'] = float(value)
                        except (ValueError, TypeError):
                            pav_data['value_text'] = str(value)
                    elif attribute.data_type == 'bool':
                        pav_data['value_bool'] = str(value).lower() in ('true', '1', 'yes', 'oui', 'vrai')
                    else:
                        pav_data['value_text'] = str(value)
                    
                    # Create or update the attribute value
                    ProductAttributeValue.objects.update_or_create(
                        product=product,
                        attribute=attribute,
                        defaults=pav_data
                    )
                    stats["attribute_values_created"] += 1
                    
            except Exception as e:
                stats["errors"] += 1
                stats["error_details"].append({
                    "row": row.row_number,
                    "error": str(e)
                })
    
    # Update import status
    product_import.status = ProductImport.Status.COMPLETED
    product_import.save(update_fields=["status"])
    
    return stats


def export_import(import_id: int, fmt: str = "xlsx") -> Path:
    product_import = ProductImport.objects.get(id=import_id)
    rows = list(ImportRow.objects.filter(product_import=product_import).order_by("row_number"))
    columns = []
    column_map = ImportColumnMap.objects.filter(product_import=product_import).first()
    if column_map:
        columns = list(column_map.mapping_json.get("columns", []))
    if not columns and rows:
        columns = list(rows[0].raw.keys())
    columns = columns or ["row_number"]

    export_dir = Path(settings.MEDIA_ROOT) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    export_path = export_dir / f"import_{import_id}_{timestamp}.{fmt}"

    if fmt == "csv":
        with export_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["row_number", *columns, "errors"])
            for row in rows:
                values = [row.raw.get(col, "") for col in columns]
                err = json.dumps(row.errors, ensure_ascii=True) if row.errors else ""
                writer.writerow([row.row_number, *values, err])
        return export_path

    try:
        from openpyxl import Workbook
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("openpyxl is required for XLSX exports.") from exc

    wb = Workbook()
    ws = wb.active
    ws.append(["row_number", *columns, "errors"])
    for row in rows:
        values = [row.raw.get(col, "") for col in columns]
        err = json.dumps(row.errors, ensure_ascii=True) if row.errors else ""
        ws.append([row.row_number, *values, err])
    wb.save(export_path)
    return export_path
