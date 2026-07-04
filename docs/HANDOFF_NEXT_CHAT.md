# Handoff Next Chat – Sentinel v0.9.5.92

## Baseline

Use:

```text
Sentinel_v0.9.5.92.zip
```

## Current state

v0.9.5.92 follows the isolated Server 551 Ground Truth validation. v0.9.5.91 achieved 50/50 matched rows, 0 missing rows, and 0 bad matches, but exported many correct rows with `rank=None`. v0.9.5.92 adds full-scope rank inference from power order while preserving OCR rank evidence in `visible_rank` / `ocr_rank`.

## Next recommended sprint

**v0.9.5.93 – Alliance Power Merge Stabilization**

Focus:

- Run Server 551 again and compare Ground Truth metrics.
- Run Server 552 Alliance Power as the next targeted benchmark.
- Validate that top Alliance Power ranks no longer drift or export as `None`.
- Keep screenshot-first review discipline.

## Rules

- Screenshot is Ground Truth.
- Cache off for benchmark validation.
- No Intelligence features until DataGuard is stable.
- Do not treat upload order, filename order, or console output as truth.
