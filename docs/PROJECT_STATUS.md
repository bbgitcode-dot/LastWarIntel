# Project Status – Sentinel v0.9.5.88

**Current baseline:** Sentinel v0.9.5.87 Data Quality Stabilization  
**Current sprint:** v0.9.5.88 Documentation Consolidation & Handoff  
**Canonical docs path:** `/docs`  
**Operating roles:** Mimir = strategic copilot; Proud Owner = product owner and acceptance authority.

## Executive state

Sentinel is in the **Data Quality before Intelligence** phase. The recent sprint line from v0.9.5.73 through v0.9.5.87 moved Sentinel from raw screenshot ingestion toward an auditable Operational Truth pipeline:

1. snapshots define import context and expected feed completeness;
2. OCR creates evidence, not truth;
3. Ranking Guard and Data Guard prevent unsafe rows from entering Operational Truth;
4. Review explains uncertainty without silently mutating truth;
5. v0.9.5.87 made cache opt-in during development and introduced rank-slot preservation for pending review rows.

The next engineering work should continue hardening data integrity. Intelligence expansion remains intentionally paused until ranking identity, rank-slot preservation, and power recovery are reliable.

## What the last sprints tried to achieve

### Snapshot and completeness foundation

The snapshot system was hardened so a collection can represent a real event scope instead of an implicit global 128-server target. Expected evidence is defined as:

```text
Expected Feed = Server × Ranking Type
```

This solved two important product cases:

- small events with only 8 participating servers should not be judged against 128 servers;
- broad transfer/season snapshots can use server ranges like `549-676` without manually entering 128 servers.

### Continuous collection

Normal import runs no longer close a snapshot automatically. This is mandatory for a real system where users may upload screenshots 24/7. Transition to `REVIEWING`, `VERIFIED`, or `LOCKED` must be explicit.

### Review explainability

Review UX was rebuilt around three separate concepts:

```text
OCR Source          = what Sentinel saw
Operational Mapping = what Sentinel thinks it may correspond to
Operational Truth   = accepted/current truth only after guards pass or review resolves
```

This is crucial: a highlighted OCR row is evidence, not automatically a proven rank.

### Recognition quality and power recovery

Runtime telemetry and power-recovery family telemetry were added. The 99-screenshot benchmark over servers 549–554 showed the main families:

- `alliance_high_explosion` such as `77B` / `79B` values;
- `thp_high_explosion` such as `7xxM` values that should be around `1xxM–2xxM`;
- `thp_low_truncation` where values miss one or two trailing digits.

Power recovery now works in some cases, but ambiguous candidate margins still require careful review.

### Cache lesson

The OCR cache produced a large repeat-run speed gain, but it also masked data-quality changes by replaying old OCR evidence. Therefore v0.9.5.87 made cache opt-in during development.

Current rule:

```text
Development / Data Quality Mode: cache OFF
Production / Performance Mode: cache may be explicitly enabled later
```

## Current risks

1. **Rank-slot drift:** quarantined rows must not make later rows move up. Rank 10 pending review must stay rank 10; rank 11 must remain rank 11.
2. **Identity fidelity:** observed display identity must preserve source text such as `[SWSq]` and `Sven the vän`; normalized forms are internal only.
3. **Cache masking:** any benchmark meant to validate recognition logic must run with cache disabled.
4. **Review history debt:** stale open reviews still need lifecycle cleanup so historical review items do not inflate current work.
5. **Promotion thresholds:** near-miss ambiguous cases are tempting to auto-promote but must not be promoted until rank, identity, and context confidence are combined safely.

## Immediate next engineering priorities

### P0 – Validate v0.9.5.87 without cache

Run the 549–554 benchmark with cache disabled and verify:

- no OCR cache hits;
- no rank shifting after quarantines;
- `Sven the vän` / `[SWSq]` display fidelity;
- pending review rows remain in their original rank slots;
- exports and HTML reports agree on rank slots.

### P0 – Rank Slot Preservation hardening

If any quarantined row disappears from the ranked export and later rows are renumbered, fix this before further recognition tuning.

Target behavior:

```text
10  PENDING REVIEW / QUARANTINED
11  next observed row remains 11
12  next observed row remains 12
```

### P0 – Raw observed identity fields

Review and export surfaces should carry:

```text
observed_name
normalized_name
canonical_name
observed_alliance
normalized_alliance
canonical_alliance
```

Only observed fields should be used for human-facing review unless a reviewer chooses a canonical identity.

### P1 – Review History cleanup

Separate:

- current open reviews;
- stale open reviews;
- resolved reviews;
- historical references;
- reopened reviews.

### P1 – Candidate confidence model

Move from power-only confidence to combined confidence:

```text
rank_confidence × identity_confidence × power_confidence × context_confidence
```

Only combined confidence should allow auto-promotion.

## Acceptance philosophy

Sentinel should prefer:

```text
missing / pending / review
```

over:

```text
plausible but false Operational Truth
```

This remains the main product principle until v1.0.0.
