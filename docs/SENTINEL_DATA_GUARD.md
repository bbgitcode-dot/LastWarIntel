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
