# Sentinel Data Guard – v0.9.5.101 Addendum

Data Guard continues to treat targeted character re-OCR as supporting evidence, not as automatic identity correction.

Rules:

1. No fuzzy identity correction.
2. No normalized identity promotion.
3. No cache-driven validation.
4. Character re-OCR evidence may reduce uncertainty only when it is based on the screenshot crop.
5. If the crop vote is ambiguous or off-target, the row remains unresolved.
6. Alliance tag case is Operational Truth.
7. A vote outside the expected/observed/confusion-family set is noise, not evidence.

v0.9.5.101 specifically tightens crop and vote precision so Character ReOCR does not accidentally verify neighbouring brackets, tags or UI glyphs.
