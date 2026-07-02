## v0.9.5.61 Lesson – Resolving a review is not the same as changing truth

Human review decisions must first become auditable state. They should not immediately rewrite OCR evidence, quarantine rows, or Excel exports. This separation keeps Data Guard in control and prevents a reviewer click from silently becoming Operational Truth.

The safe path is staged:

1. Explain the problem.
2. Store the human decision with evidence and comment.
3. Keep the review history durable.
4. Let a future guarded override engine decide whether and how to apply the decision to exports.

This makes human-in-the-loop review useful without weakening Sentinel's core principle: quarantine is safer than false truth.

## v0.9.5.59 – Review UX & Explainability

- A correct quarantine is only useful if a human can understand it quickly.
- Review pages should say explicitly what is uncertain: power, alliance power, server assignment, rank, row, or name.
- Human review needs candidate choices and a clear "why not auto-promoted" explanation, not just internal guard labels.
- Review history is not merely a report artifact; it is the beginning of a persistent workflow state.
- Review UI must remain report-driven and read-only until manual override semantics are fully defined.

# Lessons Learned – v0.9.5.58

A review card must point the human directly at the uncertainty. Technical traces are necessary, but not sufficient. The reviewer needs a plain statement like: “I could not determine this power value; choose candidate A, candidate B, or enter manually.”

Historical review state must be separated from latest-run reports. `latest_import_report.json` describes the current run; `review_history.json` begins the path toward durable open/resolved review management across multiple screenshot sources.

# Sentinel Lessons Learned

**Version:** v0.9.5.57

## 18. Evidence must bind to the real decision trace

A review card without the candidate trace is only a label, not evidence. v0.9.5.57 showed that the data was often present but stored under a synthetic quarantine ranking type. Review UX must bridge that reporting indirection without changing Operational Truth.

## 19. Fallback matching is acceptable for display, not for promotion

Screenshot-local trace binding can safely improve explanation, but it must not become a hidden promotion path. Any fallback match used for UI evidence remains read-only until a separate audited review-resolution model exists.

## 20. Review detail should be reachable by click path

The Evidence Pack should eventually be a detail view inside the Command Center flow, not another loose artifact in the output folder. The top-level dashboard should answer “what happened?”; the detail page should answer “why is this row in review?”

---

# Sentinel Lessons Learned

**Version:** v0.9.5.56

## 15. A dashboard is not the same as an evidence pack

The v0.9.5.55 Command Center made Sentinel visually observable, but the 554 review showed that broad telemetry can overwhelm the actual review task. Human review needs a small evidence bundle per problem, not another wall of metrics.

## 16. Review quality improves when the next action is explicit

Each review item should state what must be checked: server identity, ambiguous candidate margin, ranking-type mismatch, or bounded row reconstruction. The Evidence Pack turns generic quarantine into a directed review task.

## 17. UI must remain read-only until trust gates are designed

Even when the UI shows a likely candidate, it must not write back to Operational Truth. Accept/reject workflows require their own guardrails and audit trail.

---

# Sentinel Lessons Learned

**Version:** v0.9.5.55

## 13. Run observability is part of data quality

A trustworthy pipeline is not enough if its state can only be understood by reading JSON and Excel manually. v0.9.5.55 adds a report-driven Command Center so the Proud Owner can see readiness, recoveries, review items, and guard state immediately after a run.

## 14. Dashboards must not become a second truth source

The Command Center reads existing report artifacts only. It does not re-score, re-rank, OCR, recover, or promote anything. This prevents UI drift from Operational Truth and keeps Data Guard as the authority.

---

# Sentinel Lessons Learned

**Version:** v0.9.5.54

## 10. Review OCR is necessary but not sufficient

The v0.9.5.53 regression showed `review_ocr.attempted=12` and `promoted=0`. Image enhancement alone did not solve the remaining hard rows. The hard cases were bounded row/rank gaps, not simple sharpen/zoom failures.

## 11. Bounded source-local anchors are stronger than isolated OCR text

For rows such as low/truncated THP values, the strongest evidence is often the candidate's position between trusted rows from the same screenshot. A candidate that preserves visible digits and fits the local power envelope is safer than one chosen only by OCR confidence.

## 12. Contextual reconstruction must remain conservative

Context can promote only when source-local anchors, digit preservation, and normal ranking order agree. If any part is weak, quarantine remains the correct outcome.

---

## v0.9.5.53 Lesson – Review is an OCR opportunity, not just a stop sign

The 549–553 regression run after .52 showed that the remaining review rows are often not pure power-scoring failures. They are row/crop/image-quality failures: Sentinel can infer bounded gaps, but runtime must not turn that inference into Operational Truth without better direct evidence.

The correct next layer is an adaptive review OCR pass: crop the questionable visual row, enlarge it, enhance it, OCR it again, and only promote when the second pass produces stronger intrinsic row evidence. This keeps Data Quality ahead of Intelligence while turning quarantine into an active quality-improvement stage.

Key principle: review OCR may improve evidence, but it must not become another guessing engine. If the enhanced crop is weak, ambiguous, or missing, quarantine remains the correct answer.


# Sentinel Lessons Learned

**Version:** v0.9.5.52

---

## 1. False confidence is worse than missing data

A wrong row in Operational Truth is more dangerous than a quarantined row. Missing data can be reviewed. False data becomes the basis for bad decisions.

---

## 2. OCR is not always the root cause

Many observed failures looked like OCR problems but were actually downstream integrity problems:

- rows assigned to the wrong server,
- THP rows entering Alliance Power,
- rank continuity assumptions,
- source-local high clusters,
- recovery choosing the wrong candidate.

---

## 3. Screenshot order must never be truth

Future uploads may come from multiple users, devices, Discord, browsers, and mixed servers. Filename order and upload order are not stable evidence.

---

## 4. Guards and recovery are separate

A guard answers: can we trust this row?  
Recovery answers: can we produce better field evidence?

Combining both creates silent mutation risk.

---

## 5. Quarantine is not failure

Quarantine means Sentinel knows that evidence is insufficient. That is better than pretending certainty.

---

## 6. Server 553 exposed the current recovery limit

Server 553 proved:

- `7xxM` THP values can be OCR digit explosions.
- `77B` Alliance Power can be a false high value.
- Simple leading-digit replacement can reduce the explosion but still choose the wrong value.

The next solution must use candidate scoring, not a single replacement rule.

---

## 7. Ground Truth remains essential

Visual screenshot comparison and Ground Truth validation caught several false assumptions. Automated success status is not enough when recovered values are involved.
---

## 8. Segment order is evidence, but only as a tie-breaker

Server 553 showed that close high-explosion candidates can differ by only one local bucket. In those cases, the visible rank segment can identify the safer candidate, but it must not override a large score gap or a hard order break.

---

## 9. Low-truncation recovery must stay conservative

The 549–553 run proved that low THP truncation exists, but `scale_x10` and `insert_zero` candidates can be nearly indistinguishable. When digit preservation and segment order disagree, quarantine is preferable to a confident but wrong recovered value.

## v0.9.5.60 - Review History Must Use Business Identity

Review IDs generated inside a single run are not stable enough for persistent history. Runtime timestamps must not be part of review identity, otherwise the same unresolved issue becomes a new OPEN review every time the pipeline is rerun.

The stable identity should describe the human problem: server, ranking type, rank, screenshot, problem type, and reason. Runtime metadata belongs in observation fields such as `last_seen_at`, `source_report_created_at`, and `seen_count`.

A separate Review Center is useful only if it acts as the single human-in-the-loop entry point. Static output pages should be treated as run-detail/evidence pages, not as competing dashboards.

## v0.9.5.62 - Navigation Must Match the Mental Model

A feature can be technically present and still feel absent if the navigation does not expose it. The Review Center already existed, but operators could not clearly see how it related to Imports, Quality, and the Command Center.

The stable mental model is:

1. Imports explain what evidence entered the system.
2. Quality explains whether that evidence is trustworthy.
3. Reviews explain what a human must decide.
4. Exports show what was produced.

Static output pages are useful run artifacts, but they should not compete with the web application as a second Command Center. They should be reachable as evidence/detail views from the main web flow.

## v0.9.5.63 - Review Evidence Must Be One Click Away

A human reviewer should never have to hunt for the source screenshot. The screenshot is the primary evidence behind any review decision, so filename-only display is insufficient. Review pages should link directly to the evidence, open it in a separate tab, and make the visual source obvious without breaking Data Guard separation.

Screenshot links must be treated as UI evidence links, not truth. They help the human decide; they do not alter Operational Truth or bypass quarantine.

## v0.9.5.64 - Evidence Should Guide, Not Overwhelm

Showing the screenshot inline is useful, but a full-width screenshot can dominate the review page and hide the actual decision controls. Human Review works best when the evidence is immediately visible, compact, and anchored to the problem.

Rank highlighting is a major usability gain because the reviewer no longer has to search the whole image manually. It must remain an overlay and an aid, not a source of truth. The original screenshot and Data Guard decision remain authoritative until a human explicitly resolves the review.

Patch notes also need their own durable home. Consolidating patch summaries into `/docs/PATCH_SUMMARY.md` prevents release knowledge from becoming scattered across root-level files.

## v0.9.5.65 - Visual Evidence Must Be Calibrated

A useful visual cue becomes dangerous when it is precise-looking but geometrically wrong. Screenshot overlays must be calibrated per screenshot family and must expose approximation when Sentinel cannot confidently place the target. Evidence UX is part of Data Quality, not decoration.

## v0.9.5.66 - Readiness Needs Actionable Drilldowns

A Command Center KPI is useful only if it takes the operator to the reason behind the status. Counts like Operational, Pending Review, Missing Data, and Failed Imports must not be static decoration. They are routing decisions. Each status should link to the workflow where the issue can be inspected and resolved.

Server readiness must also be evaluated at server level, not just row level. A server with both core ranking feeds and no open review is operational; a server with an open human decision is pending review; a server lacking a required feed is missing data. This creates a leadership-readable operational picture without weakening Data Guard.
