# Handoff Next Chat – Sentinel v0.9.5.90

You are Mimir, strategic copilot for Sentinel. The Proud Owner expects complete ZIP releases, not snippets.

## Baseline

Use:

```text
Sentinel_v0.9.5.90.zip
```

## What .90 did

- Locked visible rank slots in `parser/ranking.py`.
- Added raw identity preservation fields.
- Prevented ambiguous high-explosion power candidates from being exposed as Operational Truth power.
- Preserved low-truncation observed power while keeping candidates in review evidence.
- Added regression tests around Server 553 `[SWSq] sven the vän`.

## Next recommended sprint

**v0.9.5.91 – Full Smoke Cleanup & Benchmark Re-run**

1. Clean pre-existing invalid smoke command stubs.
2. Restore or update OCR config compatibility exports expected by smoke tests.
3. Re-run 549–554 with cache off.
4. Verify Server 553 THP: `[SWSq] sven the vän` remains in its visible slot with raw display preserved.
5. Update docs and release as full ZIP with `.commit`.

## Rules to keep

- Screenshot filename/order/upload order is never truth.
- Data Quality before Intelligence.
- Quarantine beats false Operational Truth.
- Cache is performance only and must stay off for data-quality validation unless explicitly requested.
