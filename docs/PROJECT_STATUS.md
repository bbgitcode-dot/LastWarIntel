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
