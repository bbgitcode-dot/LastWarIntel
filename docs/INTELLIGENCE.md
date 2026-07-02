# Sentinel Intelligence Concepts

**Version:** v0.9.5.51

---

## Current position

The current v0.9.5.x work is still mostly pre-intelligence work. It creates trusted operational data. Strategic intelligence must wait until data stability is strong enough.

---

## Knowledge ladder

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

Operational Truth is the trusted runtime state after OCR, parsing, Data Guard validation, Ranking Guard validation, recovery, and quarantine decisions.

It is not necessarily perfect. It is the best evidence Sentinel can safely use without hiding uncertainty.

---

## Confidence

Confidence describes evidence quality, not randomness.

Low confidence should trigger one of:

1. targeted recovery,
2. quarantine,
3. manual review.

Low confidence must not trigger guessing.

---

## Recovered data

Recovered rows are not the same as clean rows. They must preserve original evidence, recovery method, and confidence.

Future intelligence modules must be able to distinguish:

- clean trusted observations,
- recovered trusted observations,
- reviewed observations,
- quarantined observations.

