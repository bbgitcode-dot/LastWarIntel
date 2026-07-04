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
- VIP/high-value players such as `Joncollins21` must remain discoverable under their observed screenshot identity.
