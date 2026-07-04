# Next Chat – Sentinel v0.9.5.88

Baseline for next chat:

```text
Sentinel_v0.9.5.88.zip
```

Read `docs/HANDOFF_NEXT_CHAT.md` first. It contains the full copy/paste bootstrap prompt.

## Recommended next sprint

**v0.9.5.89 – Non-cache Data Quality Validation & Rank Slot Regression**

Immediate validation target:

```bash
python main.py
```

with cache disabled by default.

Verify:

- no OCR cache hits unless `--ocr-cache` is explicitly passed;
- rank slots are preserved when rows are quarantined;
- `[SWSq] Sven the vän` remains raw/observed in review surfaces;
- pending review rows do not renumber later ranks;
- Excel, Command Center, Review Dashboard and Evidence Pack agree.

## Do not do next

Do not restart performance optimization until data-quality validation passes without cache.
