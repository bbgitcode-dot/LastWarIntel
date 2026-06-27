# Changelog

---

## v0.5.0 — Server Landscape Foundation

### Added

- Intelligence Feed
- Server Landscape foundation
- Validation integration
- Server Landscape application layer
- Feed-first navigation

### Changed

- Dashboard moved to /command

- Feed becomes primary landing page

### Intelligence

- Defined Recruitability

- Defined Recruitment Opportunity

- Introduced curated Intelligence Feed

### Planned

- Whale Movement Intelligence

- Player Movement Intelligence

- Timeline

- Morning Intelligence Brief

## v0.6.5 — Intelligence Pipeline Architecture Snapshot

### Added
- Project architecture snapshot
- Intelligence pipeline documentation
- DifferenceSet-based comparison flow
- Entity matching foundation
- Whale Intelligence facts
- Rule-based reasoning foundation

### Changed
- Whale Intelligence now emits IntelligenceFact objects
- Difference handling moved toward a unified DifferenceSet model
- Recruitment metric clarified as Recruitability where appropriate

### Architecture
- Established pipeline direction:
  Observation → Snapshot → Comparison → Matching → DifferenceSet → Intelligence Facts → Hypotheses → Assessment → Recommendation → Outlook

### Notes
- `.venv` is intentionally excluded from archived project snapshots.
- Existing `analytics/intelligence` and new `analytics/reasoning` must be bridged instead of developed as parallel systems.

# Changelog

All notable changes to Sentinel will be documented in this file.

---

# v0.7.1 — Strategic Intelligence

Release Date: YYYY-MM-DD

## Added

### Intelligence Architecture

- Introduced Strategic Indicators as a first-class concept
- Added reusable Indicator Builder
- Added Indicator Level and Indicator Scope models

### Intelligence Modules

- Added Growth Intelligence
- Added Structural Health Intelligence
- Introduced Health Signals
- Introduced Health Indicator Builder

### Server Intelligence

- Refactored Server Intelligence to consume Strategic Indicators
- Added structured recommendations
- Added strategic server assessment model

### Pipeline

- Extended Sentinel Pipeline for indicator-based processing
- Improved provider architecture

### Documentation

- Updated architecture documentation
- Added strategic intelligence layer

## Changed

- Health Intelligence no longer produces IntelligenceFacts
- Health now produces Strategic Indicators
- Server Intelligence consumes Indicators instead of internal metrics

## Internal

- Improved separation between Facts, Indicators and Assessments
- Reduced coupling between intelligence modules
- Prepared architecture for Recruitability and Recruitment Advisor