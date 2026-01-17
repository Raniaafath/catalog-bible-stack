from django.db import models

from catalog.models import Attribute, AttributeValue, Product, ProductType, Variant
from content.models import Locale
from pub.models import Channel


class KeywordRole(models.TextChoices):
    HEAD = "head", "Head"
    ATTRIBUTE = "attribute", "Attribute"
    ATTRIBUTE_VALUE = "attribute_value", "Attribute Value"
    INTENT = "intent", "Intent"
    NEGATIVE = "negative", "Negative"


class KeywordStatus(models.TextChoices):
    SUGGESTED = "suggested", "Suggested"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class KeywordClassifier(models.TextChoices):
    RULE = "rule", "Rule"
    LLM = "llm", "LLM"
    MANUAL = "manual", "Manual"


class Keyword(models.Model):
    locale = models.ForeignKey(Locale, on_delete=models.PROTECT, related_name="keywords")
    term = models.TextField()
    normalized_term = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "normalized_term"],
                name="uniq_keyword_locale_normalized",
            )
        ]
        indexes = [
            models.Index(fields=["locale", "term"], name="idx_keyword_locale_term"),
        ]

    def __str__(self) -> str:
        return f"{self.locale.code}: {self.term}"


class PlannerSeed(models.Model):
    class SeedType(models.TextChoices):
        HEAD = "head", "Head"
        FEATURE = "feature", "Feature"
        BRAND = "brand", "Brand"
        COMPETITOR = "competitor", "Competitor"
        CATEGORY = "category", "Category"

    locale = models.ForeignKey(Locale, on_delete=models.PROTECT, related_name="planner_seeds")
    term = models.TextField()
    normalized_term = models.TextField()
    seed_type = models.CharField(max_length=20, choices=SeedType.choices)
    is_active = models.BooleanField(default=True)
    product_type = models.ForeignKey(
        ProductType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="planner_seeds",
    )
    channel = models.ForeignKey(
        Channel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="planner_seeds",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "product_type", "channel", "normalized_term"],
                name="uniq_planner_seed_scope_normalized",
            )
        ]
        indexes = [
            models.Index(fields=["locale", "is_active"], name="idx_planner_seed_locale_active"),
            models.Index(
                fields=["locale", "product_type", "channel", "is_active"],
                name="idx_planner_seed_scope",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.locale.code}: {self.term}"


class Source(models.Model):
    code = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.code


class PlannerRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="planner_runs")
    locale = models.ForeignKey(Locale, on_delete=models.PROTECT, related_name="planner_runs")
    product_type = models.ForeignKey(
        ProductType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="planner_runs",
    )
    channel = models.ForeignKey(
        Channel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planner_runs",
    )
    country_code = models.CharField(max_length=2, null=True, blank=True, db_index=True)
    geo_target = models.CharField(max_length=100, null=True, blank=True)
    request_json = models.JSONField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    error_json = models.JSONField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Run {self.id} ({self.status})"


class PlannerRunSeed(models.Model):
    run = models.ForeignKey(PlannerRun, on_delete=models.CASCADE, related_name="run_seeds")
    seed = models.ForeignKey(PlannerSeed, on_delete=models.CASCADE, related_name="run_seeds")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "seed"],
                name="uniq_planner_run_seed",
            )
        ]

    def __str__(self) -> str:
        return f"Run {self.run_id} -> Seed {self.seed_id}"


class PlannerRunKeyword(models.Model):
    run = models.ForeignKey(PlannerRun, on_delete=models.CASCADE, related_name="run_keywords")
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="planner_runs")
    seed = models.ForeignKey(
        PlannerSeed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="run_keywords",
    )
    raw_json = models.JSONField(null=True, blank=True)
    concept = models.CharField(
        max_length=32,
        choices=KeywordRole.choices,
        null=True,
        blank=True,
        db_index=True,
    )
    status = models.CharField(
        max_length=16,
        choices=KeywordStatus.choices,
        default=KeywordStatus.SUGGESTED,
        db_index=True,
    )
    classifier = models.CharField(
        max_length=16,
        choices=KeywordClassifier.choices,
        null=True,
        blank=True,
    )
    confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    mapped_product_type = models.ForeignKey(
        ProductType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="planner_run_keywords",
    )
    mapped_attribute = models.ForeignKey(
        Attribute,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="planner_run_keywords",
    )
    mapped_attribute_value = models.ForeignKey(
        AttributeValue,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="planner_run_keywords",
    )
    reason_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "keyword"],
                name="uniq_planner_run_keyword",
            )
        ]
        indexes = [
            models.Index(fields=["keyword"], name="idx_prk_keyword"),
            models.Index(fields=["run"], name="idx_prk_run"),
            models.Index(fields=["run", "concept", "status"], name="idx_prk_run_concept_status"),
            models.Index(fields=["mapped_product_type", "status"], name="idx_prk_mpt_status"),
            models.Index(fields=["mapped_attribute_value", "status"], name="idx_prk_mav_status"),
        ]

    def __str__(self) -> str:
        return f"Run {self.run_id} -> Keyword {self.keyword_id}"


class Metric(models.Model):
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="metrics")
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="metrics")
    planner_run = models.ForeignKey(
        PlannerRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="metrics",
    )
    month = models.DateField()
    avg_searches = models.IntegerField(null=True, blank=True)
    competition = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    cpc = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    raw_json = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["keyword", "source", "month", "planner_run"],
                name="uniq_metric_keyword_source_month_run",
            )
        ]
        indexes = [models.Index(fields=["month"], name="idx_metric_month")]

    def __str__(self) -> str:
        return f"{self.keyword_id} {self.source.code} {self.month}"


class Concept(models.Model):
    class ConceptType(models.TextChoices):
        HEAD_TERM = "head_term", "Head Term"
        FEATURE = "feature", "Feature"
        INTENT = "intent", "Intent"
        NEGATIVE = "negative", "Negative"
        BRAND = "brand", "Brand"
        SIZE = "size", "Size"
        OTHER = "other", "Other"

    code = models.CharField(max_length=100, unique=True)
    concept_type = models.CharField(max_length=20, choices=ConceptType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.code


class KeywordConcept(models.Model):
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="concepts")
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="keywords")
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    tagged_by = models.CharField(max_length=50)
    reason = models.TextField(blank=True)
    tagged_at = models.DateTimeField(auto_now_add=True)
    origin_run_keyword = models.ForeignKey(
        "kw.PlannerRunKeyword",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="concept_suggestions",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["keyword", "concept"],
                name="uniq_keyword_concept",
            )
        ]

    def __str__(self) -> str:
        return f"{self.keyword_id} -> {self.concept.code}"


class ProductTypeMap(models.Model):
    class Status(models.TextChoices):
        SUGGESTED = "suggested", "Suggested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="product_types")
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE, related_name="keyword_maps")
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUGGESTED)
    tagged_by = models.CharField(max_length=50, blank=True)
    origin_run_keyword = models.ForeignKey(
        "kw.PlannerRunKeyword",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_type_maps",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["keyword", "product_type"],
                name="uniq_keyword_product_type",
            )
        ]

    def __str__(self) -> str:
        return f"{self.keyword_id} -> {self.product_type.code}"


class KeywordParse(models.Model):
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="parses")
    tokens = models.JSONField(default=list)
    phrases = models.JSONField(default=list)
    detected = models.JSONField(default=dict)  # roles/sizes/notes
    source = models.CharField(max_length=50, blank=True)  # e.g. rule/ai/manual
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    tagged_by = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["keyword"], name="idx_keyword_parse_keyword"),
        ]

    def __str__(self) -> str:
        return f"Parse for {self.keyword_id}"


class AttributeMap(models.Model):
    class Status(models.TextChoices):
        SUGGESTED = "suggested", "Suggested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="attribute_maps")
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name="keyword_maps")
    attribute_value = models.ForeignKey(
        AttributeValue,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="keyword_maps",
    )
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUGGESTED)
    tagged_by = models.CharField(max_length=50, blank=True)
    reason = models.TextField(blank=True)
    reason_code = models.CharField(max_length=32, blank=True, default="")
    evidence = models.JSONField(default=dict, blank=True)
    origin_run_keyword = models.ForeignKey(
        "kw.PlannerRunKeyword",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attribute_maps",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["keyword", "attribute", "attribute_value"],
                condition=models.Q(attribute_value__isnull=False),
                name="uniq_keyword_attribute_value",
            ),
            models.UniqueConstraint(
                fields=["keyword", "attribute"],
                condition=models.Q(attribute_value__isnull=True),
                name="uniq_keyword_attribute_no_value",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.keyword_id} -> {self.attribute.code}"


class ProductKeywordMap(models.Model):
    class Source(models.TextChoices):
        ENUM = "enum_map", "Enum Map"
        TEXT = "pav_text", "PAV Text"
        TEXT_I18N = "pav_text_i18n", "PAV Text (i18n)"
        TEXT_LLM = "pav_text_llm", "PAV Text (LLM)"
        NUMERIC = "pav_numeric", "PAV Numeric"
        ATTR_VALUE_LABEL = "attr_value_label", "Attribute Value Label"
        ATTR_VALUE_CODE = "attr_value_code", "Attribute Value Code"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="keyword_maps")
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="product_maps")
    run = models.ForeignKey(PlannerRun, on_delete=models.CASCADE, related_name="product_keyword_maps")
    mapping_run = models.ForeignKey(
        "kw.MappingRun",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_keyword_maps",
    )
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="product_keyword_maps",
    )
    attribute_value = models.ForeignKey(
        AttributeValue,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="product_keyword_maps",
    )
    num_value = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    num_unit = models.CharField(max_length=50, null=True, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices)
    match_kind = models.CharField(max_length=32, blank=True, default="")
    matched_text = models.TextField(blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "keyword", "run", "source"],
                name="uniq_product_keyword_run_source",
            )
        ]
        indexes = [
            models.Index(fields=["run"], name="idx_pkmap_run"),
            models.Index(fields=["product"], name="idx_pkmap_product"),
        ]

    def __str__(self) -> str:
        return f"{self.product_id} -> {self.keyword_id} ({self.source})"


class MappingRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    planner_run = models.ForeignKey(
        PlannerRun,
        on_delete=models.CASCADE,
        related_name="mapping_runs",
    )
    category_batch = models.ForeignKey(
        "importer.CategoryBatch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mapping_runs",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_by = models.CharField(max_length=100, blank=True)
    algorithm_version = models.CharField(max_length=50, blank=True)
    config_json = models.JSONField(default=dict, blank=True)
    mapping_count = models.IntegerField(default=0)
    product_count = models.IntegerField(default=0)
    keyword_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["planner_run", "created_at"], name="idx_mapping_run_planner"),
            models.Index(fields=["status", "created_at"], name="idx_mapping_run_status"),
        ]

    def __str__(self) -> str:
        return f"MappingRun {self.id} [{self.status}]"


class Candidate(models.Model):
    class CandidateRole(models.TextChoices):
        HEAD = "head", "Head"
        HOOK = "hook", "Hook"
        SUPPORTING = "supporting", "Supporting"
        NEGATIVE = "negative", "Negative"

    class CandidateStatus(models.TextChoices):
        SUGGESTED = "suggested", "Suggested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name="candidates")
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, null=True, blank=True, related_name="candidates")
    locale = models.ForeignKey(Locale, on_delete=models.PROTECT, related_name="candidates")
    channel = models.ForeignKey(
        Channel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kw_candidates",
    )
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="candidates")
    role = models.CharField(max_length=20, choices=CandidateRole.choices)
    weight = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=CandidateStatus.choices, default=CandidateStatus.SUGGESTED)
    selected_by = models.CharField(max_length=50, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["locale", "channel", "role", "status"],
                name="idx_candidate_locale_channel",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(product__isnull=False, variant__isnull=True)
                | models.Q(product__isnull=True, variant__isnull=False),
                name="chk_candidate_scope",
            ),
            models.UniqueConstraint(
                fields=["locale", "channel", "keyword", "role", "product", "variant"],
                condition=models.Q(channel__isnull=False),
                name="uq_candidate_channel_fk",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.locale.code} {self.keyword_id} ({self.role})"
