"""Import Google Ads / Keyword Planner CSV into Keyword, Metric, PlannerRunKeyword."""

from __future__ import annotations

import csv
import datetime
from io import StringIO
from typing import Optional

from content.models import Locale
from kw.models import Keyword, Metric, PlannerRun, PlannerRunKeyword, Source
from pub.models import Channel


def _agent_debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    payload = {
        "sessionId": "debug-session",
        "runId": "pre-fix",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(datetime.datetime.utcnow().timestamp() * 1000),
    }
    try:
        from core.debug_utils import DEBUG_LOG_PATH
        import os, json as _json

        os.makedirs(DEBUG_LOG_PATH.parent, exist_ok=True)
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(_json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def parse_month(month_str: Optional[str]) -> datetime.date:
    if month_str:
        try:
            return datetime.datetime.strptime(month_str.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    today = datetime.date.today()
    return today.replace(day=1)


def parse_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(str(value).replace(",", "").replace(".", ""))
    except ValueError:
        return None


def parse_decimal(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace('"', "")
    if text == "":
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _detect_csv_encoding(raw: bytes) -> str:
    """Detect encoding from BOM or UTF-16 null-byte pattern (e.g. Excel export)."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if raw.startswith(b"\xff\xfe"):
        return "utf-16-le"
    if raw.startswith(b"\xfe\xff"):
        return "utf-16-be"
    # Heuristic: UTF-16 LE often has null every other byte in ASCII text (e.g. "Keyword" -> K\x00e\x00y...)
    sample = raw[:2000]
    if len(sample) >= 4 and sample[1] == 0 and sample[3] == 0:
        try:
            sample.decode("utf-16-le")
            return "utf-16-le"
        except UnicodeDecodeError:
            pass
    return "utf-8"


def _read_csv_file_as_text(file) -> str:
    """Read file-like object into string, auto-detecting UTF-8 vs UTF-16."""
    raw = file.read()
    if isinstance(raw, str):
        return raw
    encoding = _detect_csv_encoding(raw)
    return raw.decode(encoding, errors="replace")


def import_keywords_csv(
    *,
    file,
    locale_code: str,
    channel_code: str,
    source_code: str = "google_ads",
    run_id: Optional[int] = None,
    product_type_id: Optional[int] = None,
    month_str: Optional[str] = None,
    delimiter: str = ",",
) -> dict:
    """
    Read CSV from file-like object (e.g. UploadedFile), create/update Keyword, Metric,
    PlannerRunKeyword, and optionally create a PlannerRun.
    Returns dict with run_id, keywords_created, keywords_updated, metrics_created,
    metrics_updated, run_links.
    """
    # region agent log
    _agent_debug_log(
        hypothesis_id="H1_H3",
        location="kw.services.csv_import.import_keywords_csv:start",
        message="Starting CSV import",
        data={
            "locale_code": locale_code,
            "channel_code": channel_code,
            "has_run_id": bool(run_id),
            "product_type_id": product_type_id,
            "delimiter": delimiter,
            "file_cls": file.__class__.__name__,
        },
    )
    # endregion agent log
    locale = Locale.objects.get(code=locale_code)
    channel = Channel.objects.get(code=channel_code, is_active=True)
    source, _ = Source.objects.get_or_create(code=source_code)
    month = parse_month(month_str)

    if run_id:
        run = PlannerRun.objects.get(id=run_id)
    else:
        run = PlannerRun.objects.create(
            source=source,
            locale=locale,
            channel=channel,
            product_type_id=product_type_id,
            status=PlannerRun.Status.SUCCESS,
            started_at=datetime.datetime.utcnow(),
            finished_at=datetime.datetime.utcnow(),
            request_json={"import": "google_ads_csv"},
        )

    created_kw = updated_kw = created_metric = updated_metric = linked = 0

    if hasattr(file, "read"):
        # Support UTF-8 and UTF-16 (e.g. Excel / Google export). Decode to text then parse.
        text = _read_csv_file_as_text(file)
        f = StringIO(text)
    else:
        raise TypeError("file must be a file-like object")

    reader = csv.DictReader(f, delimiter=delimiter)
    if reader.fieldnames is None:
        raise ValueError("CSV has no header row")
    raw_headers = list(reader.fieldnames)
    # If comma gave a single column that contains tabs, retry with tab (e.g. Google Keyword Stats export)
    if len(raw_headers) == 1 and "\t" in (raw_headers[0] or "") and delimiter == ",":
        f = StringIO(text)
        delimiter = "\t"
        reader = csv.DictReader(f, delimiter=delimiter)
        raw_headers = list(reader.fieldnames) if reader.fieldnames else []
    # Strip BOM and whitespace so "Keyword" / "\ufeffKeyword" / " Keyword " all match
    normalized_to_actual = {}
    for h in raw_headers:
        key = (h.lstrip("\ufeff").strip()).lower()
        if key:
            normalized_to_actual[key] = h
    # region agent log
    _agent_debug_log(
        hypothesis_id="H3",
        location="kw.services.csv_import.import_keywords_csv:after_header",
        message="Parsed CSV header",
        data={"fieldnames": raw_headers},
    )
    # endregion agent log
    # Required: (canonical name, [normalized keys to try])
    required = [
        ("Keyword", ["keyword", "keyword idea", "search term", "suchbegriff", "keyword text"]),
        ("Avg. monthly searches", ["avg. monthly searches", "avg. monthly search volume", "monthly searches"]),
    ]
    col_map = {}
    for canonical, norm_keys in required:
        actual = None
        for k in norm_keys:
            actual = normalized_to_actual.get(k)
            if actual is not None:
                break
        if actual is None:
            raise ValueError(
                f"Missing required column '{canonical}' in CSV. "
                f"Found columns: {raw_headers!r}. "
                "Expected columns: Keyword, Avg. monthly searches. See the upload page for format and example."
            )
        col_map[canonical] = actual
    # Optional columns (use canonical if missing)
    optional = [
        ("Competition (indexed value)", "competition (indexed value)"),
        ("Top of page bid (high range)", "top of page bid (high range)"),
        ("Top of page bid (low range)", "top of page bid (low range)"),
    ]
    for canonical, norm_key in optional:
        col_map[canonical] = normalized_to_actual.get(norm_key, canonical)

    for row in reader:
        term = (row.get(col_map["Keyword"]) or "").strip()
        if not term:
            continue
        avg_searches = parse_int(row.get(col_map["Avg. monthly searches"]))
        competition = parse_decimal(row.get(col_map["Competition (indexed value)"]))
        cpc_high = parse_decimal(row.get(col_map["Top of page bid (high range)"]))
        cpc_low = parse_decimal(row.get(col_map["Top of page bid (low range)"]))

        kw_obj, kw_created = Keyword.objects.get_or_create(
            locale=locale,
            normalized_term=term.lower(),
            defaults={"term": term},
        )
        if not kw_created and kw_obj.term != term:
            kw_obj.term = term
            kw_obj.save(update_fields=["term"])
        created_kw += 1 if kw_created else 0
        updated_kw += 0 if kw_created else 1

        metric_defaults = {
            "avg_searches": avg_searches,
            "competition": competition,
            "cpc": cpc_high or cpc_low,
            "raw_json": {
                "cpc_high": cpc_high,
                "cpc_low": cpc_low,
                "competition_index": competition,
            },
        }
        metric, metric_created = Metric.objects.update_or_create(
            keyword=kw_obj,
            source=source,
            month=month,
            planner_run=run,
            defaults=metric_defaults,
        )
        created_metric += 1 if metric_created else 0
        updated_metric += 0 if metric_created else 1

        _, link_created = PlannerRunKeyword.objects.get_or_create(run=run, keyword=kw_obj)
        linked += 1 if link_created else 0

    return {
        "run_id": run.id,
        "keywords_created": created_kw,
        "keywords_updated": updated_kw,
        "metrics_created": created_metric,
        "metrics_updated": updated_metric,
        "run_links": linked,
    }
