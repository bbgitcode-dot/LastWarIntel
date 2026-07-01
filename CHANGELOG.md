# Changelog


## [0.9.5.35] - THP Power Sanity Guard

### Added

- `parser/thp_sanity_guard.py` for explainable late-scroll THP power outlier quarantine.
- Smoke tests for THP outlier quarantine and normal scroll overlap.

### Fixed

- Prevents OCR digit spikes such as `198M -> 798M` from being promoted to top THP ranks during final power-order merge.
- Suspicious THP values are quarantined instead of silently entering Operational Truth.

