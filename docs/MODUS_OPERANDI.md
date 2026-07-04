# Modus Operandi – Sentinel v0.9.5.94

## Roles

- Proud Owner owns decisions and validation priority.
- Mimir produces complete ZIP releases, not snippets, unless snippets are explicitly requested.

## Release discipline

Every sprint deliverable must include:

- full downloadable ZIP release;
- version update;
- release notes;
- validation summary;
- `.commit`;
- commit command and tag command.

## Benchmark review rule

The screenshot is the truth. Validate rows in this order:

1. Screenshot observation.
2. Manual/Ground Truth expectation.
3. Sentinel output.
4. Error classification.
5. Strategy.

Never infer screenshot correctness from the export.

## Data Quality rule

Data Quality comes before Intelligence. Quarantine is preferred over false Operational Truth. Cache is performance optimization only and should be off during data-quality validation unless explicitly requested.

## Identity review rule

Fuzzy matching is not identity proof. Any drift in player name or case-sensitive alliance tag must remain visible as risk until manually accepted or fixed by code.

Alliance tags are case-sensitive Last War identifiers: `DAY` and `daY` must not collapse into a single trusted identity.
