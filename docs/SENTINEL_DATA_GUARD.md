# Sentinel Data Guard

**Current version:** v0.9.5.91

## v0.9.5.91 Addendum – Rank/Window Integrity

The 549–555 benchmark exposed a P0 family where the OCR text could be plausible but Operational Truth became corrupt because rows were merged outside their screenshot-window context. Data Guard now treats rank/window integrity as a first-class protection area.

### New protected failure families

- `rank_context_corruption`: final output no longer matches the screenshot rank context.
- `window_merge_contamination`: rows from one screenshot window displace rows from another window.
- `visible_rank_loss`: no observed visible rank survives into Operational Truth.
- `rank_scope_violation`: rank is incompatible with ranking mode/window context, without banning future Top-300 ranks.
- `duplicate_visible_rank_slot_cross_window_conflict`: same visible rank appears from conflicting windows/identities.
- `quarantine_missing_visible_rank`: a ranked context exists, but the row has no visible rank evidence.

### Current rule

A computed rank may be useful telemetry, but it is not screenshot truth. In a ranked context, visible-rank evidence must anchor Operational Truth; missing or conflicting evidence must be routed to review/diagnostics before intelligence consumes it.

---

## v0.9.5.90 – Export Boundary Is Part of Data Guard

Data Guard protection must survive export. A row that is pending review inside the pipeline must remain visibly pending in Excel and report surfaces. Export code must carry:

```text
pending_review
pending_review_reason
rank_slot_preserved
observed_name / normalized_name / canonical_name
observed_alliance / normalized_alliance / canonical_alliance
```

The observed fields are the human-facing evidence. Normalized fields are matching aids. Canonical fields are accepted identity only after review or trusted mapping.

Any export that drops a pending slot or renumbers subsequent rows creates false Operational Truth and must be treated as a data-quality defect.

# Sentinel Data Guard

## Snapshot lifecycle and Data Guard – v0.9.5.75

Data Guard remains the authority for protecting Operational Truth from bad evidence. Snapshot lifecycle does not override quarantine, ranking integrity checks or human review. Instead, it adds a context gate around the evidence collection phase.

Operational Readiness requires:

- expected feeds defined from Server Scope × Expected Rankings;
- imported/validated feeds matching the expected feed set;
- no missing feed combinations;
- no open reviews;
- Data Guard status without unresolved warnings;
- Ranking Guard without rejected feed evidence.

A snapshot can be `VERIFIED` or `LOCKED`, but downstream Intelligence must still explain which evidence and guard status support its assessment.

---

# Sentinel Data Guard

**Current version:** v0.9.5.72

Sentinel Data Guard is the integrity layer that protects Operational Truth.

## Mission

Prevent false operational data from entering exports, dashboards or strategic decisions.

## Principles

1. Do not guess.
2. Preserve original OCR evidence.
3. Recover only with explainable confidence.
4. Quarantine ambiguity.
5. Let Human Review record decisions without silently mutating truth.
6. Keep current, historical and benchmark contexts separate.

## Current protected areas

- Server assignment.
- Ranking type classification.
- Power sanity and digit explosions.
- Context-aware candidate recovery.
- Review/quarantine routing.
- Current-run vs historical vs benchmark separation.

## Relationship with Human Review

Human Review is not a bypass. It produces auditable resolution evidence. A later Manual Override Engine must decide how resolved reviews may affect exports.

## Relationship with Snapshots

Future Data Guard decisions should be snapshot-aware. A row should be evaluated in the context of its snapshot, source screenshot, ranking feed and expected server coverage.


## Snapshot binding and Data Guard

v0.9.5.73 adds an import-context gate before screenshot OCR. The gate prevents unbound Current Run evidence from entering the workflow. Data Guard remains responsible for server assignment, quarantine and protection of Operational Truth; snapshot binding only answers which named phase the evidence belongs to. If evidence is unbound or bound to a different active snapshot, it must not be interpreted as current operational completeness.

## Snapshot completeness guardrail – v0.9.5.74

Snapshot completeness is part of data integrity. It must be computed from explicit expected evidence, not from a global server count.

The expected evidence unit is:

```text
Feed = Server × Ranking Type
```

The active snapshot defines the server scope:

- `all`: dynamic known-server scope.
- `range`: inclusive server range, for example `549-676`.
- `selected`: explicit small list for special events.

Completeness uses:

```text
imported_valid_feeds / expected_feeds
```

This prevents an 8-server event from being judged against a 128-server season and prevents a 128-server season from being accidentally reduced to two endpoints.


---

## v0.9.5.76 Recognition Quality Note

Review Rank Trace is now part of the data-quality boundary. Review surfaces must not treat technical review IDs or quarantine-row ordinals as Operational Truth ranks. Sentinel carries `visible_rank`, `raw_review_rank`, `screenshot_rank_window`, and `rank_trace_source` so human reviewers see the same rank range that appears in the linked screenshot.
## v0.9.5.80 – Continuous Collection Decision

Screenshot import runs are not collection boundaries. A snapshot may remain `COLLECTING` while open reviews exist, because real Sentinel users can upload screenshots continuously. Transition to `REVIEWING` must be explicit. Source-row-only review evidence must never be rendered as a proven visible/global rank.



## v0.9.5.81 – Review Evidence Model

Reviews now distinguish OCR Source, Operational Mapping, and Operational Truth. Source-row overlays remain useful, but must be labelled as OCR evidence rather than proven ranking facts when global rank mapping is unresolved.

## v0.9.5.88 – Current Data Guard Doctrine

Data Guard is the authority that protects Operational Truth from bad evidence. The current doctrine is:

1. OCR output is evidence, not truth.
2. Screenshot row order is evidence, not truth.
3. Filename/order/upload order is never truth.
4. Snapshot context defines expected evidence.
5. Ranking Guard protects rank type and rank-slot integrity.
6. Quarantine preserves evidence and blocks unsafe truth mutation.
7. Human Review records auditable decisions.
8. Cache is never authority.

### Rank-slot preservation

If a row is unsafe, the row must remain visible as pending/quarantined in its original slot:

```text
10  PENDING REVIEW
11  remains 11
12  remains 12
```

Data Guard must reject any pipeline behavior that removes a quarantined row and renumbers subsequent Operational Truth rows.

### Development mode

During recognition and data-quality validation, all caches should be disabled by default. Recomputed evidence is the only valid basis for judging new recognition logic.
