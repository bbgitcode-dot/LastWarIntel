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
