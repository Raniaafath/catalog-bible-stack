from __future__ import annotations

from typing import Iterable, List, Optional

from django.utils import timezone

from catalog.models import Product, Variant
from content.models import Locale
from kw.models import PlannerRun
from pub.models import (
    Channel,
    ContentSet,
    ContentSetItem,
    GenerationBatch,
    GenerationBatchItem,
)
from pub.services.content_generation import generate_content, preview_content
from pub.services.title_renderer import TitleApprovalRequired, TitleRenderError


def resolve_set_variant_ids(content_set: ContentSet) -> List[int]:
    items = ContentSetItem.objects.filter(content_set=content_set).select_related("product")
    variant_ids: List[int] = []
    product_ids: List[int] = []
    for item in items:
        if item.variant_id:
            variant_ids.append(item.variant_id)
        else:
            product_ids.append(item.product_id)
    if product_ids:
        variant_ids.extend(list(Variant.objects.filter(product_id__in=product_ids).values_list("id", flat=True)))
    return sorted(set(variant_ids))


def run_generation_batch(
    *,
    batch: GenerationBatch,
    variant_ids: Iterable[int],
) -> GenerationBatch:
    variant_ids = list(variant_ids)
    batch.status = GenerationBatch.Status.RUNNING
    batch.started_at = timezone.now()
    batch.total = len(variant_ids)
    batch.save(update_fields=["status", "started_at", "total"])

    variants = (
        Variant.objects.filter(id__in=variant_ids)
        .select_related("product", "product__product_type")
        .in_bulk()
    )

    for variant_id in variant_ids:
        variant = variants.get(variant_id)
        if not variant:
            _upsert_item_error(
                batch=batch,
                product=None,
                variant=None,
                message=f"Unknown variant_id={variant_id}",
            )
            batch.errors += 1
            batch.save(update_fields=["errors"])
            continue

        try:
            result = generate_content(
                variant=variant,
                locale=batch.locale,
                channel=batch.channel,
                run=batch.planner_run,
                context=batch.context,
                include_descriptions=batch.include_descriptions,
                mode_override=batch.mode,
                batch=batch.id,
            )
            _upsert_item_generated(
                batch=batch,
                variant=variant,
                generation_run_id=result.get("generation_run_id"),
                selection_id=result.get("selection_id"),
            )
            batch.generated += 1
            batch.save(update_fields=["generated"])
        except TitleApprovalRequired as exc:
            preview = preview_content(
                variant=variant,
                locale=batch.locale,
                channel=batch.channel,
                run=batch.planner_run,
                context=batch.context,
                include_descriptions=batch.include_descriptions,
            )
            _upsert_item_needs_approval(
                batch=batch,
                variant=variant,
                selection_id=exc.selection_id,
                preview_json=preview,
            )
            batch.needs_approval += 1
            batch.save(update_fields=["needs_approval"])
        except (TitleRenderError, Exception) as exc:
            _upsert_item_error(
                batch=batch,
                product=variant.product,
                variant=variant,
                message=str(exc),
            )
            batch.errors += 1
            batch.save(update_fields=["errors"])

    batch.status = GenerationBatch.Status.DONE if batch.errors == 0 else GenerationBatch.Status.FAILED
    batch.finished_at = timezone.now()
    batch.save(update_fields=["status", "finished_at"])
    return batch


def create_batch(
    *,
    content_set: Optional[ContentSet],
    variant_ids: Optional[List[int]],
    product_ids: Optional[List[int]],
    channel: Channel,
    locale: Locale,
    context: str,
    planner_run: Optional[PlannerRun],
    mode: str,
    include_descriptions: bool,
) -> GenerationBatch:
    if content_set:
        variant_ids = resolve_set_variant_ids(content_set)
    elif product_ids:
        variant_ids = list(Variant.objects.filter(product_id__in=product_ids).values_list("id", flat=True))
    if not variant_ids:
        variant_ids = []

    batch = GenerationBatch.objects.create(
        content_set=content_set,
        channel=channel,
        locale=locale,
        context=context,
        planner_run=planner_run,
        mode=mode,
        include_descriptions=include_descriptions,
        total=len(variant_ids),
    )
    run_generation_batch(batch=batch, variant_ids=variant_ids)
    return batch


def _upsert_item_generated(
    *,
    batch: GenerationBatch,
    variant: Variant,
    generation_run_id: Optional[int],
    selection_id: Optional[int],
) -> None:
    GenerationBatchItem.objects.update_or_create(
        batch=batch,
        variant=variant,
        defaults={
            "product": variant.product,
            "status": GenerationBatchItem.ItemStatus.GENERATED,
            "generation_run_id": generation_run_id,
            "selection_id": selection_id,
            "error_message": "",
            "preview_json": {},
        },
    )


def _upsert_item_needs_approval(
    *,
    batch: GenerationBatch,
    variant: Variant,
    selection_id: Optional[int],
    preview_json: dict,
) -> None:
    GenerationBatchItem.objects.update_or_create(
        batch=batch,
        variant=variant,
        defaults={
            "product": variant.product,
            "status": GenerationBatchItem.ItemStatus.NEEDS_APPROVAL,
            "selection_id": selection_id,
            "preview_json": preview_json,
            "error_message": "",
        },
    )


def _upsert_item_error(
    *,
    batch: GenerationBatch,
    product: Optional[Product],
    variant: Optional[Variant],
    message: str,
) -> None:
    if not variant:
        return
    GenerationBatchItem.objects.create(
        batch=batch,
        product=product or (variant.product if variant else None),
        variant=variant,
        status=GenerationBatchItem.ItemStatus.ERROR,
        error_message=message,
    )
