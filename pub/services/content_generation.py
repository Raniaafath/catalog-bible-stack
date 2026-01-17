from __future__ import annotations

from typing import Dict, List, Optional

from catalog.models import Variant
from content.models import Locale
from kw.models import PlannerRun
from pub.models import Channel, ContentSelection, GenerationOutput, GenerationRun, Template
from pub.services.title_renderer import (
    TitleApprovalRequired,
    TitleRenderError,
    _get_approved_title_selection,
    _get_title_generation_policy,
    _reserve_unique_title,
    build_feature_list,
    render_title,
)
from pub.services.validation import validate_content


def preview_content(
    *,
    variant: Variant,
    locale: Locale,
    channel: Channel,
    run: Optional[PlannerRun] = None,
    context: str = "title",
    include_descriptions: bool = False,
) -> dict:
    policy = _get_title_generation_policy(
        channel=channel,
        locale=locale,
        context=context,
        mode_override=None,
    )
    selection = _get_approved_title_selection(
        variant=variant,
        locale=locale,
        channel=channel,
        context=policy.context,
        selection_scope=policy.selection_scope,
    )
    content_selection = _get_approved_content_selection(
        variant=variant,
        locale=locale,
        channel=channel,
        context=policy.context,
        selection_scope=policy.selection_scope,
    )
    title_result = render_title(
        variant=variant,
        locale=locale,
        channel=channel,
        run=run,
        include_descriptions=include_descriptions,
        selection=selection,
        rules=policy.rules,
    )
    features = build_feature_list(variant=variant, locale=locale, channel=channel)
    if content_selection:
        bullets = content_selection.bullets_json or []
        description = content_selection.description_text or ""
    else:
        bullets = _build_bullets(
            variant=variant,
            locale=locale,
            channel=channel,
            run=run,
            rules=policy.rules,
            features=features,
        )
        description = _build_description(
            variant=variant,
            locale=locale,
            channel=channel,
            run=run,
            rules=policy.rules,
            features=features,
        )
    unique_title = _reserve_unique_title(
        title=title_result.title,
        variant=variant,
        locale=locale,
        channel=channel,
    )
    constraint_report = validate_content(
        channel=channel,
        locale=locale,
        context=policy.context,
        title=unique_title,
        bullets=bullets,
        description=description,
    )
    return {
        "status": "preview",
        "title": title_result.title,
        "bullets": bullets,
        "description": description,
        "features": features,
        "constraint_report": constraint_report,
        "context": policy.context,
    }


def generate_content(
    *,
    variant: Variant,
    locale: Locale,
    channel: Channel,
    run: Optional[PlannerRun] = None,
    context: str = "title",
    include_descriptions: bool = False,
    mode_override: Optional[str] = None,
    batch: Optional[int] = None,
) -> dict:
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
    content_selection = _get_approved_content_selection(
        variant=variant,
        locale=locale,
        channel=channel,
        context=policy.context,
        selection_scope=policy.selection_scope,
    )
    if policy.title_mode == "review" and not selection:
        preview = preview_content(
            variant=variant,
            locale=locale,
            channel=channel,
            run=run,
            context=context,
            include_descriptions=include_descriptions,
        )
        draft = None
        if policy.auto_create_selection:
            draft = _create_content_selection(
                variant=variant,
                locale=locale,
                channel=channel,
                context=policy.context,
                planner_run=run,
                bullets=preview["bullets"],
                description=preview["description"],
                status=ContentSelection.Status.DRAFT,
            )
        raise TitleApprovalRequired(
            "Content selection requires approval",
            selection_id=draft.id if draft else None,
            preview_title=preview["title"],
        )

    try:
        title_result = render_title(
            variant=variant,
            locale=locale,
            channel=channel,
            run=run,
            include_descriptions=include_descriptions,
            selection=selection,
            rules=policy.rules,
        )
    except TitleRenderError as exc:
        raise TitleRenderError(str(exc)) from exc

    features = build_feature_list(variant=variant, locale=locale, channel=channel)
    if content_selection:
        bullets = content_selection.bullets_json or []
        description = content_selection.description_text or ""
    else:
        bullets = _build_bullets(
            variant=variant,
            locale=locale,
            channel=channel,
            run=run,
            rules=policy.rules,
            features=features,
        )
        description = _build_description(
            variant=variant,
            locale=locale,
            channel=channel,
            run=run,
            rules=policy.rules,
            features=features,
        )
    selection_for_save = content_selection
    if policy.auto_create_selection:
        selection_for_save = _create_content_selection(
            variant=variant,
            locale=locale,
            channel=channel,
            context=policy.context,
            planner_run=run,
            bullets=bullets,
            description=description,
            status=ContentSelection.Status.APPROVED if policy.auto_approve_selection else ContentSelection.Status.DRAFT,
        )
    constraint_report = validate_content(
        channel=channel,
        locale=locale,
        context=policy.context,
        title=title_result.title,
        bullets=bullets,
        description=description,
    )

    generation_run = GenerationRun.objects.create(
        product=None,
        variant=variant,
        planner_run=run,
        batch_id=batch,
        locale=locale,
        channel=channel,
        template=title_result.template,
    )
    outputs: List[GenerationOutput] = []
    outputs.append(
        GenerationOutput.objects.create(
            run=generation_run,
            field="title",
            position=0,
            text=unique_title,
            selection=selection,
            head_text=title_result.head_text or "",
            hook_text=title_result.hook_text or "",
            head_source=title_result.head_source or "",
            hook_source=title_result.hook_source or "",
            head_keyword_id=title_result.head_keyword_id,
            hook_keyword_id=title_result.hook_keyword_id,
            score_json={
                "parts": title_result.parts_debug,
                "candidate_ids": title_result.candidate_ids,
                "planner_run_id": run.id if run else None,
                "content_selection_id": selection_for_save.id if selection_for_save else None,
            },
        )
    )
    outputs.append(
        GenerationOutput.objects.create(
            run=generation_run,
            field="description",
            position=0,
            text=description,
            score_json={"content_selection_id": selection_for_save.id if selection_for_save else None},
        )
    )
    for index, bullet in enumerate(bullets, start=1):
        outputs.append(
            GenerationOutput.objects.create(
                run=generation_run,
                field="bullet",
                position=index,
                text=bullet,
                score_json={"content_selection_id": selection_for_save.id if selection_for_save else None},
            )
        )

    return {
        "status": "generated",
        "generation_run_id": generation_run.id,
        "selection_id": selection.id if selection else None,
        "content_selection_id": selection_for_save.id if selection_for_save else None,
        "constraint_report": constraint_report,
        "outputs": [
            {"field": out.field, "position": out.position, "text": out.text, "id": out.id}
            for out in outputs
        ],
    }


def _create_content_selection(
    *,
    variant: Variant,
    locale: Locale,
    channel: Channel,
    context: str,
    planner_run: Optional[PlannerRun],
    bullets: List[str],
    description: str,
    status: str,
) -> ContentSelection:
    return ContentSelection.objects.create(
        product=variant.product,
        variant=variant,
        locale=locale,
        channel=channel,
        context=context,
        planner_run=planner_run,
        status=status,
        bullets_json=bullets,
        description_text=description,
        created_by_type=ContentSelection.CreatedByType.SYSTEM,
    )


def _get_approved_content_selection(
    *,
    variant: Variant,
    locale: Locale,
    channel: Channel,
    context: str,
    selection_scope: str,
) -> Optional[ContentSelection]:
    qs = ContentSelection.objects.filter(
        status=ContentSelection.Status.APPROVED,
        locale=locale,
        channel=channel,
        context=context,
    )
    if selection_scope == "variant":
        return qs.filter(variant=variant).order_by("-updated_at", "-id").first()
    return qs.filter(product=variant.product, variant__isnull=True).order_by("-updated_at", "-id").first()


def _build_bullets(
    *,
    variant: Variant,
    locale: Locale,
    channel: Channel,
    run: Optional[PlannerRun],
    rules: Dict[str, object],
    features: List[dict],
) -> List[str]:
    bullet_rules = rules.get("bullets", {})
    default_n = _safe_int(bullet_rules.get("default_n"), 5)
    max_n = _safe_int(bullet_rules.get("max_n"), default_n)
    min_n = _safe_int(bullet_rules.get("min_n"), 0)
    max_chars = _safe_int(bullet_rules.get("max_chars_per_bullet"), 0)
    mode = bullet_rules.get("mode", "variable")

    bullets = []
    try:
        bullets_result = render_title(
            variant=variant,
            locale=locale,
            channel=channel,
            run=run,
            include_descriptions=True,
            selection=None,
            rules=rules,
            template_kind=Template.Kind.BULLETS,
        )
        bullets = [line.strip() for line in bullets_result.title.splitlines() if line.strip()]
    except TitleRenderError:
        for item in features:
            text = f"{item['attribute_code']}: {item['value']}"
            text = text.strip()
            if not text:
                continue
            bullets.append(text)

    if mode == "fixed":
        count = max(min_n, min(default_n, max_n))
    else:
        count = max(min_n, min(len(bullets), max_n))

    bullets = bullets[:count]
    if max_chars > 0:
        bullets = [_truncate_text(text, max_chars) for text in bullets]
    return bullets


def _build_description(
    *,
    variant: Variant,
    locale: Locale,
    channel: Channel,
    run: Optional[PlannerRun],
    rules: Dict[str, object],
    features: List[dict],
) -> str:
    try:
        description_result = render_title(
            variant=variant,
            locale=locale,
            channel=channel,
            run=run,
            include_descriptions=True,
            selection=None,
            rules=rules,
            template_kind=Template.Kind.DESCRIPTION,
        )
        text = description_result.title
    except TitleRenderError:
        text = ". ".join(f"{item['attribute_code']}: {item['value']}" for item in features if item.get("value"))

    max_length = _safe_int(rules.get("description", {}).get("max_length"), 0)
    if max_length > 0:
        text = _truncate_text(text, max_length)
    return text.strip()


def _truncate_text(text: str, max_length: int) -> str:
    if max_length <= 0 or len(text) <= max_length:
        return text
    if max_length <= 3:
        return text[:max_length].rstrip()
    return text[: max_length - 3].rstrip() + "..."


def _safe_int(value: object, fallback: int) -> int:
    if isinstance(value, int):
        return value
    return fallback
