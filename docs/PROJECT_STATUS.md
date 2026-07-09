# Project Status – Sentinel v0.9.5.129

**Current release:** v0.9.5.129 Read-only Verification Execution  
**Functional baseline:** v0.9.5.128 Alignment Intelligence Phase I  
**Sprint posture:** evidence execution without truth promotion

## Current state

SENTINEL has moved from eligibility diagnostics to evidence execution for Context Gap rows. v0.9.5.128 identified high-confidence Context Gaps through `alignment_score` and `verification_allowed_read_only`; v0.9.5.129 now executes that lane in report-only mode.

## What changed in v0.9.5.129

Eligible Context Gap rows now receive:

```text
read_only_reocr_executed
read_only_reocr_evidence
read_only_suggested_display
read_only_confidence
read_only_operational_truth_modified = false
```

This means SENTINEL can collect and expose useful evidence from uncertain rows while still refusing to mutate Operational Truth.

## Strategic interpretation

This is an architecture milestone rather than an OCR improvement. The system can now separate three layers:

1. **Observed OCR** – what the parser saw.
2. **Read-only Evidence** – what structural context strongly suggests.
3. **Operational Truth** – what is allowed into trusted data.

The third layer remains locked unless future policy explicitly promotes evidence under strict rules.

## Next recommended sprint

**v0.9.5.130 – Evidence Consumption Policy**

Recommended scope:

1. Define when read-only evidence can become a review recommendation.
2. Keep automatic Operational Truth promotion disabled.
3. Add a separate `review_recommendation_report` or extend `ocr_evidence_report` with clear recommendation status.
4. Preserve DataGuard: evidence can inform humans; it must not silently rewrite truth.

## Hard guardrails

- Operational Truth is never silently changed.
- Read-only inference remains read-only.
- Historical player memory is not an identity shortcut.
- Context Gap evidence is report-only.
- Evidence before inference remains the governing rule.


---

# Project Status – Sentinel v0.9.5.127

**Current release:** v0.9.5.127 Gold Core Resolution Plan  
**Functional baseline:** v0.9.5.126 Gold Core Blocker Triage  
**Sprint posture:** diagnostic-to-execution planning, still guardrail-first

## Current state

The 551 total_hero_power benchmark remains structurally stable:

```text
matched_rows: 50/50
missing_rows: 0
bad_matches: 0
recall: 100%
verified_core_identity_matches: 32
gold_core_blocker_rows: 15
row_integrity_score: 66%
runtime: ~423s validator total, ~223s Character ReOCR target total, CPU-only observed
```

Interpretation: Ranking, Matching, Gap Recovery, DataGuard, and read-only inference are no longer the primary blockers. The remaining V1 risk is Display Fidelity: exact player-name and alliance-tag display proof.

## v0.9.5.127 update

v0.9.5.127 adds a second layer after the blocker report:

```text
gold_core_blocker_report -> gold_core_resolution_plan_report
```

The new plan classifies each Gold Core blocker into a safe execution action:

- `P1_LOCAL_GLYPH_RETRY` – safe screenshot-local Latin glyph refinement candidate;
- `P1_WARNING_DOWNGRADE_SAFE` – candidate only if Core Identity is already proven and glyph evidence is clean;
- `P1_WARNING_DOWNGRADE_BLOCKED_BY_CORE` – noisy vote evidence exists but Core Identity is still not proven;
- `P1_CROP_GEOMETRY_FIRST` – crop/field isolation must be fixed before glyph evidence can be trusted;
- `P1_SPLIT_LOCAL_FROM_SCRIPT` – local Latin proof and nonlocal script display must be separated;
- `P2_SCRIPT_POLICY_REQUIRED` – requires multilingual/script display policy or stronger engine support;
- `P2_MANUAL_BENCHMARK_REVIEW` – observed text was confirmed; do not override without benchmark review;
- `P2_ALIGNMENT_ONLY` – context gaps remain read-only and are not Character ReOCR cases.

## What changed strategically

v0.9.5.126 answered: “What are the 15 blockers?”  
v0.9.5.127 answers: “Which blocker can be attacked safely next, and which must stay blocked?”

This keeps SENTINEL from falling back into generic OCR tuning. The next safe engineering work is now narrowly scoped: local glyph retries and warning-downgrade policy only where the guardrails allow it.

## Next recommended sprint

**v0.9.5.128 – Safe Warning Downgrade & Local Glyph Retry**

Recommended scope:

1. Implement the first actual resolver for `P1_LOCAL_GLYPH_RETRY` rows.
2. Implement a strict warning downgrade only for `P1_WARNING_DOWNGRADE_SAFE` rows.
3. Keep crop-geometry, nonlocal script, observed-text, and context-gap cases blocked.
4. Track blocker reduction without allowing new bad matches.

## Hard guardrails

- Operational Truth is never silently changed.
- Read-only inference remains read-only.
- Historical player memory is not an identity shortcut.
- Context gaps never enter Character ReOCR.
- Evidence before inference remains the governing rule.

## v0.9.5.128 Update – Alignment Intelligence Phase I

Sentinel now records Alignment Intelligence for Context Gap rows. High-confidence contextual inferences can be marked as read-only verification candidates via `alignment_score` and `verification_allowed_read_only`, while Operational Truth remains locked. This prepares the next sprint to collect evidence from uncertain rows without weakening DataGuard.


### Update v0.9.5.130
Sentinel has effectively solved matching, gap recovery and operational identity. Remaining work is concentrated on display fidelity, multilingual character reconstruction and evidence-backed verified display output.


### Update v0.9.5.131

`v0.9.5.131` implements **Display Reconstruction Engine Phase I**. The previous run showed that Ranking Guard, DataGuard, gap recovery and matching are stable, while the remaining quality loss is concentrated in display fidelity: exact player-name and alliance-tag rendering.

The new engine does not try to improve OCR directly. Instead, it consumes already collected Character ReOCR evidence and accepted read-only context-gap evidence to create report-only reconstructed display proposals. This introduces a clean Evidence Layer between raw OCR and any future Gold export.

Current policy remains conservative:

- Operational Truth is not modified.
- Ground Truth is not modified.
- Snapshots are not modified.
- Existing verified display fields are not overwritten.
- Context-gap suggestions remain evidence-only.

Next focus: use the new `display_reconstruction_report` to decide which rows are safe candidates for a future Gold Display export lane and which still require crop geometry or multilingual script policy work.

## v0.9.5.132 Status Update – Display Reconstruction Guard

The `.131` run proved that Display Reconstruction can consume Character ReOCR evidence, but it also exposed the risk of over-aggressive name synthesis. `.132` therefore adds a promotion guard: evidence can still be collected and reported, but reconstructed display names are blocked when the base text is `UNKNOWN`, evidence coverage is too low, unresolved fragments remain, or observed votes conflict with expected glyphs.

This keeps the next phase aligned with DataGuard: Evidence before Inference, read-only reconstruction remains read-only, and Operational Truth is never modified.

## v0.9.5.133 Status Update – Evidence Confidence Engine

Sentinel now separates display reconstruction from evidence confidence. The Display Reconstruction Guard introduced in `.132` prevented unsafe promotion; `.133` makes that decision explainable by scoring the underlying fragments and calculating coverage.

New reports:
- `evidence_confidence_report.json`
- `evidence_confidence_report.xlsx`

Key architectural change:
- Character evidence is no longer treated as flat evidence.
- Each fragment receives a diagnostic confidence score.
- Each display proposal receives name/tag/display coverage metrics.
- Promotion decisions can be tightened by Evidence Confidence but cannot override DataGuard.

Current strategic interpretation:
- Ranking Guard, DataGuard, Gap Recovery and Context Inference remain stable.
- Display Fidelity is now governed by reconstruction + promotion + evidence confidence.
- Remaining blockers should be handled by improving fragment quality and crop geometry, not by weakening promotion rules.

Recommended next sprint:
`v0.9.5.134 – Crop Geometry Optimizer`, focused on improving fragment quality before additional display promotion.


## v0.9.5.134 – Evidence Budget Manager

This release adds a read-only Evidence Budget Manager for Display Fidelity. The new budget layer scores display reconstruction candidates before future expensive ReOCR work is promoted into the active pipeline. It introduces `evidence_priority_score`, `evidence_budget_tier`, `evidence_budget_action`, `evidence_budget_reason`, and the standalone `evidence_budget_report.json/xlsx`.

The sprint does not change Operational Truth, snapshots, exports, Ground Truth, or DataGuard policy. Its purpose is to make future Character ReOCR investment explainable and selective: high-value candidates can receive full budget, medium candidates receive targeted budget, weak evidence is blocked early or served from cache.


## v0.9.5.135 – Evidence Scheduler Phase I

Current focus moved from collecting more display evidence to deciding which evidence is worth expensive Character ReOCR. The new Evidence Scheduler consumes the Evidence Budget fields and produces a read-only execution queue: full ReOCR, targeted ReOCR, limited retry, early exit/cache-only, or context-only evidence.

This prepares the next performance sprint without weakening DataGuard. Operational Truth remains immutable.

## v0.9.5.136 Status – Gold Accuracy Mode

The project direction has been corrected: Gold data accuracy is the primary objective; runtime is secondary. The scheduler is no longer treated as a runtime-saving mechanism during the Gold Fidelity phase. It now orders and explains work while continuing to collect evidence wherever local glyph ReOCR can improve confidence. Operational Truth remains unchanged unless a separate guarded promotion path explicitly permits it.

