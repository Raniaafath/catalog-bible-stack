import json
from typing import List, Optional

from catalog.models import Variant
from content.models import Locale
from kw.models import PlannerRun
from pub.models import Channel, ChannelListing
from pub.services.dtos import TitleGenerationOutputItem, TitleGenerationRequest, TitleGenerationResult
from pub.services.title_renderer import TitleApprovalRequired, get_title_suggestions, save_generation

# #region agent log
def _dlog(msg: str, data: dict, hypothesis_id: str):
    try:
        from core.debug_utils import DEBUG_LOG_PATH
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps({"message": msg, "data": data, "hypothesisId": hypothesis_id, "location": "generation_service"}) + "\n")
    except Exception:
        pass
# #endregion


class TitleGenerationServiceError(ValueError):
    """Raised when title generation inputs are invalid."""


def generate_titles(request: TitleGenerationRequest) -> TitleGenerationResult:
    # #region agent log
    _dlog("generate_titles entry", {"variant_ids": request.variant_ids}, "H1")
    # #endregion
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

    listing = None
    if request.listing_id is not None:
        try:
            listing = ChannelListing.objects.get(id=request.listing_id)
        except ChannelListing.DoesNotExist:
            pass

    outputs: List[TitleGenerationOutputItem] = []
    all_missing: dict = {}
    for variant_id in request.variant_ids:
        variant = variants_by_id[variant_id]
        # #region agent log
        _dlog("before save_generation", {"variant_id": variant_id}, "H1")
        # #endregion
        try:
            output, missing_translations = save_generation(
                variant=variant,
                locale=locale,
                channel=channel,
                run=planner_run,
                include_descriptions=request.include_descriptions,
                context=request.context,
                mode_override=request.title_mode_override,
                listing=listing,
                template_id=request.template_id,
            )
            # #region agent log
            _dlog("after save_generation ok", {"variant_id": variant_id}, "H1")
            # #endregion
            if missing_translations:
                all_missing.update(missing_translations)
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
            # #region agent log
            _dlog("TitleApprovalRequired, before get_title_suggestions", {"variant_id": variant_id}, "H3")
            # #endregion
            suggestions = get_title_suggestions(
                variant=variant,
                product=variant.product,
                locale=locale,
                channel=channel,
                run=planner_run,
                context=request.context,
                include_explanations=False,
            )
            # #region agent log
            _dlog("after get_title_suggestions", {"variant_id": variant_id}, "H3")
            # #endregion
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
        except Exception as e:
            # #region agent log
            _dlog("save_generation raised", {"variant_id": variant_id, "exc_type": type(e).__name__, "exc_msg": str(e)}, "H1")
            # #endregion
            raise

    # #region agent log
    _dlog("generate_titles return", {"outputs_len": len(outputs)}, "H4")
    # #endregion
    untranslated_list = [
        {
            "attribute_value_id": av_id,
            "code": info["code"],
            "attr_code": info["attr_code"],
            "attribute_id": info.get("attribute_id"),
        }
        for av_id, info in all_missing.items()
    ] if all_missing else None
    return TitleGenerationResult(outputs=outputs, untranslated_attribute_values=untranslated_list)
