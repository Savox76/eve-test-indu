# ADR-016: Belegbasierte Industrie-Jobkorrelation

## Kontext

Asset-Deltas aus Paket 21 enthalten stabile Typ-, Richtungs-, Orts- und Zeitnachweise. Paket 23 ergänzt vollständige charaktergetrennte Blueprint-Snapshots. Ein Industrieauftrag darf damit verbunden werden, ohne eine stärkere Kausalität zu behaupten, als ESI tatsächlich belegt. Gleichzeitig dürfen spätere Jobdaten weder historische Delta-Fingerabdrücke verändern noch einen von mehreren plausiblen Kandidaten willkürlich auswählen.

## Entscheidung

Persönliche Industrieaufträge werden als eigene vollständige charaktergetrennte Snapshots gespeichert. Beim Lesen wird die exakte Blueprint-Item-ID gegen aktuelle und historische vollständige Blueprint-Snapshots geprüft. Für ausgelieferte Jobs wird das Produkt nur mit eingehenden Asset-Änderungen desselben Charakters und Typs verbunden, deren Beobachtungsfenster das Abschlussdatum enthält; eine passende Ausgabelocation hat Vorrang.

Genau ein Kandidat ergibt `linked`, mehrere Kandidaten ergeben `ambiguous`. Fehlende Quellen, ausstehende Jobs und nicht anwendbare Fälle bleiben eigene Zustände. Die Asset-Historie leitet ihre Jobzuordnung in Gegenrichtung aus denselben geprüften Quellen ab. Gespeicherte Asset-Deltas und ihre Fingerabdrücke bleiben unverändert.

## Folgen

- Jede sichtbare Zuordnung nennt stabile Job-, Snapshot-, Run- oder Event-IDs.
- Unsicherheit und fehlende Quelldaten bleiben sichtbar statt zu einer scheinbar sicheren Zuordnung zu werden.
- Ein fehlgeschlagener Jobabruf löscht weder den letzten Jobstand noch Blueprint- oder Asset-Nachweise.
- Der Startabgleich führt Assets und Blueprints vor Jobs aus, damit die Korrelation die frischesten vollständigen Quellen verwendet.
- Bereits vor der ersten Synchronisierung nicht mehr von ESI gelieferte abgeschlossene Jobs können nicht rekonstruiert werden.

## Verifikation

- Backendtests prüfen eindeutige, mehrdeutige, ausstehende und nicht verfügbare Korrelationen sowie den Erhalt des letzten vollständigen Snapshots.
- Transporttests weisen ungültige Status-, Aktivitäts-, Summen- und Korrelationskombinationen geschlossen ab.
- Frontendtests prüfen Filter, Sortierung, begrenzte Seiten und manuelle Aktualisierung.
- Der eingefrorene Windows-Sidecar wird mit Jobabfrage und leerem Synchronisationslauf geprüft.

## Referenzen

- [ADR-006: Cache-first-Synchronisierung](0006-cache-first-sync.md)
- [ADR-014: Cache-first Startabgleich und persistente öffentliche Typnamen](0014-automatic-asset-refresh-and-type-name-cache.md)
- [Asset-Deltas](../asset-deltas.md)
- [Blueprint-Bestand](../blueprint-inventory.md)
- [Persönliche Industrieaufträge und Korrelation](../industry-jobs.md)
