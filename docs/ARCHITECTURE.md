# Sentinel Architecture

> **Version:** 0.8.0
> **Status:** Living Document

---

# Purpose

Sentinel is not a dashboard.

Sentinel is a **Strategic Intelligence Platform**.

Its objective is to transform observations into explainable strategic knowledge that supports alliance leaders in making better decisions.

The architecture is therefore intentionally designed around **knowledge generation**, not data visualization.

Everything inside Sentinel follows one simple idea:

```text
Observation
        ↓
Knowledge
        ↓
Decision
```

---

# Architectural Philosophy

Most analytics software answers:

> What happened?

Sentinel answers:

> What happened?

↓

> Why did it happen?

↓

> Why is it important?

↓

> What should we do?

This distinction affects every architectural decision.

---

# Core Principles

Sentinel follows six architectural principles.

## 1. Single Responsibility

Every module answers exactly one strategic question.

Examples:

* Growth Intelligence
* Whale Intelligence
* Recruitment Intelligence
* Structural Health Intelligence

Each module owns exactly one responsibility.

---

## 2. Explainability

Every output must be reproducible.

Every recommendation must be traceable back to:

* observations
* facts
* evidence
* indicators
* reasoning

No black boxes.

---

## 3. Layered Intelligence

Knowledge is generated gradually.

Each layer increases abstraction.

Each layer reduces noise.

No layer skips another.

---

## 4. Human Decision Support

Sentinel never replaces commanders.

It prepares decisions.

The final decision always belongs to humans.

---

## 5. Modular Intelligence

Every Intelligence Module can be replaced independently.

New modules must integrate without modifying existing modules.

---

## 6. Operations consume Intelligence

Analytics generate knowledge.

Operations use knowledge.

Operations never generate knowledge.

---

# High-Level Architecture

```text
Presentation
────────────────────────────────────────────

Dashboard

Reports

Morning Briefing

Discord

REST API


                ▲

                │

Operations
────────────────────────────────────────────

Watchlist

Recommendations

Decision Snapshots

Reports

Briefings

Orchestrator


                ▲

                │

Analytics
────────────────────────────────────────────

Reasoning

Strategic Assessments

Recruitment Intelligence

Opportunity Intelligence

Health Intelligence

Growth Intelligence

Whale Intelligence

Indicators

Facts


                ▲

                │

Core Data
────────────────────────────────────────────

Snapshots

Players

Alliances

Servers

Campaigns


                ▲

                │

Persistence
────────────────────────────────────────────

Repositories

Database

OCR

Import Pipeline
```

Every layer depends only on the layer below.

Never the other way around.

---

# Sentinel Intelligence Pipeline

The Intelligence Pipeline is the heart of Sentinel.

```text
Observation
        │
        ▼
Snapshot
        │
        ▼
Comparison
        │
        ▼
Entity Matching
        │
        ▼
Difference Detection
        │
        ▼
DifferenceSet
        │
        ▼
Intelligence Facts
        │
        ▼
Strategic Indicators
        │
        ▼
Reasoning
        │
        ▼
Strategic Assessments
        │
        ▼
Strategic Values
        │
        ▼
Operations
        │
        ▼
Presentation
```

Every stage has exactly one responsibility.

---

# Layer Responsibilities

## Observation

Represents raw imported data.

Examples:

* OCR
* Discord imports
* Snapshot files

No interpretation happens here.

---

## Snapshot

Represents the world at one point in time.

Examples:

* alliance strength
* player power
* server rankings

Snapshots are immutable.

---

## Comparison

Calculates changes between snapshots.

Examples:

* gained power
* lost members
* transferred players

Comparison contains no business logic.

---

## Matching

Determines entity identity across snapshots.

Examples:

* renamed players
* transferred players
* alliance changes

Matching answers:

> Who is the same entity?

---

## Difference Detection

Creates normalized differences.

Examples:

PlayerJoined

PlayerLeft

AlliancePowerChanged

OfficerTransferred

DifferenceSets are the common language for change detection.

---

## Intelligence Facts

Facts describe objective observations.

Example:

Alliance lost 21% power.

Facts never interpret.

Facts never recommend.

They simply describe reality.

---

## Strategic Indicators

Indicators summarize strategic characteristics.

Examples:

Talent Value

Recruitability

Structural Health

Whale Density

Elite Density

Recruitable Density

Indicators already contain interpretation.

They answer:

> How healthy is this alliance?

instead of

> What changed?

---

## Reasoning

Reasoning combines multiple Indicators and Facts.

Reasoning creates hypotheses.

Example:

High Recruitability

*

Declining Health

*

Officer Loss

↓

Alliance becoming unstable

Reasoning is deterministic.

The same input always creates the same output.

---

## Strategic Assessments

Assessments describe strategic situations.

Examples:

Recruitment Window

Alliance Collapse

Transfer Winner

Transfer Loser

Whale Migration

Leadership Risk

Assessments answer:

> What is happening?

They do not prioritize.

---

## Strategic Values

Values prioritize Assessments.

Examples:

Recruitment Value

Threat Value

Diplomacy Value

Expansion Value

Retention Value

Values answer:

> Which opportunity deserves attention first?

They never create knowledge.

They only prioritize existing knowledge.
