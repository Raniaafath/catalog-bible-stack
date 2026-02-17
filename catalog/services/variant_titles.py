"""
Service for generating variant titles based on variation axes.

Uses axis resolution (see axis_resolution.get_axes_for_context) so titles can
follow listing group or channel axes when provided.
"""
from typing import List, Optional, Union

from catalog.models import Product, Variant

from .axis_resolution import get_axes_for_context


def generate_variant_title(
    variant: Variant,
    separator: str = " - ",
    channel: Optional[Union[int, object]] = None,
    listing: Optional[Union[int, object]] = None,
) -> str:
    """
    Generate a descriptive title for a variant based on variation axes.

    Axes are resolved by context: listing group axes > channel axes > product family
    default axes (see GROUPING_AND_MARKETPLACE_AXES.md).

    Args:
        variant: The Variant instance.
        separator: String to separate base title from axis values (default: " - ").
        channel: Optional channel id or Channel instance (for marketplace-level axes).
        listing: Optional listing group id or ChannelListing instance (for listing axes).

    Returns:
        Generated title string.

    Example:
        Product: "Mountain Bike", axes: color=Red, size=Medium
        Result: "Mountain Bike - Red Medium"
    """
    product = variant.product

    # Base title: product family label, then variant source title, then model/code
    base_title = (
        product.default_label or
        variant.source_title or
        product.model or
        product.code
    )

    axes = get_axes_for_context(product, channel=channel, listing=listing)
    if not axes:
        return f"{base_title} ({variant.sku})"

    axis_parts = []
    for axis_obj in axes:
        pav = variant.attribute_values.filter(
            attribute=axis_obj.attribute,
            is_axis=True,
        ).first()

        if pav:
            if pav.attribute_value:
                value_str = pav.attribute_value.code.replace("-", " ").replace("_", " ").title()
            elif pav.value_text:
                value_str = str(pav.value_text).strip()
            elif pav.value_number is not None:
                value_str = str(pav.value_number)
            elif pav.value_bool is not None:
                value_str = "Yes" if pav.value_bool else "No"
            else:
                value_str = None

            if value_str and axis_obj.label_override:
                value_str = f"{axis_obj.label_override}: {value_str}"
            if value_str:
                axis_parts.append(value_str)

    if axis_parts:
        return f"{base_title}{separator}{' '.join(axis_parts)}"
    return base_title


def generate_all_variant_titles(
    product: Product,
    separator: str = " - ",
    channel: Optional[Union[int, object]] = None,
    listing: Optional[Union[int, object]] = None,
) -> dict:
    """
    Generate titles for all variants of a product family.

    Uses axis resolution when channel/listing are provided (see get_axes_for_context).

    Args:
        product: The product family (Product instance).
        separator: String to separate base title from axis values.
        channel: Optional channel id or Channel for marketplace axes.
        listing: Optional listing group id or ChannelListing for listing axes.

    Returns:
        Dictionary mapping variant SKU to generated title.
    """
    titles = {}
    for variant in product.variants.all():
        titles[variant.sku] = generate_variant_title(
            variant, separator, channel=channel, listing=listing
        )
    return titles


def get_variant_axis_values(
    variant: Variant,
    channel: Optional[Union[int, object]] = None,
    listing: Optional[Union[int, object]] = None,
) -> dict:
    """
    Get the axis values for a specific variant.

    Uses axis resolution when channel/listing are provided.

    Args:
        variant: The Variant instance.
        channel: Optional channel id or Channel for marketplace axes.
        listing: Optional listing group id or ChannelListing for listing axes.

    Returns:
        Dictionary mapping axis attribute code to value.
    """
    product = variant.product
    axes = get_axes_for_context(product, channel=channel, listing=listing)
    axis_values = {}
    for axis_obj in axes:
        pav = variant.attribute_values.filter(
            attribute=axis_obj.attribute,
            is_axis=True,
        ).first()
        if pav:
            value = None
            if pav.attribute_value:
                value = pav.attribute_value.code
            elif pav.value_text:
                value = pav.value_text
            elif pav.value_number is not None:
                value = str(pav.value_number)
            elif pav.value_bool is not None:
                value = "Yes" if pav.value_bool else "No"
            if value:
                axis_values[axis_obj.attribute_code] = value
    return axis_values


def generate_variant_title_template(
    product: Product,
    template: str = "{base_title} - {color} {size}",
    channel: Optional[Union[int, object]] = None,
    listing: Optional[Union[int, object]] = None,
) -> callable:
    """
    Create a template-based title generator for a product family's variants.

    Args:
        product: The product family (Product instance).
        template: Template string with placeholders for axis codes.
        channel: Optional channel for axis resolution.
        listing: Optional listing group for axis resolution.

    Returns:
        Function that takes a variant and returns formatted title.
    """
    def title_generator(variant: Variant) -> str:
        base_title = (
            product.default_label or
            variant.source_title or
            product.model or
            product.code
        )
        axis_values = get_variant_axis_values(
            variant, channel=channel, listing=listing
        )
        context = {"base_title": base_title}
        context.update(axis_values)
        try:
            return template.format(**context)
        except KeyError:
            return f"{base_title} - {variant.sku}"

    return title_generator


def get_axis_value_combinations(
    product: Product,
    channel: Optional[Union[int, object]] = None,
    listing: Optional[Union[int, object]] = None,
) -> List[dict]:
    """
    Get all unique combinations of axis values for a product family.

    Uses axis resolution when channel/listing are provided.

    Args:
        product: The product family (Product instance).
        channel: Optional channel for axis resolution.
        listing: Optional listing group for axis resolution.

    Returns:
        List of dicts, each one axis value combination (e.g. [{'color': 'red', 'size': 'm'}, ...]).
    """
    axes = get_axes_for_context(product, channel=channel, listing=listing)
    if not axes:
        return []
    
    from catalog.models import ProductAttributeValue

    axis_value_sets = {}
    for axis_obj in axes:
        values = set()
        pavs = ProductAttributeValue.objects.filter(
            attribute=axis_obj.attribute,
            is_axis=True,
            variant__product=product,
        )
        for pav in pavs:
            if pav.attribute_value:
                values.add(pav.attribute_value.code)
            elif pav.value_text:
                values.add(pav.value_text)
        if values:
            axis_value_sets[axis_obj.attribute_code] = sorted(values)
    
    # Generate all combinations
    if not axis_value_sets:
        return []
    
    # Create combinations using itertools.product
    from itertools import product as itertools_product
    
    axis_codes = list(axis_value_sets.keys())
    value_lists = [axis_value_sets[code] for code in axis_codes]
    
    combinations = []
    for combo in itertools_product(*value_lists):
        combination_dict = {
            axis_codes[i]: combo[i] 
            for i in range(len(axis_codes))
        }
        combinations.append(combination_dict)
    
    return combinations


# Example usage in management command or view:
"""
from catalog.models import Product
from catalog.services.variant_titles import generate_variant_title, generate_all_variant_titles

# Generate title for a single variant
product = Product.objects.get(code='BIKE-001')
variant = product.variants.first()
title = generate_variant_title(variant)
print(f"{variant.sku}: {title}")

# Generate titles for all variants
titles = generate_all_variant_titles(product)
for sku, title in titles.items():
    print(f"{sku}: {title}")

# Use custom separator
title = generate_variant_title(variant, separator=' | ')
# Result: "Mountain Bike | Red Medium"

# Use template
from catalog.services.variant_titles import generate_variant_title_template
generator = generate_variant_title_template(
    product,
    template="{base_title} ({color}, {size})"
)
for variant in product.variants.all():
    print(generator(variant))
# Result: "Mountain Bike (Red, Medium)"
"""
