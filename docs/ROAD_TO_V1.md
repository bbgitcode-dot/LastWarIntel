# Road to V1 – Sentinel

**Current release:** v0.9.5.125  
**Functional baseline:** v0.9.5.124 Gold Fidelity Engine Phase 1

## V1 principle

Sentinel v1.0.0 must be a trustworthy strategic intelligence platform, not merely an OCR exporter. It must protect Operational Truth, explain uncertainty, and support alliance leadership decisions without silently inventing identities.

The core rule remains:

> Evidence before inference. Inference remains read-only until a safe promotion workflow exists.

## Current position

The acquisition pipeline can now match the 551 benchmark with 50/50 rows, 0 missing rows, 0 bad matches, and 100% recall. The remaining challenge is exact display fidelity and reducing the final Gold Core blockers without weakening DataGuard.

## Milestones to v1.0.0

### v0.9.5.126 – Gold Core Blocker Triage

- Produce a dedicated blocker report for the remaining 15 Gold Core blockers.
- Classify each blocker as local glyph, crop geometry, nonlocal script display, observed-text-confirmed, or manual review.
- Turn noisy but successful `vote_outside_allowed_set` cases into warnings only when the selected glyph equals expected and all core evidence is safe.
- Keep Operational Truth unchanged.

Exit criteria:

```text
50/50 matched
0 bad matches
Gold Core blocker list is explicit and actionable
No context gap enters Character ReOCR
```

### v0.9.5.127 – Local Glyph Resolution Hardening

- Improve local glyph proof for rows such as `Mizzenmast`, `Drpeek`, `S I G I`, and similar Latin-only blockers.
- Add stronger per-target confidence semantics: selected expected glyph vs noisy vote environment.
- Avoid broad identity inference from rank/power/alliance alone.

Exit criteria:

```text
Gold Core blockers reduced without new bad matches
Runtime remains under control on CPU-only validation
```

### v0.9.5.128 – Multilingual Display Policy

- Define what Sentinel can and cannot prove for Hangul, Kana, and CJK display spans.
- Separate Core Identity readiness from Full Display Gold readiness.
- Introduce a clear `script_display_unresolved` class for nonlocal script drift.

Exit criteria:

```text
Mixed-script rows no longer look like generic OCR failures
Core-safe rows are operationally usable while full display remains flagged
```

### v0.9.6 – Data Stability Freeze

- Freeze DataGuard, Ranking Guard, Context Gap, and Operational Truth rules.
- Add regression tests that protect against historical failure modes: N+1 rank inference, row shifts, wrong server, wrong ranking type, and unsafe context matches.

### v0.9.7 – Snapshot and Batch Stability

- Validate dynamic server ranges, especially S6 549–676 transfer bucket.
- Confirm snapshot completeness metrics and active snapshot behavior.
- Ensure exports are snapshot-bound and auditable.

### v0.9.8 – Multi-Server Benchmark

- Expand beyond server 551 to a representative transfer-bucket sample.
- Capture runtime, completeness, review burden, and blocker categories per server.
- Establish acceptance thresholds for production usage.

### v0.9.9 – Release Candidate

- Stabilize UI/reporting output.
- Freeze documentation and operating procedures.
- Run final smoke/regression suite.
- Confirm that new users can run acquisition and validation from docs alone.

### v1.0.0 – Production Ready

Sentinel reaches v1.0.0 when:

- screenshot import is snapshot-bound and auditable;
- DataGuard prevents unsafe truth promotion;
- Ranking Guard prevents row/rank contamination;
- ground truth validation produces explainable reports;
- core identity is stable enough for strategic analysis;
- unresolved display fidelity is explicitly labeled rather than hidden;
- documentation is sufficient for handover to a new chat or developer;
- releases are full ZIP packages with `.commit`, versioning, release notes, and patch summary.

## Non-goals before V1

- No historical player database as a shortcut for OCR identity.
- No blind pre/post transfer identity linking by rank/power/alliance alone.
- No automatic Operational Truth mutation from read-only inference.
- No snippets as release deliverables.
