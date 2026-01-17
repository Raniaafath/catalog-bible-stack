import json
import re
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError

from catalog.models import Attribute, AttributeValue, ProductType
from kw.models import AttributeMap, Concept, Keyword, KeywordConcept, PlannerRun, PlannerRunKeyword, ProductTypeMap


class Command(BaseCommand):
    help = "Rule-based keyword classifier: head terms, attribute/value signals, size extraction."

    HEAD_TERMS = {"duschwanne", "duschtasse", "duschboard", "duschbecken", "duschtassen"}
    # Minimal rule set: only head term + size extraction. Other mappings are left for AI/manual.

    SIZE_PATTERN = re.compile(r"(\d{2,3})\s*x\s*(\d{2,3})", re.IGNORECASE)

    def add_arguments(self, parser):
        parser.add_argument("--run-id", type=int, required=True, help="PlannerRun ID to classify")
        parser.add_argument("--locale", required=True, help="Locale code (must match run locale)")
        parser.add_argument(
            "--product-type",
            default="receveur_douche",
            help="Product type code for head terms (default receveur_douche)",
        )

    def handle(self, *args, **options):
        run_id = options["run_id"]
        locale_code = options["locale"]
        product_type_code = options["product_type"]

        run = self._get_run(run_id, locale_code)
        pt = self._get_product_type(product_type_code)

        concepts = self._ensure_concepts()

        head_mapped = concepts_created = 0

        keywords = Keyword.objects.filter(planner_runs__run=run).distinct()
        if not keywords.exists():
            self.stdout.write(self.style.WARNING("No keywords linked to this run"))
            return

        for kw in keywords:
            tokens, phrases = self._tokenize(kw.term)
            size_matches = self.SIZE_PATTERN.findall(kw.term)
            self._handle_head(kw, tokens, pt, concepts["head_term"])
            head_mapped += 1 if any(t in self.HEAD_TERMS for t in tokens) else 0

            concepts_created += self._handle_size(size_matches, kw, concepts["size"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Head maps: {head_mapped}, Concepts added/updated: {concepts_created}"
            )
        )

    def _get_run(self, run_id: int, locale_code: str) -> PlannerRun:
        try:
            run = PlannerRun.objects.select_related("locale").get(id=run_id)
        except PlannerRun.DoesNotExist as exc:
            raise CommandError(f"PlannerRun {run_id} not found") from exc
        if run.locale.code != locale_code:
            raise CommandError(f"Run locale {run.locale.code} does not match --locale {locale_code}")
        return run

    def _get_product_type(self, code: str) -> ProductType:
        try:
            return ProductType.objects.get(code=code)
        except ProductType.DoesNotExist as exc:
            raise CommandError(f"ProductType {code} not found") from exc

    def _ensure_concepts(self) -> Dict[str, Concept]:
        concepts = {}
        concept_defs = {
            "head_term": Concept.ConceptType.HEAD_TERM,
            "feature": Concept.ConceptType.FEATURE,
            "negative": Concept.ConceptType.NEGATIVE,
            "size": Concept.ConceptType.SIZE,
        }
        for code, ctype in concept_defs.items():
            concept, _ = Concept.objects.get_or_create(code=code, defaults={"concept_type": ctype})
            concepts[code] = concept
        return concepts

    def _tokenize(self, term: str) -> Tuple[List[str], List[str]]:
        tokens = [t for t in re.split(r"[\s/+-]+", term.lower()) if t]
        phrases = []
        for i in range(len(tokens) - 1):
            phrases.append(f"{tokens[i]} {tokens[i+1]}")
        for i in range(len(tokens) - 2):
            phrases.append(f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}")
        return tokens, phrases

    def _handle_head(self, kw: Keyword, tokens: List[str], product_type: ProductType, concept: Concept):
        if not any(t in self.HEAD_TERMS for t in tokens):
            return
        ProductTypeMap.objects.update_or_create(
            keyword=kw,
            product_type=product_type,
            defaults={"confidence": Decimal("1.0")},
        )
        KeywordConcept.objects.update_or_create(
            keyword=kw,
            concept=concept,
            defaults={"confidence": Decimal("1.0"), "tagged_by": "rule"},
        )

    def _handle_size(self, matches: List[Tuple[str, str]], kw: Keyword, concept: Concept) -> int:
        if not matches:
            return 0
        sizes = [{"width": int(w), "length": int(l)} for w, l in matches]
        KeywordConcept.objects.update_or_create(
            keyword=kw,
            concept=concept,
            defaults={
                "confidence": Decimal("0.7"),
                "tagged_by": "rule",
                "reason": json.dumps({"sizes": sizes}),
            },
        )
        return 1
