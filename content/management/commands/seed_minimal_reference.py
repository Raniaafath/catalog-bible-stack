from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import (
    Attribute,
    AttributeValue,
    Product,
    ProductAttributeValue,
    ProductType,
    ProductTypeAttribute,
    ProductVariantAxis,
    Variant,
)
from content.models import AttributeI18n, AttributeValueI18n, Locale
from kw.models import Candidate, Keyword
from pub.models import Channel


def norm(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


class Command(BaseCommand):
    help = "Seed minimal demo catalog + i18n + keywords/candidates for testing title generation."

    @transaction.atomic
    def handle(self, *args, **options):
        # ---- Locale + Channel
        fr, _ = Locale.objects.get_or_create(code="fr-FR", defaults={"name": "Français (France)"})
        de, _ = Locale.objects.get_or_create(code="de-DE", defaults={"name": "Deutsch (Deutschland)"})
        shopify, _ = Channel.objects.get_or_create(code="shopify", defaults={"name": "Shopify"})

        # ---- Attributes
        attr_length, _ = Attribute.objects.get_or_create(code="length_cm", defaults={"data_type": "number", "unit": "cm"})
        attr_width, _ = Attribute.objects.get_or_create(code="width_cm", defaults={"data_type": "number", "unit": "cm"})
        attr_thick, _ = Attribute.objects.get_or_create(code="thickness_cm", defaults={"data_type": "number", "unit": "cm"})
        attr_color, _ = Attribute.objects.get_or_create(code="color", defaults={"data_type": "enum"})
        attr_drain, _ = Attribute.objects.get_or_create(code="drain_position", defaults={"data_type": "enum"})
        attr_material, _ = Attribute.objects.get_or_create(code="material", defaults={"data_type": "enum"})

        # ---- Enum values
        v_white, _ = AttributeValue.objects.get_or_create(attribute=attr_color, code="white")
        v_center, _ = AttributeValue.objects.get_or_create(attribute=attr_drain, code="centered")
        v_offset, _ = AttributeValue.objects.get_or_create(attribute=attr_drain, code="offset")
        v_inox, _ = AttributeValue.objects.get_or_create(attribute=attr_material, code="stainless_steel")

        # ---- i18n labels (attributes)
        def ai18n(a, loc, label):
            AttributeI18n.objects.get_or_create(attribute=a, locale=loc, defaults={"label": label})

        ai18n(attr_length, fr, "Longueur (cm)")
        ai18n(attr_width, fr, "Largeur (cm)")
        ai18n(attr_thick, fr, "Épaisseur (cm)")
        ai18n(attr_color, fr, "Couleur")
        ai18n(attr_drain, fr, "Position bonde")
        ai18n(attr_material, fr, "Matériau")

        ai18n(attr_length, de, "Länge (cm)")
        ai18n(attr_width, de, "Breite (cm)")
        ai18n(attr_thick, de, "Stärke (cm)")
        ai18n(attr_color, de, "Farbe")
        ai18n(attr_drain, de, "Ablaufposition")
        ai18n(attr_material, de, "Material")

        # ---- i18n labels (enum values)
        def vi18n(v, loc, label):
            AttributeValueI18n.objects.get_or_create(attribute_value=v, locale=loc, defaults={"label": label})

        vi18n(v_white, fr, "Blanc")
        vi18n(v_center, fr, "Centrée")
        vi18n(v_offset, fr, "Excentrée")
        vi18n(v_inox, fr, "Acier inox")

        vi18n(v_white, de, "Weiß")
        vi18n(v_center, de, "Zentriert")
        vi18n(v_offset, de, "Versetzt")
        vi18n(v_inox, de, "Edelstahl")

        # ---- Product types
        pt_tray, _ = ProductType.objects.get_or_create(code="receveur_carrelable")
        pt_sink, _ = ProductType.objects.get_or_create(code="plan_vasque_carrelable")
        pt_niche, _ = ProductType.objects.get_or_create(code="niche_inox")

        # ---- Allowed attributes per type (minimal)
        def allow(pt, a, required=False, variant_level=False, filterable=False):
            ProductTypeAttribute.objects.get_or_create(
                product_type=pt,
                attribute=a,
                defaults={"required": required, "variant_level": variant_level, "filterable": filterable},
            )

        for pt in (pt_tray, pt_sink, pt_niche):
            allow(pt, attr_length, variant_level=True, filterable=True)
            allow(pt, attr_width, variant_level=True, filterable=True)
            allow(pt, attr_thick, variant_level=False)
        allow(pt_tray, attr_drain, variant_level=True, filterable=True)
        allow(pt_niche, attr_color, variant_level=False, filterable=True)
        allow(pt_niche, attr_material, variant_level=False, filterable=True)

        # ---- Products + variants (from your sheet)
        # 1) Receveur Flat Board (3 variants)
        tray = Product.objects.get_or_create(
            product_type=pt_tray,
            brand="Marmox",
            model="Flat Board",
        )[0]

        # axes for variants
        ProductVariantAxis.objects.get_or_create(product=tray, attribute=attr_length, defaults={"position": 1})
        ProductVariantAxis.objects.get_or_create(product=tray, attribute=attr_width, defaults={"position": 2})

        def upsert_var(product, sku):
            v, _ = Variant.objects.get_or_create(product=product, sku=sku)
            return v

        v1 = upsert_var(tray, "RC80FLAT")
        v2 = upsert_var(tray, "RC12090FLAT")
        v3 = upsert_var(tray, "RC16090FLAT")

        # thickness is common (product-level)
        ProductAttributeValue.objects.get_or_create(
            product=tray, attribute=attr_thick, defaults={"value_number": 4, "unit": "cm"}
        )

        def set_variant_num(variant, attr, num, unit="cm"):
            ProductAttributeValue.objects.update_or_create(
                variant=variant, attribute=attr,
                defaults={"value_number": num, "unit": unit, "attribute_value": None, "value_text": None, "value_bool": None, "value_json": None},
            )

        def set_variant_enum(variant, attr, enum_value):
            ProductAttributeValue.objects.update_or_create(
                variant=variant, attribute=attr,
                defaults={"attribute_value": enum_value, "value_text": None, "value_number": None, "value_bool": None, "value_json": None, "unit": None},
            )

        set_variant_num(v1, attr_length, 80);  set_variant_num(v1, attr_width, 80);  set_variant_enum(v1, attr_drain, v_center)
        set_variant_num(v2, attr_length, 120); set_variant_num(v2, attr_width, 90);  set_variant_enum(v2, attr_drain, v_offset)
        set_variant_num(v3, attr_length, 160); set_variant_num(v3, attr_width, 90);  set_variant_enum(v3, attr_drain, v_offset)

        # 2) Plan vasque (single variant)
        sink = Product.objects.get_or_create(
            product_type=pt_sink,
            brand="Marmox",
            model="Channel Board",
        )[0]
        vs = upsert_var(sink, "CHANNEL BOARD 80")
        ProductAttributeValue.objects.get_or_create(product=sink, attribute=attr_thick, defaults={"value_number": 10, "unit": "cm"})
        set_variant_num(vs, attr_length, 80); set_variant_num(vs, attr_width, 50)

        # 3) Niche inox blanche (single variant)
        niche = Product.objects.get_or_create(
            product_type=pt_niche,
            brand="Marmox",
            model="Niche design",
        )[0]
        vn = upsert_var(niche, "NICHE3030-SE-9010")
        set_variant_num(vn, attr_length, 30); set_variant_num(vn, attr_width, 30)
        ProductAttributeValue.objects.get_or_create(product=niche, attribute=attr_thick, defaults={"value_number": 9, "unit": "cm"})
        ProductAttributeValue.objects.update_or_create(product=niche, attribute=attr_color, defaults={"attribute_value": v_white})
        ProductAttributeValue.objects.update_or_create(product=niche, attribute=attr_material, defaults={"attribute_value": v_inox})

        # ---- Minimal keywords + approved candidates (so templates can resolve keyword parts)
        def kw(term):
            k, _ = Keyword.objects.get_or_create(locale=de, normalized_term=norm(term), defaults={"term": term})
            return k

        k_tray_head = kw("Duschboard zum Fliesen")
        k_tray_hook = kw("bodengleich")
        k_sink_head = kw("Waschtischplatte zum Fliesen")
        k_niche_head = kw("Edelstahl Wandnische")

        def cand(product, keyword, role, weight):
            Candidate.objects.update_or_create(
                product=product, variant=None, locale=de, channel=shopify, keyword=keyword, role=role,
                defaults={"weight": weight, "status": "approved", "selected_by": "seed", "reason": "demo seed"},
            )

        cand(tray, k_tray_head, "head", 90)
        cand(tray, k_tray_hook, "hook", 60)
        cand(sink, k_sink_head, "head", 80)
        cand(niche, k_niche_head, "head", 80)

        self.stdout.write(self.style.SUCCESS("Seeded demo data: products, variants, i18n, keywords, candidates."))
