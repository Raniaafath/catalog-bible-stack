from __future__ import annotations

import csv
import os
from typing import Any, Dict, Iterable, List, Optional

from django.utils import timezone

from catalog.models import Product, Variant
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

    items = GenerationBatchItem.objects.filter(batch=batch).select_related("variant", "product", "generation_run")
    output_map = _load_outputs(items)

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


def _resolve_value(source: dict, *, variant: Variant, product: Product, outputs: Dict[str, Dict[int, str]]) -> str:
    src_type = source.get("type")
    if src_type == "variant":
        return str(getattr(variant, source.get("field"), "") or "")
    if src_type == "product":
        return str(getattr(product, source.get("field"), "") or "")
    if src_type == "generation_output":
        field = source.get("field")
        position = source.get("position", 0)
        return outputs.get(field, {}).get(position, "") or ""
    if src_type == "literal":
        return str(source.get("value", "") or "")
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


def _export_path(*, job: ExportJob, ext: str) -> str:
    base_dir = os.path.join("exports")
    filename = f"export_{job.id}.{ext}"
    return os.path.join(base_dir, filename)
