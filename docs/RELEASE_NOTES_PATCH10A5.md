# Patch 10A.5 - EasyOCR Compatibility Hotfix

## Problem
EasyOCR does not allow `ch_tra` together with `ch_sim`, `ja` or `ko` in one Reader.
The previous multilingual configuration attempted to initialize all languages in
one Reader and failed at startup.

## Fix
- Split multilingual OCR into EasyOCR-compatible language groups.
- Use separate readers for Chinese simplified, Chinese traditional, Japanese and Korean.
- Merge OCR observations into one result stream.
- Deduplicate overlapping OCR regions by confidence.

## Default Groups
- `en + ch_sim`
- `en + ch_tra`
- `en + ja`
- `en + ko`

## Result
The OCR pipeline can process multilingual screenshots without violating EasyOCR
language compatibility rules.
