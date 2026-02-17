"""
Service functions for variant grouping and comparison.

This module provides functionality to:
1. Compare variants and detect attribute differences
2. Suggest variation axes based on differences
3. Group variants under a product with selected axes
"""
from collections import defaultdict
from typing import Dict, List, Optional, Set, Any
from decimal import Decimal

from django.db import transaction
from django.utils.text import slugify

from catalog.models import (
    Attribute,
    AttributeValue,
    ChannelVariantAxis,
    Product,
    ProductAttributeValue,
    ProductType,
    Variant,
)
from pub.models import Channel


def compare_variants(variant_ids: List[int]) -> Dict[str, Any]:
    """
    Compare multiple variants and return their attribute differences.
    
    Args:
        variant_ids: List of variant IDs to compare
    
    Returns:
        Dict with structure:
        {
            "variants": [...variant data...],
            "differences": [
                {
                    "attribute_id": int,
                    "attribute_code": str,
                    "attribute_data_type": str,
                    "variant_values": {
                        variant_id: value,
                        ...
                    },
                    "unique_values_count": int,
                    "is_candidate_axis": bool
                }
            ],
            "common_attributes": [
                {
                    "attribute_id": int,
                    "attribute_code": str,
                    "common_value": str
                }
            ]
        }
    """
    variants = list(Variant.objects.filter(id__in=variant_ids).select_related('product'))
    
    if len(variants) < 2:
        return {
            "error": "Need at least 2 variants to compare",
            "variants": [],
            "differences": [],
            "common_attributes": []
        }
    
    # Gather all attribute values for each variant
    variant_attributes = defaultdict(dict)  # {variant_id: {attribute_id: value}}
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
                    'raw': {
                        'value_text': pav_data['value_text'],
                        'value_number': str(pav_data['value_number']) if pav_data['value_number'] else None,
                        'value_bool': pav_data['value_bool'],
                    }
                }
                
                if display_value:
                    unique_values.add(display_value)
            else:
                variant_values[variant.id] = None
        
        # Check if this attribute differs across variants
        unique_count = len(unique_values)
        
        if unique_count > 1:
            # This is a difference
            # Good candidates for variation axes:
            # - 2-10 unique values (not too few, not too many)
            # - All variants have a value (no missing)
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
            # Common attribute (same across all variants)
            common_attributes.append({
                'attribute_id': attr_data.id,
                'attribute_code': attr_data.code,
                'common_value': list(unique_values)[0],
            })
    
    # Sort differences: candidates first, then by number of unique values
    differences.sort(key=lambda x: (not x['is_candidate_axis'], x['unique_values_count']))
    
    return {
        'variants': [
            {
                'id': v.id,
                'sku': v.sku,
                'product_id': v.product_id,
                'product_code': v.product.code if v.product else None,
            }
            for v in variants
        ],
        'differences': differences,
        'common_attributes': common_attributes,
    }


@transaction.atomic
def group_variants_with_axes(
    variant_ids: List[int],
    channel_id: int,
    variation_axes: List[Dict[str, Any]],
    product_code: Optional[str] = None,
    product_type_id: Optional[int] = None,
    create_new_product: bool = True,
    target_product_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Group variants under a product and set variation axes for a channel.
    
    Args:
        variant_ids: List of variant IDs to group
        channel_id: Channel/marketplace ID
        variation_axes: List of axes with structure:
            [
                {"attribute_id": 5, "position": 0},
                {"attribute_id": 6, "position": 1}
            ]
        product_code: Code for new product (if creating)
        product_type_id: Product type ID (if creating)
        create_new_product: If True, create new product; if False, use target_product_id
        target_product_id: Existing product ID to group into (if not creating)
    
    Returns:
        Dict with created/updated product and axes info
    """
    variants = list(Variant.objects.filter(id__in=variant_ids).select_for_update())
    
    if not variants:
        raise ValueError("No variants found with provided IDs")
    
    # Get channel
    try:
        channel = Channel.objects.get(id=channel_id)
    except Channel.DoesNotExist:
        raise ValueError(f"Channel with ID {channel_id} not found")
    
    # Determine target product
    if create_new_product:
        # Create new product
        if not product_code:
            # Generate product code from first variant
            product_code = f"group-{variants[0].sku}" if variants[0].sku else f"group-{variants[0].id}"
            product_code = slugify(product_code)
        
        # Get product type
        product_type = None
        if product_type_id:
            try:
                product_type = ProductType.objects.get(id=product_type_id)
            except ProductType.DoesNotExist:
                pass
        
        # Try to use product type from first variant's current product
        if not product_type and variants[0].product:
            product_type = variants[0].product.product_type
        
        # Fallback to default
        if not product_type:
            product_type, _ = ProductType.objects.get_or_create(
                code='default',
                defaults={'default_label': 'Default'}
            )
        
        product = Product.objects.create(
            code=product_code,
            product_type=product_type,
            status=Product.Status.DRAFT,
        )
        product_created = True
    else:
        # Use existing product
        if not target_product_id:
            raise ValueError("target_product_id is required when create_new_product is False")
        
        try:
            product = Product.objects.get(id=target_product_id)
        except Product.DoesNotExist:
            raise ValueError(f"Product with ID {target_product_id} not found")
        
        product_created = False
    
    # Move all variants to this product
    Variant.objects.filter(id__in=variant_ids).update(product=product)
    
    # Set variation axes for this channel
    # Clear existing axes
    ChannelVariantAxis.objects.filter(product=product, channel=channel).delete()
    
    # Create new axes
    created_axes = []
    for axis_data in variation_axes:
        attribute_id = axis_data.get('attribute_id')
        position = axis_data.get('position', 0)
        label_override = axis_data.get('label_override')
        
        if not attribute_id:
            continue
        
        try:
            attribute = Attribute.objects.get(id=attribute_id)
            axis = ChannelVariantAxis.objects.create(
                product=product,
                channel=channel,
                attribute=attribute,
                position=position,
                label_override=label_override or None,
            )
            created_axes.append({
                'id': axis.id,
                'attribute_id': attribute.id,
                'attribute_code': attribute.code,
                'position': axis.position,
            })
        except Attribute.DoesNotExist:
            continue
    
    return {
        'product': {
            'id': product.id,
            'code': product.code,
            'created': product_created,
        },
        'channel': {
            'id': channel.id,
            'code': channel.code,
        },
        'variants_grouped': len(variant_ids),
        'axes': created_axes,
    }


@transaction.atomic
def ungroup_variants(variant_ids: List[int]) -> Dict[str, Any]:
    """
    Ungroup variants by moving each to its own individual placeholder product.
    
    This is the opposite of group_variants_with_axes - it breaks apart a group
    so that each variant becomes standalone again.
    
    Args:
        variant_ids: List of variant IDs to ungroup
    
    Returns:
        Dict with ungrouping results:
        {
            "ungrouped_count": int,
            "variants": [
                {
                    "id": int,
                    "sku": str,
                    "old_product_id": int,
                    "old_product_code": str,
                    "new_product_id": int,
                    "new_product_code": str
                }
            ],
            "orphaned_products_deleted": int
        }
    """
    variants = list(Variant.objects.filter(id__in=variant_ids).select_related('product').select_for_update())
    
    if not variants:
        raise ValueError("No variants found with provided IDs")
    
    results = []
    old_product_ids = set()
    
    for variant in variants:
        old_product = variant.product
        old_product_ids.add(old_product.id)
        
        # Create a new placeholder product for this variant
        product_code = f"variant-{variant.sku}" if variant.sku else f"variant-{variant.id}"
        product_code = slugify(product_code)
        
        # Ensure unique code
        base_code = product_code
        counter = 1
        while Product.objects.filter(code=product_code).exists():
            product_code = f"{base_code}-{counter}"
            counter += 1
        
        new_product = Product.objects.create(
            code=product_code,
            product_type=old_product.product_type,
            status=Product.Status.DRAFT,
            default_label=variant.source_title or f"Variant {variant.sku or variant.id}",
        )
        
        # Move variant to new product
        variant.product = new_product
        variant.save(update_fields=['product'])
        
        results.append({
            'id': variant.id,
            'sku': variant.sku,
            'old_product_id': old_product.id,
            'old_product_code': old_product.code,
            'new_product_id': new_product.id,
            'new_product_code': new_product.code,
        })
    
    # Clean up orphaned products (products with no remaining variants)
    orphaned_count = 0
    for product_id in old_product_ids:
        product = Product.objects.filter(id=product_id).first()
        if product and not product.variants.exists():
            # Delete orphaned product and its channel axes
            ChannelVariantAxis.objects.filter(product=product).delete()
            product.delete()
            orphaned_count += 1
    
    return {
        'ungrouped_count': len(results),
        'variants': results,
        'orphaned_products_deleted': orphaned_count,
    }
