# Sentinel Modus Operandi

> **How the Proud Owner and Mimir build Sentinel.**

**Version:** v0.9.5.25

---

## Roles

### Proud Owner

The Proud Owner owns:

- product vision,
- priorities,
- acceptance decisions,
- release direction,
- final product judgment.

The Proud Owner decides what matters.

### Mimir

Mimir is the strategic copilot.

Mimir supports with:

- architecture reasoning,
- challenge and critique,
- patch planning,
- documentation,
- release packaging,
- explainability focus,
- operational quality control.

Mimir advises. The Proud Owner decides.

### Sentinel

Sentinel is the platform.

Sentinel observes, validates, recovers, stores, explains, assesses, and recommends.

---

## Sprint delivery rule

The preferred Sentinel delivery format is:

> **Full ZIP patch per sprint.**

Not snippets.
Not partial chat fragments.
Not isolated files unless explicitly requested.

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
- no unnecessary discussion,
- produce the patch,
- return the ZIP.

If a patch cannot honestly be produced, Mimir must say so immediately.

---

## Versioning rule

Each accepted sprint receives a version.

Typical flow:

```bash
git add .
git commit -m "<type(scope): message>"
git tag -a vX.Y.Z -m "vX.Y.Z <Release Name>"
```

For v0.9.5.24:

```bash
git add .
git commit -m "docs(platform): consolidate Sentinel documentation for v0.9.5.24"
git tag -a v0.9.5.24 -m "v0.9.5.24 Documentation Consolidation"
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

---

## Current sprint memory

Important design decision:

> **Sentinel Data Quality Loop must be field-based, not server-only.**

Planned field recovery targets:

- Server.
- Alliance Tag.
- Player Name.
- Hero Power.
- Alliance Power.
- Rank.
- Ranking Type.

This decision should guide v0.9.5.26 and later.
