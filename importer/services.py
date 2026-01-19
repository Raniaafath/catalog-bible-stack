from __future__ import annotations

import csv
import datetime as dt
import json
import re
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
