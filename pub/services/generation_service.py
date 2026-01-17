from typing import List, Optional

from catalog.models import Variant
from content.models import Locale
from kw.models import PlannerRun
from pub.models import Channel
from pub.services.dtos import TitleGenerationOutputItem, TitleGenerationRequest, TitleGenerationResult
from pub.services.title_renderer import TitleApprovalRequired, get_title_suggestions, save_generation


class TitleGenerationServiceError(ValueError):
    """Raised when title generation inputs are invalid."""


def generate_titles(request: TitleGenerationRequest) -> TitleGenerationResult:
    locale = Locale.objects.get(code=request.locale_code)
    channel = Channel.objects.get(code=request.channel_code)
    planner_run: Optional[PlannerRun] = None
    if request.planner_run_id is not None:
        try:
            planner_run = PlannerRun.objects.get(id=request.planner_run_id)
        except PlannerRun.DoesNotExist as exc:
            raise TitleGenerationServiceError(f"Unknown planner_run_id: {request.planner_run_id}") from exc

    variants_by_id = Variant.objects.filter(id__in=request.variant_ids).select_related("product").in_bulk()
    missing_ids = [variant_id for variant_id in request.variant_ids if variant_id not in variants_by_id]
    if missing_ids:
        missing_str = ", ".join(str(variant_id) for variant_id in missing_ids)
        raise TitleGenerationServiceError(f"Unknown variant_ids: {missing_str}")

    outputs: List[TitleGenerationOutputItem] = []
    for variant_id in request.variant_ids:
        variant = variants_by_id[variant_id]
        try:
            output = save_generation(
                variant=variant,
                locale=locale,
                channel=channel,
                run=planner_run,
                include_descriptions=request.include_descriptions,
                context=request.context,
                mode_override=request.title_mode_override,
            )
            outputs.append(
                TitleGenerationOutputItem(
                    status="generated",
                    variant_id=variant.id,
                    product_id=variant.product_id,
                    output_id=output.id,
                    run_id=output.run_id,
                    template_id=output.run.template_id,
                    title=output.text,
                    selection_id=output.selection_id,
                )
            )
        except TitleApprovalRequired as exc:
            suggestions = get_title_suggestions(
                variant=variant,
                product=variant.product,
                locale=locale,
                channel=channel,
                run=planner_run,
                context=request.context,
                include_explanations=False,
            )
            outputs.append(
                TitleGenerationOutputItem(
                    status="needs_approval",
                    variant_id=variant.id,
                    product_id=variant.product_id,
                    selection_id=exc.selection_id,
                    preview_title=exc.preview_title,
                    suggestions=suggestions,
                )
            )

    return TitleGenerationResult(outputs=outputs)
