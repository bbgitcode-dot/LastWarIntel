# Road to v1

## Current baseline

**v0.9.5.76 – Recognition Quality & Data Integrity Pass**

## Completed foundation

- Data Guard
- Ranking Guard
- Context-aware Power Recovery
- Persistent Review History
- Snapshot Upload Binding
- Dynamic Snapshot Completeness
- Snapshot Lifecycle and Operational Readiness
- Review Rank Trace / Screenshot Window Awareness

## Remaining before v1

1. Recognition quality calibration
2. Candidate promotion threshold tuning
3. Runtime profiling and OCR performance improvements
4. Final Operational Truth validation pass
5. Intelligence expansion only after recognition quality is stable
## v0.9.5.80 – Continuous Collection Decision

Screenshot import runs are not collection boundaries. A snapshot may remain `COLLECTING` while open reviews exist, because real Sentinel users can upload screenshots continuously. Transition to `REVIEWING` must be explicit. Source-row-only review evidence must never be rendered as a proven visible/global rank.

