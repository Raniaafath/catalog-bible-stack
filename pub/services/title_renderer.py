from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

from django.conf import settings
from django.db import IntegrityError, transaction
# #region agent log
def _dlog(msg: str, data: dict, hypothesis_id: str):
    try:
        from core.debug_utils import DEBUG_LOG_PATH
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps({"message": msg, "data": data, "hypothesisId": hypothesis_id, "location": "title_renderer"}) + "\n")
    except Exception:
        pass
# #endregion
from django.db.models import Case, DecimalField, IntegerField, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Coalesce

from catalog.models import Attribute, ProductAttributeValue, ProductVariantAxis, Variant
from catalog.services.axis_resolution import AxisInfo, get_axes_for_context
from content.models import (
    AttributeValueI18n,
    AttributeValueSynonym,
    Locale,
    ProductAttributeValueI18n,
    ProductHookTerm,
    ProductTypeI18n,
    ProductTypeSynonym,
    SynonymStatus,
)
from kw.models import AttributeMap, Candidate, Keyword, Metric, PlannerRun, ProductKeywordMap
from pub.models import (
    Channel,
    ChannelLocalePolicy,
    ChannelPolicySet,
    GenerationOutput,
    GenerationRun,
    TermGlossary,
    Template,
    TemplatePart,
    TitleSelection,
    UniqueTitle,
)


class TitleRenderError(Exception):
    """Raised when a title cannot be rendered deterministically."""


class TitleApprovalRequired(TitleRenderError):
    """Raised when a title selection must be approved before generating output."""

    def __init__(
        self,
        message: str,
        *,
        selection_id: Optional[int] = None,
        preview_title: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.selection_id = selection_id
        self.preview_title = preview_title


_MATCH_PRIORITY: Dict[str, int] = {
    "pav_numeric": 100,
    "enum_map": 95,
    "attr_value_label": 90,
    "pav_text_i18n": 80,
    "pav_text": 70,
    "attr_value_code": 60,
    "product_i18n_title": 40,
    "product_source_title": 35,
    "product_label": 30,
    "product_source_desc": 10,
    "product_i18n_desc": 5,
}

_DEFAULT_RULES: Dict[str, object] = {
    "hook_strip_head_tokens": True,
    "dedupe_case_insensitive": True,
    "hook_exclude_attributes": ["product_category"],
    "head_sources_order": [
        "keyword_metric_product_category",
        "product_category",
        "product_type_metric",
        "product_type_fallback",
    ],
    "head_keyword_attribute_codes": ["product_category"],
    "head_suggestions_default_n": 5,
    "head_suggestions_max_n": 10,
    "hook_suggestions_default_n": 5,
    "hook_suggestions_max_n": 10,
    "suggestions_max_total": 12,
    "bullets": {
        "default_n": 5,
        "max_n": 10,
        "min_n": 0,
        "mode": "variable",
        "max_chars_per_bullet": 0,
    },
    "description": {
        "max_length": 0,
        "tone": "",
    },
    "export": {
        "bullet_columns_n": 5,
    },
    "constraints": {
        "title_max_length": 0,
        "description_max_length": 0,
        "bullet_max_chars": 0,
        "html_allowed": True,
        "forbidden_terms": [],
    },
}


def _normalize_term_for_match(text: Optional[str]) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class TitleRenderResult:
    title: str
    template: Template
    parts_debug: List[dict]
    candidate_ids: List[int]
    head_text: str
    hook_text: str
    head_source: str
    hook_source: str
    head_keyword_id: Optional[int]
    hook_keyword_id: Optional[int]
    missing_translations: Optional[Dict[int, Dict[str, str]]] = None  # av_id -> {code, attr_code} for UI "translate these"


@dataclass(frozen=True)
class TitleGenerationPolicy:
    title_mode: str
    auto_create_selection: bool
    auto_approve_selection: bool
    selection_scope: str
    context: str
    rules: Dict[str, object]


def render_title(
    *,
    variant: Variant,
    locale: Locale,
    channel: Channel,
    run: Optional[PlannerRun] = None,
    include_descriptions: bool = False,
    selection: Optional[TitleSelection] = None,
    rules: Optional[Dict[str, object]] = None,
    template_kind: str = Template.Kind.TITLE,
    listing=None,
    template_id: Optional[int] = None,
) -> TitleRenderResult:
    rules = _merge_rules(rules)
    product = variant.product
    # Use listing axes (e.g. color, size) when generating from a listing; else product axes
    axes_for_context: Optional[List[AxisInfo]] = get_axes_for_context(
        product, channel=channel, listing=listing
    ) if channel else None
    if template_id:
        try:
            template = Template.objects.get(
                id=template_id,
                product_type=product.product_type,
                locale=locale,
                channel=channel,
                kind=template_kind,
                status=Template.Status.ACTIVE,
            )
        except Template.DoesNotExist:
            template = None
    else:
        template = (
            Template.objects.filter(
                product_type=product.product_type,
                locale=locale,
                channel=channel,
                kind=template_kind,
                status=Template.Status.ACTIVE,
            )
            .order_by("-version", "-id")
            .first()
        )
    if not template:
        raise TitleRenderError(
            f"No active {template_kind} template for product_type={product.product_type_id} locale={locale.code} channel={channel.code}"
        )

    template_parts = (
        TemplatePart.objects.filter(template=template)
        .select_related("attribute")
        .order_by("position", "id")
    )

    variant_values = {
        pav.attribute_id: pav
        for pav in ProductAttributeValue.objects.filter(variant=variant).select_related("attribute", "attribute_value")
    }
    product_values = {
        pav.attribute_id: pav
        for pav in ProductAttributeValue.objects.filter(product=product, variant__isnull=True).select_related(
            "attribute", "attribute_value"
        )
    }
    all_pavs = list(variant_values.values()) + list(product_values.values())
    attr_value_ids = [pav.attribute_value_id for pav in all_pavs if pav.attribute_value_id]
    pav_ids = [pav.id for pav in all_pavs]
    default_locale_code = getattr(settings, "DEFAULT_LOCALE_CODE", getattr(settings, "LANGUAGE_CODE", None))
    fallback_locale = None
    if not getattr(settings, "TITLE_STRICT_LOCALE", True):
        fallback_locale = _get_fallback_locale(locale)
    # #region agent log
    _dlog(
        "render_title_locale",
        {"variant_id": variant.id, "locale_id": locale.id, "locale_code": locale.code, "attr_value_ids_sample": attr_value_ids[:15], "pav_ids_sample": pav_ids[:15]},
        "H1-H4",
    )
    # #endregion
    i18n_labels = _load_i18n_labels(attr_value_ids, locale, fallback_locale)
    pav_i18n_texts = _load_pav_i18n_texts(pav_ids, locale, fallback_locale)
    missing_av_ids = [aid for aid in attr_value_ids if aid not in i18n_labels]
    missing_codes = {}
    for pav in all_pavs:
        if pav.attribute_value_id and pav.attribute_value_id in missing_av_ids:
            missing_codes[pav.attribute_value_id] = {
                "code": pav.attribute_value.code,
                "attr_code": pav.attribute.code,
                "attribute_id": pav.attribute_id,
            }
    # #region agent log
    _dlog(
        "i18n_after_load",
        {
            "variant_id": variant.id,
            "locale_id": locale.id,
            "locale_code": locale.code,
            "i18n_labels_keys": list(i18n_labels.keys())[:20],
            "pav_i18n_texts_keys": list(pav_i18n_texts.keys())[:20] if pav_i18n_texts else [],
            "sample_av_in_labels": {aid: (aid in i18n_labels, i18n_labels.get(aid, "")[:30] if aid in i18n_labels else None) for aid in (attr_value_ids[:5])},
        },
        "H2-H4",
    )
    # #endregion
    _dlog(
        "title_i18n_loaded",
        {
            "variant_id": variant.id,
            "locale": locale.code,
            "attr_value_ids_count": len(attr_value_ids),
            "pav_ids_count": len(pav_ids),
            "i18n_labels_count": len(i18n_labels),
            "pav_i18n_texts_count": len(pav_i18n_texts) if pav_i18n_texts else 0,
            "missing_translations": missing_codes,
        },
        "translation_debug",
    )
    synonym_rows = (
        AttributeValueSynonym.objects.filter(
            attribute_value_id__in=attr_value_ids,
            locale=locale,
            status=AttributeValueSynonym.Status.APPROVED,
        )
        .filter(Q(channel=channel) | Q(channel__isnull=True))
        .annotate(
            _match_channel=Case(
                When(channel=channel, then=Value(1)),
                When(channel__isnull=True, then=Value(0)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("-_match_channel", "-score", "-updated_at", "id")
        .values("attribute_value_id", "term", "_match_channel", "score", "updated_at")
    )
    synonyms_map: Dict[int, List[str]] = {}
    for row in synonym_rows:
        synonyms_map.setdefault(row["attribute_value_id"], []).append(row["term"])

    parts: List[str] = []
    parts_debug: List[dict] = []
    candidate_ids: List[int] = []
    head_text = ""
    head_source = ""
    hook_text = ""
    hook_source = ""
    head_keyword_id: Optional[int] = None
    hook_keyword_id: Optional[int] = None
    # Track which attribute ids have already contributed axis-based values,
    # so we can avoid duplicating them via ATTRIBUTE_VALUE parts.
    axis_attribute_ids_used: Set[int] = set()
    # Context axis attribute ids — used to enforce axis-first ordering in ATTRIBUTE_VALUE parts.
    context_axis_attr_ids: Set[int] = {ai.attribute_id for ai in (axes_for_context or [])}
    # Deferred ATTRIBUTE_VALUE buckets: axes first (attr_id → text), then regular (in template order).
    _pending_axis_attr_vals: Dict[int, str] = {}
    _pending_regular_attr_vals: List[str] = []

    for part in template_parts:
        resolved = ""
        debug_entry = {
            "position": part.position,
            "part_type": part.part_type,
            "attribute": part.attribute.code if part.attribute else None,
            "keyword_role": part.keyword_role,
            "literal_text": part.literal_text,
        }
        if part.part_type == TemplatePart.PartType.KEYWORD:
            resolved, candidate_id, attr_value_id = _resolve_keyword(
                part.keyword_role,
                part.attribute,
                variant,
                locale,
                channel,
                product,
                variant_values,
                product_values,
                i18n_labels,
                synonyms_map,
                run=run,
            )
            debug_entry["candidate_id"] = candidate_id
            if attr_value_id:
                debug_entry["attribute_value_id"] = attr_value_id
            candidate_ids.append(candidate_id) if candidate_id else None
        elif part.part_type == TemplatePart.PartType.HEAD_TERM:
            if selection and selection.head_text:
                resolved = _normalize_label_text(selection.head_text)
                head_text = resolved or head_text
                head_source = selection.head_source or "selection"
                head_keyword_id = selection.head_keyword_id
                debug_entry.update({"source": head_source, "selection_id": selection.id})
            else:
                head_term, head_detail = _resolve_head_term(
                    product=product,
                    product_type=product.product_type,
                    locale=locale,
                    channel=channel,
                    run=run,
                    variant_values=variant_values,
                    product_values=product_values,
                    i18n_labels=i18n_labels,
                    synonyms_map=synonyms_map,
                    pav_i18n_texts=pav_i18n_texts,
                    rules=rules,
                )
                resolved = _normalize_label_text(head_term) if head_term else ""
                head_text = resolved or head_text
                head_source = head_detail.get("source") or ""
                head_keyword_id = head_detail.get("keyword_id")
                debug_entry.update(head_detail)
        elif part.part_type == TemplatePart.PartType.HOOK_TERM:
            if selection and selection.hook_text:
                resolved = _normalize_label_text(selection.hook_text)
                hook_text = resolved or hook_text
                hook_source = selection.hook_source or "selection"
                hook_keyword_id = selection.hook_keyword_id
                debug_entry.update({"source": hook_source, "selection_id": selection.id})
            else:
                resolved, hook_detail = _resolve_hook_term(
                    product=product,
                    locale=locale,
                    channel=channel,
                    run=run,
                    head_text=head_text,
                    include_descriptions=include_descriptions,
                    rules=rules,
                )
                hook_text = resolved or hook_text
                hook_source = hook_detail.get("source") or ""
                hook_keyword_id = hook_detail.get("keyword_id")
                debug_entry.update(hook_detail)
        elif part.part_type == TemplatePart.PartType.AXIS_ATTRIBUTE:
            resolved, axis_details = _resolve_axis_attribute(
                part.attribute,
                variant,
                variant_values,
                i18n_labels,
                synonyms_map,
                locale,
                axes_override=axes_for_context,
                pav_i18n_texts=pav_i18n_texts,
            )
            debug_entry["axis_values"] = axis_details
            # Record which attributes were used so we can avoid duplicating them
            # via ATTRIBUTE_VALUE parts later.
            # Only mark as used when the axis actually resolved a value — if it
            # resolved to empty, the ATTRIBUTE_VALUE fallback part must still fire.
            if part.attribute is not None:
                if resolved:
                    axis_attribute_ids_used.add(part.attribute.id)
                # else: resolved empty → leave fallback ATTRIBUTE_VALUE free to render
            else:
                # When no specific attribute is chosen, all axes for this context are used.
                if axes_for_context is not None:
                    for axis_info in axes_for_context:
                        axis_attribute_ids_used.add(axis_info.attribute_id)
                else:
                    # Fallback to product-level axes
                    for pav_attr_id in variant_values.keys():
                        axis_attribute_ids_used.add(pav_attr_id)
        elif part.part_type == TemplatePart.PartType.ATTRIBUTE_VALUE:
            # Skip attribute_value parts that target an attribute already rendered as an axis
            if part.attribute is not None and part.attribute.id in axis_attribute_ids_used:
                resolved = ""
                debug_entry["skipped_due_to_axis"] = True
            else:
                resolved, value_detail = _resolve_attribute_value(
                    part.attribute,
                    variant_values,
                    product_values,
                    i18n_labels,
                    synonyms_map,
                    locale,
                    pav_i18n_texts=pav_i18n_texts,
                )
                debug_entry.update(value_detail)
            # Defer emission: context-axis attributes go into an ordered bucket so they
            # always appear before non-axis attributes in the final title (axis-first rule).
            debug_entry["resolved"] = resolved
            debug_entry["included"] = bool(resolved)
            parts_debug.append(debug_entry)
            if resolved:
                if part.attribute is not None and part.attribute.id in context_axis_attr_ids:
                    # First occurrence wins; dedup handled by setdefault
                    _pending_axis_attr_vals.setdefault(part.attribute.id, resolved)
                    debug_entry["deferred_to_axis_bucket"] = True
                else:
                    _pending_regular_attr_vals.append(resolved)
            continue  # Skip the shared append block below — handled above
        elif part.part_type == TemplatePart.PartType.BRAND:
            resolved = product.brand or ""
            debug_entry["source"] = "brand"
        elif part.part_type == TemplatePart.PartType.LITERAL:
            resolved = part.literal_text or ""
            debug_entry["source"] = "literal"

        debug_entry["resolved"] = resolved
        debug_entry["included"] = bool(resolved)
        parts_debug.append(debug_entry)
        if resolved:
            parts.append(resolved)

    # Inject deferred ATTRIBUTE_VALUE parts: context axes first (in axes_for_context order),
    # then non-axis attributes in template order.  AXIS_ATTRIBUTE parts (already in parts)
    # are excluded via axis_attribute_ids_used, so no duplicates.
    for _axis_info in (axes_for_context or []):
        _val = _pending_axis_attr_vals.get(_axis_info.attribute_id)
        if _val:
            parts.append(_val)
    parts.extend(_pending_regular_attr_vals)

    title = _clean_title_parts(parts, rules=rules)
    return TitleRenderResult(
        title=title,
        template=template,
        parts_debug=parts_debug,
        candidate_ids=[cid for cid in candidate_ids if cid],
        head_text=head_text,
        hook_text=hook_text,
        head_source=head_source,
        hook_source=hook_source,
        head_keyword_id=head_keyword_id,
        hook_keyword_id=hook_keyword_id,
        missing_translations=missing_codes if missing_codes else None,
    )


def save_generation(
    *,
    variant: Variant,
    locale: Locale,
    channel: Channel,
    run: Optional[PlannerRun] = None,
    include_descriptions: bool = False,
    context: str = "title",
    mode_override: Optional[str] = None,
    listing=None,
    template_id: Optional[int] = None,
    improve_title: bool = False,
    title_ai_model: str = "",
    title_ai_instructions: str = "",
) -> GenerationOutput:
    planner_run = run
    policy = _get_title_generation_policy(
        channel=channel,
        locale=locale,
        context=context,
        mode_override=mode_override,
    )
    selection = _get_approved_title_selection(
        variant=variant,
        locale=locale,
        channel=channel,
        context=policy.context,
        selection_scope=policy.selection_scope,
    )
    if policy.title_mode == ChannelLocalePolicy.TitleMode.REVIEW and not selection:
        preview = render_title(
            variant=variant,
            locale=locale,
            channel=channel,
            run=planner_run,
            include_descriptions=include_descriptions,
            selection=None,
            rules=policy.rules,
            listing=listing,
            template_id=template_id,
        )
        draft = None
        if policy.auto_create_selection and preview.head_text:
            draft = _create_title_selection(
                variant=variant,
                locale=locale,
                channel=channel,
                context=policy.context,
                planner_run=planner_run,
                status=TitleSelection.Status.DRAFT,
                created_by_type=TitleSelection.CreatedByType.SYSTEM,
                selection_scope=policy.selection_scope,
                head_text=preview.head_text,
                head_source=preview.head_source or "auto",
                head_keyword_id=preview.head_keyword_id,
                hook_text=preview.hook_text or "",
                hook_source=preview.hook_source or "",
                hook_keyword_id=preview.hook_keyword_id,
            )
        raise TitleApprovalRequired(
            "Title selection requires approval",
            selection_id=draft.id if draft else None,
            preview_title=preview.title,
        )

    result = render_title(
        variant=variant,
        locale=locale,
        channel=channel,
        run=planner_run,
        include_descriptions=include_descriptions,
        selection=selection,
        rules=policy.rules,
        listing=listing,
        template_id=template_id,
    )

    rendered_title = result.title
    if improve_title and rendered_title:
        from pub.services.content_generation import improve_title_with_ai
        from pub.services.ai_constants import DEFAULT_DESCRIPTION_AI_MODEL
        max_chars = int((policy.rules or {}).get("title", {}).get("max_chars", 0) or 0) if isinstance((policy.rules or {}).get("title"), dict) else 0
        polished = improve_title_with_ai(
            raw_title=rendered_title,
            locale_code=locale.code,
            max_chars=max_chars,
            user_instructions=title_ai_instructions or "",
            model=(title_ai_model or "").strip() or DEFAULT_DESCRIPTION_AI_MODEL,
        )
        result.title = polished

    # #region agent log
    _dlog("save_generation before _reserve_unique_title", {"variant_id": variant.id}, "H2")
    # #endregion
    unique_title = _reserve_unique_title(
        title=result.title,
        variant=variant,
        locale=locale,
        channel=channel,
    )
    # #region agent log
    _dlog("save_generation after _reserve_unique_title", {"variant_id": variant.id}, "H2")
    # #endregion
    selection_for_output = selection
    if not selection and policy.auto_create_selection and result.head_text:
        selection_status = TitleSelection.Status.DRAFT
        if policy.title_mode == ChannelLocalePolicy.TitleMode.AUTO and policy.auto_approve_selection:
            selection_status = TitleSelection.Status.APPROVED
        selection_for_output = _create_title_selection(
            variant=variant,
            locale=locale,
            channel=channel,
            context=policy.context,
            planner_run=planner_run,
            status=selection_status,
            created_by_type=TitleSelection.CreatedByType.SYSTEM,
            selection_scope=policy.selection_scope,
            head_text=result.head_text,
            head_source=result.head_source or "auto",
            head_keyword_id=result.head_keyword_id,
            hook_text=result.hook_text or "",
            hook_source=result.hook_source or "",
            hook_keyword_id=result.hook_keyword_id,
        )
    # #region agent log
    _dlog("save_generation before atomic block", {"variant_id": variant.id}, "H1")
    # #endregion
    with transaction.atomic():
        generation_run = GenerationRun.objects.create(
            product=None,
            variant=variant,
            planner_run=planner_run,
            locale=locale,
            channel=channel,
            template=result.template,
        )
        # #region agent log
        _dlog("save_generation after GenerationRun.create", {"variant_id": variant.id}, "H1")
        # #endregion
        # Defensive: only persist keyword FKs if the Keyword still exists
        safe_head_keyword_id = result.head_keyword_id
        safe_hook_keyword_id = result.hook_keyword_id
        if safe_head_keyword_id is not None:
            if not Keyword.objects.filter(id=safe_head_keyword_id).exists():
                safe_head_keyword_id = None
        if safe_hook_keyword_id is not None:
            if not Keyword.objects.filter(id=safe_hook_keyword_id).exists():
                safe_hook_keyword_id = None

        output = GenerationOutput.objects.create(
            run=generation_run,
            field="title",
            position=0,
            text=unique_title,
            selection=selection_for_output,
            head_text=result.head_text or "",
            hook_text=result.hook_text or "",
            head_source=result.head_source or "",
            hook_source=result.hook_source or "",
            head_keyword_id=safe_head_keyword_id,
            hook_keyword_id=safe_hook_keyword_id,
            score_json={
                "title": unique_title,
                "template_id": result.template.id,
                "template_version": result.template.version,
                "parts": result.parts_debug,
                "head_text": result.head_text,
                "hook_text": result.hook_text,
                "head_source": result.head_source,
                "hook_source": result.hook_source,
                "head_keyword_id": safe_head_keyword_id,
                "hook_keyword_id": safe_hook_keyword_id,
                "selection_id": selection_for_output.id if selection_for_output else None,
                "candidate_ids": result.candidate_ids,
                "planner_run_id": planner_run.id if planner_run else None,
                "generation_run_id": generation_run.id,
                "locale": locale.code,
                "channel": channel.code,
                "variant_id": variant.id,
                "product_id": variant.product_id,
            },
        )
    # #region agent log
    _dlog("save_generation after GenerationOutput.create", {"variant_id": variant.id}, "H1")
    # #endregion
    return output, getattr(result, "missing_translations", None)


def _reserve_unique_title(
    *,
    title: str,
    variant: Variant,
    locale: Locale,
    channel: Channel,
) -> str:
    base_title = title or ""
    sku = variant.sku or variant.internal_sku or str(variant.id)
    # Prefer last segment of SKU when split by hyphen (e.g. "EXC", "LIN") so suffix is readable
    parts = re.split(r"[-_\s]+", sku)
    last_part = parts[-1].strip() if parts else ""
    if 2 <= len(last_part) <= 20 and re.match(r"^[A-Za-z0-9]+$", last_part):
        suffix = last_part
    else:
        alnum_only = re.sub(r"[^A-Za-z0-9]+", "", sku)
        suffix = alnum_only[-4:] if len(alnum_only) >= 4 else (alnum_only or str(variant.id))
    candidates = [base_title]
    if base_title:
        candidates.append(f"{base_title} {suffix}")
        candidates.append(f"{base_title} {suffix}-{variant.id}")
    else:
        candidates.append(suffix)
        candidates.append(f"{suffix}-{variant.id}")

    product_type = variant.product.product_type
    scope = UniqueTitle.Scope.VARIANT
    # #region agent log
    _dlog("_reserve_unique_title before atomic", {"variant_id": variant.id}, "H2")
    # #endregion
    with transaction.atomic():
        UniqueTitle.objects.filter(
            variant=variant,
            product_type=product_type,
            locale=locale,
            channel=channel,
            scope=scope,
        ).delete()
        for candidate in candidates:
            normalized = _normalize_term_for_match(candidate)
            if not normalized:
                continue
            # Nested atomic so IntegrityError only rolls back this create; we must not
            # run further queries in the outer atomic after an exception (Django
            # TransactionManagementError).
            try:
                with transaction.atomic():
                    UniqueTitle.objects.create(
                        product_type=product_type,
                        locale=locale,
                        channel=channel,
                        scope=scope,
                        normalized_title=normalized,
                        raw_title=candidate,
                        variant=variant,
                        product=None,
                    )
            except IntegrityError:
                continue
            return candidate
    return f"{base_title} {variant.id}".strip()


def _get_approved_title_selection(
    *,
    variant: Variant,
    locale: Locale,
    channel: Channel,
    context: str,
    selection_scope: str,
) -> Optional[TitleSelection]:
    qs = TitleSelection.objects.filter(
        status=TitleSelection.Status.APPROVED,
        locale=locale,
        channel=channel,
        context=context,
    )
    if selection_scope == ChannelLocalePolicy.SelectionScope.VARIANT:
        return qs.filter(variant=variant).order_by("-updated_at", "-id").first()
    return qs.filter(product=variant.product, variant__isnull=True).order_by("-updated_at", "-id").first()


def _resolve_keyword(
    keyword_role: str,
    slot_attribute: Optional[Attribute],
    variant: Variant,
    locale: Locale,
    channel: Channel,
    product,
    variant_values: Dict[int, ProductAttributeValue],
    product_values: Dict[int, ProductAttributeValue],
    i18n_labels: Dict[int, str],
    synonyms_map: Dict[int, List[str]],
    *,
    run: Optional[PlannerRun] = None,
) -> tuple[str, Optional[int], Optional[int]]:
    specificity = Case(
        When(variant=variant, then=Value(2)),
        When(product=product, variant__isnull=True, then=Value(1)),
        default=Value(0),
        output_field=IntegerField(),
    )
    candidates_qs = (
        Candidate.objects.filter(
            locale=locale,
            channel=channel,
            role=keyword_role,
            status=Candidate.CandidateStatus.APPROVED,
        )
        .filter(Q(variant=variant) | Q(product=product, variant__isnull=True))
        .select_related("keyword")
        .annotate(_specificity=specificity)
        .order_by("-_specificity", "-weight", "id")
    )
    candidates = list(candidates_qs)
    if candidates:
        if keyword_role == Candidate.CandidateRole.HEAD:
            head_candidate = candidates[0]
            if head_candidate:
                label = _normalize_label_text(head_candidate.keyword.term)
                return (label, head_candidate.id, None)
            return ("", None, None)

        available_value_ids = {
            pav.attribute_value_id
            for pav in list(variant_values.values()) + list(product_values.values())
            if pav.attribute_value_id
        }
        if run and available_value_ids:
            best_candidate_by_kw: Dict[int, Candidate] = {}
            for c in candidates:
                prev = best_candidate_by_kw.get(c.keyword_id)
                if not prev:
                    best_candidate_by_kw[c.keyword_id] = c
                    continue
                if (c._specificity, c.weight, -c.id) > (prev._specificity, prev.weight, -prev.id):
                    best_candidate_by_kw[c.keyword_id] = c

            kw_ids = list(best_candidate_by_kw.keys())
            metric_qs = (
                Metric.objects.filter(keyword_id=OuterRef("keyword_id"), planner_run=run)
                .order_by("-month")
            )
            avg_searches_sq = Subquery(metric_qs.values("avg_searches")[:1])
            competition_sq = Subquery(metric_qs.values("competition")[:1])
            cpc_sq = Subquery(metric_qs.values("cpc")[:1])

            priority_case = Case(
                *[When(match_kind=k, then=Value(v)) for k, v in _MATCH_PRIORITY.items()],
                default=Value(0),
                output_field=IntegerField(),
            )
            pkm = (
                ProductKeywordMap.objects.filter(
                    run=run,
                    product=product,
                    keyword_id__in=kw_ids,
                    attribute_value_id__in=available_value_ids,
                )
                .select_related("attribute_value", "attribute_value__attribute")
                .annotate(
                    _kind_priority=priority_case,
                    _avg_searches=Coalesce(avg_searches_sq, Value(0)),
                    _competition=competition_sq,
                    _cpc=cpc_sq,
                )
            )
            if slot_attribute:
                pkm = pkm.filter(attribute_id=slot_attribute.id)

            best = None
            best_key = None
            for row in pkm.iterator():
                cand = best_candidate_by_kw.get(row.keyword_id)
                if not cand:
                    continue
                label = _attribute_value_label(row.attribute_value, i18n_labels, synonyms_map)
                label_norm = _normalize_label_text(label) if label else ""
                if not label_norm:
                    continue
                comp = row._competition
                comp_sort = float(comp) if comp is not None else 1e9
                cpc = row._cpc
                cpc_sort = float(cpc) if cpc is not None else 0.0
                key = (
                    -int(row._kind_priority or 0),
                    -int(row._avg_searches or 0),
                    comp_sort,
                    -cpc_sort,
                    -int(getattr(cand, "_specificity", 0) or 0),
                    -int(cand.weight or 0),
                    row.keyword_id,
                    row.id,
                )
                if best is None or key < best_key:
                    best = (label_norm, cand.id, row.attribute_value_id)
                    best_key = key

            if best:
                return best

        if available_value_ids:
            for candidate in candidates:
                mappings = (
                    AttributeMap.objects.filter(
                        keyword=candidate.keyword,
                        status=AttributeMap.Status.APPROVED,
                        attribute_value_id__in=available_value_ids,
                    )
                    .select_related("attribute_value", "attribute_value__attribute")
                )
                if slot_attribute:
                    mappings = mappings.filter(attribute=slot_attribute)
                mappings = mappings.order_by("-confidence", "attribute_id", "attribute_value_id")

                for amap in mappings:
                    if not amap.attribute_value_id:
                        continue
                    if slot_attribute and amap.attribute_id != slot_attribute.id:
                        continue
                    label = _attribute_value_label(amap.attribute_value, i18n_labels, synonyms_map)
                    if label:
                        label_norm = _normalize_label_text(label)
                        if label_norm:
                            return (label_norm, candidate.id, amap.attribute_value_id)

    if keyword_role == Candidate.CandidateRole.HEAD:
        fallback_locale = _get_fallback_locale(locale)
        head_term = _resolve_product_type_term(product.product_type, locale, channel, fallback_locale)
        head_term = _normalize_label_text(head_term) if head_term else ""
        return (head_term, None, None) if head_term else ("", None, None)

    return ("", None, None)


def _resolve_hook_term(
    *,
    product,
    locale: Locale,
    channel: Channel,
    run: Optional[PlannerRun],
    head_text: str,
    include_descriptions: bool,
    rules: Optional[Dict[str, object]] = None,
) -> Tuple[str, dict]:
    rules = _merge_rules(rules)

    # Prefer stored hook terms for this product (group of variants) / locale / channel
    hook_terms_qs = (
        ProductHookTerm.objects.filter(product=product, locale=locale)
        .filter(Q(channel=channel) | Q(channel__isnull=True))
        .annotate(_channel_match=Case(When(channel=channel, then=Value(1)), default=Value(0), output_field=IntegerField()))
        .order_by("-_channel_match", "-priority", "id")
    )
    for hook_row in hook_terms_qs[:10]:
        hook = _normalize_label_text(hook_row.term)
        if rules.get("hook_strip_head_tokens", True):
            hook = _strip_head_tokens(hook, head_text, product=product, locale=locale, channel=channel)
        max_words = rules.get("hook_max_words")
        if isinstance(max_words, int) and max_words > 0:
            hook = " ".join(hook.split()[:max_words]).strip()
        if hook:
            return hook, {"source": "product_hook_term", "product_hook_term_id": hook_row.id}

    if not run:
        return "", {}

    metric_qs = (
        Metric.objects.filter(keyword_id=OuterRef("keyword_id"), planner_run=run)
        .order_by("-month")
    )
    avg_searches_sq = Subquery(metric_qs.values("avg_searches")[:1])
    competition_sq = Subquery(metric_qs.values("competition")[:1])
    cpc_sq = Subquery(metric_qs.values("cpc")[:1])
    priority_case = Case(
        *[When(match_kind=k, then=Value(v)) for k, v in _MATCH_PRIORITY.items()],
        default=Value(0),
        output_field=IntegerField(),
    )

    pkm = (
        ProductKeywordMap.objects.filter(run=run, product=product)
        .select_related("keyword")
        .annotate(
            _kind_priority=priority_case,
            _avg_searches=Coalesce(avg_searches_sq, Value(0)),
            _competition=competition_sq,
            _competition_sort=Coalesce(
                competition_sq,
                Value(Decimal("999999")),
                output_field=DecimalField(max_digits=20, decimal_places=6),
            ),
            _cpc=Coalesce(
                cpc_sq,
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=20, decimal_places=6),
            ),
        )
    )
    if not include_descriptions:
        pkm = pkm.exclude(match_kind__in=["product_source_desc", "product_i18n_desc"])
    pkm = pkm.exclude(match_kind__in=["pav_numeric", "attr_value_code"])
    exclude_attributes = rules.get("hook_exclude_attributes", [])
    if exclude_attributes:
        pkm = pkm.exclude(attribute__code__in=exclude_attributes)

    ordered = pkm.order_by(
        "-_kind_priority",
        "-_avg_searches",
        "_competition_sort",
        "-_cpc",
        "keyword_id",
        "id",
    )
    head_norm = _normalize_term_for_match(head_text)
    for row in ordered.iterator():
        if not row.keyword_id:
            continue
        hook = _normalize_label_text(row.keyword.term)
        hook_norm = _normalize_term_for_match(hook)
        if head_norm and hook_norm:
            if head_norm == hook_norm or head_norm in hook_norm or hook_norm in head_norm:
                continue
        if rules.get("hook_strip_head_tokens", True):
            hook = _strip_head_tokens(hook, head_text, product=product, locale=locale, channel=channel)
        if not hook:
            continue
        max_words = rules.get("hook_max_words")
        if isinstance(max_words, int) and max_words > 0:
            hook = " ".join(hook.split()[:max_words]).strip()
            if not hook:
                continue
        detail = {
            "keyword_id": row.keyword_id,
            "match_kind": row.match_kind or row.source,
            "source": row.match_kind or row.source,
            "avg_searches": int(row._avg_searches or 0),
            "competition": float(row._competition) if row._competition is not None else None,
            "cpc": float(row._cpc) if row._cpc is not None else None,
        }
        return hook, detail
    return "", {}


def _resolve_head_term(
    *,
    product,
    product_type,
    locale: Locale,
    channel: Channel,
    run: Optional[PlannerRun],
    variant_values: Dict[int, ProductAttributeValue],
    product_values: Dict[int, ProductAttributeValue],
    i18n_labels: Dict[int, str],
    synonyms_map: Dict[int, List[str]],
    pav_i18n_texts: Optional[Dict[int, str]] = None,
    rules: Optional[Dict[str, object]] = None,
) -> Tuple[str, dict]:
    rules = _merge_rules(rules)
    sources = rules.get("head_sources_order") or []
    if not isinstance(sources, list):
        sources = []
    fallback_locale = _get_fallback_locale(locale)
    fallback_term = _resolve_product_type_term(product_type, locale, channel, fallback_locale)

    for source in sources:
        if source == "keyword_metric_product_category":
            if run:
                head, detail = _resolve_head_metric_product_category(
                    product=product,
                    run=run,
                    locale=locale,
                    channel=channel,
                    i18n_labels=i18n_labels,
                    synonyms_map=synonyms_map,
                    rules=rules,
                )
                if head:
                    return head, detail
        elif source == "product_category":
            pav = _find_product_category_pav(variant_values, product_values)
            if pav:
                head, _src, _ = _stringify_attribute_value(
                    pav,
                    i18n_labels,
                    synonyms_map,
                    locale,
                    include_source=True,
                    pav_i18n_texts=pav_i18n_texts,
                )
                head = _normalize_label_text(head)
                if head:
                    return head, {"source": "product_category", "attribute_value_id": pav.attribute_value_id}
        elif source == "product_type_metric":
            if run:
                head, detail = _resolve_product_type_metric_term(
                    product_type=product_type,
                    locale=locale,
                    channel=channel,
                    run=run,
                    fallback_term=fallback_term,
                )
                if head:
                    return head, detail
        elif source == "product_type_fallback":
            if fallback_term:
                return fallback_term, {"source": "product_type_fallback"}

    if fallback_term:
        return fallback_term, {"source": "product_type_fallback"}
    return "", {"source": "product_type_fallback"}


def _find_product_category_pav(
    variant_values: Dict[int, ProductAttributeValue],
    product_values: Dict[int, ProductAttributeValue],
) -> Optional[ProductAttributeValue]:
    for pav in list(variant_values.values()) + list(product_values.values()):
        if pav.attribute and pav.attribute.code == "product_category":
            return pav
    return None


def _strip_head_tokens(
    hook: str,
    head: str,
    *,
    product=None,
    locale: Optional[Locale] = None,
    channel=None,
) -> str:
    """Remove from hook any token that matches the head or any approved head term for the product type."""
    head_tokens = set()
    if head:
        head_norm = _normalize_term_for_match(head)
        if head_norm:
            head_tokens.update(head_norm.split())
    if product and locale and channel:
        synonym_terms = (
            ProductTypeSynonym.objects.filter(
                product_type=product.product_type,
                locale=locale,
                status=SynonymStatus.APPROVED,
                is_active=True,
            )
            .filter(Q(channel=channel) | Q(channel__isnull=True))
            .values_list("term", flat=True)
        )
        for term in synonym_terms:
            if term:
                norm = _normalize_term_for_match(term)
                if norm:
                    head_tokens.update(norm.split())
    if not head_tokens:
        return hook
    orig_tokens = hook.split()
    kept = [tok for tok in orig_tokens if _normalize_term_for_match(tok) not in head_tokens]
    return " ".join(kept) if kept else hook


def _resolve_product_type_term(
    product_type,
    locale: Locale,
    channel: Channel,
    fallback_locale: Optional[Locale] = None,
) -> Optional[str]:
    """
    Return the best approved+active product_type synonym for the locale/channel,
    preferring channel-specific then channel-null, or fall back to localized label.
    """
    synonym = (
        ProductTypeSynonym.objects.filter(
            product_type=product_type,
            locale=locale,
            status=SynonymStatus.APPROVED,
            is_active=True,
        )
        .filter(Q(channel=channel) | Q(channel__isnull=True))
        .annotate(
            _match_channel=Case(
                When(channel=channel, then=Value(1)),
                When(channel__isnull=True, then=Value(0)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("-_match_channel", "-priority", "-score", "term")
        .first()
    )
    if synonym:
        return synonym.term

    label = (
        ProductTypeI18n.objects.filter(product_type=product_type, locale=locale)
        .values_list("label", flat=True)
        .first()
    )
    if label:
        return label

    if fallback_locale:
        fallback_label = (
            ProductTypeI18n.objects.filter(product_type=product_type, locale=fallback_locale)
            .values_list("label", flat=True)
            .first()
        )
        if fallback_label:
            return fallback_label

    return product_type.default_label or product_type.code


def _resolve_product_type_metric_term(
    *,
    product_type,
    locale: Locale,
    channel: Channel,
    run: PlannerRun,
    fallback_term: Optional[str],
) -> Tuple[str, dict]:
    terms: List[str] = []
    synonym_qs = (
        ProductTypeSynonym.objects.filter(
            product_type=product_type,
            locale=locale,
            status=SynonymStatus.APPROVED,
            is_active=True,
        )
        .filter(Q(channel=channel) | Q(channel__isnull=True))
        .annotate(
            _match_channel=Case(
                When(channel=channel, then=Value(1)),
                When(channel__isnull=True, then=Value(0)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("-_match_channel", "-priority", "-score", "term")
        .values_list("term", flat=True)
    )
    terms.extend(list(synonym_qs))
    label = (
        ProductTypeI18n.objects.filter(product_type=product_type, locale=locale)
        .values_list("label", flat=True)
        .first()
    )
    if label:
        terms.append(label)
    if fallback_term:
        terms.append(fallback_term)

    normalized: Dict[str, str] = {}
    for term in terms:
        norm = _normalize_term_for_match(term)
        if not norm:
            continue
        normalized.setdefault(norm, term)
    if not normalized:
        return fallback_term or "", {"source": "product_type_fallback"}

    kw_qs = Keyword.objects.filter(locale=locale, term__in=list(normalized.values())).values(
        "id",
        "term",
    )
    term_to_kw: Dict[str, int] = {}
    for row in kw_qs:
        norm = _normalize_term_for_match(row["term"])
        if norm in normalized:
            term_to_kw[normalized[norm]] = row["id"]

    best_term = None
    best_vol = -1
    best_kw_id: Optional[int] = None
    for term in normalized.values():
        kw_id = term_to_kw.get(term)
        if not kw_id:
            continue
        metric = (
            Metric.objects.filter(keyword_id=kw_id, planner_run=run)
            .order_by("-month")
            .values_list("avg_searches", flat=True)
            .first()
        )
        vol = metric or 0
        if vol > best_vol:
            best_vol = vol
            best_term = term
            best_kw_id = kw_id

    if best_term:
        return best_term, {
            "source": "product_type_metric",
            "avg_searches": int(best_vol),
            "keyword_id": best_kw_id,
        }
    return fallback_term or "", {"source": "product_type_fallback"}


def _resolve_head_metric_product_category(
    *,
    product,
    run: PlannerRun,
    locale: Locale,
    channel: Channel,
    i18n_labels: Dict[int, str],
    synonyms_map: Dict[int, List[str]],
    rules: Dict[str, object],
) -> Tuple[str, dict]:
    attribute_codes = rules.get("head_keyword_attribute_codes") or ["product_category"]
    if not isinstance(attribute_codes, list):
        attribute_codes = ["product_category"]
    metric_qs = (
        Metric.objects.filter(keyword_id=OuterRef("keyword_id"), planner_run=run)
        .order_by("-month")
    )
    avg_searches_sq = Subquery(metric_qs.values("avg_searches")[:1])
    competition_sq = Subquery(metric_qs.values("competition")[:1])
    cpc_sq = Subquery(metric_qs.values("cpc")[:1])
    priority_case = Case(
        *[When(match_kind=k, then=Value(v)) for k, v in _MATCH_PRIORITY.items()],
        default=Value(0),
        output_field=IntegerField(),
    )
    pkm = (
        ProductKeywordMap.objects.filter(run=run, product=product, attribute__code__in=attribute_codes)
        .select_related("attribute_value", "attribute_value__attribute", "keyword")
        .annotate(
            _kind_priority=priority_case,
            _avg_searches=Coalesce(avg_searches_sq, Value(0)),
            _competition=competition_sq,
            _cpc=cpc_sq,
        )
        .order_by(
            "-_kind_priority",
            "-_avg_searches",
            "_competition",
            "-_cpc",
            "keyword_id",
            "id",
        )
    )
    for row in pkm.iterator():
        label = _attribute_value_label(row.attribute_value, i18n_labels, synonyms_map)
        label_norm = _normalize_label_text(label) if label else ""
        if not label_norm:
            continue
        detail = {
            "source": "keyword_metric_product_category",
            "keyword_id": row.keyword_id,
            "attribute_value_id": row.attribute_value_id,
            "match_kind": row.match_kind or row.source,
            "avg_searches": int(row._avg_searches or 0),
            "competition": float(row._competition) if row._competition is not None else None,
            "cpc": float(row._cpc) if row._cpc is not None else None,
        }
        return label_norm, detail
    return "", {}


def _get_fallback_locale(locale: Locale) -> Optional[Locale]:
    default_locale_code = getattr(settings, "DEFAULT_LOCALE_CODE", getattr(settings, "LANGUAGE_CODE", None))
    if not default_locale_code or default_locale_code == locale.code:
        return None
    return Locale.objects.filter(code=default_locale_code).first()


def _attribute_value_label(
    av,
    i18n_labels: Dict[int, str],
    synonyms_map: Dict[int, List[str]],
) -> str:
    if not av:
        return ""
    synonym = (synonyms_map.get(av.id) or [None])[0]
    if synonym:
        return synonym
    return i18n_labels.get(av.id) or av.code or ""


def _normalize_label_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _resolve_axis_attribute(
    attribute: Optional[Attribute],
    variant: Variant,
    variant_values: Dict[int, ProductAttributeValue],
    i18n_labels: Dict[int, str],
    synonyms_map: Dict[int, List[str]],
    locale: Locale,
    axes_override: Optional[List[AxisInfo]] = None,
    pav_i18n_texts: Optional[Dict[int, str]] = None,
) -> tuple[str, List[dict]]:
    if attribute and attribute.id not in variant_values and not axes_override:
        return "", []

    if axes_override is not None:
        # Use listing/channel axes (e.g. color, size from listing Axes tab)
        resolved_values = []
        axis_details = []
        for axis_info in axes_override:
            if attribute and axis_info.attribute_id != attribute.id:
                continue
            pav = variant_values.get(axis_info.attribute_id)
            label, source, synonym_used = _stringify_attribute_value(
                pav,
                i18n_labels,
                synonyms_map,
                locale,
                include_source=True,
                pav_i18n_texts=pav_i18n_texts,
            )
            axis_details.append(
                {
                    "attribute": axis_info.attribute_code,
                    "value": label,
                    "source": source,
                    "synonym": synonym_used,
                }
            )
            if label:
                resolved_values.append(label)
        # #region agent log
        _dlog(
            "axis_attribute_resolved_values",
            {
                "variant_id": variant.id,
                "attribute": attribute.code if attribute else None,
                "resolved_values": resolved_values,
                "axis_details": axis_details,
            },
            "H1-size-axes",
        )
        # #endregion
        return " ".join(resolved_values), axis_details

    # Fallback: product-level axes only (ProductVariantAxis)
    axis_attributes = (
        ProductVariantAxis.objects.filter(product=variant.product)
        .select_related("attribute")
        .order_by("position", "id")
    )
    resolved_values: List[str] = []
    axis_details: List[dict] = []
    for axis in axis_attributes:
        if attribute and axis.attribute_id != attribute.id:
            continue
        pav = variant_values.get(axis.attribute_id)
        label, source, synonym_used = _stringify_attribute_value(
            pav,
            i18n_labels,
            synonyms_map,
            locale,
            include_source=True,
            pav_i18n_texts=pav_i18n_texts,
        )
        axis_details.append(
            {
                "attribute": axis.attribute.code,
                "value": label,
                "source": source,
                "synonym": synonym_used,
            }
        )
        if label:
            resolved_values.append(label)
        # #region agent log
        _dlog(
            "axis_attribute_resolved_values_fallback",
            {
                "variant_id": variant.id,
                "attribute": attribute.code if attribute else None,
                "resolved_values": resolved_values,
                "axis_details": axis_details,
            },
            "H1-size-axes",
        )
        # #endregion
    return " ".join(resolved_values), axis_details


def _resolve_attribute_value(
    attribute: Optional[Attribute],
    variant_values: Dict[int, ProductAttributeValue],
    product_values: Dict[int, ProductAttributeValue],
    i18n_labels: Dict[int, str],
    synonyms_map: Dict[int, List[str]],
    locale: Locale,
    pav_i18n_texts: Optional[Dict[int, str]] = None,
) -> tuple[str, dict]:
    if not attribute:
        return "", {}
    pav = variant_values.get(attribute.id) or product_values.get(attribute.id)
    value, source, synonym_used = _stringify_attribute_value(
        pav,
        i18n_labels,
        synonyms_map,
        locale,
        include_source=True,
        pav_i18n_texts=pav_i18n_texts,
    )
    detail = {"source": source}
    if synonym_used:
        detail["synonym"] = synonym_used
    return value, detail


def _stringify_attribute_value(
    pav: Optional[ProductAttributeValue],
    i18n_labels: Dict[int, str],
    synonyms_map: Dict[int, List[str]],
    locale: Locale,
    include_source: bool = False,
    pav_i18n_texts: Optional[Dict[int, str]] = None,
) -> tuple[str, Optional[str], Optional[str]] | str:
    source = None
    synonym_used = None
    if not pav:
        return ("", None, None) if include_source else ""

    if pav.attribute.data_type == Attribute.DataType.ENUM and pav.attribute_value_id:
        synonyms = synonyms_map.get(pav.attribute_value_id) or []
        # Prefer per-product translated value (ProductAttributeValueI18n) if present
        # #region agent log
        _dlog(
            "stringify_enum_check",
            {
                "pav_id": pav.id,
                "attribute_value_id": pav.attribute_value_id,
                "attr_code": pav.attribute.code,
                "locale_code": locale.code,
                "pav_in_pav_i18n": bool(pav_i18n_texts and pav.id in pav_i18n_texts),
                "av_id_in_i18n_labels": pav.attribute_value_id in i18n_labels if i18n_labels else False,
                "raw_code": pav.attribute_value.code if pav.attribute_value else None,
            },
            "H2-H5",
        )
        # #endregion
        if pav_i18n_texts and pav.id in pav_i18n_texts and pav_i18n_texts[pav.id]:
            label = pav_i18n_texts[pav.id]
            source = "enum_pav_i18n"
            return (label, source, synonym_used) if include_source else label
        if synonyms:
            synonym_used = synonyms[0]
            source = "synonym"
            return (synonym_used, source, synonym_used) if include_source else synonym_used
        label = i18n_labels.get(pav.attribute_value_id) or pav.attribute_value.code
        source = "enum_i18n" if pav.attribute_value_id in i18n_labels else "enum_code"
        if source == "enum_code":
            _dlog(
                "title_attr_using_raw",
                {
                    "attr_code": pav.attribute.code,
                    "attribute_value_id": pav.attribute_value_id,
                    "raw_code": pav.attribute_value.code,
                    "locale": locale.code,
                    "reason": "no AttributeValueI18n for this attribute_value_id + locale",
                },
                "translation_debug",
            )
        return (label, source, synonym_used) if include_source else label

    # Prefer translated label for any attribute_value (e.g. reference/code) when we have i18n
    if pav.attribute_value and pav.attribute_value.code:
        label = i18n_labels.get(pav.attribute_value_id) or pav.attribute_value.code
        source = "value_i18n" if pav.attribute_value_id and pav.attribute_value_id in i18n_labels else "value_code"
        if source == "value_code":
            _dlog(
                "title_attr_using_raw",
                {
                    "attr_code": pav.attribute.code,
                    "attribute_value_id": pav.attribute_value_id,
                    "raw_code": pav.attribute_value.code,
                    "locale": locale.code,
                    "reason": "no AttributeValueI18n for this attribute_value_id + locale",
                },
                "translation_debug",
            )
        return (label, source, synonym_used) if include_source else label

    # For free-text/numeric etc., prefer ProductAttributeValueI18n when available
    if pav_i18n_texts and pav.id in pav_i18n_texts and pav_i18n_texts[pav.id]:
        source = "value_i18n"
        return (pav_i18n_texts[pav.id], source, synonym_used) if include_source else pav_i18n_texts[pav.id]

    for value in (pav.value_text, pav.value_number, pav.value_bool, pav.value_json):
        if value not in (None, ""):
            if isinstance(value, Decimal):
                if value == value.to_integral_value():
                    text = str(int(value))
                else:
                    normalized = value.normalize()
                    text = format(normalized, "f").rstrip("0").rstrip(".")
            else:
                text = str(value)
            text_with_unit = f"{text} {pav.unit}".strip() if pav.unit else text
            source = "value"
            _dlog(
                "title_attr_using_raw",
                {
                    "attr_code": pav.attribute.code,
                    "pav_id": pav.id,
                    "raw_value": text[:80] if text else None,
                    "locale": locale.code,
                    "reason": "no ProductAttributeValueI18n for this PAV + locale; using pav.value_text/value_number",
                },
                "translation_debug",
            )
            return (text_with_unit, source, synonym_used) if include_source else text_with_unit
    return ("", source, synonym_used) if include_source else ""


def _clean_title_parts(parts: List[str], *, rules: Optional[Dict[str, object]] = None) -> str:
    rules = _merge_rules(rules)
    seen = set()
    cleaned: List[str] = []
    for part in parts:
        part_clean = part.strip()
        if not part_clean:
            continue
        if rules.get("dedupe_case_insensitive", True):
            key = part_clean.lower()
        else:
            key = part_clean
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(part_clean)
    return " ".join(cleaned).strip()


def _merge_rules(rules: Optional[Dict[str, object]]) -> Dict[str, object]:
    merged = dict(_DEFAULT_RULES)
    if isinstance(rules, dict):
        merged.update(rules)
    return merged


def get_title_suggestions(
    *,
    variant: Optional[Variant],
    product,
    locale: Locale,
    channel: Channel,
    run: Optional[PlannerRun],
    context: str,
    limit_head: Optional[int] = None,
    limit_hook: Optional[int] = None,
    include_explanations: bool = False,
    include_descriptions: bool = False,
) -> dict:
    policy = _get_title_generation_policy(
        channel=channel,
        locale=locale,
        context=context,
        mode_override=None,
    )
    variant_values = {}
    product_values = {}
    if variant:
        variant_values = {
            pav.attribute_id: pav
            for pav in ProductAttributeValue.objects.filter(variant=variant).select_related("attribute", "attribute_value")
        }
    if product:
        product_values = {
            pav.attribute_id: pav
            for pav in ProductAttributeValue.objects.filter(product=product, variant__isnull=True).select_related(
                "attribute", "attribute_value"
            )
        }
    head_limit, hook_limit = _clamp_suggestion_limits(
        rules=policy.rules,
        limit_head=limit_head,
        limit_hook=limit_hook,
    )

    selection_variant = variant or (product.variants.first() if product else None)
    selection = None
    if selection_variant:
        selection = _get_approved_title_selection(
            variant=selection_variant,
            locale=locale,
            channel=channel,
            context=policy.context,
            selection_scope=policy.selection_scope,
        )
    head_text = selection.head_text if selection else ""
    if not head_text:
        head_text, _ = _resolve_head_term(
            product=product,
            product_type=product.product_type,
            locale=locale,
            channel=channel,
            run=run,
            variant_values=variant_values,
            product_values=product_values,
            i18n_labels=_load_i18n_labels(
                _collect_attr_value_ids(variant_values, product_values),
                locale,
                _get_fallback_locale(locale),
            ),
            synonyms_map=_load_synonyms_map(
                _collect_attr_value_ids(variant_values, product_values),
                locale,
                channel,
            ),
            rules=policy.rules,
        )

    head_suggestions = _build_head_suggestions(
        product=product,
        variant=variant,
        locale=locale,
        channel=channel,
        run=run,
        rules=policy.rules,
        limit=head_limit,
        variant_values=variant_values,
        product_values=product_values,
    )
    hook_suggestions = _build_hook_suggestions(
        product=product,
        locale=locale,
        channel=channel,
        run=run,
        head_text=head_text,
        include_descriptions=include_descriptions,
        rules=policy.rules,
        limit=hook_limit,
    )
    if include_explanations:
        _attach_glossary(locale=locale, suggestions=head_suggestions)
        _attach_glossary(locale=locale, suggestions=hook_suggestions)

    return {
        "head": head_suggestions,
        "hook": hook_suggestions,
        "limits": {
            "head": head_limit,
            "hook": hook_limit,
        },
        "context": policy.context,
    }


def build_feature_list(
    *,
    variant: Variant,
    locale: Locale,
    channel: Channel,
) -> List[dict]:
    variant_values = list(
        ProductAttributeValue.objects.filter(variant=variant).select_related("attribute", "attribute_value")
    )
    product_values = list(
        ProductAttributeValue.objects.filter(product=variant.product, variant__isnull=True).select_related(
            "attribute", "attribute_value"
        )
    )
    attr_value_ids = [
        pav.attribute_value_id
        for pav in variant_values + product_values
        if pav.attribute_value_id
    ]
    fallback_locale = _get_fallback_locale(locale)
    i18n_labels = _load_i18n_labels(attr_value_ids, locale, fallback_locale)
    synonyms_map = _load_synonyms_map(attr_value_ids, locale, channel)

    features: List[dict] = []
    for pav in sorted(variant_values + product_values, key=lambda row: (row.attribute.code, row.id)):
        value, source, _synonym = _stringify_attribute_value(
            pav,
            i18n_labels,
            synonyms_map,
            locale,
            include_source=True,
        )
        if not value:
            continue
        features.append(
            {
                "attribute_code": pav.attribute.code,
                "value": value,
                "source": source,
                "attribute_value_id": pav.attribute_value_id,
            }
        )
    return features


def _clamp_suggestion_limits(
    *,
    rules: Dict[str, object],
    limit_head: Optional[int],
    limit_hook: Optional[int],
) -> Tuple[int, int]:
    head_default = _safe_int(rules.get("head_suggestions_default_n"), 5)
    head_max = _safe_int(rules.get("head_suggestions_max_n"), head_default)
    hook_default = _safe_int(rules.get("hook_suggestions_default_n"), 5)
    hook_max = _safe_int(rules.get("hook_suggestions_max_n"), hook_default)
    total_max = _safe_int(rules.get("suggestions_max_total"), head_default + hook_default)

    head = _apply_limit(limit_head, head_default, head_max)
    hook = _apply_limit(limit_hook, hook_default, hook_max)
    if head + hook > total_max:
        overflow = head + hook - total_max
        hook = max(0, hook - overflow)
    return head, hook


def _apply_limit(limit: Optional[int], default: int, max_n: int) -> int:
    if limit is None:
        return max(0, min(default, max_n))
    return max(0, min(limit, max_n))


def _safe_int(value: object, fallback: int) -> int:
    if isinstance(value, int):
        return value
    return fallback


def _build_head_suggestions(
    *,
    product,
    variant: Optional[Variant],
    locale: Locale,
    channel: Channel,
    run: Optional[PlannerRun],
    rules: Dict[str, object],
    limit: int,
    variant_values: Dict[int, ProductAttributeValue],
    product_values: Dict[int, ProductAttributeValue],
) -> List[dict]:
    if limit <= 0:
        return []
    suggestions: List[dict] = []
    seen = set()
    sources = rules.get("head_sources_order") or []
    if not isinstance(sources, list):
        sources = []

    attr_value_ids = _collect_attr_value_ids(variant_values, product_values)
    i18n_labels = _load_i18n_labels(attr_value_ids, locale, _get_fallback_locale(locale))
    synonyms_map = _load_synonyms_map(attr_value_ids, locale, channel)
    for source in sources:
        if len(suggestions) >= limit:
            break
        if source == "keyword_metric_product_category" and run:
            rows = _head_metric_product_category_candidates(
                product=product,
                run=run,
                rules=rules,
            )
            row_attr_ids = [row["attribute_value_id"] for row in rows if row.get("attribute_value_id")]
            if row_attr_ids:
                missing = [aid for aid in row_attr_ids if aid not in i18n_labels]
                if missing:
                    i18n_labels.update(_load_i18n_labels(missing, locale, _get_fallback_locale(locale)))
                    for aid, terms in _load_synonyms_map(missing, locale, channel).items():
                        synonyms_map.setdefault(aid, []).extend(terms)
            for row in rows:
                term = _attribute_value_label(row["attribute_value"], i18n_labels, synonyms_map)
                term = _normalize_label_text(term)
                if not _add_suggestion(seen, suggestions, term, row):
                    continue
                if len(suggestions) >= limit:
                    break
        elif source == "product_category":
            pav = _find_product_category_pav(variant_values, product_values)
            if pav:
                label = _attribute_value_label(pav.attribute_value, i18n_labels, synonyms_map)
                label = _normalize_label_text(label)
                _add_suggestion(
                    seen,
                    suggestions,
                    label,
                    {
                        "source": "product_category",
                        "attribute_value_id": pav.attribute_value_id,
                    },
                )
        elif source == "product_type_metric" and run:
            rows = _product_type_metric_candidates(
                product_type=product.product_type,
                locale=locale,
                channel=channel,
                run=run,
            )
            for row in rows:
                if not _add_suggestion(seen, suggestions, row["term"], row):
                    continue
                if len(suggestions) >= limit:
                    break
        elif source == "product_type_fallback":
            fallback = _resolve_product_type_term(
                product.product_type,
                locale,
                channel,
                _get_fallback_locale(locale),
            )
            _add_suggestion(
                seen,
                suggestions,
                _normalize_label_text(fallback),
                {"source": "product_type_fallback"},
            )
    return suggestions[:limit]


def _head_metric_product_category_candidates(
    *,
    product,
    run: PlannerRun,
    rules: Dict[str, object],
) -> List[dict]:
    attribute_codes = rules.get("head_keyword_attribute_codes") or ["product_category"]
    if not isinstance(attribute_codes, list):
        attribute_codes = ["product_category"]
    metric_qs = (
        Metric.objects.filter(keyword_id=OuterRef("keyword_id"), planner_run=run)
        .order_by("-month")
    )
    avg_searches_sq = Subquery(metric_qs.values("avg_searches")[:1])
    competition_sq = Subquery(metric_qs.values("competition")[:1])
    cpc_sq = Subquery(metric_qs.values("cpc")[:1])
    priority_case = Case(
        *[When(match_kind=k, then=Value(v)) for k, v in _MATCH_PRIORITY.items()],
        default=Value(0),
        output_field=IntegerField(),
    )
    rows = (
        ProductKeywordMap.objects.filter(run=run, product=product, attribute__code__in=attribute_codes)
        .select_related("attribute_value", "attribute_value__attribute", "keyword")
        .annotate(
            _kind_priority=priority_case,
            _avg_searches=Coalesce(avg_searches_sq, Value(0)),
            _competition=competition_sq,
            _cpc=cpc_sq,
        )
        .order_by(
            "-_kind_priority",
            "-_avg_searches",
            "_competition",
            "-_cpc",
            "keyword_id",
            "id",
        )
    )
    data = []
    for row in rows.iterator():
        data.append(
            {
                "source": "keyword_metric_product_category",
                "keyword_id": row.keyword_id,
                "attribute_value_id": row.attribute_value_id,
                "attribute_value": row.attribute_value,
                "match_kind": row.match_kind or row.source,
                "avg_searches": int(row._avg_searches or 0),
                "competition": float(row._competition) if row._competition is not None else None,
                "cpc": float(row._cpc) if row._cpc is not None else None,
            }
        )
    return data


def _product_type_metric_candidates(
    *,
    product_type,
    locale: Locale,
    channel: Channel,
    run: PlannerRun,
) -> List[dict]:
    fallback_term = _resolve_product_type_term(product_type, locale, channel, _get_fallback_locale(locale))
    head, detail = _resolve_product_type_metric_term(
        product_type=product_type,
        locale=locale,
        channel=channel,
        run=run,
        fallback_term=fallback_term,
    )
    if not head:
        return []
    return [
        {
            "term": head,
            "source": detail.get("source", "product_type_metric"),
            "avg_searches": detail.get("avg_searches"),
            "keyword_id": detail.get("keyword_id"),
        }
    ]


def _build_hook_suggestions(
    *,
    product,
    locale: Locale,
    channel: Channel,
    run: Optional[PlannerRun],
    head_text: str,
    include_descriptions: bool,
    rules: Dict[str, object],
    limit: int,
) -> List[dict]:
    suggestions: List[dict] = []
    seen: set = set()
    head_norm = _normalize_term_for_match(head_text)
    max_words = rules.get("hook_max_words") if isinstance(rules, dict) else None

    # Prepend stored product hook terms (for this product / locale / channel)
    hook_terms_qs = (
        ProductHookTerm.objects.filter(product=product, locale=locale)
        .filter(Q(channel=channel) | Q(channel__isnull=True))
        .annotate(_channel_match=Case(When(channel=channel, then=Value(1)), default=Value(0), output_field=IntegerField()))
        .order_by("-_channel_match", "-priority", "id")[:limit]
    )
    for hook_row in hook_terms_qs:
        if len(suggestions) >= limit:
            break
        hook = _normalize_label_text(hook_row.term)
        if rules.get("hook_strip_head_tokens", True):
            hook = _strip_head_tokens(hook, head_text, product=product, locale=locale, channel=channel)
        if isinstance(max_words, int) and max_words > 0:
            hook = " ".join(hook.split()[:max_words]).strip()
        if hook and _add_suggestion(seen, suggestions, hook, {"source": "product_hook_term", "product_hook_term_id": hook_row.id}):
            pass

    if len(suggestions) >= limit:
        return suggestions[:limit]
    if not run or limit <= 0:
        return suggestions[:limit]
    metric_qs = (
        Metric.objects.filter(keyword_id=OuterRef("keyword_id"), planner_run=run)
        .order_by("-month")
    )
    avg_searches_sq = Subquery(metric_qs.values("avg_searches")[:1])
    competition_sq = Subquery(metric_qs.values("competition")[:1])
    cpc_sq = Subquery(metric_qs.values("cpc")[:1])
    priority_case = Case(
        *[When(match_kind=k, then=Value(v)) for k, v in _MATCH_PRIORITY.items()],
        default=Value(0),
        output_field=IntegerField(),
    )

    pkm = (
        ProductKeywordMap.objects.filter(run=run, product=product)
        .select_related("keyword")
        .annotate(
            _kind_priority=priority_case,
            _avg_searches=Coalesce(avg_searches_sq, Value(0)),
            _competition=competition_sq,
            _competition_sort=Coalesce(
                competition_sq,
                Value(Decimal("999999")),
                output_field=DecimalField(max_digits=20, decimal_places=6),
            ),
            _cpc=Coalesce(
                cpc_sq,
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=20, decimal_places=6),
            ),
        )
    )
    if not include_descriptions:
        pkm = pkm.exclude(match_kind__in=["product_source_desc", "product_i18n_desc"])
    pkm = pkm.exclude(match_kind__in=["pav_numeric", "attr_value_code"])
    exclude_attributes = rules.get("hook_exclude_attributes", [])
    if exclude_attributes:
        pkm = pkm.exclude(attribute__code__in=exclude_attributes)

    ordered = pkm.order_by(
        "-_kind_priority",
        "-_avg_searches",
        "_competition_sort",
        "-_cpc",
        "keyword_id",
        "id",
    )
    for row in ordered.iterator():
        if len(suggestions) >= limit:
            break
        hook = _normalize_label_text(row.keyword.term)
        hook_norm = _normalize_term_for_match(hook)
        if head_norm and hook_norm:
            if head_norm == hook_norm or head_norm in hook_norm or hook_norm in head_norm:
                continue
        if rules.get("hook_strip_head_tokens", True):
            hook = _strip_head_tokens(hook, head_text, product=product, locale=locale, channel=channel)
        if isinstance(max_words, int) and max_words > 0:
            hook = " ".join(hook.split()[:max_words]).strip()
        if not hook:
            continue
        data = {
            "term": hook,
            "source": row.match_kind or row.source,
            "keyword_id": row.keyword_id,
            "match_kind": row.match_kind or row.source,
            "avg_searches": int(row._avg_searches or 0),
            "competition": float(row._competition) if row._competition is not None else None,
            "cpc": float(row._cpc) if row._cpc is not None else None,
        }
        if not _add_suggestion(seen, suggestions, hook, data):
            continue
    return suggestions[:limit]


def _add_suggestion(seen: set, suggestions: List[dict], term: Optional[str], data: dict) -> bool:
    if not term:
        return False
    norm = _normalize_term_for_match(term)
    if not norm or norm in seen:
        return False
    seen.add(norm)
    payload = {"term": term}
    payload.update(data)
    suggestions.append(payload)
    return True


def _attach_glossary(*, locale: Locale, suggestions: List[dict]) -> None:
    terms = [_normalize_term_for_match(item.get("term")) for item in suggestions]
    norms = [norm for norm in terms if norm]
    if not norms:
        return
    glossary = TermGlossary.objects.filter(locale=locale, term_norm__in=norms)
    by_norm = {row.term_norm: row for row in glossary}
    for item in suggestions:
        norm = _normalize_term_for_match(item.get("term"))
        row = by_norm.get(norm)
        if not row:
            continue
        item["definition"] = row.short_definition
        if row.synonyms_json:
            item["synonyms"] = row.synonyms_json
        if row.examples_json:
            item["examples"] = row.examples_json


def _load_synonyms_map(
    attr_value_ids: Iterable[int],
    locale: Locale,
    channel: Channel,
) -> Dict[int, List[str]]:
    synonym_rows = (
        AttributeValueSynonym.objects.filter(
            attribute_value_id__in=list(attr_value_ids),
            locale=locale,
            status=AttributeValueSynonym.Status.APPROVED,
        )
        .filter(Q(channel=channel) | Q(channel__isnull=True))
        .annotate(
            _match_channel=Case(
                When(channel=channel, then=Value(1)),
                When(channel__isnull=True, then=Value(0)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("-_match_channel", "-score", "-updated_at", "id")
        .values("attribute_value_id", "term")
    )
    synonyms_map: Dict[int, List[str]] = {}
    for row in synonym_rows:
        synonyms_map.setdefault(row["attribute_value_id"], []).append(row["term"])
    return synonyms_map


def _get_title_generation_policy(
    *,
    channel: Channel,
    locale: Locale,
    context: str,
    mode_override: Optional[str],
) -> TitleGenerationPolicy:
    policy = _get_channel_locale_policy(channel=channel, locale=locale, context=context)
    if policy:
        title_mode = policy.title_mode
        auto_create_selection = policy.auto_create_selection
        auto_approve_selection = policy.auto_approve_selection
        selection_scope = policy.selection_scope
        rules = _merge_rules(policy.rules_json)
        if mode_override:
            title_mode = _validate_title_mode(mode_override)
        return TitleGenerationPolicy(
            title_mode=title_mode,
            auto_create_selection=auto_create_selection,
            auto_approve_selection=auto_approve_selection,
            selection_scope=selection_scope,
            context=policy.context or context,
            rules=rules,
        )

    rules = _merge_rules({})
    title_mode = _validate_title_mode(mode_override) if mode_override else ChannelLocalePolicy.TitleMode.AUTO
    return TitleGenerationPolicy(
        title_mode=title_mode,
        auto_create_selection=False,
        auto_approve_selection=False,
        selection_scope=ChannelLocalePolicy.SelectionScope.PRODUCT,
        context=context,
        rules=rules,
    )


def _get_channel_locale_policy(
    *,
    channel: Channel,
    locale: Locale,
    context: str,
) -> Optional[ChannelLocalePolicy]:
    policy_set = (
        ChannelPolicySet.objects.filter(channel=channel, status=ChannelPolicySet.Status.ACTIVE)
        .order_by("-version", "-id")
        .first()
    )
    if not policy_set:
        return None
    policy = ChannelLocalePolicy.objects.filter(
        policy_set=policy_set,
        locale=locale,
        context=context,
    ).first()
    if policy:
        return policy
    if context != "title":
        return ChannelLocalePolicy.objects.filter(
            policy_set=policy_set,
            locale=locale,
            context="title",
        ).first()
    return None


def _validate_title_mode(mode: str) -> str:
    if mode in (ChannelLocalePolicy.TitleMode.AUTO, ChannelLocalePolicy.TitleMode.REVIEW):
        return mode
    raise TitleRenderError(f"Unknown title_mode override: {mode}")


def _create_title_selection(
    *,
    variant: Variant,
    locale: Locale,
    channel: Channel,
    context: str,
    planner_run: Optional[PlannerRun],
    status: str,
    created_by_type: str,
    selection_scope: str,
    head_text: str,
    head_source: str,
    head_keyword_id: Optional[int],
    hook_text: str,
    hook_source: str,
    hook_keyword_id: Optional[int],
) -> TitleSelection:
    product = variant.product
    target_variant = variant if selection_scope == ChannelLocalePolicy.SelectionScope.VARIANT else None
    selection, _created = TitleSelection.objects.get_or_create(
        product=product,
        variant=target_variant,
        locale=locale,
        channel=channel,
        context=context,
        defaults={
            "planner_run": planner_run,
            "status": status,
            "created_by_type": created_by_type,
            "head_text": head_text,
            "head_source": head_source,
            "head_keyword_id": head_keyword_id,
            "hook_text": hook_text,
            "hook_source": hook_source,
            "hook_keyword_id": hook_keyword_id,
        },
    )
    return selection


def _load_i18n_labels(
    attribute_value_ids: List[int],
    locale: Locale,
    fallback_locale: Optional[Locale] = None,
) -> Dict[int, str]:
    if not attribute_value_ids:
        return {}

    rows = list(AttributeValueI18n.objects.filter(
        attribute_value_id__in=attribute_value_ids, locale=locale
    ).values("attribute_value_id", "label"))
    # #region agent log
    _dlog(
        "load_i18n_labels_query",
        {"locale_id": locale.id, "locale_code": locale.code, "queried_av_ids": attribute_value_ids[:15], "rows_returned": len(rows), "returned_av_ids": [r["attribute_value_id"] for r in rows[:15]]},
        "H4",
    )
    # #endregion
    labels: Dict[int, str] = {row["attribute_value_id"]: row["label"] for row in rows}

    if fallback_locale and fallback_locale != locale:
        missing_ids = [aid for aid in attribute_value_ids if aid not in labels]
        if missing_ids:
            fallback_rows = AttributeValueI18n.objects.filter(
                attribute_value_id__in=missing_ids, locale=fallback_locale
            ).values("attribute_value_id", "label")
            for row in fallback_rows:
                labels.setdefault(row["attribute_value_id"], row["label"])

    # When AttributeValueI18n is empty (e.g. backfill not run), use any ProductAttributeValueI18n
    # for this attribute_value_id + locale so existing PAV translations are used in titles.
    missing_av_ids = [aid for aid in attribute_value_ids if aid not in labels]
    if missing_av_ids:
        pav_based = _load_i18n_labels_from_pav(missing_av_ids, locale)
        for av_id, label in pav_based.items():
            labels.setdefault(av_id, label)

    return labels


def _load_i18n_labels_from_pav(
    attribute_value_ids: List[int],
    locale: Locale,
) -> Dict[int, str]:
    """Load attribute_value_id -> label from ProductAttributeValueI18n (any PAV with that attribute_value_id).
    Used when AttributeValueI18n has no row so existing PAV translations still apply in titles."""
    if not attribute_value_ids:
        return {}
    out: Dict[int, str] = {}
    for i18n in ProductAttributeValueI18n.objects.filter(
        product_attribute_value__attribute_value_id__in=attribute_value_ids,
        locale=locale,
    ).select_related("product_attribute_value"):
        av_id = i18n.product_attribute_value.attribute_value_id
        text = (i18n.value_text or "").strip()
        if av_id and text and av_id not in out:
            out[av_id] = text
    return out


def _load_pav_i18n_texts(
    product_attribute_value_ids: List[int],
    locale: Locale,
    fallback_locale: Optional[Locale] = None,
) -> Dict[int, str]:
    """Load translated value_text for ProductAttributeValue (free-text attributes) per locale."""
    if not product_attribute_value_ids:
        return {}
    texts: Dict[int, str] = {
        row["product_attribute_value_id"]: (row["value_text"] or "").strip()
        for row in ProductAttributeValueI18n.objects.filter(
            product_attribute_value_id__in=product_attribute_value_ids,
            locale=locale,
        ).values("product_attribute_value_id", "value_text")
        if (row.get("value_text") or "").strip()
    }
    if fallback_locale and fallback_locale != locale:
        missing_ids = [pid for pid in product_attribute_value_ids if pid not in texts]
        if missing_ids:
            for row in ProductAttributeValueI18n.objects.filter(
                product_attribute_value_id__in=missing_ids,
                locale=fallback_locale,
            ).values("product_attribute_value_id", "value_text"):
                if (row.get("value_text") or "").strip():
                    texts.setdefault(row["product_attribute_value_id"], (row["value_text"] or "").strip())
    return texts


def _collect_attr_value_ids(
    variant_values: Dict[int, ProductAttributeValue],
    product_values: Dict[int, ProductAttributeValue],
) -> List[int]:
    return [
        pav.attribute_value_id
        for pav in list(variant_values.values()) + list(product_values.values())
        if pav.attribute_value_id
    ]
