# Sentinel Lessons Learned

**Current version:** v0.9.5.72

## 1. Data Quality before Intelligence

Sentinel should not rush into strategic recommendations until data integrity is stable. The platform is only valuable if alliance leadership can trust the underlying data.

## 2. Quarantine is a success state, not a failure

A row moved to review/quarantine is better than a false exported value. The system must prefer visible uncertainty over silent corruption.

## 3. Review must be human-readable

A correct quarantine is not enough. The reviewer needs a plain problem statement, candidate choices, screenshot evidence and a clear reason why Sentinel did not auto-promote.

## 4. Screenshot evidence changes review speed

Review detail became significantly more useful once screenshots were linked, previewed and highlighted at the target rank. Evidence must be close to the decision.

## 5. Dashboards must drill down

Operational Readiness tiles are useful only when they lead directly to the affected details: missing data, pending review, imports or server status.

## 6. Current, historical and benchmark data must not mix

Server 551 benchmark data appearing as current Quality data was misleading. Every UI surface must label and filter its source context.

## 7. Historical import performance matters

A historical import that takes minutes discourages use and creates suspicion. Bulk import and progress output turned the importer from a blocker into a useful tool.

## 8. Review resolution is not truth mutation

A human choice must first become auditable state. Only a future guarded override engine should decide whether it changes exports or Operational Truth.

## 9. Snapshot context is required before scaling uploads

As soon as multiple screenshot batches or users exist, “latest run” is not enough. Screenshots need a named event/phase container such as `S6 pre Transfer`.

## 10. Documentation is part of the product

After many rapid sprints, undocumented architecture becomes operational risk. Consolidated docs, release notes, patch summaries and next-chat handoff are necessary for continuity.


## v0.9.5.73 – Snapshot context must be enforced, not remembered

A human can intend that a screenshot batch belongs to `S6 pre Transfer`, but Sentinel must not rely on that intent being remembered later. The import boundary now requires an active snapshot and writes the binding into import reports, exports and review history. This keeps Current Run evidence phase-aware without turning context into Operational Truth.
