
# Sentinel Data Guard – v0.9.5.95 Addendum

## Targeted Character Verification

Data Guard now distinguishes three cases:

1. **Exact identity** – safe for historical intelligence.
2. **Usable/fuzzy identity** – useful for review context, not definitive truth.
3. **Character verification candidate** – a specific visible character should be re-read from screenshot evidence.

Examples:

```text
Joncollins21 vs Joncollinszl -> verify 2/z and 1/l
PbC vs PBC                  -> verify case-sensitive alliance tag character b/B
DAY vs daY                  -> verify case-sensitive alliance tag characters
```

No automatic correction is performed by this sprint.
