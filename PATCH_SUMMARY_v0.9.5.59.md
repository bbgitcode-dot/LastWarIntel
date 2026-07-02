# Sentinel v0.9.5.59 Patch Summary

## Review UX & Explainability Foundation

This sprint turns review output from a technical quarantine list into a human-readable review workflow foundation.

### Added
- Integrated `review_center.html` as the future human-in-the-loop workspace.
- Open review cards with explicit problem statements, choices, and explainability trace.
- Review history table inside the Review Center.
- `why_bullets` and `explainability_steps` in review evidence payloads.
- Resolution template fields prepared for later interactive review handling.

### Preserved
- `review_evidence_pack.html` remains available as a legacy/static evidence view.
- No OCR, Data Guard, Ranking Guard, or export decision logic was changed.
- Operational Truth remains protected; review pages are read-only.

### Validation
- `pytest tests/smoke/test_command_center.py -q` → 3 passed.
- `compileall services/command_center.py main.py version.py` → passed.
