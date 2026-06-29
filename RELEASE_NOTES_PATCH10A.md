# Sentinel v0.9.5.18 — Final Gap Cleanup

## Ziel
Schließe die letzte Validierungs-Lücke ohne neue spekulative Matches.

## Änderung
- Rejected rank fallbacks werden nicht mehr als `bad_server_rank` geführt.
- Neuer Status: `blocked_rank_fallback`.
- Blockierte Rank-Fallbacks zählen nicht als valide Matches und nicht als Bad Matches.
- Neue Summary-Metrik: `unresolved_gap_rows`.
- Gap Recovery erkennt `blocked_rank_fallback` als Gap-Zeile.
- Effektive Match-Metriken zählen blockierte Fallbacks nicht mehr mit.

## Ergebnis gegen Server 551
- Valid matches: 43 / 50
- Bad matches: 6 → 0
- Blocked rank fallbacks: 6
- Gap rows: 7
- Gap resolved rows: 7
- F1: 0.8775
- Score: 63.45

## Interpretation
Der Parser erzeugt keine bekannten falschen Rank-Fallback-Matches mehr. Die verbleibenden 7 Zeilen sind echte unresolved gaps und brauchen bessere Inputdaten oder spätere OCR/segmentation fixes, keine spekulativen Validator-Regeln.
