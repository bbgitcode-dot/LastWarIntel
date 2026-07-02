# SENTINEL

> Transforming observations into operational truth and explainable strategic intelligence.

**Version:** v0.9.5.51

---

## Why Sentinel exists

Sentinel was never intended to be only an OCR script, spreadsheet exporter, or dashboard.

Sentinel exists to reduce uncertainty for alliance leadership.

```text
Information
    ↓
Observation
    ↓
Operational Truth
    ↓
Knowledge
    ↓
Understanding
    ↓
Action
```

---

## Current doctrine

> False confidence is worse than missing data.

If Sentinel is uncertain, it must not guess. It must recover better evidence, preserve uncertainty, or quarantine the data for review.

---

## Current operational stack

```text
Screenshots
    ↓
OCR Provider
    ↓
Parser + Normalizer
    ↓
Sentinel Data Guard
    ↓
Ranking Guard / Power Sanity Guard
    ↓
Recovery or Quarantine
    ↓
Operational Import Report
    ↓
Command Center
```

---

## Current sprint status

v0.9.5.51 is a recovery decision cutover sprint. It removes the legacy leading-digit decision fallback and requires clear candidate-score margins before automatic recovery.

The next development focus is import session and segment integrity.

