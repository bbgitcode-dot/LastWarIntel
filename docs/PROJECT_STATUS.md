# PROJECT STATUS — v0.9.5.160

## Current sprint
Strike XVII adds a read-only Resolution Simulator above Resolution Readiness and Stability Verification. Every open Gold-Core case receives multiple bounded action alternatives scored for expected resolution gain, information gain, risk, effort, and utility.

## Safety position
The simulator performs no OCR, crop, vote, policy, binding, clearance, or Operational Truth action. Recommendations are diagnostic decision support only. Evidence before Inference remains mandatory.

## Next validation
Run the benchmark and confirm full case coverage, multiple alternatives per case, exactly one recommendation per case, plausible lane-specific rankings, zero automatic fixes, zero Gold clearances, and unchanged core metrics.

# Current release: v0.9.5.159

Strike XVI operationalizes the v0.9.5.158 fingerprints as persistent cross-run history. Sentinel now retains an idempotent decision timeline per Gold-Core case and attributes classification, decision, confidence, and evidence-coverage drift. Unexplained drift is a release-blocking diagnostic failure; the layer remains read-only and cannot alter Operational Truth or clear Gold Core.

## Immediate benchmark objective

Run the same benchmark repeatedly with the same output directory or preserved `decision_history_state.json`. The expected result is `STABLE` for every unchanged case, with zero unexplained drift. Rank 11 must remain traceable across runs and may only change classification when its evidence fingerprint changes.

# Project Status

## v0.9.5.150 — Position-Bound Evidence Provenance

The Gold-Core phase remains focused on eliminating the final blockers without reducing Gold Fidelity. v0.9.5.149 established which character positions block exact name proof. v0.9.5.150 now establishes where each position loses evidence in the processing chain.

For every blocked position Sentinel can distinguish the first failed stage among character acquisition, crop geometry, OCR observation, vote resolution, and evidence reconstruction. The downstream Promotion Guard remains visible as the final consumer of incomplete proof, not as the assumed root cause.

The sprint is diagnostic only. Benchmark truth must determine whether the dominant next lane is crop repair, targeted acquisition, vote evidence, or conflict resolution.


**Release type:** Documentation consolidation after the v0.9.5.147 benchmark.

## Current truth

- Recall: 100%.
- Missing: 0.
- Bad Matches: 0.
- Operational Truth modified: no.
- Gold Core: 15 before elimination, 14 after elimination.
- `.147` Evidence Reconstruction eliminations: 0.
- Remaining `vote_warning_gate_review`: 5 of 5.

## Assessment

Gold Core Zero III was safe but ineffective against its intended target. It proved that evidence-bound reconstruction can preserve all stop signs, but the current screenshot evidence does not provide complete positional coverage for any target case. The dominant remaining blocker is still `name_exact`; this is now an evidence-acquisition problem, not a justification to weaken the guard.

## Open technical risks

- incomplete per-position name evidence;
- crop contamination and field bleed;
- unresolved or conflicting vote fragments;
- multilingual display policy;
- UNKNOWN rows without a trustworthy base string;
- one separate power-proof failure at rank 39.

## Next elimination strategy

The next code sprint should acquire missing current-screenshot character evidence for the five vote-warning cases, position by position. It must not infer missing characters from Ground Truth, historical identity, or expected strings. Exact reconstruction is acceptable only at 100% evidence coverage with no conflicts, field mismatch, unresolved votes, or UNKNOWN base.

---

# v0.9.5.142 – Gold Core Strike III

## Functional changes

- Adds a conservative Strike III validator gate for one or two Latin substitutions that belong exclusively to known OCR glyph-confusion families.
- Requires accepted same-snapshot identity matching, exact power anchor, proven Core Alliance, Promotion Guard eligibility, zero unresolved fragments, zero observed votes, and confirmed character evidence for every changed position.
- Blocks identity guessing, arbitrary fuzzy substitutions, insertion/deletion shapes, context-gap inference and unstable Character Position Intelligence states.
- Preserves Operational Truth, Ground Truth, snapshots and exports unchanged.
- Adds dedicated Strike III smoke regressions while retaining Strike I/II coverage.

## Validation

- Targeted Gold-Core regression suite: 12 passed.
- The legacy full smoke suite is not clean in the supplied .141 baseline because it contains two shell-command files saved as Python tests and obsolete OCR configuration imports. These pre-existing collection defects were not masked or rewritten in this sprint.

# v0.9.5.141 – Character Position Intelligence Phase I

- Implements functional Character Position Intelligence in the validator, not just report scaffolding.
- Adds `character_position_intelligence_report.json/xlsx` with position-level risk, action, and rank-level acquisition focus.
- Feeds weak/critical position decisions into the Evidence Scheduler so Gold Accuracy prioritizes problematic character positions.
- Keeps Display Reconstruction, Strike clearance, Context Gaps, and Operational Truth read-only.
- Report phase label: `v0.9.5.141_character_position_intelligence`.

# v0.9.5.140 – Gold Regression & Strike II

- Adds permanent GC-001 Joncollins21 Gold-Core regression metadata.
- Extends Gold-Core elimination with Strike II: one missing Latin glyph plus optional known local glyph confusion, only when Rank/Power/Core Alliance anchors are proven.
- Keeps context gaps read-only and never modifies Operational Truth.
- Report phase label: `v0.9.5.140_gold_regression_strike_ii`.

# Project Status – Sentinel v0.9.5.140

**Current release:** v0.9.5.141 Gold Core Elimination Phase I  
**Functional baseline:** v0.9.5.136 Gold Accuracy Mode  
**Sprint posture:** Gold Accuracy / evidence acquisition over runtime optimization

## Current assessment

Sentinel's structural identity pipeline is stable: Ranking Guard, Data Guard, Gap Recovery, Alignment Intelligence, Display Reconstruction, Promotion Guard and the Evidence Scheduler are mature enough that the next quality gains come from better character evidence acquisition, not more global scheduling or promotion logic.

## What v0.9.5.140 adds

- Gold Core Elimination Phase I.
- `character_acquisition_report.json/xlsx`.
- Per-observation confidence from OCR confidence, vote consensus, crop quality and target status.
- Per-position character consensus across observations.
- Character position heatmap for recurring weak glyph positions.
- Read-only detail metrics: acquisition positions, verified/probable/unresolved positions and average acquisition confidence.

## Guardrails

- Operational Truth remains locked.
- Ground Truth is not modified.
- Snapshot/export values are not silently changed.
- Character Acquisition produces evidence only; promotion remains controlled by Display Reconstruction Guard and Promotion Guard.

## Next recommended sprint

`v0.9.5.140 – Multi-Crop Consensus` should use the new acquisition report to gather richer observations per weak character position. The objective is to improve the 15 remaining Gold-Core blockers by increasing character evidence quality rather than adding new decision gates.


## v0.9.5.140 Functional Outcome

The sprint moves from diagnostics to functional Gold-Core elimination. Sentinel now has an evidence-only gate that can reduce Gold Core blockers when display reconstruction is strong enough to prove Core Identity. The gate updates benchmark validation status only; it does not write to snapshots, exports, Ground Truth, or Operational Truth.

Next work: run Server 551 regression and inspect `gold_core_elimination_report.*` to verify how many of the 15 blockers are actually cleared.

## v0.9.5.140 – Gold Blocker Strike I

This release turns Gold-Core elimination from classification into a first targeted strike. It adds a narrow validator-side clearance path for localized Latin single-glyph blockers when every other identity anchor is already proven: non-context row, power match, core alliance proof, promotion eligibility, non-blocked evidence confidence, and one-character Latin display drift. Operational Truth remains unchanged; the clearance only affects benchmark evidence status and is fully reported.

Key changes:
- Added `clear_gold_core_blocker_strike_i` action.
- Added single-glyph Latin blocker clearance guard.
- Updated Gold-Core elimination phase labels to `v0.9.5.140_gold_blocker_strike_i`.
- Preserved context-gap read-only policy and DataGuard protections.

## Previous sprint: v0.9.5.143 – Gold Core Strike IV

The Gold Core phase now includes read-only root-cause analytics and persistent failure memory. The next benchmark run on server 551 should be used to measure the remaining blocker distribution and select the highest-impact path toward Gold Core Zero.

## v0.9.5.144 status – Gold Core Strike V

Gold Core Root Cause Truth is consolidated. Established blocker classification now leads
analytics, and every case can be traced through one stable case ID, Failure Memory,
prioritized recommendation, and cross-report explorer. The next phase is targeted
Gold Core elimination based on the generated action plan, not further analytics scaffolding.

## v0.9.5.145 Status — Gold Core Zero I

Gold Core knowledge consolidation is complete enough to begin targeted elimination. The first elimination lane is Vote Selection Policy. `.145` introduces a narrow, deterministic warning downgrade for expected-only vote noise. It does not relax crop, identity, script, or counterevidence safeguards. The next benchmark determines the actual blocker reduction and which remaining root-cause lane should be addressed next.


## v0.9.5.146 Status — Gold Core Zero II

The Promotion Guard is no longer an opaque terminal reason. Sentinel now records every individual guard condition and identifies the first active blocker per Gold Case. A conservative rationalization path can clear only authoritative vote-warning cases where low coverage is the sole legacy blocker and all current-snapshot identity evidence is otherwise complete. The next benchmark must measure both blocker reduction and the distribution of `promotion_guard_primary_blocker` across remaining cases.

## v0.9.5.147 Status — Gold Core Zero III

The validator can now prove a complete name without requiring raw OCR exactness. Proof is position-bound and current-snapshot-only. The next benchmark must determine which vote-warning cases reach 100 percent evidence coverage; partial and UNKNOWN cases are expected to remain blocked.

## v0.9.5.149 — Position-Bound Evidence Intelligence

The current implementation sprint adds Gold-Core-specific observability at character-position level. Each remaining blocker now exposes confirmed, missing, unresolved, and conflicting positions together with screenshot and crop provenance. This sprint intentionally performs no clearance. Its purpose is to make the next evidence-acquisition change measurable and case-specific.

## v0.9.5.151 — Position Evidence Acquisition Bridge

The current Gold-Core phase now distinguishes missing evidence from existing but unbound, ambiguous, conflicting, or unsafe evidence. The bridge is diagnostic-only and establishes no new clearance. Separator handling and authoritative Root Cause metadata propagation are now explicit. The next benchmark must measure how many of the prior 38 acquisition failures are reclassified into actionable binding states.

## v0.9.5.152 – Source-Bound Display Reconstruction

Display Reconstruction now preserves a read-only provenance object per character. Base OCR characters retain screenshot/source-row and character-offset provenance; crop-bound Character ReOCR evidence retains its stronger crop chain. These links improve explainability and acquisition diagnostics but never become Gold-authoritative by themselves. Authoritative Gold-Core root-cause metadata is joined through the blocker report rather than the generic validation match status.


## v0.9.5.153 – Provenance-Aware Character Alignment

Sentinel now carries source provenance through explicit edit operations rather than assuming identical character indices. Exact matches and evidenced separator gaps may remain bridgeable; substitutions are counterevidence, deletions remain missing evidence, insertions remain unbound source observations, and ambiguous/UNKNOWN cases remain blocked. This layer is diagnostic and cannot modify Operational Truth or create Gold clearance.

## Update v0.9.5.155 – Identity Composition

Sentinel now models Gold Core identity blockers above the character level. The Identity Composition Engine assigns observed components to diagnostic slots, aggregates confidence, carries provenance to screenshots and OCR observations, and produces a prioritized manual review queue. This is an explainability and review-orchestration milestone, not a Gold clearance sprint. The remaining Gold Core reduction work must now target the actual acquisition/policy lanes identified by the queue rather than add further generic identity infrastructure.

## Update v0.9.5.156 – Gold-Core-Bound Review Orchestration

The Identity Composition layer is now operationally connected to the authoritative Gold Core. Manual Review Queue entries no longer inherit generic match metadata. Queue coverage, case binding, metadata completeness, action mapping, confidence calibration, and zero-clearance safety are validated explicitly. The next benchmark must confirm 14 open Gold-Core cases, 14 queue entries, 100% binding, zero `matched` failure classes, and differentiated review actions.

## v0.9.5.158 — Classification Stability established

Strike XV protects Gold-Core diagnosis from silent cross-run drift. Each open case now carries deterministic evidence, classification, and decision fingerprints. The validator persists a comparison state, reports unexplained changes as CRITICAL, calculates evidence coverage against action-specific requirements, and exposes score-factor decompositions and qualitative labels. Resolution execution remains out of scope until stability history is proven across repeated identical benchmark runs.

## Current Sprint — v0.9.5.161

Reporting Architecture Consolidation is implemented. Sentinel now treats benchmark folders as input/runtime territory and publishes consolidated outputs beneath the root `/reports` tree. Stability history remains durable through state migration. Resolution simulation now distinguishes primary strategy from prerequisite action.
