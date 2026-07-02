## ADR – Review Resolution Is Audit State Before Truth

### Decision
Manual review resolution is stored in persistent review history, but it does not directly mutate OCR evidence, quarantine state, Operational Truth, or Excel exports.

### Rationale
A human decision is strong evidence, but it still needs a guarded application layer. Separating resolution capture from override application preserves auditability and prevents accidental truth changes.

### Consequence
The Review Center may write `RESOLVED` state, selected candidate/manual values, reviewer, and comments. A future Manual Override Engine must explicitly consume those records before exports can change.

## ADR – Review Center as Human-in-the-Loop Workspace

### Decision
The Review Center becomes the preferred review surface. Legacy static pages such as the Evidence Pack may remain available, but the Command Center should guide users into the integrated Review Center.

### Rationale
Review quality depends on explainability and persistent state, not more dashboard surface area. A single review workspace reduces confusion and prepares the system for future manual resolution.

### Guardrail
The Review Center is report-driven and read-only until manual override semantics are implemented. It must not mutate OCR evidence or Operational Truth.

## ADR – Adaptive Review OCR before final quarantine

**Status:** Accepted in v0.9.5.53

**Context:** After .52, many remaining review rows were not solved by additional power scoring. They required better direct OCR evidence from the questionable visual row.

**Decision:** Add a source-local adaptive OCR pass for review/quarantine rows. Generate row crops and enhanced variants; promote only when the second-pass OCR evidence is strong.

**Consequence:** Review becomes an evidence-improvement stage. Quarantine remains the fallback when enhanced OCR is weak or ambiguous. Filename/order/upload order remain explicitly non-authoritative.


# Sentinel Architectural Decisions

**Version:** v0.9.5.52

---

## ADR-001 – Screenshot order is not truth

**Decision:** Sentinel must not rely on filename order, timestamp order, or upload order as truth.

**Reason:** Production imports may combine screenshots from multiple users, devices, servers, and sessions.

**Consequence:** Ranking reconstruction must use intrinsic evidence: server evidence, ranking type, source-local row shape, ranks, powers, and continuity.

---

## ADR-002 – Ground Truth validates Sentinel but does not power runtime

**Decision:** Ground Truth is development tooling only.

**Reason:** Runtime must work without curated benchmark files.

**Consequence:** Command Center and operational services read runtime repositories and import reports, not Ground Truth outputs.

---

## ADR-003 – Data Guard protects Operational Truth

**Decision:** The Data Guard may validate, warn, quarantine, or block. It may not guess.

**Reason:** Silent repair creates false confidence.

**Consequence:** Uncertain data must either go through recovery or review.

---

## ADR-004 – Ranking Guard validates semantic fit

**Decision:** Ranking Guard checks whether rows belong to their ranking type.

**Reason:** THP rows and Alliance Power rows have different scales, fields, and row shapes.

**Consequence:** Ranking-type contamination is treated as an integrity issue, not a cosmetic parsing issue.

---

## ADR-005 – Recovery must preserve original evidence

**Decision:** Recovered values must retain original value and method metadata.

**Reason:** Recovered data is useful but must remain auditable.

**Consequence:** Exports and reports should preserve fields such as `power_original`, `power_recovered_from`, `power_recovery_method`, and future candidate scores.

---

## ADR-006 – Candidate recovery is required for power digits

**Decision:** Future power recovery should score multiple candidates rather than replacing a single leading digit.

**Reason:** `764M` may recover to `164M`, `224M`, `174M`, or another value depending on context.

**Consequence:** v0.9.5.48 should implement context-aware candidate generation and scoring.


---

## ADR-007 – Legacy power recovery may not decide truth

**Decision:** Leading-digit recovery may generate candidates but may not select a recovered value by itself.

**Reason:** Server 553 showed cases where legacy recovery selected a lower-scored or tied candidate.

**Consequence:** v0.9.5.51 uses the candidate decision engine only. Ambiguous score margins quarantine the row.

## ADR - Stable Review Identity and Navigation Consolidation

Decision: Persistent review history uses stable business identity, not runtime-generated review IDs or report timestamps. The Review Center is the web entry point for human decisions, while static output HTML remains a transitional run-detail surface.

Rationale: Sentinel must support repeated targeted test runs and future multi-source screenshot ingestion without multiplying unresolved reviews. The operator must see one durable issue with updated observations, not one issue per run.

## ADR - v0.9.5.62 Visible Command Center Workflow

### Decision

The Sentinel web UI uses a single visible operator workflow: Command Center -> Imports -> Quality -> Reviews -> Exports. The sidebar and top workflow bar both expose this structure.

### Rationale

The previous implementation had technically valid pages, but the relationship between Command Center, Imports, Quality, Review Dashboard, Review Evidence Pack, and static output pages was not obvious. That made the Review workflow feel disconnected even though the data foundation existed.

### Consequences

- The web app becomes the primary operator surface.
- Static output HTML remains available as latest-run evidence, not as a competing Command Center.
- Review detail is reachable through `/reviews/{history_key}` and can later become the natural place for guarded human resolution.
- CSS and navigation changes must keep new pages visually consistent with the existing Command Center design.

## ADR - v0.9.5.63 Screenshot Evidence Links in Review UI

**Decision:** Review UI mounts and links source screenshots through a dedicated `/screenshots` static route and renders screenshot evidence in Review Detail with open-in-new-tab behavior.

**Reason:** The Review Center exists to let a human compare OCR hypotheses against source evidence. The screenshot is the evidence of record for a review item and must be available without navigating the filesystem manually.

**Guardrails:** URL generation uses `Path(...).name` to avoid path traversal from persisted review data. The link is evidence access only and does not change Data Guard, Ranking Guard, Review History state, exports, or Operational Truth.

## v0.9.5.67 - Current-run readiness is authoritative for Command Center drill-downs

The Command Center Operational Readiness layer uses latest import/review state as its primary scope. Historical SQLite intelligence and benchmark validation are separate scopes and may enrich detail pages, but must not break navigation or be shown as current-run missing data.
