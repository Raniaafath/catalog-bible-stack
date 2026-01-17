from django.db import models


class Channel(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class ChannelPolicySet(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name="policy_sets",
    )
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "version"],
                name="uniq_channel_policy_set_version",
            )
        ]
        indexes = [
            models.Index(fields=["channel", "status"], name="idx_channel_policy_status"),
        ]

    def __str__(self) -> str:
        return f"{self.channel.code} v{self.version} ({self.status})"


class ChannelLocalePolicy(models.Model):
    class TitleMode(models.TextChoices):
        AUTO = "auto", "Auto"
        REVIEW = "review", "Review"

    class SelectionScope(models.TextChoices):
        PRODUCT = "product", "Product"
        VARIANT = "variant", "Variant"

    class BrandPosition(models.TextChoices):
        START = "start", "Start"
        END = "end", "End"
        NONE = "none", "None"

    policy_set = models.ForeignKey(
        ChannelPolicySet,
        on_delete=models.CASCADE,
        related_name="locale_policies",
    )
    locale = models.ForeignKey(
        "content.Locale",
        on_delete=models.PROTECT,
        related_name="channel_locale_policies",
    )
    country_code = models.CharField(max_length=2, blank=True)
    currency_code = models.CharField(max_length=3, blank=True)
    title_max_len = models.IntegerField(default=150)
    meta_title_max_len = models.IntegerField(default=70)
    meta_description_max_len = models.IntegerField(default=160)
    description_max_len = models.IntegerField(default=5000)
    bullet_count = models.IntegerField(default=5)
    bullet_max_len = models.IntegerField(default=200)
    title_separator = models.CharField(max_length=20, default=" – ")
    brand_position = models.CharField(
        max_length=10,
        choices=BrandPosition.choices,
        default=BrandPosition.END,
    )
    title_mode = models.CharField(
        max_length=10,
        choices=TitleMode.choices,
        default=TitleMode.AUTO,
    )
    auto_create_selection = models.BooleanField(default=False)
    auto_approve_selection = models.BooleanField(default=False)
    selection_scope = models.CharField(
        max_length=10,
        choices=SelectionScope.choices,
        default=SelectionScope.PRODUCT,
    )
    context = models.CharField(max_length=50, default="title")
    normalize_whitespace = models.BooleanField(default=True)
    dedupe_words = models.BooleanField(default=True)
    banned_terms = models.JSONField(default=list)
    rules_json = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["policy_set", "locale", "context"],
                name="uniq_channel_locale_policy_context",
            )
        ]

    def __str__(self) -> str:
        return f"{self.policy_set} {self.locale.code}"


class ChannelConstraintPolicy(models.Model):
    policy_set = models.OneToOneField(
        ChannelPolicySet,
        on_delete=models.CASCADE,
        related_name="constraint_policy",
    )
    max_variants = models.IntegerField(null=True, blank=True)
    max_options = models.IntegerField(null=True, blank=True)
    max_option_values = models.IntegerField(null=True, blank=True)
    allow_bundles = models.BooleanField(default=True)
    allow_multi_currency = models.BooleanField(default=True)
    require_approval = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Constraints for {self.policy_set}"


class ChannelBundlePolicy(models.Model):
    class BundleTitleMode(models.TextChoices):
        PARENT_ONLY = "parent_only", "Parent Only"
        INCLUDE_COMPONENTS = "include_components", "Include Components"
        INCLUDE_COUNTS = "include_counts", "Include Counts"

    policy_set = models.OneToOneField(
        ChannelPolicySet,
        on_delete=models.CASCADE,
        related_name="bundle_policy",
    )
    bundle_title_mode = models.CharField(
        max_length=30,
        choices=BundleTitleMode.choices,
        default=BundleTitleMode.PARENT_ONLY,
    )
    max_components_in_title = models.IntegerField(default=0)
    show_components_in_bullets = models.BooleanField(default=True)
    show_components_in_description = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Bundle policy for {self.policy_set}"


class ChannelProductOption(models.Model):
    class OptionKind(models.TextChoices):
        ATTRIBUTE = "attribute", "Attribute"
        COMPOSITE = "composite", "Composite"
        LITERAL = "literal", "Literal"

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="channel_options",
    )
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name="product_options",
    )
    slot_index = models.PositiveSmallIntegerField()
    code = models.CharField(max_length=50, blank=True)
    option_kind = models.CharField(max_length=20, choices=OptionKind.choices)
    label_default = models.CharField(max_length=100, blank=True)
    literal_value = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "channel", "slot_index"],
                name="uniq_channel_product_option_slot",
            ),
            models.CheckConstraint(
                condition=models.Q(slot_index__gte=1) & models.Q(slot_index__lte=10),
                name="chk_option_slot_index_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(option_kind="literal")  # literal requires a value
                    & models.Q(literal_value__isnull=False)
                    & ~models.Q(literal_value="")
                )
                | ~models.Q(option_kind="literal"),
                name="chk_option_literal_requires_value",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_id}@{self.channel.code} slot {self.slot_index}"


class ChannelProductOptionI18n(models.Model):
    option = models.ForeignKey(
        ChannelProductOption,
        on_delete=models.CASCADE,
        related_name="i18n",
    )
    locale = models.ForeignKey(
        "content.Locale",
        on_delete=models.PROTECT,
        related_name="channel_product_option_labels",
    )
    label = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["option", "locale"],
                name="uniq_channel_product_option_i18n",
            )
        ]

    def __str__(self) -> str:
        return f"{self.option_id}:{self.locale.code}"


class ChannelProductOptionAttribute(models.Model):
    option = models.ForeignKey(
        ChannelProductOption,
        on_delete=models.CASCADE,
        related_name="attributes",
    )
    attribute = models.ForeignKey(
        "catalog.Attribute",
        on_delete=models.PROTECT,
        related_name="channel_product_options",
    )
    position = models.IntegerField(default=0)
    prefix = models.CharField(max_length=20, blank=True)
    suffix = models.CharField(max_length=20, blank=True)
    separator = models.CharField(max_length=10, blank=True, default="x")
    unit_override = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["option", "attribute"],
                name="uniq_channel_option_attribute",
            ),
            models.UniqueConstraint(
                fields=["option", "position"],
                name="uniq_channel_option_attribute_position",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.option_id}:{self.attribute.code}"


class Template(models.Model):
    class Kind(models.TextChoices):
        TITLE = "title", "Title"
        BULLETS = "bullets", "Bullets"
        DESCRIPTION = "description", "Description"
        META_TITLE = "meta_title", "Meta Title"
        META_DESCRIPTION = "meta_description", "Meta Description"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    product_type = models.ForeignKey(
        "catalog.ProductType",
        on_delete=models.PROTECT,
        related_name="templates",
    )
    locale = models.ForeignKey(
        "content.Locale",
        on_delete=models.PROTECT,
        related_name="templates",
    )
    channel = models.ForeignKey(
        Channel,
        on_delete=models.PROTECT,
        related_name="templates",
    )
    kind = models.CharField(max_length=50, choices=Kind.choices)
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product_type", "locale", "channel", "kind", "version"],
                name="uniq_template_scope",
            ),
            models.UniqueConstraint(
                fields=["product_type", "locale", "channel", "kind"],
                condition=models.Q(status="active"),
                name="uniq_active_template_scope",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_type.code} {self.locale.code} {self.channel.code} {self.kind} v{self.version}"


class TemplatePart(models.Model):
    class PartType(models.TextChoices):
        KEYWORD = "keyword", "Keyword"
        AXIS_ATTRIBUTE = "axis_attribute", "Axis Attribute"
        ATTRIBUTE_VALUE = "attribute_value", "Attribute Value"
        HEAD_TERM = "head_term", "Head Term"
        HOOK_TERM = "hook_term", "Hook Term"
        LITERAL = "literal", "Literal"
        BRAND = "brand", "Brand"

    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        related_name="parts",
    )
    position = models.IntegerField()
    part_type = models.CharField(max_length=20, choices=PartType.choices)
    attribute = models.ForeignKey(
        "catalog.Attribute",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="template_parts",
    )
    keyword_role = models.CharField(
        max_length=20,
        choices=[
            ("head", "Head"),
            ("hook", "Hook"),
            ("supporting", "Supporting"),
        ],
        null=True,
        blank=True,
    )
    literal_text = models.TextField(null=True, blank=True)
    required = models.BooleanField(default=False)
    fallback_text = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["template", "position"],
                name="uniq_template_part_position",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(part_type="literal")
                    & models.Q(literal_text__isnull=False)
                    & ~models.Q(literal_text="")
                )
                | ~models.Q(part_type="literal"),
                name="chk_part_literal_requires_text",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(part_type__in=["attribute_value", "axis_attribute"])
                    & models.Q(attribute__isnull=False)
                )
                | ~models.Q(part_type__in=["attribute_value", "axis_attribute"]),
                name="chk_part_attribute_requires_attr",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(part_type="keyword") & models.Q(keyword_role__isnull=False)
                )
                | ~models.Q(part_type="keyword"),
                name="chk_part_keyword_requires_role",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.template_id}:{self.position}"


class GenerationRun(models.Model):
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="generation_runs",
    )
    variant = models.ForeignKey(
        "catalog.Variant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="generation_runs",
    )
    planner_run = models.ForeignKey(
        "kw.PlannerRun",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_runs",
    )
    batch = models.ForeignKey(
        "pub.GenerationBatch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_runs",
    )
    locale = models.ForeignKey("content.Locale", on_delete=models.PROTECT, related_name="generation_runs")
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="generation_runs")
    template = models.ForeignKey(Template, on_delete=models.PROTECT, related_name="generation_runs")
    model_info = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(product__isnull=False, variant__isnull=True)
                | models.Q(product__isnull=True, variant__isnull=False),
                name="chk_generation_run_scope",
            )
        ]

    def __str__(self) -> str:
        target = self.product or self.variant
        return f"Run {self.id} for {target}"


class TitleSelection(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    class CreatedByType(models.TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"

    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)
    variant = models.ForeignKey("catalog.Variant", null=True, blank=True, on_delete=models.CASCADE)
    locale = models.ForeignKey("content.Locale", on_delete=models.CASCADE)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    context = models.CharField(max_length=50, default="title")
    planner_run = models.ForeignKey("kw.PlannerRun", null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    created_by_type = models.CharField(
        max_length=10,
        choices=CreatedByType.choices,
        default=CreatedByType.SYSTEM,
    )
    head_text = models.CharField(max_length=255)
    head_source = models.CharField(max_length=64)
    head_keyword_id = models.IntegerField(null=True, blank=True)
    hook_text = models.CharField(max_length=255, blank=True, default="")
    hook_source = models.CharField(max_length=64, blank=True, default="")
    hook_keyword_id = models.IntegerField(null=True, blank=True)
    overrides_json = models.JSONField(default=dict, blank=True)
    meta_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "variant", "locale", "channel", "context"],
                name="uniq_title_selection_scope_context",
            )
        ]
        indexes = [
            models.Index(fields=["product", "locale", "channel", "context"], name="idx_title_selection_scope"),
            models.Index(fields=["planner_run"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        target = self.variant or self.product
        return f"{target} {self.locale.code} {self.channel.code} {self.status}"


class GenerationOutput(models.Model):
    run = models.ForeignKey(GenerationRun, on_delete=models.CASCADE, related_name="outputs")
    field = models.CharField(max_length=50)
    position = models.IntegerField(null=True, blank=True)
    text = models.TextField()
    is_approved = models.BooleanField(default=False)
    approved_by = models.CharField(max_length=100, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    selection = models.ForeignKey(
        TitleSelection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_outputs",
    )
    head_text = models.CharField(max_length=255, blank=True)
    hook_text = models.CharField(max_length=255, blank=True)
    head_source = models.CharField(max_length=50, blank=True)
    hook_source = models.CharField(max_length=50, blank=True)
    head_keyword = models.ForeignKey(
        "kw.Keyword",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_head_outputs",
    )
    hook_keyword = models.ForeignKey(
        "kw.Keyword",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_hook_outputs",
    )
    score_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "field", "position"],
                name="uniq_generation_output_field_position",
            )
        ]

    def __str__(self) -> str:
        return f"{self.run_id} {self.field}"


class Approval(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    entity_type = models.CharField(max_length=80)
    entity_id = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approved_by = models.CharField(max_length=100, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["entity_type", "entity_id"],
                name="uniq_approval_entity",
            )
        ]

    def __str__(self) -> str:
        return f"{self.entity_type}:{self.entity_id}"


class ChannelListingMap(models.Model):
    variant = models.ForeignKey("catalog.Variant", on_delete=models.CASCADE, related_name="channel_listings")
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="variant_listings")
    external_id = models.CharField(max_length=120, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(max_length=50, blank=True)
    error_json = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "channel"],
                name="uniq_channel_listing_variant_channel",
            )
        ]

    def __str__(self) -> str:
        return f"{self.variant_id}@{self.channel.code}"


class ContentSelection(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    class CreatedByType(models.TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"

    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)
    variant = models.ForeignKey("catalog.Variant", null=True, blank=True, on_delete=models.CASCADE)
    locale = models.ForeignKey("content.Locale", on_delete=models.CASCADE)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    context = models.CharField(max_length=50, default="title")
    planner_run = models.ForeignKey("kw.PlannerRun", null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    created_by_type = models.CharField(
        max_length=10,
        choices=CreatedByType.choices,
        default=CreatedByType.SYSTEM,
    )
    bullets_json = models.JSONField(default=list, blank=True)
    description_text = models.TextField(blank=True)
    meta_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "variant", "locale", "channel", "context"],
                name="uniq_content_selection_scope_context",
            )
        ]
        indexes = [
            models.Index(fields=["product", "locale", "channel", "context"], name="idx_cs_scope"),
            models.Index(fields=["planner_run"], name="idx_cs_planner_run"),
            models.Index(fields=["status"], name="idx_cs_status"),
        ]

    def __str__(self) -> str:
        target = self.variant or self.product
        return f"{target} {self.locale.code} {self.channel.code} {self.status}"


class ContentEditSession(models.Model):
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)
    variant = models.ForeignKey("catalog.Variant", null=True, blank=True, on_delete=models.CASCADE)
    locale = models.ForeignKey("content.Locale", on_delete=models.CASCADE)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    context = models.CharField(max_length=50, default="title")
    mode = models.CharField(max_length=10, default="review")
    title_selection = models.ForeignKey(
        TitleSelection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edit_sessions",
    )
    content_selection = models.ForeignKey(
        ContentSelection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edit_sessions",
    )
    messages_json = models.JSONField(default=list, blank=True)
    meta_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["product", "locale", "channel", "context"], name="idx_ce_scope"),
        ]

    def __str__(self) -> str:
        return f"EditSession {self.id} {self.locale.code} {self.channel.code}"


class ContentSet(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    channel = models.ForeignKey("pub.Channel", null=True, blank=True, on_delete=models.SET_NULL)
    locale = models.ForeignKey("content.Locale", null=True, blank=True, on_delete=models.SET_NULL)
    context = models.CharField(max_length=64, default="content")
    kind = models.CharField(max_length=16, default="static")
    filter_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["channel", "locale"], name="idx_content_set_scope"),
        ]

    def __str__(self) -> str:
        return self.name


class ContentSetItem(models.Model):
    content_set = models.ForeignKey(ContentSet, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)
    variant = models.ForeignKey("catalog.Variant", null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["content_set", "product", "variant"],
                name="uniq_content_set_member",
            )
        ]

    def __str__(self) -> str:
        return f"{self.content_set_id}:{self.product_id}:{self.variant_id or 'product'}"


class GenerationBatch(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    content_set = models.ForeignKey(ContentSet, null=True, blank=True, on_delete=models.SET_NULL)
    channel = models.ForeignKey("pub.Channel", on_delete=models.PROTECT)
    locale = models.ForeignKey("content.Locale", on_delete=models.PROTECT)
    context = models.CharField(max_length=64, default="content")
    planner_run = models.ForeignKey("kw.PlannerRun", null=True, blank=True, on_delete=models.SET_NULL)
    mode = models.CharField(max_length=16, default="auto")
    include_descriptions = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    total = models.IntegerField(default=0)
    generated = models.IntegerField(default=0)
    needs_approval = models.IntegerField(default=0)
    errors = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"], name="idx_batch_status"),
        ]

    def __str__(self) -> str:
        return f"Batch {self.id} {self.status}"


class GenerationBatchItem(models.Model):
    class ItemStatus(models.TextChoices):
        GENERATED = "generated", "Generated"
        NEEDS_APPROVAL = "needs_approval", "Needs Approval"
        ERROR = "error", "Error"

    batch = models.ForeignKey(GenerationBatch, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)
    variant = models.ForeignKey("catalog.Variant", on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=ItemStatus.choices)
    error_message = models.TextField(blank=True, default="")
    generation_run = models.ForeignKey("pub.GenerationRun", null=True, blank=True, on_delete=models.SET_NULL)
    selection_id = models.IntegerField(null=True, blank=True)
    preview_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "variant"],
                name="uniq_batch_variant",
            )
        ]

    def __str__(self) -> str:
        return f"{self.batch_id}:{self.variant_id}:{self.status}"


class ExportProfile(models.Model):
    class Format(models.TextChoices):
        CSV = "csv", "CSV"
        XLSX = "xlsx", "XLSX"

    name = models.CharField(max_length=200)
    channel = models.ForeignKey("pub.Channel", on_delete=models.PROTECT)
    context = models.CharField(max_length=64, default="content")
    format = models.CharField(max_length=8, choices=Format.choices, default=Format.CSV)
    version = models.IntegerField(default=1)
    columns_json = models.JSONField(default=list)
    options_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "context", "format", "version"],
                name="uniq_export_profile_version",
            )
        ]
        indexes = [
            models.Index(fields=["channel", "context", "is_active"], name="idx_export_profile_active"),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"


class ExportJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    profile = models.ForeignKey(ExportProfile, on_delete=models.PROTECT)
    batch = models.ForeignKey("pub.GenerationBatch", null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    result_file = models.CharField(max_length=255, blank=True, default="")
    stats_json = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"], name="idx_export_job_status"),
        ]

    def __str__(self) -> str:
        return f"ExportJob {self.id} {self.status}"


class UniqueTitle(models.Model):
    class Scope(models.TextChoices):
        PARENT = "parent", "Parent"
        VARIANT = "variant", "Variant"

    product_type = models.ForeignKey(
        "catalog.ProductType",
        on_delete=models.PROTECT,
        related_name="unique_titles",
    )
    locale = models.ForeignKey(
        "content.Locale",
        on_delete=models.PROTECT,
        related_name="unique_titles",
    )
    channel = models.ForeignKey(
        Channel,
        on_delete=models.PROTECT,
        related_name="unique_titles",
    )
    scope = models.CharField(max_length=20, choices=Scope.choices)
    normalized_title = models.TextField()
    raw_title = models.TextField()
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="unique_titles",
    )
    variant = models.ForeignKey(
        "catalog.Variant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="unique_titles",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(product__isnull=False, variant__isnull=True)
                | models.Q(product__isnull=True, variant__isnull=False),
                name="chk_unique_title_scope",
            ),
            models.UniqueConstraint(
                fields=["product_type", "locale", "channel", "scope", "normalized_title"],
                name="uniq_unique_title_scope_norm",
            ),
        ]
        indexes = [
            models.Index(fields=["product_type", "locale", "channel"], name="idx_unique_title_scope"),
            models.Index(fields=["normalized_title"], name="idx_unique_title_norm"),
        ]

    def __str__(self) -> str:
        return f"{self.product_type.code} {self.locale.code} {self.channel.code} {self.scope}"


class TermGlossary(models.Model):
    locale = models.ForeignKey("content.Locale", on_delete=models.PROTECT, related_name="term_glossary")
    term_norm = models.CharField(max_length=200)
    term = models.CharField(max_length=200)
    short_definition = models.TextField(blank=True)
    synonyms_json = models.JSONField(default=list, blank=True)
    examples_json = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "term_norm"],
                name="uniq_term_glossary_locale_norm",
            )
        ]
        indexes = [
            models.Index(fields=["locale", "term_norm"], name="idx_term_glossary_locale_norm"),
        ]

    def __str__(self) -> str:
        return f"{self.locale.code}:{self.term_norm}"
