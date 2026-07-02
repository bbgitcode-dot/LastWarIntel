# Sentinel v0.9.5.70 Patch Summary

## Historical Import Integrity & Coverage Drilldown

This patch makes historical Excel coverage visible and auditable from the web UI after the v0.9.5.69 importer performance fix.

### Included changes
- New read-only `application.historical_import` dashboard service.
- Import Center panels for historical Excel report, source collections and SQLite snapshot coverage.
- Quality missing-data drilldown now displays operational missing evidence plus historical baseline context.
- Historical data remains reference coverage and does not overwrite Operational Truth.
- Updated `/docs/PATCH_SUMMARY.md`, release notes, changelog, lessons learned and project status.

### Validation
```text
7 passed
compileall application/historical_import importer/historical_excel_import.py application/command_center/service.py web/routes web/templates version.py passed
```

### Commit
```bash
git add .
git commit -m "feat(import): expose historical coverage drilldown"
git tag -a v0.9.5.70 -m "v0.9.5.70 Historical Import Integrity and Coverage Drilldown"
```
