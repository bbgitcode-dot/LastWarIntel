# Sentinel - Project Status

**Current Version:** v0.8.0

**Current Sprint:** v0.8.1 – Data Quality

---

# Project Summary

Sentinel is an explainable strategic intelligence platform for Last War.

The project has completed its architectural foundation and Recruitment Intelligence MVP.

The current focus is improving data quality before implementing Strategic Assessments.

---

# Completed

## Core

* OCR Pipeline
* Screenshot Import
* Snapshot Generation
* Difference Detection
* Recruitment Intelligence MVP
* Recruitment Value
* WatchTargets
* Morning Briefing
* Reports

## Documentation

Completed:

* README.md
* ARCHITECTURE.md
* SENTINEL.md
* INTELLIGENCE.md
* VISION.md
* ROADMAP.md
* CHANGELOG.md

---

# Current Priority

## Sprint v0.8.1 – Data Quality

Highest priority:

1. THP Parser
2. Alliance Tag Extraction
3. Player Name Extraction
4. OCR Normalization
5. Player Matching
6. Unknown Ranking Fallback
7. Snapshot Quality

No new Intelligence modules should be implemented until data quality is sufficient.

---

# Recent Findings

Smoke Test successfully completed.

Results:

* Screenshot import works.
* OCR pipeline works.
* Multi-screenshot merge works.
* Top 50+ THP can already be reconstructed.
* Export to Excel works.

Current issues:

* Ranking type "unknown" should automatically fall back to THP or Alliance Power based on detected values.
* OCR occasionally corrupts player names.
* Alliance tag and player name are not yet parsed separately.
* Player identity cannot yet be reliably tracked across snapshots.

---

# Recruitment Intelligence Notes

Important recruitment signals:

* Recruitment Value
* Structural Health
* Recruitability
* Talent Value
* Whale Density
* Elite Density

New high-priority assessment planned:

**Recruitable Whale**

Trigger:

* THP >= 180M
* No Alliance

However, the assessment must also consider:

* historical activity
* time without alliance
* recent growth
* recruitment freshness

A player without an alliance for several weeks and no measurable growth should gradually lose recruitment priority.

---

# Next Milestones

v0.8.1

* Data Quality
* OCR Improvements
* Player Matching

v0.9

* Strategic Assessments
* Explainable Intelligence
* Recruitment Calibration

v1.0

* Production-ready Strategic Intelligence Platform

---

# Design Principle

Current development principle:

**Data Quality before Intelligence.**

Reliable strategic decisions require reliable structured data.
