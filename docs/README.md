# Documentation Index

## Architecture
- **[GROUPING_AND_MARKETPLACE_AXES.md](GROUPING_AND_MARKETPLACE_AXES.md)** — Two-level grouping (catalog vs marketplace) and how variation axes are resolved. **Start here for architecture questions.**
- **[CATALOG_ARCHITECTURE.md](CATALOG_ARCHITECTURE.md)** — Canonical catalog + publishing layer pattern; axis resolution priority; when to use ChannelVariantAxis vs ChannelListingAxis.
- **[ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)** — Import data-flow diagram, ERD, processing flow, axis scoring.

## Title Generation
- **[TITLE_GENERATION_SCRIPT.md](TITLE_GENERATION_SCRIPT.md)** — How head/hook/axis parts are assembled; why "LATE"/"OOTH" suffixes appear; checklist for clean titles.
- **[TITLE_GENERATION_LOGIC.md](TITLE_GENERATION_LOGIC.md)** — End-to-end flow from API to stored title; translation lookup priority; TITLE_STRICT_LOCALE.

## Description Generation
- **[DD_DESCRIPTION_STRUCTURE.md](DD_DESCRIPTION_STRUCTURE.md)** — Recommended structure for per-variant descriptions (parent block, variant delta, user instructions, channel output).

## Import System
- **[TESTING_PRODUCTS.md](TESTING_PRODUCTS.md)** — How to add test products via CSV import; column name auto-detection; grouping behaviour.
- **[START_HERE.md](START_HERE.md)** — Overview of the import workflow with quick links.
- **[QUICK_START.md](QUICK_START.md)** — Step-by-step import tutorial; CSV structure options.
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** — Cheat sheet for import column mapping.
- **[CSV_STRUCTURE_EXAMPLES.md](CSV_STRUCTURE_EXAMPLES.md)** — All CSV format options.
- **[VISUAL_IMPORT_FLOW.md](VISUAL_IMPORT_FLOW.md)** — Step-by-step import diagrams.
- **[WHAT_IMPORT_DOES.md](WHAT_IMPORT_DOES.md)** — Technical details of what the import creates.
- **[FRONTEND_MAPPING_GUIDE.md](FRONTEND_MAPPING_GUIDE.md)** — How to use the attribute mapping UI.
- **[IMPORT_LOGIC_ANALYSIS.md](IMPORT_LOGIC_ANALYSIS.md)** — Import logic internals.

## Keyword Research & Mapping
- **[KEYWORD_MAPPING_GUIDE.md](KEYWORD_MAPPING_GUIDE.md)** — Full pipeline: rules-based vs AI mapping, how they interact, numeric matching rules, size/language filtering, head/hook term extraction with AI reasons.
- **[RESEARCH_QUICK_START.md](RESEARCH_QUICK_START.md)** — Keyword research quick start.
- **[EXTRACTION_FRAMEWORK.md](EXTRACTION_FRAMEWORK.md)** — Keyword extraction framework internals.

## Listing Groups
- **[LISTING_GROUPS_EXPLAINED.md](LISTING_GROUPS_EXPLAINED.md)** — What listing groups are; DB structure; axis resolution; API endpoints.
- **[LISTING_GROUP_WORKFLOW.md](LISTING_GROUP_WORKFLOW.md)** — Current workflow status (create, add variants, set axes, generate titles).
- **[SIMPLE_GROUPING_WORKFLOW.md](SIMPLE_GROUPING_WORKFLOW.md)** — Manual grouping workflow guide.
- **[USER_GUIDE_GROUPING.md](USER_GUIDE_GROUPING.md)** — User-facing grouping guide.

## Attributes
- **[ATTRIBUTE_SCOPING.md](ATTRIBUTE_SCOPING.md)** — Product-level vs variant-level attribute scoping; queries.
- **[ATTRIBUTE_MIGRATION_GUIDE.md](ATTRIBUTE_MIGRATION_GUIDE.md)** — How to migrate attribute values from product-level to variant-level.
- **[ATTRIBUTE_RESEARCH_FEATURES.md](ATTRIBUTE_RESEARCH_FEATURES.md)** — Multi-field attribute search in the mapping UI.
- **[ATTRIBUTE_ONE_DIMENSION.md](ATTRIBUTE_ONE_DIMENSION.md)** — Single-dimension attribute handling.

## API & Development
- **[API_GUIDE.md](API_GUIDE.md)** — All API endpoints, auth, router registrations.
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Docker image, entrypoint behaviour, runtime settings.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Project dependencies and what exists in the repo.
- **[project_overview.md](project_overview.md)** — Evidence-based project overview.
- **[DATABASE_CLEANUP.md](DATABASE_CLEANUP.md)** — `cleanup_database` management command usage.
- **[CHANNEL_VARIANT_AXES.md](CHANNEL_VARIANT_AXES.md)** — Channel-specific variation axes.
- **[FRONTEND_UI_SPECS.md](FRONTEND_UI_SPECS.md)** — Frontend UI specifications.

## Example Files
- **[examples/](examples/)** — Sample CSV files and column mapping examples.
