"""
AI model constants shared across services and serializers.
Kept in a standalone module to avoid circular import chains.
"""

DEFAULT_DESCRIPTION_AI_MODEL = "gpt-4o-mini"

# Allowed models per provider — add new models here.
# The model name prefix determines which SDK is used (see content_generation.py).
DESCRIPTION_AI_MODELS = frozenset({
    # OpenAI
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4o-turbo",
    "gpt-3.5-turbo",
    # Anthropic (claude- prefix → anthropic SDK, needs ANTHROPIC_API_KEY)
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
    "claude-opus-4-6",
    # Google (gemini- prefix → google-generativeai SDK, needs GOOGLE_AI_API_KEY)
    "gemini-2.0-flash",
    "gemini-1.5-pro",
})

# OpenAI-only title models for teams using ChatGPT API only.
OPENAI_TITLE_AI_MODELS = frozenset(sorted([m for m in DESCRIPTION_AI_MODELS if m.startswith("gpt-")]))

DEFAULT_TITLE_POLISH_INSTRUCTIONS = (
    "Write for marketplace SEO and CTR. Keep primary keyword in the first half of the title. "
    "Use natural local phrasing, avoid keyword stuffing, do not invent facts, and respect title length limits."
)

# Mapping task: keyword-to-attribute/product classification.
# gpt-4o-mini is a good default: fast, cheap, handles structured JSON output well.
# For complex product domains consider gpt-4o or claude-sonnet-4-6.
DEFAULT_MAPPING_AI_MODEL = "gpt-4o-mini"

# Reuse the same model whitelist — any provider that works for descriptions
# also works for mapping (same JSON-output structured task pattern).
MAPPING_AI_MODELS = DESCRIPTION_AI_MODELS
