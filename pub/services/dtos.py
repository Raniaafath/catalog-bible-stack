from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class TitleGenerationRequest:
    variant_ids: List[int]
    locale_code: str
    channel_code: str
    planner_run_id: Optional[int] = None
    include_descriptions: bool = False
    title_mode_override: Optional[str] = None
    context: str = "title"
    listing_id: Optional[int] = None
    template_id: Optional[int] = None


@dataclass(frozen=True)
class TitleGenerationOutputItem:
    status: str
    variant_id: int
    product_id: int
    output_id: Optional[int] = None
    run_id: Optional[int] = None
    template_id: Optional[int] = None
    title: Optional[str] = None
    selection_id: Optional[int] = None
    preview_title: Optional[str] = None
    suggestions: Optional[dict] = None


@dataclass(frozen=True)
class TitleGenerationResult:
    outputs: List[TitleGenerationOutputItem]
    untranslated_attribute_values: Optional[List[dict]] = None  # [{attribute_value_id, code, attr_code}, ...] for UI
