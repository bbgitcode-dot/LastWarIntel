# Sprint v0.8.1 – Data Quality

**Status:** Planning
**Version:** v0.8.1

---

# Goal

With Recruitment Intelligence MVP completed in v0.8.0, the next development phase focuses entirely on **Data Quality**.

The current OCR pipeline successfully imports screenshots and reconstructs rankings. However, future Strategic Intelligence depends on structured, reliable and historically consistent data.

The objective of v0.8.1 is therefore:

> **Transform OCR output into reliable structured intelligence data.**

---

# Current State

The current pipeline already supports:

* Screenshot Import
* OCR
* Server Detection
* Ranking Detection
* Multi-screenshot Merge
* Excel Export

Smoke tests using approximately 35 screenshots across two servers confirmed that the overall pipeline is functional.

---

# Smoke Test Results

Successful:

* Screenshot import
* OCR processing
* Multi-image merge
* Excel export
* Reconstruction of more than 70 THP entries from multiple screenshots

Confirmed limitation:

The bottleneck is no longer OCR.

The bottleneck is **data quality**.

---

# Issue 1 – Ranking Type Detection

## Problem

Several screenshots are classified as:

```text
unknown
```

although they clearly contain either:

* Alliance Power
* Total Hero Power

As a result, these screenshots are processed separately and never merged into the correct ranking.

---

## Planned Solution

Introduce a fallback classifier.

If OCR cannot identify the ranking type:

* Highest detected value > 1,000,000,000
  → Alliance Power

* Highest detected value < 1,000,000,000
  → Total Hero Power

The OCR classification remains the primary source.

The fallback is only used when OCR fails.

---

# Issue 2 – Alliance Tag and Player Name are not separated

## Current Situation

OCR currently produces entries such as:

```text
[ACEv] Tarori 292341388
```

This is treated as a single string.

---

## Why this is a problem

Without separating alliance and player names Sentinel cannot detect:

* Alliance changes
* Players without alliances
* Recruitable players
* Historical player identity

---

## Planned Solution

Introduce a structured PlayerRankingEntry.

```text
PlayerRankingEntry

rank
server
alliance_tag
player_name
hero_power
snapshot
confidence
```

Every OCR row should immediately be transformed into this structure.

---

# Issue 3 – OCR Noise

OCR occasionally produces variations such as:

```text
Tarori
Tar0ri
Tarorl
```

or

```text
([ACEv]
{[ACEv]
[ACEv|
```

These should not become separate entities.

---

## Planned Solution

Introduce a Normalization layer.

Responsibilities:

* Normalize alliance tags
* Normalize player names
* Remove OCR artefacts
* Standardize formatting

---

# Issue 4 – Player Matching

Player identity cannot rely on names alone.

OCR inaccuracies make exact string matching unreliable.

---

## Planned Solution

Introduce identity matching using multiple signals.

Matching should consider:

* Name similarity
* Hero Power similarity
* Alliance
* Server

The result should be an Identity Score.

This enables reliable historical tracking even when OCR is imperfect.

---

# Issue 5 – Snapshot Identity

Sentinel currently has no reliable mechanism to determine whether identical data has already been imported.

---

## Planned Solution

Every snapshot should receive a unique identity.

Example:

* Season
* Server
* Ranking Type
* Snapshot Date

Future imports can then either:

* replace
* skip
* create a new snapshot

depending on user choice.

---

# Issue 6 – Ranking Limits

Originally, merged rankings were limited to only ten entries.

This is insufficient for Recruitment Intelligence.

---

## Decision

Alliance rankings:

approximately Top 50

Hero Power rankings:

approximately Top 150

The long-term goal is to capture at least the Top 100 Hero Power players of every server.

---

# Issue 7 – Recruitable Players

A player without an alliance represents a potentially valuable recruitment opportunity.

However, current parsing does not allow Sentinel to detect alliance-less players.

---

## Planned Solution

Alliance tags must be extracted separately.

This enables future assessments such as:

Recruitable Player

Recruitable Elite

Recruitable Whale

---

# Issue 8 – Recruitment requires History

A player without an alliance is not automatically a recruitment target.

Examples:

Player A

300M Hero Power

No alliance

2 days

High recruitment priority.

Player B

300M Hero Power

No alliance

6 weeks

Minimal growth

Likely inactive.

Low recruitment priority.

---

## Planned Solution

Recruitment Intelligence should evaluate:

* Time without alliance
* Historical growth
* Activity
* Freshness

Recruitment decisions should be based on trends rather than a single snapshot.

---

# Issue 9 – OCR Confidence

OCR currently treats all parsed rows equally.

Future matching should distinguish between:

* high confidence
* medium confidence
* low confidence

Every parsed row should therefore contain a confidence value.

---

# Issue 10 – Parser Architecture

Currently, much of the parsing logic resides inside main.py.

As Sentinel grows this becomes increasingly difficult to maintain.

---

## Planned Architecture

```text
Screenshot
        │
        ▼
OCR
        │
        ▼
Image Classification
        │
        ▼
Alliance Ranking Parser
Player Ranking Parser
        │
        ▼
Normalizer
        │
        ▼
Matcher
        │
        ▼
Snapshot Builder
        │
        ▼
Repository
        │
        ▼
Facts
        │
        ▼
Indicators
        │
        ▼
Assessments
        │
        ▼
Values
```

Each component should have a single responsibility.

---

# Development Priority

The implementation order for v0.8.1 should be:

1. Ranking Type Fallback
2. Structured THP Parser
3. Structured Alliance Parser
4. OCR Normalization
5. Player Matching
6. Snapshot Identity
7. Recruitment Signals

No additional Intelligence modules should be implemented before the underlying data quality has reached production level.

---

# Key Principle

The guiding principle for Sprint v0.8.1 is:

> **Data Quality before Intelligence.**

Reliable strategic intelligence is only possible when the underlying data is structured, consistent and historically traceable.
