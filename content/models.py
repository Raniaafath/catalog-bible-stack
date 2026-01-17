from django.db import models

from catalog.models import Attribute, AttributeValue, Product, ProductType, ProductAttributeValue
from pub.models import Channel


class Locale(models.Model):
    code = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class ProductI18n(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="i18n")
    locale = models.ForeignKey(Locale, on_delete=models.PROTECT, related_name="product_translations")
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    slug = models.SlugField(max_length=255, blank=True)
    is_locked = models.BooleanField(default=False)
    locked_by = models.CharField(max_length=100, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "locale"],
                name="uniq_product_locale",
            ),
            models.UniqueConstraint(
                fields=["locale", "slug"],
                condition=models.Q(slug__isnull=False) & ~models.Q(slug=""),
                name="uniq_locale_slug_when_set",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_id} [{self.locale.code}]"


class ProductAttributeValueI18n(models.Model):
    product_attribute_value = models.ForeignKey(
        ProductAttributeValue,
        on_delete=models.CASCADE,
        related_name="i18n",
    )
    locale = models.ForeignKey(Locale, on_delete=models.PROTECT, related_name="product_attribute_value_translations")
    value_text = models.TextField(blank=True)
    is_locked = models.BooleanField(default=False)
    locked_by = models.CharField(max_length=100, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product_attribute_value", "locale"],
                name="uniq_pav_locale",
            )
        ]
        indexes = [
            models.Index(fields=["locale"], name="idx_pav_i18n_locale"),
        ]

    def __str__(self) -> str:
        return f"PAV {self.product_attribute_value_id} [{self.locale.code}]"


class AttributeI18n(models.Model):
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name="i18n")
    locale = models.ForeignKey(Locale, on_delete=models.PROTECT, related_name="attribute_translations")
    label = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "locale"],
                name="uniq_attribute_locale",
            )
        ]

    def __str__(self) -> str:
        return f"{self.attribute.code} [{self.locale.code}]"


class ProductTypeI18n(models.Model):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE, related_name="i18n")
    locale = models.ForeignKey(Locale, on_delete=models.PROTECT, related_name="product_type_translations")
    label = models.CharField(max_length=255)
    main_category = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product_type", "locale"],
                name="uniq_product_type_locale",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product_type.code} [{self.locale.code}]"


class SynonymStatus(models.TextChoices):
    SUGGESTED = "suggested", "Suggested"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class ProductTypeSynonym(models.Model):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE, related_name="synonyms")
    locale = models.ForeignKey(Locale, on_delete=models.PROTECT, related_name="product_type_synonyms")
    channel = models.ForeignKey(
        Channel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="product_type_synonyms",
    )
    term = models.CharField(max_length=255)
    keyword = models.ForeignKey(
        "kw.Keyword",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_type_synonyms",
    )
    status = models.CharField(
        max_length=20,
        choices=SynonymStatus.choices,
        default=SynonymStatus.SUGGESTED,
        db_index=True,
    )
    is_active = models.BooleanField(default=False, db_index=True)
    priority = models.IntegerField(default=0, db_index=True)
    score = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    source = models.CharField(max_length=64, default="gads_keyword_planner")
    reason_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product_type", "locale", "channel", "term"],
                name="uq_ptsyn_pt_loc_ch_term",
            )
        ]
        indexes = [
            models.Index(
                fields=["product_type", "locale", "channel", "status", "is_active"],
                name="idx_ptsyn_lookup",
            )
        ]

    def __str__(self) -> str:
        scope = self.channel.code if self.channel else "any"
        return f"{self.product_type.code} {self.locale.code} [{scope}] {self.term}"


class AttributeValueI18n(models.Model):
    attribute_value = models.ForeignKey(
        AttributeValue,
        on_delete=models.CASCADE,
        related_name="i18n",
    )
    locale = models.ForeignKey(Locale, on_delete=models.PROTECT, related_name="attribute_value_translations")
    label = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attribute_value", "locale"],
                name="uniq_attribute_value_locale",
            )
        ]

    def __str__(self) -> str:
        return f"{self.attribute_value_id} [{self.locale.code}]"


class AttributeValueSynonym(models.Model):
    class Status(models.TextChoices):
        SUGGESTED = "suggested", "Suggested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    attribute_value = models.ForeignKey(
        AttributeValue,
        on_delete=models.CASCADE,
        related_name="synonyms",
    )
    locale = models.ForeignKey(Locale, on_delete=models.PROTECT, related_name="attribute_value_synonyms")
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attribute_value_synonyms",
    )
    term = models.CharField(max_length=255)
    keyword = models.ForeignKey(
        "kw.Keyword",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="value_synonyms",
    )
    source = models.CharField(max_length=50, blank=True)
    score = models.DecimalField(max_digits=9, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUGGESTED)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attribute_value", "locale", "channel", "term"],
                name="uniq_attr_value_synonym",
            )
        ]
        indexes = [
            models.Index(
                fields=["attribute_value", "locale", "channel", "status", "score"],
                name="idx_attr_syn_locale_status",
            ),
        ]

    def __str__(self) -> str:
        scope = self.channel.code if self.channel else "any"
        return f"{self.attribute_value_id} {self.locale.code} [{scope}] {self.term}"


class ContentBlock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="content_blocks")
    locale = models.ForeignKey(Locale, on_delete=models.PROTECT, related_name="content_blocks")
    block_type = models.CharField(max_length=50)
    body = models.TextField()
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["product", "locale", "sort_order"], name="idx_block_product_locale_sort"),
        ]

    def __str__(self) -> str:
        return f"{self.product_id} [{self.locale.code}] {self.block_type}"


class TranslationTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    locale = models.CharField(max_length=15)
    scope = models.CharField(max_length=30)  # attribute, attribute_value, product_type
    target_ids = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["locale", "scope", "status"], name="idx_trtask_scope_status"),
        ]

    def __str__(self) -> str:
        return f"{self.scope}@{self.locale} [{self.status}]"


class ProductMedia(models.Model):
    class Kind(models.TextChoices):
        IMAGE = "image", "Image"
        PDF = "pdf", "PDF"
        VIDEO = "video", "Video"
        TECH_SHEET = "tech_sheet", "Tech Sheet"
        OTHER = "other", "Other"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="media")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    url = models.URLField(max_length=1000)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["product_id", "sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.product_id} {self.kind}"


class ComplianceClaim(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="compliance_claims")
    code = models.CharField(max_length=80)
    value = models.CharField(max_length=255, blank=True)
    document_url = models.URLField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "code"],
                name="uniq_product_compliance_code",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product_id} {self.code}"
