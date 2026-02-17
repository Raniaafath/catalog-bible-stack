from __future__ import annotations

from typing import Optional, Tuple

from catalog.models import Variant
from content.models import Locale
from kw.models import PlannerRun
from pub.models import Channel, GenerationOutput, GenerationRun
from pub.services.title_renderer import TitleRenderError, save_generation


class TitleBuilderError(Exception):
    """Raised when a title cannot be generated."""


def build_title_for_variant(
    *,
    variant: Variant,
    locale: Locale,
    channel: Channel,
    planner_run: Optional[PlannerRun] = None,
    include_descriptions: bool = False,
) -> Tuple[GenerationRun, GenerationOutput]:
    try:
        output, _ = save_generation(
            variant=variant,
            locale=locale,
            channel=channel,
            run=planner_run,
            include_descriptions=include_descriptions,
        )
    except TitleRenderError as exc:
        raise TitleBuilderError(str(exc)) from exc
    return output.run, output
