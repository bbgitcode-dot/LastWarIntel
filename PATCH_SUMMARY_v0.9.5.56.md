# Sentinel v0.9.5.56 Patch Summary

## Focus

Review Quality Sprint: add a focused Review Evidence Pack instead of expanding the Command Center with more broad telemetry.

## Added

- `output/review_evidence_pack.html` generated after each run.
- `output/review_evidence_pack.json` generated after each run.
- Review evidence cards with:
  - server / ranking / rank
  - screenshot reference
  - original and selected power
  - best and second candidate
  - margin and decision reason
  - Review OCR and Row Reconstruction status
  - suggested human action
  - expandable candidate details
- Command Center artifact links to the Evidence Pack.
- Smoke test coverage for Evidence Pack generation.

## Changed

- `main.py` prints the Evidence Pack output path.
- `version.py` updated to `0.9.5.56`.
- `/docs` updated: CHANGELOG, RELEASE_NOTES, PROJECT_STATUS, ROADMAP, LESSONS_LEARNED.

## Guardrails

- Evidence Pack is report-driven and read-only.
- It does not promote rows.
- It does not alter OCR, recovery, Data Guard, Ranking Guard, quarantine, or export decisions.

## Validation

```text
python -m compileall -q services/command_center.py main.py version.py
pytest tests/smoke/test_command_center.py -q
1 passed
```

## Commit

```bash
git add .
git commit -m "feat(review): add review evidence pack"
git tag -a v0.9.5.56 -m "v0.9.5.56 Review Evidence Pack"
```
