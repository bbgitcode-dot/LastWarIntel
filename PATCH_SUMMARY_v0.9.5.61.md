# Sentinel v0.9.5.61 Patch Summary

## Sprint
Interactive Review Resolution Foundation

## Added
- Web Review Center can mark persistent review-history items as `RESOLVED`.
- Resolution form supports candidate selection, manual power value, manual name, manual alliance, reviewer, and comment.
- Resolved reviews can be reopened from the Review Center.
- Review history counts are recalculated after resolve/reopen actions.
- Smoke test coverage for resolve/reopen helper logic.

## Changed
- Review Center now displays open and resolved review sections.
- Static Review Center text clarifies that static HTML remains read-only run-detail evidence.
- Version updated to `0.9.5.61`.

## Guardrail
Manual resolution is audit state only. It does not change OCR evidence, quarantine, Operational Truth, or Excel exports.

## Validation
```text
pytest tests/smoke/test_command_center.py -q
python -m compileall -q services/command_center.py web/app.py web/routes/reviews.py version.py
```
