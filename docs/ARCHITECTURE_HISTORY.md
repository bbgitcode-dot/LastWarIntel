# Architecture History – Sentinel

## Phase 1 – OCR export orientation

The early system focused on reading screenshots and producing structured exports. This was necessary but not sufficient: OCR could produce plausible but unsafe data.

## Phase 2 – Data Quality and DataGuard

The project introduced DataGuard to prevent unsafe data from becoming Operational Truth. This shifted Sentinel from extraction to guarded evidence handling.

## Phase 3 – Ranking Guard and quarantine

Ranking/rank-order failures proved more dangerous than normal OCR mistakes. Ranking Guard was introduced to block unsafe row fallback and quarantine ambiguous cases.

## Phase 4 – Ground Truth validation

Server 551 became the benchmark for controlled validation. The validator established measurable accuracy, recall, identity fidelity, and failure classes.

## Phase 5 – Character ReOCR

The team added targeted glyph-level ReOCR for exact display fidelity. This solved local cases like `Joncollins21`, but broad use was too expensive and noisy.

## Phase 6 – Evidence Inspector

The Evidence Inspector introduced row-level proof categories and fragment provenance. This made failures explainable: crop issue, context gap, unresolved glyph, observed-text confirmation, or policy skip.

## Phase 7 – Gold Fidelity Engine Phase 1

v0.9.5.124 introduced snapshot-local evidence caching to avoid repeated CPU-heavy ReOCR for identical glyph claims. It preserved DataGuard by marking cached evidence explicitly and keeping it within one validation run.

## Current direction

The project is moving toward a full Evidence Engine: fewer blind OCR attempts, more confidence management, stricter blocker classification, and safer promotion boundaries.
