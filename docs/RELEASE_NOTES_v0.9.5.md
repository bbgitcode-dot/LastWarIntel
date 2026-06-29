# Sentinel v0.9.5 - OCR Benchmark Framework

## Added

- Pluggable OCR provider architecture
- EasyOCR provider
- PaddleOCR provider
- OCR provider factory
- Benchmark runner: `benchmark_ocr.py`
- Runtime and quality benchmark metrics
- Benchmark Excel and JSON reports
- OCR provider documentation
- OCR benchmark documentation
- Engineering principles documentation

## Changed

- `parser/ocr.py` now delegates to an OCR provider instead of instantiating EasyOCR directly.
- `main.py` supports provider-selected output files through `SENTINEL_OUTPUT_FILE`.
- `main.py` prints selected OCR provider and runtime summary.

## Quality

- Existing parser and quality gates remain the benchmark constant.
- Only OCR provider changes between benchmark runs.

## Usage

```bash
python benchmark_ocr.py
```

or

```bash
python benchmark_ocr.py --providers easy,paddle
```

## Git

```bash
git add .
git commit -m "feat(ocr): add OCR benchmark framework"
git tag -a v0.9.5 -m "Sentinel v0.9.5 - OCR Benchmark Framework"
git push origin main
git push origin v0.9.5
```

The Sentinel approves.
