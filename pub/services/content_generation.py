from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

from pub.services.ai_constants import DEFAULT_DESCRIPTION_AI_MODEL, DESCRIPTION_AI_MODELS  # noqa: E402

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
    improve_description: bool = False,
    description_user_instructions: str = "",
    description_ai_model: str = DEFAULT_DESCRIPTION_AI_MODEL,
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

    description = _maybe_improve_description(
        description=description,
        locale_code=getattr(locale, "code", "") or "",
        features=features,
        user_instructions=description_user_instructions,
        model=description_ai_model,
        improve_description=improve_description,
        rules=policy.rules,
    )

    # Preview is side-effect free: do NOT reserve unique title here.
    preview_title = title_result.title
    constraint_report = validate_content(
        channel=channel,
        locale=locale,
        context=policy.context,
        title=preview_title,
        bullets=bullets,
        description=description,
    )
    return {
        "status": "preview",
        "title": preview_title,
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
    improve_description: bool = False,
    description_user_instructions: str = "",
    description_ai_model: str = DEFAULT_DESCRIPTION_AI_MODEL,
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
            improve_description=improve_description,
            description_user_instructions=description_user_instructions,
            description_ai_model=description_ai_model,
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
                user_instructions=description_user_instructions,
                ai_model=description_ai_model,
                ai_enabled=improve_description,
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

    description = _maybe_improve_description(
        description=description,
        locale_code=getattr(locale, "code", "") or "",
        features=features,
        user_instructions=description_user_instructions,
        model=description_ai_model,
        improve_description=improve_description,
        rules=policy.rules,
    )

    unique_title = _reserve_unique_title(
        title=title_result.title,
        variant=variant,
        locale=locale,
        channel=channel,
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
            user_instructions=description_user_instructions,
            ai_model=description_ai_model,
            ai_enabled=improve_description,
        )
    constraint_report = validate_content(
        channel=channel,
        locale=locale,
        context=policy.context,
        title=unique_title,
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
            score_json={
                "content_selection_id": selection_for_save.id if selection_for_save else None,
                "description_ai_enabled": improve_description,
                "description_ai_model": description_ai_model,
                "description_user_instructions": description_user_instructions,
            },
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
    user_instructions: str = "",
    ai_model: str = DEFAULT_DESCRIPTION_AI_MODEL,
    ai_enabled: bool = False,
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
        description_user_instructions=user_instructions or "",
        description_ai_model=ai_model or DEFAULT_DESCRIPTION_AI_MODEL,
        description_ai_enabled=bool(ai_enabled),
    )


def save_content_selection(
    *,
    variant_id: int,
    locale_code: str,
    channel_code: str,
    description: str,
    bullets: Optional[List[str]] = None,
    context: str = "title",
) -> ContentSelection:
    """
    Create or update a ContentSelection for the given variant/locale/channel with
    user-provided description and bullets (e.g. after preview). Uses status DRAFT
    and created_by_type USER so it can be edited or approved later.
    """
    from django.db import transaction
    variant = Variant.objects.select_related("product").get(id=variant_id)
    locale = Locale.objects.get(code=locale_code)
    channel = Channel.objects.get(code=channel_code)
    bullets_list = list(bullets) if bullets is not None else []
    with transaction.atomic():
        selection, created = ContentSelection.objects.update_or_create(
            product=variant.product,
            variant=variant,
            locale=locale,
            channel=channel,
            context=context,
            defaults={
                "description_text": (description or "").strip(),
                "bullets_json": bullets_list,
                "status": ContentSelection.Status.DRAFT,
                "created_by_type": ContentSelection.CreatedByType.USER,
            },
        )
    return selection


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
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except Exception:
            return fallback
    return fallback


logger = logging.getLogger(__name__)


def _detect_provider(model: str) -> str:
    """Return the provider name from a model identifier."""
    if model.startswith("claude-"):
        return "anthropic"
    if model.startswith("gemini-"):
        return "google"
    return "openai"


def _build_ai_prompt(
    locale_code: str,
    attributes_summary: str,
    draft_description: str,
    user_instructions: str,
) -> tuple[str, str]:
    """Return (system_msg, user_content) shared across all providers."""
    system_msg = (
        "You are an e-commerce product copywriter. "
        "Rewrite/improve the draft in the target locale. "
        "Use ONLY provided product facts and attribute values. "
        "Do NOT invent certifications, materials, dimensions, guarantees, or performance claims. "
        "Follow user instructions for tone/style/format. "
        "Return ONLY the final description text."
    )
    user_content = (
        f"Target locale/language: {locale_code}\n\n"
        f"Attribute values (source of truth):\n{attributes_summary}\n\n"
        f"Current draft description:\n{draft_description}\n\n"
        f"User instructions:\n{user_instructions or 'Improve clarity and conversion while staying factual.'}"
    )
    return system_msg, user_content


def _build_title_ai_prompt(
    locale_code: str,
    raw_title: str,
    max_chars: int,
    user_instructions: str,
) -> tuple[str, str]:
    """Return (system_msg, user_content) for title linguistic polish."""
    char_rule = f" Do NOT exceed {max_chars} characters total." if max_chars > 0 else ""
    system_msg = (
        f"You are an SEO copywriter for marketplace product listings in {locale_code}. "
        "You receive a raw product title assembled from parts in a fixed order. "
        "Your ONLY task: add natural liaison words (articles, prepositions, connectors) "
        "between the parts so the title reads fluently in the target language and country market. "
        "Examples of liaison words: 'en', 'de', 'avec', 'für', 'mit', 'di', 'in', 'with', 'and'. "
        "STRICT RULES: "
        "1. Do NOT change the order of the existing words. "
        "2. Do NOT add any new product facts (dimensions, materials, brand names, certifications). "
        f"3.{char_rule} Keep ALL original words — only add small liaison words between them. "
        "4. If the title already reads naturally, return it unchanged. "
        "5. Return ONLY the final title text, nothing else — no quotes, no explanation."
    )
    user_content = (
        f"Target locale/language: {locale_code}\n\n"
        f"Raw title to polish:\n{raw_title}\n\n"
        f"Additional instructions:\n{user_instructions or 'Make the title flow naturally for this market.'}"
    )
    return system_msg, user_content


def _improve_with_openai(
    draft_description: str,
    locale_code: str,
    attributes_summary: str,
    user_instructions: str,
    model: str,
) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set; returning draft description")
        return draft_description
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed; returning draft description")
        return draft_description
    system_msg, user_content = _build_ai_prompt(locale_code, attributes_summary, draft_description, user_instructions)
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        text = (response.choices[0].message.content or "").strip()
        return text if text else draft_description
    except Exception as exc:
        logger.exception("OpenAI description improvement failed: %s", exc)
        return draft_description


def _improve_with_anthropic(
    draft_description: str,
    locale_code: str,
    attributes_summary: str,
    user_instructions: str,
    model: str,
) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set; returning draft description")
        return draft_description
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed; returning draft description")
        return draft_description
    system_msg, user_content = _build_ai_prompt(locale_code, attributes_summary, draft_description, user_instructions)
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_msg,
            messages=[{"role": "user", "content": user_content}],
        )
        text = (message.content[0].text if message.content else "").strip()
        return text if text else draft_description
    except Exception as exc:
        logger.exception("Anthropic description improvement failed: %s", exc)
        return draft_description


def _improve_with_google(
    draft_description: str,
    locale_code: str,
    attributes_summary: str,
    user_instructions: str,
    model: str,
) -> str:
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_AI_API_KEY not set; returning draft description")
        return draft_description
    try:
        import google.generativeai as genai
    except ImportError:
        logger.warning("google-generativeai package not installed; returning draft description")
        return draft_description
    system_msg, user_content = _build_ai_prompt(locale_code, attributes_summary, draft_description, user_instructions)
    try:
        genai.configure(api_key=api_key)
        gemini = genai.GenerativeModel(model_name=model, system_instruction=system_msg)
        response = gemini.generate_content(user_content)
        text = (response.text or "").strip()
        return text if text else draft_description
    except Exception as exc:
        logger.exception("Google AI description improvement failed: %s", exc)
        return draft_description


def improve_description_with_ai(
    draft_description: str,
    locale_code: str,
    attributes_summary: str,
    user_instructions: str,
    model: str = DEFAULT_DESCRIPTION_AI_MODEL,
) -> str:
    """
    Improve a product description using the specified AI model.
    Routes to OpenAI, Anthropic, or Google depending on model name prefix.
    Returns the improved description, or the original draft on any failure.
    """
    model = (model or "").strip() or DEFAULT_DESCRIPTION_AI_MODEL
    if model not in DESCRIPTION_AI_MODELS:
        logger.warning("Unknown AI model %r — falling back to %s", model, DEFAULT_DESCRIPTION_AI_MODEL)
        model = DEFAULT_DESCRIPTION_AI_MODEL

    provider = _detect_provider(model)
    if provider == "anthropic":
        return _improve_with_anthropic(draft_description, locale_code, attributes_summary, user_instructions, model)
    if provider == "google":
        return _improve_with_google(draft_description, locale_code, attributes_summary, user_instructions, model)
    return _improve_with_openai(draft_description, locale_code, attributes_summary, user_instructions, model)


# ── AI Title Polish ────────────────────────────────────────────────────────────

def _polish_title_with_openai(raw_title: str, locale_code: str, max_chars: int, user_instructions: str, model: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return raw_title
    try:
        from openai import OpenAI
    except ImportError:
        return raw_title
    system_msg, user_content = _build_title_ai_prompt(locale_code, raw_title, max_chars, user_instructions)
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_content}],
            temperature=0.2,
            max_tokens=256,
        )
        text = (response.choices[0].message.content or "").strip()
        return text if text else raw_title
    except Exception as exc:
        logger.exception("OpenAI title polish failed: %s", exc)
        return raw_title


def _polish_title_with_anthropic(raw_title: str, locale_code: str, max_chars: int, user_instructions: str, model: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return raw_title
    try:
        import anthropic
    except ImportError:
        return raw_title
    system_msg, user_content = _build_title_ai_prompt(locale_code, raw_title, max_chars, user_instructions)
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=256,
            system=system_msg,
            messages=[{"role": "user", "content": user_content}],
        )
        text = (message.content[0].text if message.content else "").strip()
        return text if text else raw_title
    except Exception as exc:
        logger.exception("Anthropic title polish failed: %s", exc)
        return raw_title


def _polish_title_with_google(raw_title: str, locale_code: str, max_chars: int, user_instructions: str, model: str) -> str:
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        return raw_title
    try:
        import google.generativeai as genai
    except ImportError:
        return raw_title
    system_msg, user_content = _build_title_ai_prompt(locale_code, raw_title, max_chars, user_instructions)
    try:
        genai.configure(api_key=api_key)
        gemini = genai.GenerativeModel(model_name=model, system_instruction=system_msg)
        response = gemini.generate_content(user_content)
        text = (response.text or "").strip()
        return text if text else raw_title
    except Exception as exc:
        logger.exception("Google AI title polish failed: %s", exc)
        return raw_title


def improve_title_with_ai(
    raw_title: str,
    locale_code: str,
    max_chars: int = 0,
    user_instructions: str = "",
    model: str = DEFAULT_DESCRIPTION_AI_MODEL,
) -> str:
    """
    Linguistically polish a raw template-built title for natural flow in the target locale.
    Only adds liaison words (articles, prepositions) — never adds new facts or reorders parts.
    Returns the polished title, or the original on any failure.
    """
    model = (model or "").strip() or DEFAULT_DESCRIPTION_AI_MODEL
    if model not in DESCRIPTION_AI_MODELS:
        logger.warning("Unknown AI model %r — falling back to %s", model, DEFAULT_DESCRIPTION_AI_MODEL)
        model = DEFAULT_DESCRIPTION_AI_MODEL

    provider = _detect_provider(model)
    if provider == "anthropic":
        polished = _polish_title_with_anthropic(raw_title, locale_code, max_chars, user_instructions, model)
    elif provider == "google":
        polished = _polish_title_with_google(raw_title, locale_code, max_chars, user_instructions, model)
    else:
        polished = _polish_title_with_openai(raw_title, locale_code, max_chars, user_instructions, model)

    if max_chars > 0:
        polished = _truncate_text(polished, max_chars)
    return (polished or "").strip() or raw_title


def polish_title_with_explanation(
    raw_title: str,
    locale_code: str,
    user_instructions: str = "",
    model: str = DEFAULT_DESCRIPTION_AI_MODEL,
) -> Dict[str, str]:
    """
    Polish a title and return both the result and an explanation of changes.
    Returns {"polished": str, "explanation": str}.
    """
    import json as _json
    model = (model or "").strip() or DEFAULT_DESCRIPTION_AI_MODEL
    if model not in DESCRIPTION_AI_MODELS:
        model = DEFAULT_DESCRIPTION_AI_MODEL

    char_rule = ""
    system_msg = (
        f"You are an SEO copywriter for marketplace product listings in {locale_code}. "
        "You receive a raw product title assembled from template parts. "
        "Your task: improve the title for natural fluency in the target language and market. "
        "You may add liaison words (articles, prepositions, connectors) and fix grammar or word order if needed. "
        "STRICT RULES: "
        "1. Do NOT add new product facts (dimensions, materials, brand names, certifications). "
        "2. Keep ALL original content words. "
        "3. If the title already reads naturally, return it unchanged. "
        f"Return JSON only: {{\"polished\": \"<improved title>\", \"explanation\": \"<what you changed and why, in {locale_code} language>\"}}"
    )
    user_content = (
        f"Target locale: {locale_code}\n\n"
        f"Raw title:\n{raw_title}\n\n"
        f"Additional instructions:\n{user_instructions or 'Make the title flow naturally for this market.'}"
    )

    raw = None
    try:
        provider = _detect_provider(model)
        if provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                msg = client.messages.create(
                    model=model, max_tokens=512, system=system_msg,
                    messages=[{"role": "user", "content": user_content}], temperature=0.2,
                )
                raw = (msg.content[0].text if msg.content else "").strip()
        elif provider == "google":
            api_key = os.getenv("GOOGLE_AI_API_KEY")
            if api_key:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                g = genai.GenerativeModel(
                    model_name=model, system_instruction=system_msg,
                    generation_config={"temperature": 0.2, "max_output_tokens": 512, "response_mime_type": "application/json"},
                )
                raw = g.generate_content(user_content).text
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                resp = client.chat.completions.create(
                    model=model, temperature=0.2, max_tokens=512,
                    messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_content}],
                    response_format={"type": "json_object"},
                )
                raw = (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.exception("AI title polish with explanation failed: %s", exc)

    if raw:
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[1:]).rsplit("```", 1)[0]
            data = _json.loads(cleaned)
            polished = (data.get("polished") or "").strip()
            explanation = (data.get("explanation") or "").strip()
            if polished:
                return {"polished": polished, "explanation": explanation}
        except Exception:
            pass

    return {"polished": raw_title, "explanation": "No changes made."}


def _attributes_summary_from_features(features: List[dict]) -> str:
    lines = []
    for item in features:
        code = str(item.get("attribute_code") or "").strip()
        value = str(item.get("value") or "").strip()
        if code and value:
            lines.append(f"- {code}: {value}")
    return "\n".join(lines)


def _maybe_improve_description(
    *,
    description: str,
    locale_code: str,
    features: List[dict],
    user_instructions: str,
    model: str,
    improve_description: bool,
    rules: Dict[str, object],
) -> str:
    if not improve_description:
        return description
    attributes_summary = _attributes_summary_from_features(features)
    improved = improve_description_with_ai(
        draft_description=description,
        locale_code=locale_code,
        attributes_summary=attributes_summary,
        user_instructions=user_instructions,
        model=model,
    )
    desc = rules.get("description")
    max_length = _safe_int(desc.get("max_length"), 0) if isinstance(desc, dict) else 0
    if max_length > 0:
        improved = _truncate_text(improved, max_length)
    improved = (improved or "").strip()
    return improved if improved else description
