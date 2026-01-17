from __future__ import annotations

from typing import Dict, List, Optional

from pub.models import Channel, ChannelLocalePolicy
from pub.services.title_renderer import _get_channel_locale_policy, _get_title_generation_policy


def validate_content(
    *,
    channel: Channel,
    locale,
    context: str,
    title: str,
    bullets: List[str],
    description: str,
) -> dict:
    policy = _get_title_generation_policy(
        channel=channel,
        locale=locale,
        context=context,
        mode_override=None,
    )
    channel_policy = _get_channel_locale_policy(channel=channel, locale=locale, context=policy.context)
    constraints = policy.rules.get("constraints", {}) if policy.rules else {}

    violations: List[dict] = []
    warnings: List[dict] = []

    title_max = _effective_limit(constraints.get("title_max_length"), getattr(channel_policy, "title_max_len", 0))
    if title_max and len(title) > title_max:
        violations.append({"field": "title", "code": "max_length", "max": title_max, "actual": len(title)})

    forbidden_terms = constraints.get("forbidden_terms") or []
    if channel_policy and channel_policy.banned_terms:
        forbidden_terms = list({*forbidden_terms, *channel_policy.banned_terms})
    for term in forbidden_terms:
        if term and term.lower() in title.lower():
            violations.append({"field": "title", "code": "forbidden_term", "term": term})

    bullet_rules = policy.rules.get("bullets", {}) if policy.rules else {}
    bullet_max_n = _safe_int(bullet_rules.get("max_n"), 0)
    if bullet_max_n and len(bullets) > bullet_max_n:
        violations.append({"field": "bullets", "code": "max_count", "max": bullet_max_n, "actual": len(bullets)})
    bullet_max_chars = _effective_limit(
        bullet_rules.get("max_chars_per_bullet"), constraints.get("bullet_max_chars")
    )
    if bullet_max_chars:
        for idx, bullet in enumerate(bullets, start=1):
            if len(bullet) > bullet_max_chars:
                violations.append(
                    {
                        "field": "bullet",
                        "position": idx,
                        "code": "max_length",
                        "max": bullet_max_chars,
                        "actual": len(bullet),
                    }
                )

    desc_max = _effective_limit(
        policy.rules.get("description", {}).get("max_length") if policy.rules else 0,
        getattr(channel_policy, "description_max_len", 0),
    )
    if desc_max and len(description) > desc_max:
        violations.append(
            {"field": "description", "code": "max_length", "max": desc_max, "actual": len(description)}
        )

    html_allowed = constraints.get("html_allowed", True)
    if not html_allowed and "<" in description and ">" in description:
        warnings.append({"field": "description", "code": "html_disallowed"})

    return {
        "violations": violations,
        "warnings": warnings,
        "context": policy.context,
    }


def _effective_limit(primary: Optional[int], fallback: Optional[int]) -> int:
    primary_val = _safe_int(primary, 0)
    if primary_val:
        return primary_val
    return _safe_int(fallback, 0)


def _safe_int(value: object, fallback: int) -> int:
    if isinstance(value, int):
        return value
    return fallback
