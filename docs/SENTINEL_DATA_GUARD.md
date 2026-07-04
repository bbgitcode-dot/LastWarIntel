# Sentinel Data Guard

**Current version:** v0.9.5.94

## Principle

Data Quality comes before Intelligence. Quarantine is preferred over false Operational Truth. Screenshot evidence is the only ground truth.

## v0.9.5.94 Addendum – Exact Identity Fidelity

v0.9.5.94 upgrades Identity Guard from an initial metadata layer into a measured validation dimension. The Ground Truth validator now reports:

- `player_name_display_exact_matches`
- `alliance_tag_display_exact_matches`
- `exact_identity_matches`
- `identity_risk_rows`
- `high_value_identity_risk_rows`
- `alliance_tag_case_sensitive_mismatches`
- `player_name_drift_rows`
- `identity_fidelity_score`

A row can be a valid OCR/Power match and still be an identity-risk row. Example: `Joncollins21` -> `Joncollinszl` must remain visible as drift even when power and rank match.

## Hard rule

Fuzzy matching may suggest candidates and explain recovery. It must not silently mutate Operational Truth or mark identity as safe.

## Protected failure families

- Exact Player Name Drift
- Case-Sensitive Alliance Tag Drift
- Fuzzy Identity Treated As Safe
- Review Leakage into Operational Truth
- Rank Context Corruption
- Window Merge Contamination
- Visible Rank Loss
- Rank Scope Violation
- Duplicate Identity
- Power Explosion
- Low-Truncation Power Ambiguity

---

# Sentinel Data Guard

**Current version:** v0.9.5.93

## Principle

Data Quality comes before Intelligence. Quarantine is preferred over false Operational Truth.

## v0.9.5.93 Addendum – Identity Fidelity Guard

Identity Guard separates OCR similarity from historical identity fidelity. Similar names may be useful for review matching, but Operational Truth must retain exact observed identity whenever possible.

Protected identity rules:

- Alliance tags are case-sensitive Last War identifiers.
- `DAY` and `daY` must not collapse into one Operational Truth identity.
- Player name digit/letter confusions such as `21` vs `zl` are identity-risk signals.
- Fuzzy matching must not mutate player or alliance identity.
- Identity-risk rows should remain traceable for review and future regression tests.

## v0.9.5.93 Addendum – Review / Operational Separation

Review placeholders preserve evidence but are not accepted Operational Truth. They belong in quarantine/review surfaces, not in normal ranking sheets as artificial ranks.

## v0.9.5.92 Addendum – Rank Evidence vs Final Rank

Sentinel separates rank evidence from final exported truth:

- `visible_rank` / `ocr_rank`: observed OCR evidence from the screenshot.
- `computed_rank`: row position after reconstruction/power order.
- `rank` / `operational_rank` / `final_rank`: export/Operational Truth rank.

For partial windows, screenshot-visible ranks stay authoritative. For full-scope/multi-window imports, Last War's power-sorted ranking context may infer or repair final ranks when OCR rank evidence is missing or broken. The repair must be explainable via `rank_context_status`, `merge_reason`, and `rank_warning`.

## Protected failure families

- Review Leakage into Operational Truth
- Identity Fidelity Drift
- Case-Sensitive Alliance Tag Drift
- Player Name Digit/Letter Confusion
- Rank Context Corruption
- Window Merge Contamination
- Visible Rank Loss
- Rank Scope Violation
- Duplicate Identity
- Power Explosion
- Low-Truncation Power Ambiguity
