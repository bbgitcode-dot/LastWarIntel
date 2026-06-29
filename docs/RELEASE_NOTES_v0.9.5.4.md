# Sentinel v0.9.5.4 - Benchmark Subprocess Encoding Hotfix

## Fixed

- Benchmark subprocess output is now decoded as UTF-8 with replacement fallback.
- Windows cp1252 decode crashes no longer stop the benchmark runner.
- Missing stdout/stderr values are handled safely.
- Provider logs are written with UTF-8 replacement fallback.

## Purpose

This hotfix ensures benchmark infrastructure survives OCR output containing Asian characters or provider logs with non-cp1252 bytes.
