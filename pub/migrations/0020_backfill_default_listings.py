# Data migration: Backfill default listings from existing ChannelListingMap

from django.db import migrations


def backfill_default_listings(apps, schema_editor):
    """
    Create default listings for existing (product, channel) combinations.
    
    For each distinct (product_id, channel_id) present in ChannelListingMap,
    create a default ChannelListing (with locale=None) and attach all
    existing ChannelListingMap rows for that product+channel to it.
    """
    ChannelListing = apps.get_model('pub', 'ChannelListing')
    ChannelListingMap = apps.get_model('pub', 'ChannelListingMap')
    Variant = apps.get_model('catalog', 'Variant')
    ChannelListingAxis = apps.get_model('catalog', 'ChannelListingAxis')
    ChannelVariantAxis = apps.get_model('catalog', 'ChannelVariantAxis')
    
    # Get all ChannelListingMap rows with their variant's product_id
    all_maps = ChannelListingMap.objects.select_related('variant').all()
    
    # Build a dict of (product_id, channel_id) -> list of map_ids
    product_channel_groups = {}
    for listing_map in all_maps:
        if listing_map.variant and listing_map.variant.product_id:
            key = (listing_map.variant.product_id, listing_map.channel_id)
            if key not in product_channel_groups:
                product_channel_groups[key] = []
            product_channel_groups[key].append(listing_map.id)
    
    created_count = 0
    updated_count = 0
    
    for (product_id, channel_id), map_ids in product_channel_groups.items():
        # Create or get default listing for this product+channel
        listing, created = ChannelListing.objects.get_or_create(
            product_id=product_id,
            channel_id=channel_id,
            locale_id=None,  # Default listing is locale-agnostic
            defaults={
                'is_default': True,
                'name': '',
            }
        )
        
        if created:
            created_count += 1
            
            # Copy axes from ChannelVariantAxis to ChannelListingAxis
            channel_axes = ChannelVariantAxis.objects.filter(
                product_id=product_id,
                channel_id=channel_id
            ).order_by('position')
            
            for channel_axis in channel_axes:
                ChannelListingAxis.objects.create(
                    listing=listing,
                    attribute_id=channel_axis.attribute_id,
                    position=channel_axis.position,
                    label_override=channel_axis.label_override,
                    enabled=True,
                )
        
        # Update all ChannelListingMap rows for this product+channel to point to the listing
        updated = ChannelListingMap.objects.filter(
            id__in=map_ids,
            listing_id__isnull=True,  # Only update rows that don't have a listing yet
        ).update(listing_id=listing.id)
        
        updated_count += updated
    
    print(f"Created {created_count} default listings, updated {updated_count} ChannelListingMap rows")


def reverse_backfill(apps, schema_editor):
    """
    Reverse migration: Remove listing_id from ChannelListingMap rows.
    This sets listing_id back to None, effectively undoing the backfill.
    """
    ChannelListingMap = apps.get_model('pub', 'ChannelListingMap')
    ChannelListingMap.objects.all().update(listing_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ('pub', '0019_add_channel_listing'),
        ('catalog', '0017_add_channel_listing_axis'),
    ]

    operations = [
        migrations.RunPython(backfill_default_listings, reverse_backfill),
    ]
