# Architectural Decisions – Sentinel

This document summarizes active architectural decisions. Detailed ADR files remain under `docs/ADR/`.

## Current active decisions

### AD-001: Evidence-first pipeline

Sentinel treats OCR as evidence, not truth. Every later step must preserve provenance and uncertainty.

### AD-002: Operational Truth protection

Operational Truth may not be silently mutated by OCR, validation, or inference. Unsafe rows are quarantined or marked for review.

### AD-003: Ranking Guard before identity confidence

Rank and row safety come before identity repair. A plausible name on the wrong row is dangerous.

### AD-004: Read-only contextual inference

Inference can explain bounded gaps and accept them for validation context, but it remains read-only.

### AD-005: Character ReOCR is local glyph proof

Character ReOCR is for local character ambiguities and case-sensitive tags. It is not a general solution for broad name reconstruction or multilingual replacement spans.

### AD-006: No historical identity shortcut before V1

Sentinel must support first-contact screenshots across the 549–676 transfer bucket and eventually 2000+ servers. It must not depend on a historical player database to identify names.

### AD-007: Evidence cache scope is snapshot-local

The v0.9.5.124 cache reuses exact glyph evidence only inside one validation run. It is not cross-snapshot identity memory.

### AD-008: Core Identity and Display Fidelity are separate

A row can be operationally safe while not full-display Gold-ready. Reports must show this distinction.

## ADR maintenance note

Some historical ADR numbers are duplicated in `docs/ADR/`. They are retained for historical continuity. Future ADRs should use the next unused number and a unique slug.
