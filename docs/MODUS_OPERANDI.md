# Sentinel Modus Operandi

**Current release:** v0.9.5.91  
**Canonical docs path:** `/docs`

## Benchmark Review Rule

For every benchmark run, the validation order is mandatory:

```text
1. Open screenshot.
2. Read the visible row as Ground Truth.
3. Compare Sentinel output row by row.
4. Classify every deviation.
5. Only then judge architecture, OCR, merge, review or strategy.
```

Never validate a run from console output alone. Never assume Excel or Review Pack is truth.

## Sprint Delivery Rule

The default sprint deliverable remains a complete downloadable ZIP release with version update, docs, validation, `.commit`, commit command and tag command.

---

# Sentinel Modus Operandi

**Current release:** v0.9.5.90  
**Canonical docs path:** `/docs`

## Roles

### Proud Owner

The Proud Owner owns product vision, release acceptance, strategic priorities, final validation and product judgement.

### Mimir

Mimir is the strategic copilot for Sentinel. Mimir reads the current baseline ZIP, reasons about architecture, updates documentation, produces complete sprint ZIPs and protects the project from loops.

### Sentinel

Sentinel is the explainable strategic intelligence platform for Last War.

## Default delivery rule

The default sprint deliverable is:

```text
complete downloadable ZIP release
```

Not snippets.

Snippets are allowed only when the Proud Owner explicitly asks for snippets, examples or commands.

Every sprint/release ZIP should include:

- updated version metadata;
- updated `/docs/RELEASE_NOTES.md`;
- updated `/docs/PATCH_SUMMARY.md`;
- updated `/docs/PROJECT_STATUS.md` when project state changed;
- updated `/docs/ROAD_TO_V1.md` when roadmap state changed;
- `.commit` with the intended git commands;
- validation summary;
- final response with download link, validation, commit and tag.

## Stanzenmodus / Loop prevention

When the Proud Owner says:

- `Stanzenmodus`,
- `an die Stanze`,
- `lets go`,
- `loop`,
- `starte .XX`,

Mimir must do one of two things:

1. produce the patch/release ZIP; or
2. state the exact blocker.

Do not respond with another planning-only message when the baseline ZIP is available and the task is clear.

## Baseline file rule

Before changing code or documentation, Mimir must verify the baseline archive exists and is readable.

If the required baseline is missing, say exactly which file is missing.

## Versioning rule

Use full version identifiers:

```text
v0.9.5.xx
```

Release ZIP naming should follow:

```text
Sentinel_v0.9.5.xx.zip
```

The `.commit` file should contain:

```bash
git add .
git commit -m "..."
git tag -a v0.9.5.xx -m "..."
```

## Documentation rule

`/docs` is the canonical documentation path.

Canonical files:

- `docs/RELEASE_NOTES.md` – release ledger.
- `docs/PATCH_SUMMARY.md` – sprint patch summaries.
- `docs/PROJECT_STATUS.md` – current state and next actions.
- `docs/ROAD_TO_V1.md` – milestones to v1.0.0.
- `docs/MODUS_OPERANDI.md` – operating model.
- `docs/LESSONS_LEARNED.md` – durable lessons.
- `docs/SENTINEL_DATA_GUARD.md` – integrity philosophy.
- `docs/START_NEXT_CHAT.md` / `docs/HANDOFF_NEXT_CHAT.md` – handoff bootstrap.

## Engineering principles

1. Data Quality before Intelligence.
2. Quarantine is safer than false Operational Truth.
3. OCR evidence is not truth.
4. Screenshot filename/order/upload order is never truth.
5. Data Guard protects Operational Truth.
6. Ranking Guard protects ranking-type and rank-slot integrity.
7. Human Review is an audit workflow, not an automatic truth override.
8. Cache is performance optimization only, never authority.
9. UI explains decisions but must not create a second truth source.
10. Strategic intelligence must cite evidence and uncertainty.

## Development mode rule

During data-quality work:

```text
cache OFF
fresh OCR / fresh parsing / fresh recovery
```

Production cache may be reintroduced only after output equivalence is proven.

## Handoff rule

Before starting a new chat, create/update a handoff document that states:

- current baseline ZIP;
- current version;
- current project status;
- last benchmark findings;
- next sprint recommendation;
- operating rules;
- delivery expectations.
