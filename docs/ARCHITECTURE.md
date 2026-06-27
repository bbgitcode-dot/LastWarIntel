# Sentinel Architecture

> **Version:** 0.6.5
> **Status:** Living Document

---

# Vision

Sentinel is not a dashboard.

Sentinel is a strategic intelligence platform.

Its purpose is to transform observations into actionable strategic knowledge.

The system follows one simple principle:

> **Raw data → Knowledge → Strategic Decisions**

---

# Architecture

```text
Presentation
────────────────────────────────────────

Web
Reports
Dashboard
Breaking News
Morning Report


Application
────────────────────────────────────────

Sentinel Pipeline
Server Landscape
Intelligence Feed
View Builders


Analytics
────────────────────────────────────────

Comparison
Matching
Difference Detection

Intelligence Modules

Repository
Publisher

Hypothesis
Recommendation
Outlook


Domain
────────────────────────────────────────

Campaign
Snapshot
Alliance
Player
Server

Business Models


Persistence
────────────────────────────────────────

Repositories

Snapshots

Database

Import Pipeline
```

---

# Responsibilities

## Presentation

Responsible for displaying information.

Contains

* Dashboard
* Reports
* Breaking News
* Morning Report

Rules

* No business logic
* No calculations
* Uses ViewModels only

---

## Application

Responsible for orchestrating workflows.

Contains

* SentinelPipeline
* Builders
* ViewModel generation

Rules

* Coordinates analytics modules
* Contains no business logic
* Never performs calculations

---

## Analytics

The intelligence engine of Sentinel.

Responsible for transforming raw observations into knowledge.

Contains

* Comparison
* Matching
* Difference Detection
* Intelligence Modules
* Publisher
* Repository
* Hypothesis Engine
* Recommendation Engine
* Outlook Engine

Rules

* Generates IntelligenceFacts
* Never communicates directly with the UI
* Contains business logic

---

## Domain

Contains the core business entities.

Examples

* Campaign
* Snapshot
* Player
* Alliance
* Server

Rules

* Independent from UI
* Independent from storage
* Independent from analytics

---

## Persistence

Responsible for data storage.

Contains

* Snapshots
* Repositories
* Database
* Import Pipeline

Rules

* No business logic
* No strategic calculations

---

# Sentinel Intelligence Pipeline

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
Intelligence Modules
        │
        ▼
IntelligenceFacts
        │
        ▼
Intelligence Publisher
        │
        ▼
Intelligence Repository
        │
        ▼
Hypothesis Engine
        │
        ▼
Strategic Assessment
        │
        ▼
Recommendation
        │
        ▼
Outlook
```

---

# Knowledge Flow

Sentinel transforms information in several stages.

```text
Raw Data

↓

Observations

↓

Differences

↓

Facts

↓

Hypotheses

↓

Assessment

↓

Recommendations

↓

Strategic Decisions
```

Every stage increases abstraction while reducing noise.

---

# Intelligence Philosophy

Every intelligence module answers exactly one strategic question.

Examples

Whale Intelligence

> Which strategically relevant players moved?

Alliance Intelligence

> Which alliances changed significantly?

Growth Intelligence

> Which entities are growing or shrinking?

Health Intelligence

> How stable is the current situation?

Recruitment Intelligence

> Where are the best recruitment opportunities?

Each module produces IntelligenceFacts.

Nothing else.

---

# IntelligenceFacts

IntelligenceFacts are the common language of Sentinel.

Everything is built upon them.

They are consumed by

* Breaking News
* Morning Report
* Intelligence Feed
* Entity Pages
* Reasoning
* Strategic Assessment

Future modules should never communicate directly with each other.

They communicate through IntelligenceFacts.

---

# Publisher

The Publisher is the only component allowed to write into the Intelligence Repository.

Responsibilities

* Validation
* Deduplication
* Publication

Rules

Analytics modules never write directly to the repository.

---

# Repository

The Intelligence Repository is the central knowledge store.

It stores IntelligenceFacts only.

Provides

* Breaking News
* Latest Facts
* Search by Entity
* Search by Tag
* Search by Severity
* Search by Source

It does not perform calculations.

---

# Architecture Rules

## Rule 1

Analytics modules never call each other directly.

---

## Rule 2

Every intelligence module produces IntelligenceFacts.

---

## Rule 3

Only the Publisher writes into the Intelligence Repository.

---

## Rule 4

The Repository is the single source of truth for intelligence.

---

## Rule 5

Application orchestrates workflows.

Analytics generates knowledge.

Presentation displays knowledge.

---

## Rule 6

Domain never depends on Analytics, Application or Web.

---

## Rule 7

Every metric must answer a strategic question.

Metrics exist to support decisions.

Not to decorate dashboards.

---

# Design Principles

Sentinel follows several core principles.

## Separation of Concerns

Each layer has one responsibility.

---

## Deterministic Intelligence

Facts are generated by deterministic logic.

Reasoning is reproducible.

---

## Explainability

Every recommendation must be traceable.

Facts

↓

Hypotheses

↓

Assessment

↓

Recommendation

---

## Extensibility

New intelligence modules should be pluggable.

Examples

* Whale Intelligence
* Alliance Intelligence
* Growth Intelligence
* Health Intelligence
* Recruitment Intelligence
* Diplomacy Intelligence

The Sentinel Pipeline should not require structural changes when new modules are added.

---

# Long-Term Vision

Sentinel should evolve into a Strategic Intelligence Platform capable of answering questions such as:

* Which server is becoming unstable?
* Which alliance is likely to collapse?
* Where are the best recruitment opportunities?
* Which whales transferred?
* Which server gained the most strategic strength?
* What changed overnight?
* What should the president focus on today?

The objective is not to visualize data.

The objective is to support strategic decision making.
