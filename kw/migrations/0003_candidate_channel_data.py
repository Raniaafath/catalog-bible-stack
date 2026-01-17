from django.db import migrations


def forwards_populate_channel(apps, schema_editor):
    Candidate = apps.get_model("kw", "Candidate")
    Channel = apps.get_model("pub", "Channel")

    distinct_codes = (
        Candidate.objects.filter(channel_code__isnull=False)
        .exclude(channel_code="")
        .values_list("channel_code", flat=True)
        .distinct()
    )

    normalized_to_id = {}
    for raw_code in distinct_codes:
        normalized = raw_code.strip().lower()
        if not normalized:
            continue
        if normalized not in normalized_to_id:
            channel, _ = Channel.objects.get_or_create(code=normalized)
            normalized_to_id[normalized] = channel.id
        channel_id = normalized_to_id[normalized]
        Candidate.objects.filter(channel__isnull=True, channel_code=raw_code).update(channel_id=channel_id)


def backwards_clear_channel(apps, schema_editor):
    Candidate = apps.get_model("kw", "Candidate")
    Channel = apps.get_model("pub", "Channel")

    channel_ids = (
        Candidate.objects.filter(channel__isnull=False)
        .values_list("channel_id", flat=True)
        .distinct()
    )
    channels = Channel.objects.filter(id__in=channel_ids)

    for channel in channels:
        Candidate.objects.filter(
            channel_id=channel.id,
        ).filter(channel_code__isnull=True).update(channel_code=channel.code)
        Candidate.objects.filter(channel_id=channel.id, channel_code="").update(channel_code=channel.code)

    Candidate.objects.filter(channel__isnull=False).update(channel=None)


class Migration(migrations.Migration):

    dependencies = [
        ("kw", "0002_candidate_channel_fk"),
        ("pub", "0003_generation"),
    ]

    operations = [
        migrations.RunPython(forwards_populate_channel, backwards_clear_channel),
    ]
