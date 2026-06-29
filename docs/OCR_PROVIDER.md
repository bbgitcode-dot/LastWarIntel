# OCR Provider Architecture

Version: v0.9.5

Sentinel treats OCR as an exchangeable observation sensor.

The import pipeline must not depend directly on EasyOCR, PaddleOCR or any future OCR engine. It depends only on the provider contract.

```text
Screenshot
    ↓
OCR Provider
    ↓
OCR Results
    ↓
Existing Parser
    ↓
Quality Gates
    ↓
Structured Snapshot
```

## Providers

Supported provider names:

- `easy`
- `paddle`

Provider selection:

```bash
set SENTINEL_OCR_PROVIDER=easy
python main.py
```

or

```bash
set SENTINEL_OCR_PROVIDER=paddle
python main.py
```

## EasyOCR

EasyOCR remains the stable default provider.

Recommended baseline profile:

```bash
set SENTINEL_OCR_PROVIDER=easy
set SENTINEL_OCR_PROFILE=fast
```

## PaddleOCR

PaddleOCR is optional and used first through the benchmark framework.

Install only if benchmark testing is required:

```bash
pip install paddleocr
```

Default Paddle row languages:

- `ch`
- `chinese_cht`
- `japan`
- `korean`

They can be overridden:

```bash
set SENTINEL_PADDLE_ROW_LANGS=ch,japan,korean
```

## Principle

OCR is not Sentinel.

OCR is one sensor that generates raw observations. The intelligence pipeline must remain independent from the selected OCR engine.
