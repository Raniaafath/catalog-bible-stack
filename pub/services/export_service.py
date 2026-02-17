from __future__ import annotations

import csv
import os
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from django.utils import timezone

from django.db import models

from catalog.models import Attribute, Product, ProductAttributeValue, Variant
from content.models import Locale
from pub.models import ExportJob, ExportProfile, GenerationBatch, GenerationBatchItem, GenerationOutput
from pub.services.title_renderer import _get_title_generation_policy


class ExportServiceError(RuntimeError):
    """Raised when an export job cannot be completed."""


def run_export_job(*, job: ExportJob) -> ExportJob:
    job.status = ExportJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    try:
        profile = job.profile
        if profile.format == ExportProfile.Format.CSV:
            file_path = _export_csv(job=job, profile=profile)
        elif profile.format == ExportProfile.Format.XLSX:
            file_path = _export_xlsx(job=job, profile=profile)
        else:
            raise ExportServiceError(f"Unsupported export format: {profile.format}")
        job.result_file = file_path
        job.stats_json = job.stats_json or {}
        job.status = ExportJob.Status.DONE
        job.finished_at = timezone.now()
        job.save(update_fields=["result_file", "stats_json", "status", "finished_at"])
    except Exception as exc:
        job.status = ExportJob.Status.FAILED
        job.error_message = str(exc)
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_message", "finished_at"])
        raise

    return job


def _export_csv(*, job: ExportJob, profile: ExportProfile) -> str:
    rows = list(_build_rows(job=job, profile=profile))
    file_path = _export_path(job=job, ext="csv")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)
    return file_path


def _export_xlsx(*, job: ExportJob, profile: ExportProfile) -> str:
    try:
        import openpyxl
    except Exception as exc:
        raise ExportServiceError("openpyxl is required for XLSX exports.") from exc

    rows = list(_build_rows(job=job, profile=profile))
    file_path = _export_path(job=job, ext="xlsx")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    workbook.save(file_path)
    return file_path


def _build_rows(*, job: ExportJob, profile: ExportProfile) -> Iterable[List[str]]:
    columns = profile.columns_json or []
    if not isinstance(columns, list):
        raise ExportServiceError("columns_json must be a list.")

    header = [col.get("key", "") for col in columns]
    yield header

    batch = job.batch
    if not batch:
        return

    policy = _get_title_generation_policy(
        channel=batch.channel,
        locale=batch.locale,
        context=batch.context,
        mode_override=None,
    )

    items = list(GenerationBatchItem.objects.filter(batch=batch).select_related("variant", "product", "generation_run"))
    output_map = _load_outputs(items)
    
    # Prefetch attribute values for all variants and products to avoid N+1 queries
    variant_ids = [item.variant_id for item in items if item.variant_id]
    product_ids = [item.product_id for item in items if item.product_id]
    
    # Load all attribute values for variants and products
    variant_pavs = {}
    product_pavs = {}
    if variant_ids or product_ids:
        pavs = ProductAttributeValue.objects.filter(
            models.Q(variant_id__in=variant_ids) | models.Q(product_id__in=product_ids)
        ).select_related("attribute", "attribute_value")
        
        for pav in pavs:
            if pav.variant_id:
                variant_pavs.setdefault(pav.variant_id, {})[pav.attribute.code] = pav
            if pav.product_id:
                product_pavs.setdefault(pav.product_id, {})[pav.attribute.code] = pav
    
    # Build attribute code cache - include both explicit attribute sources and potential fallback fields
    attribute_codes = set()
    for col in columns:
        source = col.get("source", {})
        if source.get("type") == "attribute":
            attribute_codes.add(source.get("code", ""))
        elif source.get("type") in ("variant", "product"):
            # Also cache fields that might be attributes (for fallback lookup)
            field = source.get("field", "")
            if field:
                attribute_codes.add(field)
    
    # Also add all attribute codes from the prefetched PAVs
    for pav_list in [*variant_pavs.values(), *product_pavs.values()]:
        for pav in pav_list.values():
            if pav.attribute:
                attribute_codes.add(pav.attribute.code)
    
    attribute_cache = {}
    if attribute_codes:
        attributes = Attribute.objects.filter(code__in=attribute_codes)
        attribute_cache = {attr.code: attr for attr in attributes}

    total_rows = 0
    total_errors = 0
    for item in items:
        variant = item.variant
        product = item.product
        row = []
        for col in columns:
            value = _resolve_value(
                col.get("source", {}),
                variant=variant,
                product=product,
                outputs=output_map.get(item.generation_run_id, {}),
                variant_pavs=variant_pavs.get(variant.id if variant else None, {}),
                product_pavs=product_pavs.get(product.id if product else None, {}),
                attribute_cache=attribute_cache,
            )
            value = _apply_transforms(value, col.get("transform", []), policy.rules)
            if col.get("required") and not value:
                total_errors += 1
            row.append(value or "")
        total_rows += 1
        yield row

    job.stats_json = {
        "rows": total_rows,
        "errors": total_errors,
    }


def _resolve_value(
    source: dict,
    *,
    variant: Variant,
    product: Product,
    outputs: Dict[str, Dict[int, str]],
    variant_pavs: Dict[str, ProductAttributeValue] = None,
    product_pavs: Dict[str, ProductAttributeValue] = None,
    attribute_cache: Dict[str, Attribute] = None,
) -> str:
    src_type = source.get("type")
    if src_type == "variant":
        field = source.get("field", "")
        # Try to get the field from variant model
        value = getattr(variant, field, None)
        if value is not None and value != "":
            return str(value)
        # If field doesn't exist or is empty, try as attribute (fallback)
        if field and variant_pavs and field in variant_pavs:
            pav = variant_pavs[field]
            return _format_attribute_value(pav, attribute_cache.get(field) if attribute_cache else None)
        # Also check product-level attributes as fallback
        if field and product_pavs and field in product_pavs:
            pav = product_pavs[field]
            return _format_attribute_value(pav, attribute_cache.get(field) if attribute_cache else None)
        return ""
    if src_type == "product":
        field = source.get("field", "")
        # Try to get the field from product model
        value = getattr(product, field, None)
        if value is not None and value != "":
            return str(value)
        # If field doesn't exist or is empty, try as attribute (fallback)
        if field and product_pavs and field in product_pavs:
            pav = product_pavs[field]
            return _format_attribute_value(pav, attribute_cache.get(field) if attribute_cache else None)
        # Also check variant-level attributes as fallback
        if field and variant_pavs and field in variant_pavs:
            pav = variant_pavs[field]
            return _format_attribute_value(pav, attribute_cache.get(field) if attribute_cache else None)
        return ""
    if src_type == "generation_output":
        field = source.get("field")
        position = source.get("position", 0)
        return outputs.get(field, {}).get(position, "") or ""
    if src_type == "literal":
        return str(source.get("value", "") or "")
    if src_type == "attribute":
        attribute_code = source.get("code", "")
        if not attribute_code:
            return ""
        
        # Try variant-level first, then product-level
        pav = None
        if variant_pavs and attribute_code in variant_pavs:
            pav = variant_pavs[attribute_code]
        elif product_pavs and attribute_code in product_pavs:
            pav = product_pavs[attribute_code]
        
        if pav:
            return _format_attribute_value(pav, attribute_cache.get(attribute_code) if attribute_cache else None)
        return ""
    return ""


def _apply_transforms(value: str, transforms: list, rules: dict) -> str:
    if not transforms:
        return value
    out = value
    for transform in transforms:
        op = transform.get("op")
        if op == "truncate":
            max_len = transform.get("max")
            if max_len is None:
                max_len = _policy_value(rules, transform.get("max_from_policy"))
            out = _truncate(out, max_len)
        elif op == "strip_newlines":
            out = out.replace("\n", " ").replace("\r", " ").strip()
        elif op == "strip_html":
            out = _strip_html(out)
        elif op == "default_if_empty":
            if not out:
                out = transform.get("value", "")
        elif op == "join_list":
            if isinstance(out, list):
                separator = transform.get("separator", " ")
                out = separator.join([str(item) for item in out if item])
    return out


def _policy_value(rules: dict, path: Optional[str]) -> Optional[int]:
    if not path:
        return None
    current = rules
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current if isinstance(current, int) else None


def _truncate(text: str, max_len: Optional[int]) -> str:
    if not max_len or len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."


def _strip_html(text: str) -> str:
    out = []
    in_tag = False
    for ch in text:
        if ch == "<":
            in_tag = True
            continue
        if ch == ">":
            in_tag = False
            continue
        if not in_tag:
            out.append(ch)
    return "".join(out).strip()


def _load_outputs(items: Iterable[GenerationBatchItem]) -> Dict[int, Dict[str, Dict[int, str]]]:
    run_ids = [item.generation_run_id for item in items if item.generation_run_id]
    outputs = GenerationOutput.objects.filter(run_id__in=run_ids)
    output_map: Dict[int, Dict[str, Dict[int, str]]] = {}
    for output in outputs:
        run_map = output_map.setdefault(output.run_id, {})
        field_map = run_map.setdefault(output.field, {})
        field_map[output.position or 0] = output.text
    return output_map


def _format_attribute_value(pav: ProductAttributeValue, attribute: Optional[Attribute] = None) -> str:
    """
    Format a ProductAttributeValue into a string for export.
    Similar to _stringify_attribute_value but simpler (no i18n/synonyms).
    """
    if not pav:
        return ""
    
    # Use attribute from pav if not provided
    if not attribute:
        attribute = pav.attribute
    
    # Handle ENUM type - use attribute_value code
    if attribute.data_type == Attribute.DataType.ENUM and pav.attribute_value:
        return pav.attribute_value.code
    
    # Handle different value types
    if pav.value_text:
        text = pav.value_text
    elif pav.value_number is not None:
        # Format numbers nicely
        if isinstance(pav.value_number, Decimal):
            if pav.value_number == pav.value_number.to_integral_value():
                text = str(int(pav.value_number))
            else:
                normalized = pav.value_number.normalize()
                text = format(normalized, "f").rstrip("0").rstrip(".")
        else:
            text = str(pav.value_number)
    elif pav.value_bool is not None:
        text = "Yes" if pav.value_bool else "No"
    elif pav.value_json:
        text = str(pav.value_json)
    else:
        return ""
    
    # Add unit if present
    if pav.unit:
        return f"{text} {pav.unit}".strip()
    return text


def _export_path(*, job: ExportJob, ext: str) -> str:
    base_dir = os.path.join("exports")
    filename = f"export_{job.id}.{ext}"
    return os.path.join(base_dir, filename)
