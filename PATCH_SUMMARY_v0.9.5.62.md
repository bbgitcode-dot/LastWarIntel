# Sentinel v0.9.5.62 Patch Summary

## Sprint
Visible Navigation Consolidation

## Added

- Persistent Command Center workflow bar across web pages: Command, Imports, Quality, Reviews, Exports.
- Expanded readable sidebar with grouped navigation, descriptions, and consistent product language.
- Review detail route `/reviews/{history_key}`.
- Review detail template showing problem statement, choices, resolution form, why-bullets, and explainability trace.
- Cross-link panels on Command Center, Imports, and Quality pages.
- Shared CSS for workflow navigation, link cards, review detail cards, trace cards, and resolution forms.
- Smoke test coverage for navigation model, templates, cross-links, and review detail route registration.

## Changed

- Review evidence is now accessible through the web application, not only through `output/review_evidence_pack.html`.
- The visible UI now matches the target operator flow: Command Center -> Imports -> Quality -> Reviews -> Exports.
- Version updated to `0.9.5.62`.

## Guardrail

No OCR, Data Guard, Ranking Guard, recovery, quarantine, Operational Truth, or Excel export behavior was changed.

## Validation

```text
pytest tests/smoke/test_web_navigation_consolidation.py tests/smoke/test_command_center.py -q
9 passed
python -m compileall -q web/app.py web/navigation.py web/routes web/templates version.py
```

## Commit

```bash
git add .
git commit -m "feat(ui): expose command center workflow navigation"
git tag -a v0.9.5.62 -m "v0.9.5.62 Visible Navigation Consolidation"
```
