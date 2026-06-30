# Sentinel

> **Transforming observations into operational truth and explainable strategic intelligence.**

**Current Version:** v0.9.5.25  
**Runtime Baseline:** v0.9.5.25 – Sentinel Ranking Guard  
**Status:** Active Development

---

## What Sentinel is

Sentinel is an explainable strategic intelligence platform for **Last War: Survival**.

It is not just an OCR script, spreadsheet exporter, or statistics dashboard. Those are implementation details. Sentinel exists to help alliance leadership answer one operational question:

> **What deserves our attention today?**

Sentinel transforms raw screenshots and ranking observations into structured operational data, guards that data against silent corruption, and prepares the foundation for strategic assessments, recruitment intelligence, transfer intelligence, and decision support.

---

## Current operational stack

```text
Screenshots
    ↓
OCR Provider
    ↓
Parser + Normalizer
    ↓
Sentinel Data Guard
    ↓
Sentinel Data Quality Loop
    ↓
Quarantine / Review or Import
    ↓
Operational Import Report
    ↓
Command Center
```

The Command Center is the user-facing operations surface. It shows the latest import state, current runtime health, import coverage, and review/quarantine signals.

---

## Core components

### Command Center

The browser-based operational interface. It answers what happened in the last import and what requires attention next.

### Sentinel Data Guard

The integrity layer. It validates server assignment and protects runtime data from silent misclassification. The Data Guard must not guess or silently repair data. It validates, blocks, explains, and quarantines.

### Sentinel Data Quality Loop

The recovery layer. It attempts targeted OCR recovery before human review is required. It may improve image evidence and retry OCR, but it does not make strategic decisions. The Data Guard remains the authority after each recovery attempt.

### Ground Truth Validator

A development and benchmark tool. Ground Truth validates Sentinel; it does not power the runtime application.

---

## Current findings from v0.9.5.21–v0.9.5.23

Recent sprints proved that server assignment must be protected before data enters runtime views. The original 551→552 issue showed that a screenshot can be parsed correctly at row level and still be assigned incorrectly downstream. Sentinel Data Guard was introduced to prevent this class of silent error.

The rebuilt Data Quality Loop removed filename and timestamp logic from server decisions. This is important because future uploads may come from Discord, phones, browsers, or third parties with arbitrary file names.

The latest test on servers 549, 550, and 551 showed:

- Server 552 no longer appears as a false operational server.
- The system recognizes only servers 549, 550, and 551 in the latest import report.
- The Data Quality Loop increases runtime cost significantly and must be measured against recovered quality.
- A new problem surfaced: THP rows can still enter Alliance Power rankings. This is not a server-assignment problem; it is a ranking-type integrity problem.

The current stabilization step is **v0.9.5.25 – Sentinel Ranking Guard**, which quarantines ranking-type contamination before merge/export.

---

## Start commands

Run the parser/import:

```bat
python main.py
```

Run the Command Center:

```bat
python -m uvicorn sentinel:app --reload --host 127.0.0.1 --port 8010
```

Open:

```text
http://127.0.0.1:8010
```

---

## Operating model

The Sentinel project is developed sprint by sprint as full ZIP patch packages.

- No partial snippets as deliverables.
- Every sprint produces a full downloadable ZIP.
- Every release includes versioning and commit guidance.
- The Proud Owner defines direction and accepts releases.
- Mimir acts as strategic copilot, architecture reviewer, and patch builder.

Details: `docs/MODUS_OPERANDI.md`

---

## Key documents

- `docs/ARCHITECTURE.md`
- `docs/PROJECT_STATUS.md`
- `docs/ROAD_TO_V1.md`
- `docs/ROADMAP.md`
- `docs/RELEASE_NOTES.md`
- `docs/MODUS_OPERANDI.md`
- `docs/SENTINEL_DATA_GUARD.md`
