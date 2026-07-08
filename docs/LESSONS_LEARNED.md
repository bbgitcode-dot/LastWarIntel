# Lessons Learned – Sentinel

## 1. Data stability beats OCR optimism

Early OCR output can look convincing while still being wrong. Sentinel must never promote plausible text into Operational Truth without evidence. Quarantine and review are safer than false certainty.

## 2. Ranking Guard is as important as OCR

Many dangerous failures were not OCR failures; they were row, rank, or context failures. A wrong row with a plausible name is worse than an UNKNOWN row.

## 3. Context gaps are not character drift

Cases such as `K9 Thunder` vs `YUNS`, `HUNI` vs `Zacharys`, or hangul-only rows with unrelated OCR text must not enter Character ReOCR. These are alignment/context problems. Treating them as glyph errors would create false identities.

## 4. Ground Truth must remain read-only

Ground Truth is benchmark reference, not a mutable repair target. Inference can annotate, explain, or accept a context gap as read-only, but it must not rewrite Operational Truth.

## 5. First-contact identity cannot depend on history

Sentinel must work across 128 transfer-bucket servers and eventually 2000+ servers. A historical player database cannot be the core solution. The primary proof must come from the current screenshot.

## 6. Character ReOCR must be targeted

Broad ReOCR is too expensive on CPU and produces noisy signals. It is useful for local glyph confusions such as `z/2`, `l/1`, `O/D`, `6/G`, or alliance-tag case. It is not a magic solution for whole multilingual spans.

## 7. Evidence Inspector changed the project

The Evidence Inspector reframed failures from “OCR bad” into actionable classes:

- row context gap;
- field mismatch;
- unresolved local glyph;
- observed text confirmed;
- outside allowed set;
- policy skip;
- crop warning.

This made debugging scientific instead of speculative.

## 8. Core Identity and Full Display Fidelity must be separate

A row can be operationally safe for Core Identity while still not Gold-ready for exact display fidelity. Sentinel should report this distinction explicitly.

## 9. Cache is allowed only as evidence reuse, not identity memory

The v0.9.5.124 cache is intentionally snapshot-local and target-specific. It reuses exact glyph evidence inside the same validation run. It must not become a historical player identity resolver.

## 10. Performance must not weaken DataGuard

Runtime reductions are valuable only if 0 bad matches and read-only inference rules remain intact. v0.9.5.124 was successful because it reduced repeated ReOCR while preserving evidence provenance.

## 11. Documentation is part of the product

Sentinel is a long-running strategic intelligence project. A new chat must be able to continue from the ZIP and `/docs` without relying on hidden memory.
