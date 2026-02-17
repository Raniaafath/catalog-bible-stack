"""Catalog services for business logic."""

from .axis_resolution import (
    AxisInfo,
    get_axes_for_context,
)
from .variant_titles import (
    generate_variant_title,
    generate_all_variant_titles,
    get_variant_axis_values,
    generate_variant_title_template,
    get_axis_value_combinations,
)
from .variant_grouping import (
    compare_variants,
    group_variants_with_axes,
    ungroup_variants,
)
from .channel_listings import (
    ChannelListingError,
    VariantNotFoundError,
    ListingNotFoundError,
    ChannelNotFoundError,
    ProductMismatchError,
    create_channel_listing,
    move_variants_to_listing,
    remove_variants_from_listing,
    get_available_variants_for_listing,
    get_listing_differences,
    set_listing_axes,
    get_available_templates_for_listing,
    create_default_title_template_for_listing,
    generate_titles_for_listing,
    get_listing_generated_titles,
    update_listing_generated_title,
    get_all_generated_titles,
)

__all__ = [
    'AxisInfo',
    'get_axes_for_context',
    'generate_variant_title',
    'generate_all_variant_titles',
    'get_variant_axis_values',
    'generate_variant_title_template',
    'get_axis_value_combinations',
    'compare_variants',
    'group_variants_with_axes',
    'ungroup_variants',
    # Channel Listings (Groups)
    'ChannelListingError',
    'VariantNotFoundError',
    'ListingNotFoundError',
    'ChannelNotFoundError',
    'ProductMismatchError',
    'create_channel_listing',
    'move_variants_to_listing',
    'remove_variants_from_listing',
    'get_available_variants_for_listing',
    'get_listing_differences',
    'set_listing_axes',
    'get_available_templates_for_listing',
    'create_default_title_template_for_listing',
    'generate_titles_for_listing',
    'get_listing_generated_titles',
    'update_listing_generated_title',
    'get_all_generated_titles',
]
