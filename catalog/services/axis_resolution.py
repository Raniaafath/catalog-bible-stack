"""
Single entry point for resolving variation axes by context.

Resolution order (see GROUPING_AND_MARKETPLACE_AXES.md):
1. ChannelListingAxis (listing group) if listing is provided and has axes
2. ChannelVariantAxis (product + channel) if channel is provided
3. ProductVariantAxis (product family default) as fallback
"""
from dataclasses import dataclass
from typing import List, Optional, Union

from catalog.models import (
    ChannelListingAxis,
    ChannelVariantAxis,
    Product,
    ProductVariantAxis,
)


@dataclass
class AxisInfo:
    """One variation axis with attribute, order, and optional label override."""
    attribute: "Attribute"  # catalog.models.Attribute
    attribute_id: int
    attribute_code: str
    position: int
    label_override: Optional[str] = None


def get_axes_for_context(
    product: Product,
    channel=None,
    listing=None,
) -> List[AxisInfo]:
    """
    Return the ordered list of variation axes for the given context.

    Use this everywhere axes are needed (title generation, listing API) so
    priority and ordering are defined in one place.

    Resolution order:
    1. If listing is provided and has ChannelListingAxis (enabled): use those.
    2. Else if channel is provided and product has ChannelVariantAxis for that channel: use those.
    3. Else: use ProductVariantAxis for the product (catalog default).

    Args:
        product: The product family (catalog Product).
        channel: Optional Channel instance or channel id (for marketplace-level axes).
        listing: Optional ChannelListing instance or listing id (for listing group axes).

    Returns:
        List of AxisInfo (attribute_id, attribute_code, position, label_override), ordered by position.
    """
    # Resolve listing by id if needed
    listing_obj = None
    if listing is not None:
        if isinstance(listing, int):
            from pub.models import ChannelListing
            try:
                listing_obj = ChannelListing.objects.get(id=listing)
            except ChannelListing.DoesNotExist:
                pass
        else:
            listing_obj = listing
        if listing_obj is not None and listing_obj.product_id != product.id:
            listing_obj = None  # listing belongs to another product, ignore

    # Resolve channel by id if needed
    channel_obj = None
    if channel is not None:
        if isinstance(channel, int):
            from pub.models import Channel
            try:
                channel_obj = Channel.objects.get(id=channel)
            except Channel.DoesNotExist:
                pass
        else:
            channel_obj = channel

    # 1. Listing group axes (highest priority)
    if listing_obj is not None:
        axes = (
            ChannelListingAxis.objects.filter(
                listing=listing_obj,
                enabled=True,
            )
            .select_related("attribute")
            .order_by("position")
        )
        if axes.exists():
            return [
                AxisInfo(
                    attribute=a.attribute,
                    attribute_id=a.attribute_id,
                    attribute_code=a.attribute.code,
                    position=a.position,
                    label_override=a.label_override or None,
                )
                for a in axes
            ]

    # 2. Channel axes (product + channel)
    if channel_obj is not None:
        axes = (
            ChannelVariantAxis.objects.filter(
                product=product,
                channel=channel_obj,
            )
            .select_related("attribute")
            .order_by("position")
        )
        if axes.exists():
            return [
                AxisInfo(
                    attribute=a.attribute,
                    attribute_id=a.attribute_id,
                    attribute_code=a.attribute.code,
                    position=a.position,
                    label_override=a.label_override or None,
                )
                for a in axes
            ]

    # 3. Product family default axes
    axes = (
        ProductVariantAxis.objects.filter(product=product)
        .select_related("attribute")
        .order_by("position")
    )
    return [
        AxisInfo(
            attribute=a.attribute,
            attribute_id=a.attribute_id,
            attribute_code=a.attribute.code,
            position=a.position,
            label_override=a.label_override or None,
        )
        for a in axes
    ]
