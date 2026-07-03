# Patch Summary – v0.9.5.81

## Sentinel v0.9.5.81 – Review Evidence Model

This patch fixes the review explanation model: the highlighted screenshot row is now explicitly treated as OCR evidence, while Operational Rank remains unresolved unless Sentinel can prove it.

### Changed

- Review Detail separates OCR Source, Evidence Location, and Operational Mapping.
- Source-row-only overlays are labelled `OCR Row N`.
- Review list and history no longer present screenshot-local rows as global ranks.
- Static review reports use Operational Rank / OCR Evidence wording.
- Documentation records the separation of OCR observation, mapping hypothesis, and Operational Truth.

### Validation

```text
pytest tests/smoke/test_review_identity_consistency.py tests/smoke/test_review_context.py
compileall OK
zip integrity OK
```

### Git

```bash
git add .
git commit -m "fix(review): separate OCR source from operational mapping"
git tag -a v0.9.5.81 -m "v0.9.5.81 Review Evidence Model"
```
