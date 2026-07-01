# Changelog


## [0.9.5.39] - General Top Alliance Power Allowance

### Fixed

- Generalized the Alliance Power top-of-source allowance beyond the Server 552 mobile case.
- Legitimate top Alliance Power rows at the start of desktop/mobile scroll screenshots are no longer quarantined solely because of local median ratio.
- Keeps lower-row Alliance Power outliers and THP late-scroll outliers protected by the existing Power Sanity Guard.

### Validation

- Added smoke coverage for Server 550/551-style top-of-source Alliance Power rows without OCR rank anchors.
- Added regression coverage to ensure a late-row Alliance Power spike remains quarantined.


## [0.9.5.35] - THP Power Sanity Guard

### Added

- `parser/thp_sanity_guard.py` for explainable late-scroll THP power outlier quarantine.
- Smoke tests for THP outlier quarantine and normal scroll overlap.

### Fixed

- Prevents OCR digit spikes such as `198M -> 798M` from being promoted to top THP ranks during final power-order merge.
- Suspicious THP values are quarantined instead of silently entering Operational Truth.

