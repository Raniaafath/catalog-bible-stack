from django.test import TestCase

from catalog.models import Attribute, AttributeValue, Product, ProductAttributeValue, ProductType, Variant
from content.models import Locale
from pub.models import Channel, ChannelLocalePolicy, ChannelPolicySet, Template, TemplatePart
from pub.services.title_renderer import (
    TitleApprovalRequired,
    _clamp_suggestion_limits,
    _strip_head_tokens,
    render_title,
    save_generation,
)


class TitlePolicyTests(TestCase):
    def setUp(self):
        self.locale = Locale.objects.create(code="de-DE", name="German")
        self.channel = Channel.objects.create(code="shopify", name="Shopify")
        self.product_type = ProductType.objects.create(code="pt", default_label="Duschtasse")
        self.product = Product.objects.create(product_type=self.product_type, code="p1")
        self.variant = Variant.objects.create(product=self.product, sku="v1")

        self.template = Template.objects.create(
            product_type=self.product_type,
            locale=self.locale,
            channel=self.channel,
            kind=Template.Kind.TITLE,
            status=Template.Status.ACTIVE,
            version=1,
        )
        TemplatePart.objects.create(
            template=self.template,
            position=1,
            part_type=TemplatePart.PartType.HEAD_TERM,
            required=True,
        )

    def test_review_mode_blocks_output_without_approved_selection(self):
        policy_set = ChannelPolicySet.objects.create(channel=self.channel, status=ChannelPolicySet.Status.ACTIVE)
        ChannelLocalePolicy.objects.create(
            policy_set=policy_set,
            locale=self.locale,
            title_mode=ChannelLocalePolicy.TitleMode.REVIEW,
            auto_create_selection=False,
            context="title",
        )
        with self.assertRaises(TitleApprovalRequired):
            save_generation(variant=self.variant, locale=self.locale, channel=self.channel)

    def test_head_sources_order_respected(self):
        policy_set = ChannelPolicySet.objects.create(channel=self.channel, status=ChannelPolicySet.Status.ACTIVE)
        ChannelLocalePolicy.objects.create(
            policy_set=policy_set,
            locale=self.locale,
            title_mode=ChannelLocalePolicy.TitleMode.AUTO,
            context="title",
            rules_json={
                "head_sources_order": ["product_type_fallback", "product_category"],
            },
        )
        attr = Attribute.objects.create(code="product_category", data_type=Attribute.DataType.ENUM)
        value = AttributeValue.objects.create(attribute=attr, code="duschwanne")
        ProductAttributeValue.objects.create(
            product=self.product,
            attribute=attr,
            attribute_value=value,
        )
        result = render_title(
            variant=self.variant,
            locale=self.locale,
            channel=self.channel,
            rules={"head_sources_order": ["product_type_fallback", "product_category"]},
        )
        self.assertEqual(result.head_source, "product_type_fallback")
        self.assertEqual(result.head_text, "Duschtasse")

    def test_strip_head_tokens_handles_hyphen(self):
        hook = _strip_head_tokens("mineralguss duschwanne", "Unterbau-Duschwanne")
        self.assertEqual(hook, "mineralguss")

    def test_suggestion_limits_clamped(self):
        rules = {
            "head_suggestions_default_n": 2,
            "head_suggestions_max_n": 4,
            "hook_suggestions_default_n": 3,
            "hook_suggestions_max_n": 5,
            "suggestions_max_total": 6,
        }
        head, hook = _clamp_suggestion_limits(rules=rules, limit_head=10, limit_hook=10)
        self.assertEqual(head, 4)
        self.assertEqual(hook, 2)
