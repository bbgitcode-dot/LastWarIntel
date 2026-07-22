# Benchmark Analysis — Sentinel v0.9.5.147

Benchmark timestamp: 2026-07-22
Validation scope: Server 551, `total_hero_power`, 50 Ground-Truth rows.

## Executive Summary

v0.9.5.147 is safe but did not achieve its intended primary objective. Evidence-Bound Name Reconstruction did not eliminate any of the five `vote_warning_gate_review` cases. Gold Core decreased from 15 pre-elimination cases to 14 only because the pre-existing Strike-I lane cleared rank 47 (`Sc4rfac3` / `Scyrfac3`).

Evidence Reconstruction produced no `EVIDENCE_RECONSTRUCTED_EXACT` result among the 15 evaluated Gold-Core candidates. Every reconstruction remained partial, conflicting, or insufficient. The circular dependency is therefore not removed in practice: the Promotion Guard still sees `name_exact` as the primary blocker in 13 of 14 remaining cases.

Safety remained intact: Recall 100%, Missing 0, Bad Matches 0, Operational Truth unchanged, and the UNKNOWN base at rank 8 was not completed.

## Core Metrics

| Metric | Result |
|---|---:|
| Ground Truth rows | 50 |
| Matched rows | 50 |
| Recall | 100% |
| Missing | 0 |
| Bad Matches | 0 |
| Inference accepted | 3 / 3 |
| Gold Core before elimination | 15 |
| Gold Core after elimination | 14 |
| Net reduction | 1 |
| `vote_warning_gate_review` before | 5 |
| `vote_warning_gate_review` after | 5 |
| Evidence-reconstructed exact names | 0 |
| Operational Truth modified | No |

## Root Cause Distribution After Elimination

| Failure class | Cases | Fix lane |
|---|---:|---|
| `vote_warning_gate_review` | 5 | `safe_warning_downgrade_candidate` |
| `crop_geometry_problem` | 3 | `crop_geometry` |
| `observed_text_confirmed` | 3 | `manual_or_policy` |
| `policy_nonlocal_script_display` | 1 | `policy_or_engine` |
| `local_glyph_solvable` | 1 | `glyph_crop_refinement` |
| `mixed_local_and_nonlocal_blocker` | 1 | `split_policy` |

## Promotion Guard

The Promotion Guard remains the immediate blocking layer. Primary blockers among the 14 remaining cases:

- `name_exact`: 13 cases.
- `power_proven`: 1 case (rank 39), with name evidence also incomplete.

The five vote-warning cases were not cleared because reconstruction never supplied complete position coverage. Their remaining blockers are not a single low-coverage flag; they include incomplete name evidence, missing position coverage, unresolved votes, counterevidence, crop-field mismatch, or absence of expected-only consensus depending on the case.

## Evidence Reconstruction

The implementation respected its safety contract:

- no Ground-Truth fill was used;
- UNKNOWN was not silently completed;
- partial evidence stayed partial;
- conflicting evidence stayed conflicting;
- crop mismatch and unresolved fragments remained stop signs.

However, the benchmark proves that the available evidence was insufficient to reconstruct any exact name. Coverage ranged from 0.0 to 0.875 among the remaining cases. Rank 47 also remained only 0.875 reconstructed and was cleared by the older single-Latin-glyph Strike-I rule, not by Evidence Reconstruction.

## Remaining Cases

| Rank | Expected | Observed / Verified | Proof status | Coverage | Main blocking facts |
|---:|---|---|---|---:|---|
| 2 | `MEITTü メ 메잇` | `MEITTi X 叫@1` | Partial | 0.6364 | nonlocal script policy; 4 unresolved positions |
| 8 | `GD VIP 지디` | `UNKNOWN` | Partial | 0.2222 | UNKNOWN base protected; 7 unresolved positions |
| 11 | `Drpeek` | `Ieek` | Partial | 0.6667 | 2 unresolved positions |
| 19 | `S I G I` | `5161 四咆#电` | Partial | 0.4286 | unresolved fragments; mixed local/nonlocal |
| 20 | `N E R D` | `NER0` | Partial | 0.4286 | unresolved votes; local glyph lane |
| 23 | `이도Ido` | `0/5Ido` | Conflicting | 0.6000 | observed counterevidence |
| 36 | `시로시로 Mio` | `UNKNOWN` | Insufficient | 0.0000 | no usable name evidence |
| 39 | `Beast 짐승` | `Beast 召合` | Partial | 0.7500 | power not proven; crop/field mismatch; unresolved votes |
| 41 | `JDubbz04` | `JQubbzoy` | Partial | 0.6250 | crop mismatch; 3 unresolved positions |
| 42 | `P8n` | `pgn 02硇8_` | Conflicting | 0.3333 | observed counterevidence |
| 43 | `Códy` | `四85 Cody` | Conflicting | 0.7500 | observed counterevidence |
| 45 | `Pitbullx2` | `Pibullxz` | Partial | 0.7778 | crop mismatch; unresolved votes |
| 48 | `쓸모 없는 Draco` | `笞 & Iac` | Partial | 0.4545 | 6 unresolved positions |
| 50 | `JOK3R x 또깡` | `JDK3 X 虫` | Partial | 0.7000 | 3 unresolved positions |

Resolved during the run: rank 47, `Sc4rfac3` / `Scyrfac3`, through `clear_gold_core_blocker_strike_i`. This is not evidence that `.147` reconstruction worked.

## Recommendation for v0.9.5.149

Do not relax `name_exact`, UNKNOWN protection, counterevidence, or crop-field guards. The next implementation sprint should target evidence acquisition completeness rather than another policy bypass.

Recommended order:

1. Isolate the five `vote_warning_gate_review` cases and report the exact missing character positions and evidence sources per case.
2. Add position-targeted crop acquisition for those missing positions only.
3. Separate crop-field contamination from true glyph uncertainty before voting.
4. Re-run reconstruction only when every position has current-screenshot evidence.
5. Keep conflicting or UNKNOWN cases blocked.
6. Treat rank 39 separately because `power_proven` is the primary blocker.

Acceptance requires a measurable reduction in the five vote-warning cases caused specifically by `EVIDENCE_RECONSTRUCTED_EXACT`, with Recall 100%, Missing 0, Bad Matches 0, and Operational Truth unchanged.
