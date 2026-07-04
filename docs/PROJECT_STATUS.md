
# Project Status – Sentinel v0.9.5.95

**Current sprint:** v0.9.5.95 Targeted Character Verification Planning  
**Proud Owner:** Stefan  
**Copilot:** Mimir

## Current understanding

The v0.9.5.94 Server 551 benchmark showed strong Data Quality but weak exact Identity Fidelity. Recall can remain 100% while exact identity remains unsafe for historical intelligence. The critical example is `Joncollins21` being read as `Joncollinszl`. Fuzzy matching cannot be allowed to silently repair this, because a real `Joncollinszl` could exist.

## v0.9.5.95 direction

Sentinel now marks targeted character verification candidates: specific characters that should be re-read from screenshot evidence. This includes player-name confusions such as `2/z` and `1/l`, and case-sensitive alliance-tag drift such as `PbC` vs `PBC`.

## Remaining P0 before V1

- Convert verification candidates into actual screenshot crop/re-OCR attempts.
- Ensure alliance tags preserve exact case.
- Keep fuzzy/normalized identity out of definitive joiner/leaver logic.
- Add report UX for character-level verification evidence.
