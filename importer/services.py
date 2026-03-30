from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import re
import tempfile
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


# Token keywords for auto-detecting column roles.
# Each entry is a set of normalized single tokens (underscores removed by _norm_col).
# A column matches if the normalized column name contains all tokens in any keyword entry.
# Language-specific terms should NOT be added here — use the column mapping UI for those.
_ROLE_KEYWORDS: dict[str, set[str]] = {
    ImportColumnRule.Role.VARIANT_KEY: {"sku", "ean", "barcode", "gtin"},
    ImportColumnRule.Role.PRODUCT_KEY: {"parent", "group"},
    ImportColumnRule.Role.CATEGORY: {"category", "taxonomy"},
    ImportColumnRule.Role.BRAND: {"brand", "manufacturer", "vendor"},
    ImportColumnRule.Role.TITLE: {"title"},
    ImportColumnRule.Role.DESCRIPTION: {"description"},
    ImportColumnRule.Role.BARCODE: {"barcode", "ean", "gtin"},
    ImportColumnRule.Role.MPN: {"mpn"},
}

# Exact normalized column name matches take highest priority over token matching.
_ROLE_EXACT: dict[str, str] = {
    "sku": ImportColumnRule.Role.VARIANT_KEY,
    "variant_sku": ImportColumnRule.Role.VARIANT_KEY,
    "id_variant": ImportColumnRule.Role.VARIANT_KEY,
    "variant_id": ImportColumnRule.Role.VARIANT_KEY,
    "parent_id": ImportColumnRule.Role.PRODUCT_KEY,
    "product_id": ImportColumnRule.Role.PRODUCT_KEY,
    "group_id": ImportColumnRule.Role.PRODUCT_KEY,
    "handle": ImportColumnRule.Role.PRODUCT_KEY,
    "parent_sku": ImportColumnRule.Role.PRODUCT_KEY,
    "model_id": ImportColumnRule.Role.PRODUCT_KEY,
    "product_type": ImportColumnRule.Role.CATEGORY,
    "product_name": ImportColumnRule.Role.TITLE,
    "name": ImportColumnRule.Role.TITLE,
    "body_html": ImportColumnRule.Role.DESCRIPTION,
}


def _guess_role(column_name: str) -> str:
    normalized = _norm_col(column_name)
    # 1. Exact match wins
    if normalized in _ROLE_EXACT:
        return _ROLE_EXACT[normalized]
    # 2. Token-subset match: column contains all tokens of a keyword entry
    col_tokens = set(normalized.split("_"))
    for role, keywords in _ROLE_KEYWORDS.items():
        if keywords & col_tokens:  # any keyword token present in column tokens
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
    """
    Read CSV file and return headers and rows.
    Tries multiple encodings to handle different file formats.
    """
    if not path.exists():
        raise RuntimeError(f"CSV file not found: {path}")
    
    if path.stat().st_size == 0:
        raise RuntimeError(f"CSV file is empty: {path}")
    
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252", "iso-8859-1"]
    
    for encoding in encodings:
        try:
            with path.open(newline="", encoding=encoding) as handle:
                reader = csv.DictReader(handle)
                headers = reader.fieldnames or []
                
                # Read all rows into a list
                rows = []
                for row in reader:
                    rows.append(row)
                
                # Validate we got data
                if not headers:
                    raise RuntimeError("CSV file has no headers. Please ensure the first row contains column names.")
                
                return headers, rows
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as e:
            # If it's not an encoding error, re-raise
            if encoding == encodings[0]:  # Only raise on first attempt if not encoding issue
                raise RuntimeError(f"Error reading CSV file: {e}") from e
            continue
    
    # If all encodings failed, try with errors='replace' as last resort
    try:
        with path.open(newline="", encoding="utf-8", errors="replace") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            rows = []
            for row in reader:
                rows.append(row)
            return headers, rows
    except Exception as e:
        raise RuntimeError(f"Failed to read CSV file with any encoding: {e}") from e


def _read_xlsx_rows(path: Path) -> tuple[List[str], List[Dict[str, object]]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("openpyxl is required for XLSX imports.") from exc

    wb = load_workbook(path, read_only=True)
    best_headers: List[str] = []
    best_rows: List[Dict[str, object]] = []

    for ws in wb.worksheets:
        rows_iter = ws.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration:
            continue

        headers = []
        for idx, value in enumerate(header_row):
            label = str(value).strip() if value is not None else ""
            headers.append(label or f"column_{idx + 1}")

        rows = []
        rows_with_data = 0
        for row in rows_iter:
            values = list(row)
            payload = {
                headers[idx]: _jsonable(values[idx]) if idx < len(values) else ""
                for idx in range(len(headers))
            }
            rows.append(payload)
            if rows_with_data == 0 and any(
                value is not None and str(value).strip() != "" for value in values
            ):
                rows_with_data = 1

        # Prefer the first sheet that has at least one data row
        if headers and rows_with_data:
            return headers, rows

        # Otherwise keep the first sheet with headers as a fallback
        if headers and not best_headers:
            best_headers = headers
            best_rows = rows

    return best_headers, best_rows


def parse_import(import_id: int) -> ParseResult:
    import logging
    logger = logging.getLogger(__name__)
    
    product_import = ProductImport.objects.get(id=import_id)
    
    # Handle file path - check if file exists and is accessible
    if not product_import.source_file:
        raise RuntimeError("No source file uploaded for this import.")
    
    tmp_file_created = False
    file_path = None
    
    try:
        # Refresh from database to ensure file is saved
        product_import.refresh_from_db()
        
        # Try to get file path from FileField
        try:
            file_path = Path(product_import.source_file.path)
            logger.info(f"File path from FileField: {file_path}")
            if not file_path.exists():
                logger.warning(f"File not found at path: {file_path}, trying alternative method")
                raise FileNotFoundError()
            # Verify file is readable and has content
            file_size = file_path.stat().st_size
            logger.info(f"File exists, size: {file_size} bytes")
            if file_size == 0:
                error_message = "Uploaded file is empty (0 bytes). Please upload a file with content."
                with transaction.atomic():
                    product_import.parse_error_message = error_message
                    product_import.status = ProductImport.Status.FAILED
                    product_import.save(update_fields=["parse_error_message", "status"])
                raise RuntimeError(error_message)
        except (ValueError, AttributeError, FileNotFoundError) as e:
            # FileField might not have a path if using storage backend
            # Try to read directly from the file object and save to temp file
            logger.info(f"File path not accessible ({e}), creating temp file from file object")
            if hasattr(product_import.source_file, 'read'):
                # Reset file pointer to beginning
                try:
                    product_import.source_file.seek(0)
                except (AttributeError, io.UnsupportedOperation):
                    # Some file objects don't support seek, that's OK
                    pass
                
                # Save to temp file for processing (preserve original extension when possible)
                orig_suffix = Path(product_import.source_file.name or "").suffix.lower()
                if orig_suffix not in {".csv", ".xlsx"}:
                    fallback = f".{product_import.file_type or 'csv'}"
                    orig_suffix = fallback if fallback.startswith(".") else f".{fallback}"
                tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=orig_suffix)
                try:
                    bytes_written = 0
                    # Try chunks() first (Django FileField method)
                    if hasattr(product_import.source_file, 'chunks'):
                        for chunk in product_import.source_file.chunks():
                            tmp_file.write(chunk)
                            bytes_written += len(chunk)
                    else:
                        # Fallback to read()
                        data = product_import.source_file.read()
                        tmp_file.write(data)
                        bytes_written = len(data)
                    
                    tmp_file.flush()
                    os.fsync(tmp_file.fileno())  # Ensure data is written to disk
                    file_path = Path(tmp_file.name)
                    tmp_file_created = True
                    logger.info(f"Created temp file: {file_path} ({bytes_written} bytes written)")
                    
                    if bytes_written == 0:
                        error_message = "File object is empty (0 bytes read). Please upload a file with content."
                        with transaction.atomic():
                            product_import.parse_error_message = error_message
                            product_import.status = ProductImport.Status.FAILED
                            product_import.save(update_fields=["parse_error_message", "status"])
                        raise RuntimeError(error_message)
                finally:
                    tmp_file.close()
            else:
                raise RuntimeError(f"Cannot access file: {e}")
    
    except Exception as e:
        logger.error(f"Error accessing file: {e}", exc_info=True)
        error_message = f"Error accessing uploaded file: {str(e)}. Please ensure the file was uploaded correctly."
        # Save error message to database before raising
        with transaction.atomic():
            product_import.parse_error_message = error_message
            product_import.status = ProductImport.Status.FAILED
            product_import.save(update_fields=["parse_error_message", "status"])
        raise RuntimeError(error_message) from e
    
    if not file_path or not file_path.exists():
        error_message = f"File path is invalid or file does not exist: {file_path}"
        with transaction.atomic():
            product_import.parse_error_message = error_message
            product_import.status = ProductImport.Status.FAILED
            product_import.save(update_fields=["parse_error_message", "status"])
        raise RuntimeError(error_message)
    
    # Get file type
    file_type = (product_import.file_type or file_path.suffix.lstrip(".")).lower()
    logger.info(f"Processing {file_type} file: {file_path} (size: {file_path.stat().st_size} bytes)")

    if file_type == "xls":
        raise RuntimeError("Legacy .xls not supported. Please upload .xlsx or .csv.")
    
    # Read file - DO NOT delete temp file yet, we need it for processing
    try:
        if file_type == "xlsx":
            headers, rows = _read_xlsx_rows(file_path)
        else:
            headers, rows = _read_csv_rows(file_path)
        
        logger.info(f"Read {len(headers)} headers and {len(rows)} rows from file")
        logger.info(
            "Import sample: file_type=%s name=%s",
            file_type,
            product_import.source_file.name,
        )
        if headers:
            logger.info("Import sample headers: %s", headers[:10])
        if rows:
            sample_row = rows[0]
            logger.info("Import sample row keys: %s", list(sample_row.keys())[:10])
            logger.info(
                "Import sample row values: %s",
                list(sample_row.values())[:5],
            )
        
        # Validate we got data and provide specific error messages
        error_message = ""
        
        if not headers:
            error_message = (
                "No column headers found in the file. "
                "The first row must contain column names (e.g., 'parent_id,sku,brand,title'). "
                "Please ensure your CSV/XLSX file has a header row."
            )
            logger.warning(error_message)
        elif not rows:
            error_message = (
                f"File contains {len(headers)} column headers but no data rows. "
                "Your file must have at least one row of data below the header row. "
                "Please add product data rows to your file."
            )
            logger.warning(error_message)
            
    except Exception as e:
        logger.error(f"Error reading file: {e}", exc_info=True)
        # Clean up temp file on error
        if tmp_file_created and file_path and file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass
        error_message = f"Failed to read file: {str(e)}. Please check that the file is a valid CSV or XLSX format."
        # Save error message to database before raising
        with transaction.atomic():
            product_import.parse_error_message = error_message
            product_import.status = ProductImport.Status.FAILED
            product_import.save(update_fields=["parse_error_message", "status"])
        raise RuntimeError(error_message) from e

    total = ok = errors = 0
    empty_row_count = 0
    rows_with_data = 0

    with transaction.atomic():
        ImportRow.objects.filter(product_import=product_import).delete()
        ImportColumnMap.objects.filter(product_import=product_import).delete()

        if headers:
            ImportColumnMap.objects.create(
                product_import=product_import,
                mapping_json={"columns": headers},
            )
            init_column_rules_for_import(product_import, headers, reset=False)
            logger.info(f"Created column map with {len(headers)} columns")

        # Process rows - skip completely empty rows but count rows with any data
        for row_number, raw in enumerate(rows, start=2):
            # Skip rows that are completely empty (all None or empty strings)
            if not raw:
                logger.debug(f"Row {row_number}: skipping empty row dict")
                empty_row_count += 1
                continue
            
            # Check if row has any non-empty values
            has_data = any(
                value is not None and str(value).strip() != "" 
                for value in raw.values()
            )
            
            if not has_data:
                logger.debug(f"Row {row_number}: skipping row with no data")
                empty_row_count += 1
                continue  # Skip completely empty rows
            
            # Row has data, process it
            rows_with_data += 1
            total += 1
            row_errors = {}
            is_valid = True
            
            # Additional validation can be added here if needed
            # For now, if we got here, the row has data and is valid

            ImportRow.objects.create(
                product_import=product_import,
                row_number=row_number,
                raw=raw,
                errors=row_errors or None,
                is_valid=is_valid,
            )
            
            ok += 1

        # Generate detailed error message if no rows were processed
        if total == 0:
            if not error_message:  # Only set if we didn't already set one above
                if empty_row_count > 0:
                    error_message = (
                        f"Found {len(rows)} row(s) in the file, but all {empty_row_count} row(s) are completely empty. "
                        "Each data row must contain at least one non-empty value. "
                        "Please check your file and ensure data rows have actual values (not just spaces or empty cells)."
                    )
                elif len(rows) == 0:
                    error_message = (
                        "No data rows found in the file. "
                        "Your file must have at least one row of data below the header row. "
                        "Please add product data rows to your file."
                    )
                else:
                    error_message = (
                        "No valid data rows were detected. "
                        "Please ensure your file has data rows with at least one non-empty value in each row."
                    )
            logger.warning(f"No rows processed. Error: {error_message}")

        logger.info(f"Processed {total} rows: {ok} valid, {errors} errors (skipped {empty_row_count} empty rows)")
        
        product_import.status = ProductImport.Status.PARSED
        product_import.row_count = total
        product_import.error_count = errors
        product_import.parse_error_message = error_message
        product_import.save(update_fields=["status", "row_count", "error_count", "parse_error_message"])

    # Clean up temp file AFTER processing is complete
    if tmp_file_created and file_path and file_path.exists():
        try:
            file_path.unlink()
            logger.info(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not delete temp file {file_path}: {e}")
    
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
    Process the import by creating Product, Variant, and ProductAttributeValue records.
    
    Key principles:
    - 1 Excel row = 1 Variant (always)
    - Product is a grouping container (for manual grouping later via Listings)
    - ALL attributes are linked to Variants, not Products
    - ProductType comes from CategoryBatch (assigned in step 2)
    
    Grouping modes:
    - If PRODUCT_KEY column has values: group variants by that key
    - Otherwise: create one individual placeholder product per variant (for manual grouping later)
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
        "errors": 0,
        "error_details": [],
    }
    
    # Get column rules to understand the structure
    column_rules = {
        rule.column_name: rule
        for rule in ImportColumnRule.objects.filter(product_import=product_import)
    }
    
    # Find key columns by role
    product_key_col = None
    variant_key_col = None
    
    for col_name, rule in column_rules.items():
        if rule.role == ImportColumnRule.Role.PRODUCT_KEY:
            product_key_col = col_name
        elif rule.role == ImportColumnRule.Role.VARIANT_KEY:
            variant_key_col = col_name
    
    # Resolve ProductType from the category field on the import.
    # Falls back to CategoryBatch (legacy path) then 'default'.
    category_name = product_import.category or ""
    if not category_name:
        legacy_batch = CategoryBatch.objects.filter(product_import=product_import).first()
        category_name = (legacy_batch.category if legacy_batch else "") or ""

    if category_name:
        category_code = slugify(category_name)
        product_type, _ = ProductType.objects.get_or_create(
            code=category_code,
            defaults={'default_label': category_name}
        )
    else:
        product_type, _ = ProductType.objects.get_or_create(
            code='default',
            defaults={'default_label': 'Default'}
        )
    
    # Get all valid rows
    rows = list(ImportRow.objects.filter(
        product_import=product_import,
        is_valid=True
    ).order_by('row_number'))
    
    if not rows:
        return stats
    
    # Determine grouping mode
    # Respect the group_by_product_key setting AND check if PRODUCT_KEY column exists AND has values
    use_grouping = False
    if product_import.group_by_product_key and product_key_col:
        # Check if PRODUCT_KEY column has values in first 20 rows
        for row in rows[:20]:
            if row.raw.get(product_key_col):
                use_grouping = True
                break
    
    # Cache for products when grouping by product_key
    product_cache = {}  # product_key -> Product
    
    # Process each row: 1 row = 1 Variant
    for row in rows:
        try:
            raw_data = row.raw
            
            # STEP 1: Determine variant unique key
            variant_sku = None
            variant_barcode = None
            
            if variant_key_col and raw_data.get(variant_key_col):
                variant_sku = str(raw_data[variant_key_col]).strip()
            
            # Check for barcode - either from mapped column or literal 'barcode' column
            for col_name, rule in column_rules.items():
                if rule.role == ImportColumnRule.Role.BARCODE and raw_data.get(col_name):
                    variant_barcode = str(raw_data[col_name]).strip()
                    break
            if not variant_barcode and 'barcode' in raw_data and raw_data['barcode']:
                variant_barcode = str(raw_data['barcode']).strip()
            
            # STEP 2: Check if variant already exists
            existing_variant = None
            if variant_sku:
                existing_variant = Variant.objects.filter(sku=variant_sku).first()
            if not existing_variant and variant_barcode:
                existing_variant = Variant.objects.filter(barcode=variant_barcode).first()
            
            # STEP 3: Determine target product
            if existing_variant:
                # Existing variant: preserve its product (manual grouping may have been done)
                target_product = existing_variant.product
            elif use_grouping and product_key_col and raw_data.get(product_key_col):
                # Grouping mode: get or create product by product_key
                product_key = str(raw_data[product_key_col]).strip()
                
                if product_key in product_cache:
                    target_product = product_cache[product_key]
                else:
                    product_code = slugify(product_key) or f"group-{row.row_number}"
                    
                    # Build product data
                    product_data = {
                        'product_type': product_type,
                        'status': Product.Status.DRAFT,
                    }
                    
                    # Extract product-level fields from row
                    for col_name, rule in column_rules.items():
                        value = raw_data.get(col_name)
                        if not value:
                            continue
                        if rule.role == ImportColumnRule.Role.BRAND:
                            product_data['brand'] = str(value)
                        elif rule.role == ImportColumnRule.Role.TITLE:
                            if 'default_label' not in product_data:
                                product_data['default_label'] = str(value)
                        elif rule.role == ImportColumnRule.Role.PRODUCT_MODEL:
                            product_data['model'] = str(value)
                        elif rule.role == ImportColumnRule.Role.PRODUCT_SERIES:
                            product_data['series'] = str(value)
                    
                    target_product, created = Product.objects.update_or_create(
                        code=product_code,
                        defaults=product_data
                    )
                    
                    if created:
                        stats["products_created"] += 1
                    else:
                        stats["products_updated"] += 1
                    
                    product_cache[product_key] = target_product
            else:
                # No grouping: create individual placeholder product for this variant
                # Extract variant title for product label
                variant_title = None
                for col_name, rule in column_rules.items():
                    if rule.role == ImportColumnRule.Role.TITLE:
                        variant_title = str(raw_data.get(col_name, '')).strip()
                        break
                if not variant_title and raw_data.get('title'):
                    variant_title = str(raw_data['title']).strip()
                
                # Generate product code from variant SKU or row number
                if variant_sku:
                    product_code = f"variant-{variant_sku}"
                else:
                    product_code = f"variant-row-{row.row_number}"
                
                product_code = slugify(product_code)
                
                # Ensure unique code
                base_code = product_code
                suffix = 1
                while Product.objects.filter(code=product_code).exists():
                    product_code = f"{base_code}-{suffix}"
                    suffix += 1
                
                # Create individual placeholder product
                target_product = Product.objects.create(
                    product_type=product_type,
                    code=product_code,
                    default_label=variant_title or f"Variant {variant_sku or row.row_number}",
                    status=Product.Status.DRAFT,
                )
                stats["products_created"] += 1
            
            # STEP 4: Create or update Variant
            variant_data = {
                'product': target_product,
            }
            
            if variant_barcode:
                variant_data['barcode'] = variant_barcode
            if 'mpn' in raw_data and raw_data['mpn']:
                variant_data['mpn'] = str(raw_data['mpn'])
            
            # Extract variant fields from mapped columns
            for col_name, rule in column_rules.items():
                value = raw_data.get(col_name)
                if not value:
                    continue
                if rule.role == ImportColumnRule.Role.TITLE:
                    variant_data['source_title'] = str(value)
                elif rule.role == ImportColumnRule.Role.DESCRIPTION:
                    variant_data['source_description'] = str(value)
                elif rule.role == ImportColumnRule.Role.MPN:
                    variant_data['mpn'] = str(value)
                elif rule.role == ImportColumnRule.Role.SOURCE_SKU:
                    variant_data['source_sku'] = str(value)
                elif rule.role == ImportColumnRule.Role.SOURCE_SUPPLIER:
                    variant_data['source_supplier'] = str(value)
                elif rule.role == ImportColumnRule.Role.SOURCE_LOCALE:
                    variant_data['source_locale'] = str(value)
            
            # Fallback: Common source fields from literal column names
            if 'source_sku' not in variant_data and raw_data.get('source_sku'):
                variant_data['source_sku'] = str(raw_data['source_sku'])
            if 'source_supplier' not in variant_data and (raw_data.get('supplier') or raw_data.get('fournisseur')):
                variant_data['source_supplier'] = str(raw_data.get('supplier') or raw_data.get('fournisseur', ''))
            
            if existing_variant:
                # Update existing variant (safe fields only)
                update_fields = []
                if variant_barcode and existing_variant.barcode != variant_barcode:
                    existing_variant.barcode = variant_barcode
                    update_fields.append('barcode')
                if 'mpn' in variant_data and existing_variant.mpn != variant_data.get('mpn'):
                    existing_variant.mpn = variant_data.get('mpn')
                    update_fields.append('mpn')
                # Update source fields if provided
                if 'source_title' in variant_data and existing_variant.source_title != variant_data.get('source_title'):
                    existing_variant.source_title = variant_data.get('source_title')
                    update_fields.append('source_title')
                if 'source_description' in variant_data and existing_variant.source_description != variant_data.get('source_description'):
                    existing_variant.source_description = variant_data.get('source_description')
                    update_fields.append('source_description')
                if 'source_sku' in variant_data and existing_variant.source_sku != variant_data.get('source_sku'):
                    existing_variant.source_sku = variant_data.get('source_sku')
                    update_fields.append('source_sku')
                if 'source_supplier' in variant_data and existing_variant.source_supplier != variant_data.get('source_supplier'):
                    existing_variant.source_supplier = variant_data.get('source_supplier')
                    update_fields.append('source_supplier')
                if 'source_locale' in variant_data and existing_variant.source_locale != variant_data.get('source_locale'):
                    existing_variant.source_locale = variant_data.get('source_locale')
                    update_fields.append('source_locale')
                if update_fields:
                    existing_variant.save(update_fields=update_fields)
                variant = existing_variant
                stats["variants_updated"] += 1
            else:
                # Create new variant
                if variant_sku:
                    variant_data['sku'] = variant_sku
                variant = Variant.objects.create(**variant_data)
                stats["variants_created"] += 1
            
            # Update row tracking
            row.parent_key = target_product.code if target_product else "unknown"
            row.save(update_fields=["parent_key"])
            
            # STEP 5: Create attributes (ALL linked to variant)
            for col_name, rule in column_rules.items():
                if rule.role != ImportColumnRule.Role.ATTRIBUTE:
                    continue
                
                value = raw_data.get(col_name)
                if not value:
                    continue
                
                # Get or create attribute
                attribute = None
                if rule.target_attribute_code:
                    from catalog.models import Attribute
                    attribute = Attribute.objects.filter(code=rule.target_attribute_code).first()
                
                if not attribute and rule.create_attribute_name:
                    from catalog.models import Attribute
                    attr_code = slugify(rule.create_attribute_name)
                    if attr_code:
                        attribute, _ = Attribute.objects.get_or_create(
                            code=attr_code,
                            defaults={'data_type': rule.attribute_type or 'text'}
                        )
                
                if not attribute:
                    continue
                
                # Build attribute value data
                pav_data = {'attribute': attribute, 'variant': variant, 'product': None}
                
                if attribute.data_type in ('text', 'enum'):
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
                
                if rule.is_variation_axis:
                    pav_data['is_axis'] = True
                
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
