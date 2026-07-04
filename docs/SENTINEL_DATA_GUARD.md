# Sentinel Data Guard – v0.9.5.99 Addendum

Data Guard now treats targeted character re-OCR as supporting evidence, not as a promotion mechanism.

Rules:

1. No fuzzy identity correction.
2. No normalized identity promotion.
3. No cache-driven validation.
4. Character re-OCR evidence may reduce uncertainty only when it is based on the screenshot crop.
5. If the crop vote is ambiguous, the row remains unresolved.
6. Alliance tag case is Operational Truth.

The purpose is to move toward a 551 Gold Run without compromising the principle that the screenshot is the source of truth.
