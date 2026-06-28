# Intelligence Concepts

> **Sentinel Intelligence Model**

Version: **v0.8.0**

---

# Purpose

This document defines the common vocabulary used throughout Sentinel.

Every intelligence module, assessment, recommendation and report uses the concepts defined here.

A shared language is essential.

Without it, modules slowly drift apart and begin describing identical concepts using different terminology.

This document prevents that.

---

# The Intelligence Hierarchy

Sentinel transforms observations through multiple knowledge layers.

```text
Observation
        │
        ▼
Difference
        │
        ▼
Fact
        │
        ▼
Evidence
        │
        ▼
Strategic Indicator
        │
        ▼
Reasoning
        │
        ▼
Assessment
        │
        ▼
Value
        │
        ▼
Recommendation
```

Every layer has a unique purpose.

---

# Observation

## Definition

An observation is raw imported information.

It has not yet been interpreted.

Examples:

* OCR result
* Discord screenshot
* Imported ranking
* Snapshot data
* Manual input

Observations are the lowest level of knowledge.

---

# Snapshot

## Definition

A snapshot represents the complete game state at a single point in time.

Examples:

* Alliance rankings
* Player power
* Server strength
* Campaign status

Snapshots are immutable.

They never change after creation.

---

# Difference

## Definition

A Difference represents a change between two snapshots.

Examples

* PlayerJoined
* PlayerLeft
* AlliancePowerChanged
* OfficerTransferred
* AllianceRenamed

Differences answer only one question:

> **What changed?**

Nothing more.

---

# Intelligence Fact

## Definition

A Fact is an objective observation generated from one or more Differences.

Facts describe reality.

They never interpret.

They never recommend.

Examples

Alliance lost 18% power.

Officer transferred.

Whale joined server.

Activity declined by 21%.

Facts are always objective.

---

# Evidence

Evidence supports a hypothesis.

Evidence consists of one or more Facts.

Example

Evidence:

* Alliance lost 18%
* Officer left
* Activity decreased

Evidence answers:

> **Why do we believe this?**

Evidence never contains conclusions.

---

# Strategic Indicator

## Definition

Indicators summarize multiple observations into strategic characteristics.

Indicators are no longer raw facts.

They already contain interpretation.

Examples

Talent Value

Recruitability

Structural Health

Whale Density

Elite Density

Recruitable Density

Indicators answer:

> **How should this entity be described?**

---

# Reasoning

Reasoning combines multiple Indicators and Facts.

Its purpose is to build strategic understanding.

Example

```text
High Recruitability

+

Low Structural Health

+

Officer Loss

↓

Alliance becoming unstable
```

Reasoning produces hypotheses.

Not priorities.

---

# Hypothesis

A hypothesis represents a possible explanation.

Hypotheses are deterministic.

They may still contain uncertainty.

Examples

* Alliance stability decreasing
* Leadership becoming weaker
* Recruitment becoming easier

Confidence expresses uncertainty.

Not randomness.

---

# Strategic Assessment

Assessments describe strategic situations.

They answer:

> **What is happening?**

Examples

Recruitment Window

Alliance Collapse

Leadership Risk

Whale Migration

Transfer Winner

Transfer Loser

High Internal Stability

Hidden Opportunity

Assessments intentionally avoid prioritization.

---

# Strategic Value

Values prioritize Assessments.

Different objectives require different priorities.

Examples

Recruitment Value

Threat Value

Diplomacy Value

Expansion Value

Retention Value

Example

Two alliances may both have the assessment:

Recruitment Window

However:

Alliance A

Recruitment Value

94

Alliance B

Recruitment Value

68

The assessment explains.

The value prioritizes.

---

# Recommendation

Recommendations describe suggested actions.

Recommendations always depend on

Assessment

*

Value

Examples

Contact alliance leadership.

Observe for one week.

Ignore.

Strengthen diplomacy.

Recommendations always remain explainable.

---

# Confidence

Confidence describes certainty.

It is not probability.

Confidence expresses how strongly Sentinel believes an assessment is supported by available evidence.

Examples

95%

Very strong evidence.

70%

Likely.

45%

Weak evidence.

Confidence never replaces evidence.

---

# WatchTarget

A WatchTarget represents an operational intelligence object.

It is Sentinel's digital representation of an entity.

Examples

Alliance

Player

Server

Future campaign

A WatchTarget accumulates knowledge over time.

It may contain

* Assessments
* Values
* Decision Snapshots
* History
* Trend Information
* Contact History
* Notes

WatchTargets become richer as Sentinel learns more.

---

# Recruitment Value

Recruitment Value is not an assessment.

It is a prioritization.

Current implementation considers

* Talent Value
* Structural Health
* Recruitability
* Whale Density
* Recruitable Density
* Elite Density
* Recruitment Momentum

Future versions may include

* Historical trends
* Transfer timing
* Diplomacy
* Leadership stability
* Season phase

---

# Intelligence Module

Every Intelligence Module answers one strategic question.

Examples

Growth Intelligence

Which entities are growing?

Whale Intelligence

Which strategically relevant players moved?

Health Intelligence

How stable is this alliance?

Recruitment Intelligence

How attractive is this alliance for recruiting?

Opportunity Intelligence

Which opportunities currently exist?

Modules never overlap responsibilities.

---

# Design Rules

Every new Intelligence Module must follow these rules.

## Rule 1

Generate knowledge.

Never presentation.

---

## Rule 2

Produce deterministic output.

---

## Rule 3

Never communicate directly with another Intelligence Module.

---

## Rule 4

Use shared Intelligence concepts.

---

## Rule 5

Every metric must support a strategic decision.

---

## Rule 6

Every recommendation must remain explainable.

---

# One Sentence

If the complete Intelligence Model could be summarized in one sentence, it would be this:

> **Sentinel transforms observations into explainable knowledge by progressing through Facts, Indicators, Reasoning, Assessments and Values before producing recommendations.**
