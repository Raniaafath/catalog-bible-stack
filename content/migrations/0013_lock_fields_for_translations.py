from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0012_productattributevaluei18n"),
    ]

    operations = [
        migrations.AddField(
            model_name="producti18n",
            name="is_locked",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="producti18n",
            name="locked_by",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="producti18n",
            name="locked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="productattributevaluei18n",
            name="is_locked",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="productattributevaluei18n",
            name="locked_by",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="productattributevaluei18n",
            name="locked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
