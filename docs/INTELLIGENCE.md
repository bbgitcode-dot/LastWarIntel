# Sentinel Intelligence Concepts

> **Version:** v0.9.5.24

---

## Purpose

This document defines the shared vocabulary used by Sentinel.

The current v0.9.5.x work is still mostly pre-intelligence work: it creates trusted operational data. This is necessary before strategic assessments can be reliable.

---

## Updated knowledge ladder

```text
Raw Screenshot
    ↓
OCR Observation
    ↓
Parsed Row
    ↓
Data Guard Evidence
    ↓
Operational Truth
    ↓
Snapshot
    ↓
Difference
    ↓
Fact
    ↓
Evidence
    ↓
Strategic Indicator
    ↓
Reasoning
    ↓
Assessment
    ↓
Value
    ↓
Recommendation
```

---

## Operational Truth

Operational Truth is the trusted runtime state after OCR, parsing, Data Guard validation, Quality Loop recovery, and quarantine decisions.

It is not necessarily perfect. It is the best evidence Sentinel can safely use without hiding uncertainty.

---

## Confidence

Confidence describes evidence quality, not randomness.

A low confidence value should trigger one of three outcomes:

1. targeted recovery,
2. quarantine,
3. manual review.

A low confidence value should not trigger guessing.

---

## Quarantine

Quarantine is a safe holding state for data that may be useful but cannot yet be trusted.

Quarantined data should preserve:

- source screenshot,
- OCR output,
- suspected issue,
- confidence,
- Data Guard reason,
- recommended next step.

---

## Next concept: Ranking Guard

The upcoming Ranking Guard is an integrity module that validates whether a row belongs to its assigned ranking type.

It will protect against issues such as:

- THP rows entering Alliance Power rankings,
- Alliance Power rows entering THP rankings,
- invalid value ranges,
- impossible rank continuity,
- missing required ranking fields.
