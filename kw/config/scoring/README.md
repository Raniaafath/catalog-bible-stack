# Scoring & confidence policy

Global thresholds and output buckets.

## Intended policy (from design)

- **High (≥ 0.90):** auto-map
- **Medium (0.70–0.89):** review queue
- **Low (< 0.70):** keyword only, no mapping
- Hard fail: intent mismatch, cross-category contamination, impossible dimensions

## Intended contents (when implemented)

- `policies.yaml` or per-environment thresholds
- Links to `human_review_queue` and auto-apply logic

Schema TBD. Add YAML here when ready.
