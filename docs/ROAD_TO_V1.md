# Road to Sentinel v1.0.0

## v1 definition

Sentinel v1.0.0 is not just a working OCR importer. It is an explainable strategic intelligence platform that can turn screenshot evidence into trustworthy Operational Truth and then into decision support for Last War alliance leadership.

The v1 bar is:

```text
Correct data first.
Explainable uncertainty second.
Strategic intelligence third.
Performance last.
```

## Current baseline

**Current development baseline:** v0.9.5.87  
**Current documentation release:** v0.9.5.88

The project is in the final data-stability phase before broader intelligence expansion.

## Milestone 1 – Data Quality Stabilization

Status: in progress.

Goals:

- OCR cache disabled by default in development.
- Screenshot evidence always recomputed during recognition validation.
- Rank-slot preservation for quarantined rows.
- Raw observed identity preserved separately from normalized/canonical identity.
- Review does not silently mutate Operational Truth.
- All import reports, HTML reports and Excel exports agree on rank slots.

Exit criteria:

- 549–554 benchmark can run without cache and without rank drift.
- Known regression case `[SWSq] Sven the vän` remains at the correct visible rank.
- Quarantined rows remain visible as pending slots.
- Critical Data Guard count remains zero.

## Milestone 2 – Review Lifecycle & History Hygiene

Goals:

- Current reviews, stale reviews, resolved reviews and historical reviews are clearly separated.
- Review IDs remain globally monotonic and stable.
- Resolved reviews are auditable and do not reappear as new current work unless reopened.
- Review History can be used as evidence, not as noise.

Exit criteria:

- Current review count reflects only current unresolved issues.
- Stale open reviews are either archived/historical or reopened with explicit reason.
- Evidence Pack and Review Dashboard show the same current review set.

## Milestone 3 – Recognition Confidence Model

Goals:

- Replace power-only promotion with combined confidence:

```text
rank confidence
identity confidence
power confidence
context confidence
```

- Promote only when all required dimensions are strong.
- Quarantine near-miss candidates when identity or rank confidence is weak.

Exit criteria:

- Ambiguous reviews reduce without false promotions.
- Each auto-promotion has an explainable trace.
- Candidate scoring is regression-tested by family:
  - alliance high explosion;
  - THP high explosion;
  - low truncation;
  - rank/row ambiguity.

## Milestone 4 – Ground Truth Regression Suite

Goals:

- Convert known 549–554 cases into durable regression fixtures.
- Include positive and negative cases.
- Make small targeted tests the first validation step before expensive 99-screenshot runs.

Required fixtures:

- `[SWSq] Sven the vän` display fidelity and rank-slot preservation.
- 77B/79B alliance power explosions.
- 7xxM THP high explosions.
- low-truncated THP values.
- source-row-only review evidence.
- Unicode and diacritics.

Exit criteria:

- Any future change that breaks these cases fails smoke/regression tests.

## Milestone 5 – Production Cache Reintroduction

Cache returns only after data quality is stable.

Goals:

- Cache key includes engine version and OCR/identity/recovery version.
- Production cache output must be bit-identical to development mode output.
- Cache never becomes an authority.

Exit criteria:

- Same screenshot set with cache off and cache on produces identical Operational Truth, reviews and exports.
- Cache only changes runtime.

## Milestone 6 – Operational Readiness & Snapshot Verification

Goals:

- Snapshot completeness accurately reflects expected feeds.
- Verified/locked snapshots become trusted evidence sets.
- Missing feeds and review debt block readiness.

Exit criteria:

- A snapshot can be moved from collecting to verified only with explicit readiness gates satisfied.
- Readiness is explainable in Command Center.

## Milestone 7 – Strategic Intelligence Expansion

Only after data stability.

Goals:

- Server power posture assessments.
- Alliance mobility and transfer-surge support.
- Recruitment and threat intelligence.
- Comparative server profiles.
- Decision support for alliance leadership.

Exit criteria:

- Strategic assessments cite Operational Truth, review state and Data Guard status.
- Intelligence never hides data uncertainty.

## v1.0.0 Release Candidate Gate

Sentinel can approach v1.0.0 when:

- Operational Truth is stable and auditable.
- Review lifecycle is clean.
- Benchmarks are repeatable.
- Cache is proven output-equivalent or disabled.
- Documentation reflects the real system.
- Every release is delivered as a full ZIP with commit and tag commands.
