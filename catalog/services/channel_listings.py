"""
Service functions for listing groups (ChannelListing).

A listing group defines which variants are published together on a channel and
which variation axes apply. See GROUPING_AND_MARKETPLACE_AXES.md for product
family vs listing group and axis resolution.

Key business rules (Option A):
- A variant can only belong to ONE listing per channel
- Moving variants to a listing removes them from any other listing on that channel
- This prevents duplicate/conflicting listings on the same marketplace
"""
from collections import defaultdict
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import Q

from catalog.models import (
    Attribute,
    ChannelListingAxis,
    Product,
    ProductAttributeValue,
    ProductTypeAttribute,
    Variant,
)
from pub.models import (
    Channel,
    ChannelListing,
    ChannelListingMap,
    ContentSelection,
    Template,
    TemplatePart,
    GenerationRun,
    GenerationOutput,
)
from content.models import Locale
from pub.services.dtos import TitleGenerationRequest
from pub.services.generation_service import generate_titles


class ChannelListingError(Exception):
    """Base exception for channel listing operations."""
    pass


class VariantNotFoundError(ChannelListingError):
    """Raised when one or more variants are not found."""
    pass


class ListingNotFoundError(ChannelListingError):
    """Raised when a listing is not found."""
    pass


class ChannelNotFoundError(ChannelListingError):
    """Raised when a channel is not found."""
    pass


class ProductMismatchError(ChannelListingError):
    """Raised when variants don't belong to the listing's product."""
    pass


@transaction.atomic
def create_channel_listing(
    product_id: Optional[int] = None,
    channel_id: int = None,
    locale_id: Optional[int] = None,
    name: str = "",
    is_default: bool = True,
) -> ChannelListing:
    """
    Create a new channel listing (group) for a product.
    
    Args:
        product_id: Optional product this listing belongs to. If None, will be auto-assigned when variants are added.
        channel_id: The channel/marketplace for this listing
        locale_id: Optional locale for locale-specific listings
        name: Optional label for the listing (e.g., "eBay - Color variants only")
        is_default: Whether this is the default listing for this product+channel+locale
    
    Returns:
        The created ChannelListing instance
    
    Raises:
        ProductNotFoundError: If product_id is provided but product doesn't exist
        ChannelNotFoundError: If channel doesn't exist
    """
    product = None
    if product_id:
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ChannelListingError(f"Product with ID {product_id} not found")
    
    if not channel_id:
        raise ChannelNotFoundError("channel_id is required")
    
    try:
        channel = Channel.objects.get(id=channel_id)
    except Channel.DoesNotExist:
        raise ChannelNotFoundError(f"Channel with ID {channel_id} not found")
    
    # If this is default and product is set, unset any existing default for this scope
    if is_default and product:
        ChannelListing.objects.filter(
            product=product,
            channel=channel,
            locale_id=locale_id,
            is_default=True,
        ).update(is_default=False)
    
    listing = ChannelListing.objects.create(
        product=product,
        channel=channel,
        locale_id=locale_id,
        name=name,
        is_default=is_default,
    )
    
    return listing


@transaction.atomic
def move_variants_to_listing(
    listing_id: int,
    variant_ids: List[int],
) -> Dict[str, Any]:
    """
    Move variants to a channel listing (group).
    
    This is the core "Option A" operation:
    - Removes variants from any other listing on the SAME channel
    - Adds variants to the specified listing
    - Ensures one variant = one listing per channel
    
    Args:
        listing_id: The target listing ID
        variant_ids: List of variant IDs to move
    
    Returns:
        Dict with:
        {
            "listing_id": int,
            "moved_count": int,
            "removed_from": [
                {"listing_id": int, "listing_name": str, "variant_ids": [...]}
            ],
            "variants": [...]
        }
    
    Raises:
        ListingNotFoundError: If listing doesn't exist
        VariantNotFoundError: If any variant doesn't exist
        ProductMismatchError: If variants don't belong to the listing's product
    """
    # Get the target listing with related product and channel
    try:
        listing = ChannelListing.objects.select_related(
            'product', 'channel'
        ).get(id=listing_id)
    except ChannelListing.DoesNotExist:
        raise ListingNotFoundError(f"Listing with ID {listing_id} not found")
    
    # Validate all variants exist
    variants = list(Variant.objects.filter(id__in=variant_ids).select_related('product', 'product__product_type'))
    if len(variants) != len(variant_ids):
        found_ids = {v.id for v in variants}
        missing = [vid for vid in variant_ids if vid not in found_ids]
        raise VariantNotFoundError(f"Variants not found: {missing}")
    
    channel = listing.channel
    
    # Handle product assignment
    if not listing.product:
        # Listing has no product - determine from variants
        product_ids = {v.product_id for v in variants if v.product_id}
        
        if len(product_ids) == 1:
            # All variants from same product - use it
            listing.product = variants[0].product
            listing.save(update_fields=['product'])
        elif len(product_ids) > 1:
            # Variants from different products - create a new "mix" product
            from django.utils.text import slugify
            from catalog.models import ProductType
            
            # Get product type from first variant (or use default)
            product_type = variants[0].product.product_type if variants[0].product else None
            if not product_type:
                product_type, _ = ProductType.objects.get_or_create(
                    code='default',
                    defaults={'default_label': 'Default'}
                )
            
            # Create mix product name
            mix_code = f"mix-listing-{listing.id}"
            base_code = mix_code
            counter = 1
            while Product.objects.filter(code=mix_code).exists():
                mix_code = f"{base_code}-{counter}"
                counter += 1
            
            # Create the mix product
            mix_product = Product.objects.create(
                code=slugify(mix_code),
                product_type=product_type,
                status=Product.Status.DRAFT,
                default_label=f"Mix Product (Listing {listing.id})",
            )
            listing.product = mix_product
            listing.save(update_fields=['product'])
    else:
        # Listing has a product - validate variants belong to it (or allow if it's a mix product)
        # If it's a mix product (starts with "mix-"), allow any variants (don't move variants to mix product)
        is_mix_product = listing.product.code.startswith('mix-')
        if not is_mix_product:
            wrong_product = [v for v in variants if v.product_id != listing.product_id]
            if wrong_product:
                raise ProductMismatchError(
                    f"Variants {[v.id for v in wrong_product]} don't belong to product {listing.product_id}. "
                    f"Create a new listing group to mix variants from different products."
                )
    
    # Find existing listings on the same channel that have these variants
    existing_maps = ChannelListingMap.objects.filter(
        variant_id__in=variant_ids,
        channel=channel,
    ).select_related('listing')
    
    # Track what we're removing from
    removed_from = defaultdict(list)
    for map_obj in existing_maps:
        if map_obj.listing_id and map_obj.listing_id != listing_id:
            removed_from[map_obj.listing_id].append(map_obj.variant_id)
    
    # Delete existing mappings for these variants on this channel
    ChannelListingMap.objects.filter(
        variant_id__in=variant_ids,
        channel=channel,
    ).delete()
    
    # Create new mappings to the target listing
    new_maps = [
        ChannelListingMap(
            listing=listing,
            variant_id=vid,
            channel=channel,
        )
        for vid in variant_ids
    ]
    ChannelListingMap.objects.bulk_create(new_maps)
    
    # Build response
    removed_from_data = []
    if removed_from:
        old_listings = ChannelListing.objects.filter(id__in=removed_from.keys())
        listing_names = {l.id: l.name for l in old_listings}
        for old_listing_id, vids in removed_from.items():
            removed_from_data.append({
                'listing_id': old_listing_id,
                'listing_name': listing_names.get(old_listing_id, ''),
                'variant_ids': vids,
            })
    
    return {
        'listing_id': listing.id,
        'moved_count': len(variant_ids),
        'removed_from': removed_from_data,
        'variants': [
            {
                'id': v.id,
                'sku': v.sku,
                'product_id': v.product_id,
            }
            for v in variants
        ],
    }


@transaction.atomic
def remove_variants_from_listing(
    listing_id: int,
    variant_ids: List[int],
) -> Dict[str, Any]:
    """
    Remove variants from a channel listing.
    
    Note: This removes the channel mapping entirely, not moving to another listing.
    The variant will no longer be listed on this channel.
    
    Args:
        listing_id: The listing to remove variants from
        variant_ids: List of variant IDs to remove
    
    Returns:
        Dict with removed count
    """
    try:
        listing = ChannelListing.objects.get(id=listing_id)
    except ChannelListing.DoesNotExist:
        raise ListingNotFoundError(f"Listing with ID {listing_id} not found")
    
    deleted_count, _ = ChannelListingMap.objects.filter(
        listing=listing,
        variant_id__in=variant_ids,
    ).delete()
    
    return {
        'listing_id': listing_id,
        'removed_count': deleted_count,
    }


def _pav_display_value(pav: ProductAttributeValue) -> Optional[str]:
    """Return a display string for a ProductAttributeValue."""
    if pav.attribute_value_id:
        return pav.attribute_value.code if pav.attribute_value else None
    if pav.value_text:
        return pav.value_text
    if pav.value_number is not None:
        return str(pav.value_number)
    if pav.value_bool is not None:
        return str(pav.value_bool).lower()
    return None


def get_available_variants_for_listing(listing_id: int) -> Dict[str, Any]:
    """
    Get variants that can be added to this listing (same product, not already in listing),
    with variant-level attribute values so the user can see what they're choosing.

    Returns:
        {
            "product_id": int | null,
            "product_code": str | null,
            "attribute_codes": ["color", "size", ...],
            "variants": [
                {
                    "id": int,
                    "sku": str | null,
                    "barcode": str | null,
                    "product_id": int,
                    "attributes": {"color": "Red", "size": "M", ...}
                },
                ...
            ]
        }
    """
    try:
        listing = ChannelListing.objects.select_related(
            "product", "product__product_type"
        ).get(id=listing_id)
    except ChannelListing.DoesNotExist:
        raise ListingNotFoundError(f"Listing with ID {listing_id} not found")

    product = listing.product
    if not product:
        return {
            "product_id": None,
            "product_code": None,
            "attribute_codes": [],
            "variants": [],
        }

    # Variant IDs already in this listing
    in_listing_ids = set(
        ChannelListingMap.objects.filter(listing=listing).values_list(
            "variant_id", flat=True
        )
    )

    # All variants of this product not already in this listing
    candidates = list(
        Variant.objects.filter(product=product)
        .exclude(id__in=in_listing_ids)
        .order_by("id")
    )

    # Variant-level attribute codes for this product type (for column headers)
    variant_attrs = list(
        ProductTypeAttribute.objects.filter(
            product_type=product.product_type_id, variant_level=True
        )
        .select_related("attribute")
        .order_by("attribute__code")
    )
    attribute_codes = [pta.attribute.code for pta in variant_attrs]
    attr_ids = [pta.attribute_id for pta in variant_attrs]

    if not attr_ids:
        # No variant-level attributes; still return variants with empty attributes
        return {
            "product_id": product.id,
            "product_code": product.code,
            "attribute_codes": [],
            "variants": [
                {
                    "id": v.id,
                    "sku": v.sku,
                    "barcode": v.barcode,
                    "product_id": v.product_id,
                    "attributes": {},
                }
                for v in candidates
            ],
        }

    # Load PAVs for these variants and attributes
    pavs = (
        ProductAttributeValue.objects.filter(
            variant_id__in=[v.id for v in candidates],
            attribute_id__in=attr_ids,
        )
        .select_related("attribute", "attribute_value")
        .order_by("variant_id", "attribute_id")
    )

    # Build variant_id -> attribute_code -> display_value
    variant_attributes: Dict[int, Dict[str, str]] = {v.id: {} for v in candidates}
    for pav in pavs:
        display = _pav_display_value(pav)
        if display is not None:
            variant_attributes[pav.variant_id][pav.attribute.code] = display

    return {
        "product_id": product.id,
        "product_code": product.code,
        "attribute_codes": attribute_codes,
        "variants": [
            {
                "id": v.id,
                "sku": v.sku,
                "barcode": v.barcode,
                "product_id": v.product_id,
                "attributes": variant_attributes.get(v.id, {}),
            }
            for v in candidates
        ],
    }


def get_listing_differences(listing_id: int) -> Dict[str, Any]:
    """
    Get attribute differences for variants in a listing.
    
    This helps users understand which attributes vary across variants
    and choose appropriate variation axes.
    
    Args:
        listing_id: The listing to analyze
    
    Returns:
        Dict with structure similar to compare_variants():
        {
            "listing": {...listing info...},
            "variants": [...],
            "differences": [...attributes that differ...],
            "common_attributes": [...attributes that are the same...],
            "suggested_axes": [...good candidates for variation axes...]
        }
    """
    try:
        listing = ChannelListing.objects.select_related(
            'product', 'channel', 'locale'
        ).get(id=listing_id)
    except ChannelListing.DoesNotExist:
        raise ListingNotFoundError(f"Listing with ID {listing_id} not found")
    
    # Get variants in this listing
    variant_ids = list(
        ChannelListingMap.objects.filter(listing=listing)
        .values_list('variant_id', flat=True)
    )
    
    if len(variant_ids) < 2:
        return {
            'listing': {
                'id': listing.id,
                'name': listing.name,
                'product_id': listing.product_id,
                'channel_id': listing.channel_id,
            },
            'variants': [],
            'differences': [],
            'common_attributes': [],
            'suggested_axes': [],
            'message': 'Need at least 2 variants to analyze differences',
        }
    
    variants = list(Variant.objects.filter(id__in=variant_ids))
    
    # Gather all attribute values for each variant
    variant_attributes = defaultdict(dict)
    all_attributes = set()
    
    for variant in variants:
        pavs = ProductAttributeValue.objects.filter(
            variant=variant
        ).select_related('attribute', 'attribute_value')
        
        for pav in pavs:
            all_attributes.add(pav.attribute.id)
            variant_attributes[variant.id][pav.attribute.id] = {
                'attribute': pav.attribute,
                'value_text': pav.value_text,
                'value_number': pav.value_number,
                'value_bool': pav.value_bool,
                'attribute_value_code': pav.attribute_value.code if pav.attribute_value else None,
                'attribute_value_id': pav.attribute_value_id,
            }
    
    # Analyze differences
    differences = []
    common_attributes = []
    
    for attr_id in all_attributes:
        # Get attribute object
        attr_data = None
        for v_id in variant_attributes:
            if attr_id in variant_attributes[v_id]:
                attr_data = variant_attributes[v_id][attr_id]['attribute']
                break
        
        if not attr_data:
            continue
        
        # Collect values for this attribute across all variants
        variant_values = {}
        unique_values = set()
        
        for variant in variants:
            if attr_id in variant_attributes[variant.id]:
                pav_data = variant_attributes[variant.id][attr_id]
                
                # Get display value based on data type
                if pav_data['attribute_value_code']:
                    display_value = pav_data['attribute_value_code']
                elif pav_data['value_text']:
                    display_value = pav_data['value_text']
                elif pav_data['value_number'] is not None:
                    display_value = str(pav_data['value_number'])
                elif pav_data['value_bool'] is not None:
                    display_value = str(pav_data['value_bool'])
                else:
                    display_value = None
                
                variant_values[variant.id] = {
                    'display': display_value,
                    'attribute_value_id': pav_data['attribute_value_id'],
                }
                
                if display_value:
                    unique_values.add(display_value)
            else:
                variant_values[variant.id] = None
        
        unique_count = len(unique_values)
        
        if unique_count > 1:
            has_missing = any(v is None for v in variant_values.values())
            is_candidate = (2 <= unique_count <= 10) and not has_missing
            
            differences.append({
                'attribute_id': attr_data.id,
                'attribute_code': attr_data.code,
                'attribute_data_type': attr_data.data_type,
                'variant_values': variant_values,
                'unique_values': sorted(list(unique_values)),
                'unique_values_count': unique_count,
                'is_candidate_axis': is_candidate,
                'has_missing_values': has_missing,
            })
        elif unique_count == 1:
            common_attributes.append({
                'attribute_id': attr_data.id,
                'attribute_code': attr_data.code,
                'common_value': list(unique_values)[0],
            })
    
    # Sort differences: candidates first, then by number of unique values
    differences.sort(key=lambda x: (not x['is_candidate_axis'], x['unique_values_count']))
    
    # Suggested axes = first N good candidates
    suggested_axes = [
        {
            'attribute_id': d['attribute_id'],
            'attribute_code': d['attribute_code'],
            'unique_values': d['unique_values'],
        }
        for d in differences if d['is_candidate_axis']
    ][:3]  # Max 3 suggested
    
    return {
        'listing': {
            'id': listing.id,
            'name': listing.name,
            'product_id': listing.product_id,
            'product_code': listing.product.code,
            'channel_id': listing.channel_id,
            'channel_code': listing.channel.code,
            'locale_code': listing.locale.code if listing.locale else None,
        },
        'variants': [
            {
                'id': v.id,
                'sku': v.sku,
            }
            for v in variants
        ],
        'differences': differences,
        'common_attributes': common_attributes,
        'suggested_axes': suggested_axes,
    }


@transaction.atomic
def set_listing_axes(
    listing_id: int,
    axes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Set variation axes for a channel listing.
    
    Args:
        listing_id: The listing to update
        axes: List of axis definitions:
            [
                {"attribute_id": 5, "position": 0, "label_override": "Color"},
                {"attribute_id": 6, "position": 1}
            ]
    
    Returns:
        Dict with created axes info
    """
    try:
        listing = ChannelListing.objects.select_related('product', 'channel').get(id=listing_id)
    except ChannelListing.DoesNotExist:
        raise ListingNotFoundError(f"Listing with ID {listing_id} not found")
    
    # Clear existing axes for this listing
    ChannelListingAxis.objects.filter(listing=listing).delete()
    
    # Create new axes
    created_axes = []
    for axis_data in axes:
        attribute_id = axis_data.get('attribute_id')
        position = axis_data.get('position', 0)
        label_override = axis_data.get('label_override')
        enabled = axis_data.get('enabled', True)
        
        if not attribute_id:
            continue
        
        try:
            attribute = Attribute.objects.get(id=attribute_id)
            axis = ChannelListingAxis.objects.create(
                listing=listing,
                attribute=attribute,
                position=position,
                label_override=label_override or None,
                enabled=enabled,
            )
            created_axes.append({
                'id': axis.id,
                'attribute_id': attribute.id,
                'attribute_code': attribute.code,
                'position': axis.position,
                'label_override': axis.label_override,
                'enabled': axis.enabled,
            })
        except Attribute.DoesNotExist:
            continue
    
    return {
        'listing_id': listing.id,
        'axes': created_axes,
    }


def get_available_templates_for_listing(listing_id: int, locale_code: str) -> List[Dict[str, Any]]:
    """
    Get available templates for a channel listing.
    
    Returns active templates that match the listing's product_type and channel,
    filtered by the specified locale.
    
    Args:
        listing_id: The channel listing ID
        locale_code: The locale code to filter templates by
    
    Returns:
        List of template summaries
    
    Raises:
        ListingNotFoundError: If listing doesn't exist
    """
    try:
        listing = ChannelListing.objects.select_related(
            'product__product_type', 'channel'
        ).get(id=listing_id)
    except ChannelListing.DoesNotExist:
        raise ListingNotFoundError(f"Listing {listing_id} not found")
    
    if not listing.product:
        raise ChannelListingError("Listing has no product assigned")
    
    # Get locale
    try:
        locale = Locale.objects.get(code=locale_code)
    except Locale.DoesNotExist:
        raise ChannelListingError(f"Locale {locale_code} not found")
    
    # Query all non-archived templates matching product type, channel, and locale
    templates = Template.objects.filter(
        product_type=listing.product.product_type,
        channel=listing.channel,
        locale=locale,
        kind=Template.Kind.TITLE,
    ).exclude(status=Template.Status.ARCHIVED).select_related(
        'product_type', 'channel', 'locale'
    ).order_by('-version', '-id')
    
    return [
        {
            'id': template.id,
            'kind': template.kind,
            'version': template.version,
            'locale': template.locale.code,
            'part_count': template.parts.count(),
            'status': template.status,
            'created_at': template.created_at.isoformat() if template.created_at else None,
        }
        for template in templates
    ]


def create_default_title_template_for_listing(
    listing_id: int,
    locale_code: str,
) -> Dict[str, Any]:
    """
    Create or return a default title template for a channel listing and locale.
    Default structure: [Head term] - [Hook term] (uses saved head/hook terms).
    If an active template already exists for this product_type + channel + locale, returns it.
    """
    try:
        listing = ChannelListing.objects.select_related("product", "channel").get(id=listing_id)
    except ChannelListing.DoesNotExist:
        raise ListingNotFoundError(f"Listing {listing_id} not found")

    if not listing.product:
        raise ChannelListingError("Listing has no product assigned")

    try:
        locale = Locale.objects.get(code=locale_code)
    except Locale.DoesNotExist:
        raise ChannelListingError(f"Locale {locale_code} not found")

    product_type = listing.product.product_type
    channel = listing.channel

    # If an active title template already exists, return it
    existing = Template.objects.filter(
        product_type=product_type,
        channel=channel,
        locale=locale,
        kind=Template.Kind.TITLE,
        status=Template.Status.ACTIVE,
    ).first()
    if existing:
        return {
            "template": {
                "id": existing.id,
                "kind": existing.kind,
                "version": existing.version,
                "locale": existing.locale.code,
                "part_count": existing.parts.count(),
                "status": existing.status,
                "created_at": existing.created_at.isoformat() if existing.created_at else None,
            },
            "created": False,
        }

    with transaction.atomic():
        # Next version if there are drafts/archived
        next_version = (
            Template.objects.filter(
                product_type=product_type,
                channel=channel,
                locale=locale,
                kind=Template.Kind.TITLE,
            ).values_list("version", flat=True).order_by("-version").first()
            or 0
        ) + 1

        template = Template.objects.create(
            product_type=product_type,
            locale=locale,
            channel=channel,
            kind=Template.Kind.TITLE,
            version=next_version,
            status=Template.Status.ACTIVE,
        )
        TemplatePart.objects.create(
            template=template,
            position=0,
            part_type=TemplatePart.PartType.HEAD_TERM,
        )
        TemplatePart.objects.create(
            template=template,
            position=1,
            part_type=TemplatePart.PartType.LITERAL,
            literal_text=" - ",
        )
        TemplatePart.objects.create(
            template=template,
            position=2,
            part_type=TemplatePart.PartType.HOOK_TERM,
        )

    return {
        "template": {
            "id": template.id,
            "kind": template.kind,
            "version": template.version,
            "locale": template.locale.code,
            "part_count": template.parts.count(),
            "status": template.status,
            "created_at": template.created_at.isoformat() if template.created_at else None,
        },
        "created": True,
    }


def generate_titles_for_listing(
    listing_id: int,
    locale_code: str,
    template_id: Optional[int] = None,
    planner_run_id: Optional[int] = None,
    improve_title: bool = False,
    title_ai_model: str = "",
    title_ai_instructions: str = "",
) -> Dict[str, Any]:
    """
    Generate titles for all variants in a channel listing.
    
    Args:
        listing_id: The channel listing ID
        locale_code: The locale code for translations
        template_id: Optional template ID to use (otherwise auto-selected)
        planner_run_id: Optional planner run ID for keyword data
        improve_title: Whether to run AI polish on generated titles
        title_ai_model: AI model for title polish
        title_ai_instructions: Optional AI instructions for title polish
    
    Returns:
        Dictionary with generation results:
        - generation_run_ids: List of run IDs created
        - variant_count: Number of variants processed
        - outputs: List of generation outputs
    
    Raises:
        ListingNotFoundError: If listing doesn't exist
        ChannelListingError: If listing has no variants
    """
    try:
        listing = ChannelListing.objects.select_related('channel').get(id=listing_id)
    except ChannelListing.DoesNotExist:
        raise ListingNotFoundError(f"Listing {listing_id} not found")
    
    # Get all variant IDs in this listing
    listing_maps = ChannelListingMap.objects.filter(listing=listing).values_list('variant_id', flat=True)
    variant_ids = list(listing_maps)
    
    if not variant_ids:
        raise ChannelListingError("Listing has no variants")
    
    # Validate template if provided
    if template_id:
        try:
            template = Template.objects.select_related('product_type', 'channel', 'locale').get(id=template_id)
            # Verify template matches listing
            if listing.product and template.product_type_id != listing.product.product_type_id:
                raise ChannelListingError(
                    f"Template product type ({template.product_type.code}) doesn't match "
                    f"listing product type ({listing.product.product_type.code})"
                )
            if template.channel_id != listing.channel_id:
                raise ChannelListingError(
                    f"Template channel ({template.channel.code}) doesn't match "
                    f"listing channel ({listing.channel.code})"
                )
        except Template.DoesNotExist:
            raise ChannelListingError(f"Template {template_id} not found")
    
    # Create generation request (listing_id so axis attributes use listing axes; template_id if user selected one)
    request = TitleGenerationRequest(
        variant_ids=variant_ids,
        locale_code=locale_code,
        channel_code=listing.channel.code,
        planner_run_id=planner_run_id,
        include_descriptions=False,
        context="title",
        listing_id=listing.id,
        template_id=template_id,
        improve_title=improve_title,
        title_ai_model=title_ai_model,
        title_ai_instructions=title_ai_instructions,
    )
    # Generate titles
    result = generate_titles(request)
    # Extract run IDs and build JSON-serializable response (native types only)
    generation_run_ids = [
        int(x) for x in set(
            output.run_id for output in result.outputs if output.run_id is not None
        )
    ]

    def _out_item(o):
        out = {
            'status': str(o.status),
            'variant_id': int(o.variant_id),
            'product_id': int(o.product_id),
            'output_id': int(o.output_id) if o.output_id is not None else None,
            'run_id': int(o.run_id) if o.run_id is not None else None,
            'template_id': int(o.template_id) if o.template_id is not None else None,
            'title': str(o.title) if o.title is not None else None,
            'selection_id': int(o.selection_id) if o.selection_id is not None else None,
            'preview_title': str(o.preview_title) if o.preview_title is not None else None,
        }
        if getattr(o, 'suggestions', None) is not None:
            out['suggestions'] = o.suggestions
        return out

    return {
        'generation_run_ids': generation_run_ids,
        'variant_count': len(variant_ids),
        'outputs': [_out_item(o) for o in result.outputs],
        'untranslated_attribute_values': getattr(result, 'untranslated_attribute_values', None),
    }


def get_listing_generated_titles(
    listing_id: int,
    locale_code: str,
) -> List[Dict[str, Any]]:
    """
    Return the latest generated title per variant for this listing and locale.
    Each item: { "variant_id", "sku", "title", "generated_at" }.
    """
    try:
        listing = ChannelListing.objects.select_related("channel").get(id=listing_id)
    except ChannelListing.DoesNotExist:
        raise ListingNotFoundError(f"Listing {listing_id} not found")
    try:
        locale = Locale.objects.get(code=locale_code)
    except Locale.DoesNotExist:
        return []
    variant_ids = list(
        ChannelListingMap.objects.filter(listing=listing).values_list("variant_id", flat=True)
    )
    if not variant_ids:
        return []
    # Latest run per variant for this channel+locale (order by -created_at so first per variant is latest)
    runs = (
        GenerationRun.objects.filter(
            variant_id__in=variant_ids,
            channel_id=listing.channel_id,
            locale_id=locale.id,
        )
        .select_related("variant")
        .prefetch_related("outputs")
        .order_by("-created_at")
    )
    seen_variants = set()
    out = []
    for run in runs:
        if run.variant_id in seen_variants:
            continue
        seen_variants.add(run.variant_id)
        title_text = None
        for output in run.outputs.all():
            if output.field == "title":
                title_text = output.text
                break
        if title_text is None and run.outputs.exists():
            title_text = run.outputs.first().text
        out.append({
            "variant_id": run.variant_id,
            "sku": (run.variant.sku or run.variant.internal_sku or str(run.variant_id)) if run.variant else str(run.variant_id),
            "title": title_text or "",
            "generated_at": run.created_at.isoformat() if run.created_at else None,
        })
    # Preserve listing variant order
    id_to_item = {item["variant_id"]: item for item in out}
    return [id_to_item[vid] for vid in variant_ids if vid in id_to_item]


def update_listing_generated_title(
    listing_id: int,
    variant_id: int,
    locale_code: str,
    title: str,
) -> Dict[str, Any]:
    """
    Update the latest generated title for a variant in a listing (channel + locale).
    Returns the updated item dict or raises ListingNotFoundError / ValueError.
    """
    try:
        listing = ChannelListing.objects.select_related("channel").get(id=listing_id)
    except ChannelListing.DoesNotExist:
        raise ListingNotFoundError(f"Listing {listing_id} not found")
    if not ChannelListingMap.objects.filter(listing=listing, variant_id=variant_id).exists():
        raise ChannelListingError(f"Variant {variant_id} is not in listing {listing_id}")
    try:
        locale = Locale.objects.get(code=locale_code)
    except Locale.DoesNotExist:
        raise ValueError(f"Locale {locale_code} not found")
    title = (title or "").strip()
    run = (
        GenerationRun.objects.filter(
            variant_id=variant_id,
            channel_id=listing.channel_id,
            locale_id=locale.id,
        )
        .prefetch_related("outputs")
        .order_by("-created_at")
        .first()
    )
    if not run:
        raise ChannelListingError(
            f"No generated title found for variant {variant_id} in listing {listing_id} for {locale_code}. Generate titles first."
        )
    title_output = run.outputs.filter(field="title").first()
    if not title_output:
        raise ChannelListingError(
            f"No title output found for variant {variant_id} in listing {listing_id}. "
            "Re-generate titles and try again."
        )
    title_output.text = title
    title_output.save(update_fields=["text"])
    return {
        "variant_id": variant_id,
        "sku": (run.variant.sku or run.variant.internal_sku or str(variant_id)) if run.variant else str(variant_id),
        "title": title_output.text,
        "generated_at": run.created_at.isoformat() if run.created_at else None,
    }


def get_all_generated_titles(
    locale_code: Optional[str] = None,
    channel_code: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
    include_descriptions: bool = False,
) -> Dict[str, Any]:
    """
    Return all generated titles in the database, optionally filtered by locale and/or channel.
    Latest title per (variant, channel, locale). Paginated.

    When include_descriptions=True, each result includes "description" from the same
    generation run, with saved ContentSelection.description_text overriding when present.

    Returns:
        { "count": int, "results": [ { "variant_id", "sku", "product_id", "product_code",
          "channel_code", "locale_code", "title", "generated_at"[, "description"] }, ... ] }
    """
    qs = (
        GenerationRun.objects.filter(variant_id__isnull=False)
        .select_related("variant", "channel", "locale", "variant__product")
        .prefetch_related("outputs")
        .order_by("-created_at")
    )
    if locale_code:
        qs = qs.filter(locale__code=locale_code)
    if channel_code:
        qs = qs.filter(channel__code=channel_code)
    # Cap query to avoid loading unbounded rows (dedupe in memory)
    qs = qs[:50000]

    seen = set()  # (variant_id, channel_id, locale_id)
    results = []
    for run in qs:
        key = (run.variant_id, run.channel_id, run.locale_id)
        if key in seen:
            continue
        seen.add(key)
        title_text = None
        description_text = None
        for output in run.outputs.all():
            if output.field == "title":
                title_text = output.text
            elif output.field == "description":
                description_text = output.text
        if title_text is None and run.outputs.exists():
            title_text = run.outputs.first().text
        product = run.variant.product if run.variant else None
        row = {
            "run_id": run.id,
            "variant_id": run.variant_id,
            "sku": (run.variant.sku or run.variant.internal_sku or str(run.variant_id)) if run.variant else str(run.variant_id),
            "product_id": run.product_id or (product.id if product else None),
            "product_code": product.code if product else None,
            "channel_code": run.channel.code if run.channel else None,
            "locale_code": run.locale.code if run.locale else None,
            "title": title_text or "",
            "generated_at": run.created_at.isoformat() if run.created_at else None,
        }
        if include_descriptions:
            row["description"] = (description_text or "").strip()
            row["_locale_id"] = run.locale_id
            row["_channel_id"] = run.channel_id
        results.append(row)

    if include_descriptions and results:
        keys = [(r["variant_id"], r["_locale_id"], r["_channel_id"]) for r in results]
        variant_ids = {k[0] for k in keys}
        locale_ids = {k[1] for k in keys}
        channel_ids = {k[2] for k in keys}
        cs_qs = ContentSelection.objects.filter(
            variant_id__in=variant_ids,
            locale_id__in=locale_ids,
            channel_id__in=channel_ids,
        ).values("variant_id", "locale_id", "channel_id", "description_text")
        cs_map = {}
        for cs in cs_qs:
            cs_map[(cs["variant_id"], cs["locale_id"], cs["channel_id"])] = (cs["description_text"] or "").strip()
        for r in results:
            key = (r["variant_id"], r["_locale_id"], r["_channel_id"])
            if key in cs_map and cs_map[key]:
                r["description"] = cs_map[key]
            del r["_locale_id"]
            del r["_channel_id"]

    count = len(results)
    page = max(1, page)
    start = (page - 1) * page_size
    end = start + page_size
    page_results = results[start:end]
    return {"count": count, "results": page_results}
