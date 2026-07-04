# Road to Sentinel v1.0

**Current development baseline:** v0.9.5.94  
**Current documentation release:** v0.9.5.94

## Path

```text
v0.9.5.91  Rank Context & Window Merge Hardening
v0.9.5.92  Rank Inference & Export Precision Hardening
v0.9.5.93  Review Export Separation & Identity Fidelity Guard
v0.9.5.94  Identity Fidelity Metrics & Risk Reporting
v0.9.5.95  Identity Regression / Screenshot Replay
v1.0.0     Strategic Intelligence Readiness
```

## Current gate

The V1 gate is now stricter than row matching. Sentinel must show that a row is present and that its identity is preserved. `DAY` and `daY` can be different alliances. `Joncollins21` and `Joncollinszl` can represent different future search keys. Fuzzy similarity can support review, but not trusted historical identity.

## Identity Fidelity gate

- `exact_identity_matches` must become a central release metric.
- `identity_risk_rows` must trend down before Intelligence features resume.
- High-value/top-rank identity risks must be surfaced explicitly.
- Any future transfer engine must consume exact/case-sensitive identifiers, not fuzzy aliases, unless a human-reviewed alias map exists.

---

# Road to Sentinel v1.0

**Current development baseline:** v0.9.5.93  
**Current documentation release:** v0.9.5.93

## Path

```text
v0.9.5.91  Rank Context & Window Merge Hardening
v0.9.5.92  Rank Inference & Export Precision Hardening
v0.9.5.93  Review Export Separation & Identity Fidelity Guard
v0.9.5.94  Alliance Tag / Player Identity Regression
v0.9.5.95  Regression Replay Framework
v1.0.0     Strategic Intelligence Readiness
```

## Current gate

Before Intelligence work resumes, Sentinel must prove that screenshot observations become stable Operational Truth and that identities remain historically linkable. A row can match by power and still fail V1 quality if the alliance tag or player name is not preserved exactly enough for future transfer detection.

## Identity Fidelity gate

- Alliance tags are case-sensitive: `DAY` and `daY` are different identifiers.
- Player names must not be silently canonicalized into a different identity.
- Fuzzy matching may suggest review candidates, but it must not mutate Operational Truth.
- All, but especially VIP/high-value players such as `Joncollins21`, must remain discoverable under their observed screenshot identity.
