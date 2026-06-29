# Patch 10A.11.1 – Ground Truth Validator Import Hotfix

Fixes the first real validation run against Sentinel's OCR Excel export.

The OCR export may encode the server in the worksheet name instead of a dedicated `server` column. The validator now derives that value from sheets such as `551_total_hero_power`. It also tolerates duplicate OCR-name columns created by Excel round-tripping.
