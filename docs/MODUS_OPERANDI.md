# Sentinel Modus Operandi

## Snapshot operating procedure – v0.9.5.75

1. Create or activate the correct snapshot before importing screenshots.
2. Define Server Scope and expected rankings before the import batch.
3. Keep the snapshot in `OPEN` or `COLLECTING` while screenshots are still arriving.
4. Move to `REVIEWING` when import collection is finished.
5. Resolve reviews and missing feeds before treating the snapshot as evidence.
6. Move to `VERIFIED` only when readiness is acceptable.
7. Move to `LOCKED` when the snapshot must become an immutable reference.
8. Never use filename order, upload order or screenshot naming as truth.

Quarantine remains preferred over false Operational Truth.

---

# Sentinel Modus Operandi

**Current version:** v0.9.5.72  
**Default documentation path:** `/docs`

## Roles

### Proud Owner
The Proud Owner owns product vision, priorities, acceptance decisions, release direction and final judgement.

### Mimir
Mimir is the strategic copilot for Sentinel. Mimir reads the baseline code, reasons about architecture, produces full sprint patches/releases, keeps documentation current and protects the project from planning loops.

### Sentinel
Sentinel is the platform: an explainable strategic intelligence system for Last War.

## Delivery rule

Default sprint deliverable:

> A complete downloadable ZIP patch or full release ZIP.

No snippets as sprint deliverables unless the Proud Owner explicitly requests snippets.

Every sprint must include:

- version update,
- release notes / patch summary update,
- documentation updates when relevant,
- validation notes,
- commit command,
- tag command.

## Stanzenmodus

When the Proud Owner says **Stanzenmodus** or equivalent, Mimir must either:

1. produce the requested patch/release ZIP, or
2. state the exact blocker.

Do not remain in a planning loop.

## File and version rules

- Baseline ZIP must be read before patching.
- If the baseline ZIP is missing or unreadable, stop immediately and state the missing file.
- The delivered artifact should be named consistently with the target version.
- `.commit` should be updated where applicable.
- Version tags use the full version, e.g. `v0.9.5.72`.

## Documentation rules

- `/docs` is the canonical documentation path.
- `docs/RELEASE_NOTES.md` is the canonical release-note ledger.
- `docs/PATCH_SUMMARY.md` is the canonical patch-summary ledger.
- `docs/PROJECT_STATUS.md` records current state and immediate next steps.
- `docs/ROAD_TO_V1.md` records the path to v1.0.0.
- `docs/LESSONS_LEARNED.md` must be updated whenever a sprint reveals a durable project lesson.
- `docs/NEXT_CHAT.md` should be updated before handoff.

## Core engineering principles

1. Data Quality before Intelligence.
2. Quarantine is safer than false Operational Truth.
3. Screenshot filename/order/upload order is never truth.
4. Data Guard protects Operational Truth.
5. Ranking Guard protects ranking-type integrity.
6. Human Review is audit workflow, not automatic truth override.
7. Historical data is reference context until explicitly promoted through guarded processes.
8. Benchmark/Ground Truth is development validation, not runtime data.
9. UI must explain decisions but must not become a second truth source.
10. Every strategic assessment must eventually be evidence-backed and explainable.

## Standard handoff sentence

Proud Owner and Mimir operate Sentinel through complete sprint ZIPs. Mimir does not deliver partial code snippets unless explicitly requested. Every patch comes with version, release notes, validation, commit command and tag command.


## v0.9.5.73 operating rule

Before running screenshot import, create or activate the correct snapshot in Import Center. If the active snapshot is missing or wrong, stop the sprint/import and fix the context first. Do not use filenames, upload order or chat upload sequence as a substitute for snapshot context.


---

## v0.9.5.76 Recognition Quality Note

Review Rank Trace is now part of the data-quality boundary. Review surfaces must not treat technical review IDs or quarantine-row ordinals as Operational Truth ranks. Sentinel carries `visible_rank`, `raw_review_rank`, `screenshot_rank_window`, and `rank_trace_source` so human reviewers see the same rank range that appears in the linked screenshot.

## v0.9.5.77 Note – Review Context

Review surfaces now separate human-visible rank from internal matching rank. Reviewers should see the screenshot-visible rank, screenshot window and target identity instead of quarantine ordinals. This protects human review quality and prevents misleading validation prompts.
## v0.9.5.80 – Continuous Collection Decision

Screenshot import runs are not collection boundaries. A snapshot may remain `COLLECTING` while open reviews exist, because real Sentinel users can upload screenshots continuously. Transition to `REVIEWING` must be explicit. Source-row-only review evidence must never be rendered as a proven visible/global rank.

