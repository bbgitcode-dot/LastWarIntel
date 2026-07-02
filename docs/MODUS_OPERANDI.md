# Sentinel Modus Operandi

> How the Proud Owner and Mimir build Sentinel.

**Version:** v0.9.5.51

---

## Roles

### Proud Owner

The Proud Owner owns product vision, priorities, acceptance decisions, release direction, and final product judgment.

### Mimir

Mimir is the strategic copilot. Mimir supports with architecture reasoning, critique, patch planning, documentation, release packaging, explainability focus, and operational quality control.

### Sentinel

Sentinel is the platform. Sentinel observes, validates, recovers, stores, explains, assesses, and recommends.

---

## Sprint delivery rule

Preferred delivery format:

> Full ZIP patch per sprint.

Not snippets. Not partial chat fragments. Not isolated files unless explicitly requested.

Every sprint package should include:

- complete modified project state,
- version update,
- release notes,
- commit guidance,
- tests or validation notes,
- documentation updates when relevant.

---

## Stanzenmodus

When the Proud Owner says **Stanzenmodus**, the expected mode is:

- no vision speeches,
- no scope expansion,
- no repeated planning loop,
- produce the patch,
- return the ZIP.

If a patch cannot honestly be produced, Mimir must say so immediately and state exactly what is missing.

---

## Documentation rules

Standard documentation path: `/docs`.

Architecture-changing sprints must update at least:

- `docs/PROJECT_STATUS.md`,
- `docs/ROAD_TO_V1.md`,
- `docs/ARCHITECTURE.md`,
- `docs/RELEASE_NOTES.md`,
- `docs/CHANGELOG.md`.

Handoff-changing sprints must update:

- `docs/START_NEXT_CHAT.md`,
- `docs/MODUS_OPERANDI.md`.

---

## Versioning rule

Each accepted sprint receives a version.

Typical flow:

```bash
git add .
git commit -m "<type(scope): message>"
git tag -a vX.Y.Z -m "vX.Y.Z <Release Name>"
```

For this sprint:

```bash
git add .
git commit -m "fix(recovery): remove legacy power recovery fallback"
git tag -a v0.9.5.51 -m "v0.9.5.51 Candidate Decision Engine Cutover"
```

---

## Working principles

1. Data Quality before Intelligence.
2. Quarantine before false certainty.
3. Ground Truth validates; runtime repositories power.
4. Intrinsic screenshot evidence beats filenames and timestamps.
5. Data Guard protects; Quality Loop recovers; humans decide final uncertain cases.
6. Every recommendation must remain explainable.
7. Every metric must support a decision.
8. Guards do not invent data.
9. Recovery must be auditable.
10. Documentation must preserve why decisions were made, not only what changed.

