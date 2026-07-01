
## [0.9.5.41] - High-Cluster Alliance Power Guard

### Fixed

- Blocks paired 50B+ Alliance Power OCR spikes when source-local shape evidence shows a much lower remaining power envelope.
- Completes the 552 `79B / 77B / 70B` quarantine behavior without relying on screenshot order or upload order.
- Keeps legitimate 550/551 leaders allowed and leaves THP sanity behavior unchanged.

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


## [0.9.5.40] - Alliance Power Shape Guard

### Fixed

- Added source-local Alliance Power shape detection for 50B+ OCR high clusters.
- Blocked false 552-style `79B / 77B / 70B` Alliance Power spikes without relying on screenshot order.
- Preserved legitimate 550/551 top Alliance Power rows and existing THP late-scroll quarantine behavior.

### Validation

- `25 passed` across Ranking Power, THP Sanity, Semantic Ranking Guard, Sentinel Ranking Guard, Mobile German Ranking Type, and Power First Reconstruction smoke suites.
