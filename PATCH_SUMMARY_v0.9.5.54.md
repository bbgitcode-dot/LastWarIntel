# Sentinel v0.9.5.54 Patch Summary

## Name

Contextual Row Reconstruction

## Summary

Adds a conservative second review remediation layer after Adaptive Review OCR. Low/truncated THP review rows may be promoted only when a digit-preserving candidate fits between trusted source-local anchors from the same screenshot.

## Validation

```text
31 passed
compileall parser/services/main/version/ground_truth_validator passed
```

## Commit

```bash
git add .
git commit -m "feat(review): add contextual row reconstruction"
git tag -a v0.9.5.54 -m "v0.9.5.54 Contextual Row Reconstruction"
```
