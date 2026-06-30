# Sentinel Data Guard -- Die Integritätsschicht von Sentinel

Der **Sentinel Data Guard** ist nicht einfach eine weitere
Validierungskomponente. Er ist die zentrale Integritätsschicht der
gesamten Sentinel-Architektur.

Seine Aufgabe besteht darin, **Operational Truth** zu schützen.

Alle späteren Komponenten -- Command Center, Historie, Intelligence,
Assessments und Empfehlungen -- verlassen sich darauf, dass die Daten,
die den Data Guard verlassen, vertrauenswürdig sind.

------------------------------------------------------------------------

## Warum der Data Guard entstanden ist

Die Entwicklung der letzten Sprints hat gezeigt, dass OCR-Fehler selten
das eigentliche Problem sind.

Das größere Problem waren **stille Datenfehler**, beispielsweise:

-   Screenshots wurden dem falschen Server zugeordnet (551 → 552).
-   Einzelne Ranking-Blöcke wurden automatisch anderen Servern
    zugeordnet.
-   THP-Zeilen tauchten plötzlich im Alliance-Power-Ranking auf.
-   Korrekte OCR-Ergebnisse wurden durch falsche nachgelagerte
    Entscheidungen verfälscht.

Diese Fehler waren besonders gefährlich, weil sie plausibel aussahen und
dadurch unbemerkt in die Datenbasis gelangten.

------------------------------------------------------------------------

# Architekturprinzip

Der Parser extrahiert Informationen.

Der Data Guard beantwortet anschließend genau eine Frage:

> **Kann Sentinel diesen Informationen vertrauen?**

Nicht:

> *Sind sie wahrscheinlich richtig?*

Sondern:

> **Sind sie ausreichend durch die vorhandenen Belege abgesichert?**

Dieser Unterschied ist entscheidend.

------------------------------------------------------------------------

# Aufgabe des Data Guard

Der Data Guard schützt ausschließlich die Integrität der Daten.

Er darf:

-   validieren
-   Konflikte erkennen
-   Unsicherheit erklären
-   Daten blockieren
-   Daten in Quarantäne verschieben

Er darf niemals:

-   raten
-   Daten erfinden
-   automatisch „reparieren"
-   widersprüchliche Daten zusammenführen
-   Dateinamen oder Zeitstempel als Wahrheit interpretieren

Seine Philosophie lautet:

> **Protect truth --- never fabricate it.**

------------------------------------------------------------------------

# Warum Quarantäne eingeführt wurde

Während v0.9.5.22 zeigte sich:

Die automatische Zusammenführung ("Auto Merge") beseitigte zwar den
falschen Server 552, führte aber gleichzeitig dazu, dass unsichere Daten
stillschweigend Server 551 zugeordnet wurden.

Das war zwar optisch schöner, architektonisch jedoch falsch.

Deshalb wurde die Philosophie geändert:

``` text
Unsicher
    ↓
Sentinel Data Guard
    ↓
Sentinel Data Quality Loop
    ↓
OCR-Recovery
    ↓
Erneute Validierung
    ↓
Quarantäne
    ↓
Manuelles Review
```

Unsicherheit wird nicht versteckt, sondern bewusst erhalten.

------------------------------------------------------------------------

# Die Rolle des Sentinel Data Quality Loop

Der Data Guard entscheidet **nicht**, ob OCR erneut ausgeführt wird.

Er erkennt lediglich, dass die vorhandenen Beweise nicht ausreichen.

Dann übernimmt der **Sentinel Data Quality Loop**.

Seine Aufgabe ist es, die Quelle zu verbessern, nicht die Daten.

Beispiele:

-   Header zuschneiden
-   Kontrast erhöhen
-   CLAHE
-   Upscaling
-   Schärfen
-   Thresholding
-   erneuter OCR-Lauf

Erst danach bewertet der Data Guard die neuen OCR-Ergebnisse erneut.

Falls die Evidenz weiterhin nicht ausreicht, erfolgt konsequent die
Quarantäne.

Der Quality Loop versucht also, bessere Beweise zu erzeugen -- niemals
bessere Vermutungen.

------------------------------------------------------------------------

# Warum der Data Guard das Fundament von Sentinel ist

Alle zukünftigen Module verlassen sich auf ihn.

Zum Beispiel:

-   Recruitment Intelligence
-   Whale Detection
-   Alliance Stability
-   Transfer Intelligence
-   Morning Briefing
-   Decision Center

Keines dieser Module überprüft später erneut die Rohdaten.

Sie vertrauen darauf, dass der Data Guard bereits entschieden hat:

-   **trusted**
-   **untrusted**

Der Data Guard bildet damit das Fundament der gesamten Plattform.

------------------------------------------------------------------------

# Der Data Guard ist keine OCR-Komponente

Ein häufiger Denkfehler wäre:

> "Wenn OCR irgendwann besser wird, braucht man den Data Guard nicht
> mehr."

Genau das Gegenteil ist der Fall.

Je leistungsfähiger OCR wird und je mehr Daten Sentinel verarbeitet,
desto wichtiger wird eine unabhängige Integritätsschicht.

Die Architektur lautet bewusst:

``` text
Screenshot
    ↓
OCR
    ↓
Parser
    ↓
Sentinel Data Guard
    ↓
Sentinel Data Quality Loop (bei Unsicherheit)
    ↓
Operational Truth
    ↓
Snapshot
    ↓
Strategic Intelligence
```

Jede Schicht besitzt eine klar definierte Verantwortung.

Diese Schichten dürfen niemals vermischt werden.

------------------------------------------------------------------------

# Langfristige Vision

Der Sentinel Data Guard soll sich langfristig zu einem modularen
Validierungsframework entwickeln.

``` text
Sentinel Data Guard
│
├── Server Guard
├── Ranking Guard
├── Value Guard
├── Entity Guard
├── Consistency Guard
├── Snapshot Guard
├── History Guard
└── Intelligence Guard
```

Jeder Guard schützt genau eine Ebene der Datenintegrität.

Dadurch bleibt Sentinel jederzeit nachvollziehbar, erklärbar und
auditierbar.

------------------------------------------------------------------------

# Grundprinzip

> **Lieber eine Zeile zu viel in Quarantäne als eine einzige falsche
> Zeile in der Operational Truth.**

Sentinel Data Guard existiert nicht, um Daten zu verbessern.

Er existiert, um die Integrität der gesamten Plattform zu schützen.

Erst auf einer vertrauenswürdigen Datenbasis kann Sentinel belastbare
strategische Intelligenz erzeugen.
