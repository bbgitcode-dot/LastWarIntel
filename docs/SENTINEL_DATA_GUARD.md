# Sentinel Data Guard – Die Integritätsschicht von Sentinel

**Version:** v0.9.5.47

---

## Aufgabe

Der Sentinel Data Guard schützt **Operational Truth**.

Alle späteren Komponenten – Command Center, Historie, Intelligence, Assessments und Empfehlungen – verlassen sich darauf, dass die Daten, die den Data Guard verlassen, vertrauenswürdig und nachvollziehbar sind.

---

## Grundprinzip

> Lieber eine Zeile zu viel in Quarantäne als eine einzige falsche Zeile in der Operational Truth.

---

## Warum der Data Guard entstanden ist

Die Entwicklung zeigte, dass OCR-Fehler selten das einzige Problem sind. Gefährlicher waren stille Datenfehler:

- Screenshots wurden dem falschen Server zugeordnet.
- Einzelne Ranking-Blöcke wurden automatisch falsch gemerged.
- THP-Zeilen tauchten im Alliance-Power-Ranking auf.
- Korrekte OCR-Ergebnisse wurden durch falsche nachgelagerte Entscheidungen verfälscht.
- Power-OCR-Explosionen wirkten plausibel, waren aber falsch.

---

## Was der Data Guard darf

- validieren,
- Konflikte erkennen,
- Unsicherheit erklären,
- Daten blockieren,
- Daten in Quarantäne verschieben,
- Recovery anstoßen, wenn bessere Evidenz möglich ist.

---

## Was der Data Guard nicht darf

- raten,
- Daten erfinden,
- widersprüchliche Daten automatisch zusammenführen,
- Dateinamen oder Zeitstempel als Wahrheit interpretieren,
- Unsicherheit verstecken.

---

## Zusammenspiel mit Recovery

```text
Unsicher
    ↓
Data Guard
    ↓
Recovery / Quality Loop
    ↓
Guard recheck
    ↓
Trusted recovered row or quarantine
```

Recovery darf Felder nur verändern, wenn die Veränderung nachvollziehbar und metadatenpflichtig ist.

---

## Aktuelle Erweiterung

v0.9.5.45 führte source-local leading digit recovery ein. v0.9.5.47 dokumentiert die Grenze dieses Ansatzes: Die nächste Version benötigt context-aware candidate recovery.

