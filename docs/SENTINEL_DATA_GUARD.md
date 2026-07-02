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
