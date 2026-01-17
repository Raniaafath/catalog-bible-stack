from django.contrib import admin

from .models import (
    AttributeMap,
    ProductKeywordMap,
    Candidate,
    Concept,
    Keyword,
    KeywordConcept,
    Metric,
    PlannerRun,
    PlannerRunKeyword,
    PlannerRunSeed,
    PlannerSeed,
    ProductTypeMap,
    Source,
    KeywordParse,
)


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ("id", "locale", "term", "normalized_term", "created_at")
    search_fields = ("term", "normalized_term")
    list_filter = ("locale",)


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("code", "created_at")
    search_fields = ("code",)


@admin.register(PlannerSeed)
class PlannerSeedAdmin(admin.ModelAdmin):
    list_display = ("id", "locale", "product_type", "channel", "term", "seed_type", "is_active", "created_at")
    list_filter = ("locale", "product_type", "channel", "seed_type", "is_active")
    search_fields = ("term", "normalized_term", "product_type__code")


class PlannerRunSeedInline(admin.TabularInline):
    model = PlannerRunSeed
    extra = 0


class PlannerRunKeywordInline(admin.TabularInline):
    model = PlannerRunKeyword
    extra = 0
    readonly_fields = ("keyword", "seed", "raw_json", "created_at")


@admin.register(PlannerRun)
class PlannerRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "source",
        "locale",
        "channel",
        "status",
        "started_at",
        "finished_at",
        "created_at",
    )
    list_filter = ("status", "source", "locale", "channel")
    search_fields = ("id", "geo_target")
    readonly_fields = ("created_at",)
    inlines = [PlannerRunSeedInline, PlannerRunKeywordInline]


@admin.register(PlannerRunSeed)
class PlannerRunSeedAdmin(admin.ModelAdmin):
    list_display = ("run", "seed")
    list_filter = ("run__locale", "seed__seed_type")
    search_fields = ("run__id", "seed__term")


@admin.register(PlannerRunKeyword)
class PlannerRunKeywordAdmin(admin.ModelAdmin):
    list_display = (
        "run",
        "keyword",
        "seed",
        "concept",
        "status",
        "mapped_product_type",
        "mapped_attribute",
        "mapped_attribute_value",
        "created_at",
    )
    list_filter = ("run__source", "run__locale", "concept", "status", "mapped_product_type")
    search_fields = ("keyword__term", "keyword__normalized_term", "run__id")


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ("keyword", "source", "month", "planner_run", "avg_searches", "competition", "cpc")
    list_filter = ("source", "month")
    search_fields = ("keyword__term", "keyword__normalized_term")


@admin.register(Concept)
class ConceptAdmin(admin.ModelAdmin):
    list_display = ("code", "concept_type", "created_at")
    search_fields = ("code",)
    list_filter = ("concept_type",)


@admin.register(KeywordConcept)
class KeywordConceptAdmin(admin.ModelAdmin):
    list_display = ("keyword", "concept", "confidence", "tagged_by", "tagged_at")
    list_filter = ("tagged_by", "concept__concept_type")
    search_fields = ("keyword__term", "concept__code")


@admin.register(ProductTypeMap)
class ProductTypeMapAdmin(admin.ModelAdmin):
    list_display = ("keyword", "product_type", "confidence", "status", "tagged_by", "origin_run_keyword", "updated_at")
    list_filter = ("product_type", "status", "tagged_by")
    search_fields = ("keyword__term", "product_type__code")
    autocomplete_fields = ("keyword", "product_type", "origin_run_keyword")


@admin.register(AttributeMap)
class AttributeMapAdmin(admin.ModelAdmin):
    list_display = (
        "keyword",
        "attribute",
        "attribute_value",
        "confidence",
        "status",
        "tagged_by",
        "origin_run_keyword",
    )
    list_filter = ("attribute", "status", "tagged_by")
    search_fields = ("keyword__term", "attribute__code", "attribute_value__code")
    autocomplete_fields = ("keyword", "attribute", "attribute_value", "origin_run_keyword")


@admin.register(ProductKeywordMap)
class ProductKeywordMapAdmin(admin.ModelAdmin):
    list_display = ("product", "keyword", "run", "source", "confidence", "created_at")
    list_filter = ("run", "source")
    search_fields = ("keyword__term", "product__id")
    autocomplete_fields = ("product", "keyword", "run", "attribute_value")


@admin.register(KeywordParse)
class KeywordParseAdmin(admin.ModelAdmin):
    list_display = ("keyword", "source", "tagged_by", "confidence", "created_at")
    search_fields = ("keyword__term", "tagged_by", "source")


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = (
        "locale",
        "channel",
        "keyword",
        "role",
        "status",
        "product",
        "variant",
        "weight",
        "created_at",
    )
    list_filter = ("locale", "role", "status", "channel")
    search_fields = ("keyword__term", "keyword__normalized_term", "product__id", "variant__id")
