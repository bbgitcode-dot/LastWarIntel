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

