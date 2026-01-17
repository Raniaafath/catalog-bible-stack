from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence


@dataclass
class KeywordIdeaRow:
    text: str
    avg_monthly_searches: int | None
    competition: str | None
    monthly_volumes: list[tuple[int, int, int]]  # (year, month, searches)


def generate_keyword_ideas(
    *,
    customer_id: str,
    language_constant_id: int,
    geo_target_constant_ids: Sequence[int],
    keyword_texts: Sequence[str],
    page_url: Optional[str] = None,
    google_ads_config_path: Optional[str] = None,
) -> Iterable[KeywordIdeaRow]:
    """
    Wrap Google Ads KeywordPlanIdeaService.GenerateKeywordIdeas.
    Requires google-ads Python client and configured credentials (google-ads.yaml).
    """
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError as exc:  # pragma: no cover - runtime safeguard
        raise RuntimeError(
            "google-ads client library is not installed. Install with `pip install google-ads` inside the container."
        ) from exc

    client = (
        GoogleAdsClient.load_from_storage(google_ads_config_path)
        if google_ads_config_path
        else GoogleAdsClient.load_from_storage()
    )

    keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")
    request = client.get_type("GenerateKeywordIdeasRequest")

    request.customer_id = customer_id
    request.language = f"languageConstants/{language_constant_id}"
    request.geo_target_constants.extend([f"geoTargetConstants/{i}" for i in geo_target_constant_ids])
    request.include_adult_keywords = False
    request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS

    # Only one seed mode can be set: keyword_seed, url_seed, or keyword_and_url_seed.
    if keyword_texts and page_url:
        request.keyword_and_url_seed.url = page_url
        request.keyword_and_url_seed.keywords.extend(keyword_texts)
    elif keyword_texts:
        request.keyword_seed.keywords.extend(keyword_texts)
    elif page_url:
        request.url_seed.url = page_url
    else:
        raise ValueError("Provide at least one keyword seed or a page_url seed.")

    response = keyword_plan_idea_service.generate_keyword_ideas(request=request)

    for idea in response:
        metrics = idea.keyword_idea_metrics
        monthly = []
        for mv in getattr(metrics, "monthly_search_volumes", []):
            monthly.append((mv.year, mv.month, mv.monthly_searches))

        yield KeywordIdeaRow(
            text=idea.text,
            avg_monthly_searches=int(getattr(metrics, "avg_monthly_searches", 0) or 0),
            competition=getattr(metrics, "competition", None).name if getattr(metrics, "competition", None) else None,
            monthly_volumes=monthly,
        )
