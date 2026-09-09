# ADR-006: Cache-first-Synchronisierung mit sichtbarer Datenalterung

- **Status:** Angenommen
- **Datum:** 7. September 2026
- **Entscheider:** Projektverantwortlicher

## Kontext

ESI ist ein Fremdsystem mit Cacheheadern, Pagination, Ratenbegrenzung und zeitweisen Fehlern. Eine Oberfläche, die beim Start ausschließlich auf Liveantworten wartet oder bekannte Daten durch leere Ergebnisse ersetzt, ist für tägliche Planung unzuverlässig.

## Entscheidung

Alle Ansichten starten aus dem letzten konsistenten lokalen Snapshot und synchronisieren anschließend im Hintergrund.

- Jede Datenmenge führt Zeitpunkt, Quelle, Ergebnisstatus und fachliche Vollständigkeit des letzten Versuchs.
- Die UI unterscheidet frisch, veraltet, teilweise, nie geladen, synchronisierend und fehlgeschlagen.
- Ein fehlgeschlagener Abruf behält den letzten erfolgreichen Snapshot und zeigt Fehler sowie Alter.
- ETag, Expires und vergleichbare Cacheinformationen werden zentral beachtet.
- Pagination wird vollständig abgeschlossen, bevor ein Lauf als erfolgreich gilt.
- Rate-Limit- und Fehlerbudgets, `Retry-After`, begrenzter Backoff und Circuit Breaker liegen im zentralen ESI-Client.
- Nutzerinitiierte Aktualisierung ignoriert keine Servergrenzen und erzeugt keine parallelen Duplikatläufe.
- Deltas entstehen nur zwischen zwei vollständigen, vergleichbaren Snapshots.

## Folgen

Jede Fachansicht benötigt Zustände für Alterung und Teilverfügbarkeit. Das Datenmodell speichert Laufmetadaten zusätzlich zu Nutzdaten. Cache-Invalidierung und Speicheraufbewahrung werden fachlich definiert, nicht pro Komponente improvisiert.

Seit Schema-Version 4 trägt ein Cache-Snapshot optional seinen bestätigten Ablaufzeitpunkt. Der lokale Startpfad unterscheidet `loading`, `refreshing`, `empty`, `fresh`, `stale`, `offline` und `error`. Nur Snapshots vollständig abgeschlossener Läufe dürfen als verfügbar gelten. Fehlgeschlagene oder laufende Folgeläufe ändern den gespeicherten Snapshot nicht; unbekannte oder fehlende Ablaufmetadaten werden vorsichtshalber als veraltet behandelt.

## Verifikation

Golden- und Integrationstests simulieren 304, Pagination, 403 für Strukturen, 420/429, 5xx, Timeout, abgebrochenen Lauf und Offline-Start. In keinem Fall wird ein bekannter vollständiger Snapshot stillschweigend geleert.

## Referenzen

- [EVE Developer Documentation – ESI](https://developers.eveonline.com/docs/services/esi/)
- [Lebender Masterplan](../MASTERPLAN.md)
