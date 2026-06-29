# Sentinel v0.9.5.1 - OCR Benchmark Hotfix

## Fixed

- Removed incompatible `show_log=False` argument from PaddleOCR initialization.
- Added constructor fallback for newer PaddleOCR versions.
- Sanitized benchmark rows before writing Excel reports.
- Removed ANSI/control characters that caused `openpyxl.IllegalCharacterError`.

## Validation

- `python -m py_compile benchmark_ocr.py ocr/paddleocr_provider.py ocr/provider.py ocr/provider_factory.py ocr/utils.py`

## Run

```bash
python benchmark_ocr.py
```

If PaddleOCR is installed correctly, the benchmark now writes:

- `benchmarks/ocr_benchmark_report.json`
- `benchmarks/ocr_benchmark_report.xlsx`
- `benchmarks/easy_run.log`
- `benchmarks/paddle_run.log`
