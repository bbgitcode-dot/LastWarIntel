# NEXT CHAT – Sentinel v0.9.5.82 Handover

Baseline: **Sentinel v0.9.5.82 – Recognition Quality Pass**

Use `Sentinel_v0.9.5.82.zip` as the next baseline.

## What changed

- Import reports now include `runtime_breakdown`.
- Import reports now include recognition-quality counters under `recognition_quality`.
- Command Center displays Recognition Quality and Runtime / Screenshot.
- High alliance-power OCR explosions can be auto-promoted only when candidate evidence is very strong and source-local order is consistent.

## Next likely work

Run a small targeted test first, then one full 99-screenshot benchmark when convenient. Compare:

- review item count
- power recovered
- power ambiguous
- runtime per screenshot
- OCR vs report/export time split

If the 77B/79B family still produces unnecessary reviews, tune candidate scoring using the new telemetry rather than changing UI.


## v0.9.5.83 Note

The fast report-rebuild feedback loop is now considered mandatory before expensive screenshot benchmarks. `python main.py --rebuild-reports` must work without OCR and without changing snapshot state. This preserves development velocity while recognition quality is hardened.
