# SENTINEL

> **The Philosophy of Sentinel**

**Version:** v0.9.5.25

---

## Why Sentinel exists

Sentinel was never intended to be another OCR project, spreadsheet exporter, or dashboard.

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

## Current philosophy after v0.9.5.23

The last sprints proved a critical rule:

> **False confidence is worse than missing data.**

If Sentinel is uncertain, it must not guess. It must either recover better evidence or quarantine the data for review.

---

## The current integrity doctrine

### Data Guard protects

The Data Guard validates data integrity and explains concerns. As of v0.9.5.25, Ranking Guard is a modular Data Guard component for ranking-type integrity.

It may:

- approve,
- warn,
- block,
- quarantine.

It must not:

- silently merge,
- guess a server,
- guess a ranking type,
- use filename timestamps as truth.

### Data Quality Loop recovers

The Quality Loop tries to improve the source evidence and run OCR again.

It may:

- crop,
- sharpen,
- upscale,
- improve contrast,
- retry field-specific OCR.

It must not:

- invent missing values,
- override Data Guard,
- make strategic conclusions.

### Human review remains final fallback

Review is not failure. Review is the correct outcome when evidence remains insufficient.

---

## Working culture

Sentinel is built by the Proud Owner and Mimir.

- The Proud Owner owns product direction, priorities, and acceptance.
- Mimir acts as strategic copilot, architectural challenger, and patch builder.
- Sprint deliverables are full ZIP packages, not fragments.

See `docs/MODUS_OPERANDI.md`.

---

## One sentence

> **Sentinel transforms observations into trusted, explainable intelligence so humans can make better strategic decisions.**


## v0.9.5.28 – Inference Engine Core

Sentinel now contains a first read-only Inference Layer. The Context Engine derives explainable validation conclusions from trusted neighboring evidence while keeping Operational Truth unchanged. This strengthens the path from guarded observations to strategic intelligence.
