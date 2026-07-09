# Sentinel Architecture

**Current version:** v0.9.5.137

## Gold Accuracy Architecture

Sentinel is now structured as an evidence-first identity pipeline:

```text
OCR / Raw Export
  ↓
Ranking Guard
  ↓
Data Guard
  ↓
Alignment Intelligence
  ↓
Character ReOCR
  ↓
Character Acquisition Engine
  ↓
Display Reconstruction
  ↓
Evidence Confidence / Promotion Guard
  ↓
Reports / Decision Support
```

## Character Acquisition Engine

The v0.9.5.137 Character Acquisition Engine converts individual Character ReOCR fragments into scored observations and per-position consensus. It produces:

- observation confidence,
- vote consensus,
- crop quality,
- consensus status,
- position heatmap,
- row-level acquisition coverage metrics.

This layer is strictly read-only. It does not mutate Operational Truth, snapshots, exports, Ground Truth, or verified display fields. Its purpose is to increase evidence quality for later Gold-Core blocker elimination.
