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

