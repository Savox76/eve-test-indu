# ADR-014: Cache-first Startabgleich und persistente öffentliche Typnamen

## Kontext

Die Asset-Ansicht musste bislang manuell aktualisiert werden. Ohne gebündelten vollständigen SDE-Bestand erschienen unbekannte Inventartypen außerdem nur als `Type #<ID>`. Ein synchroner Netzabruf vor Anzeige der Oberfläche würde den cache-first Startpfad verletzen.

## Entscheidung

Nach dem Laden des lokalen Kerns startet die Desktop-Oberfläche genau einen Hintergrund-Abgleich für alle aktivierten Charaktere. Derselbe Abgleich läuft nach einer neuen Charakterverbindung; der manuelle Befehl bleibt verfügbar. Vorhandene vollständige Snapshots bleiben sofort sichtbar.

Unbekannte Type-IDs werden über den öffentlichen ESI-Endpunkt `/universe/names/` in Paketen von höchstens 1.000 IDs aufgelöst. Streng validierte Inventartypnamen werden in der versionierten SQLite-Tabelle `resolved_type_names` gespeichert. Vorhandene lokale SDE-Namen haben beim Lesen Vorrang.

## Folgen

- Ein normaler Programmstart aktualisiert aktivierte Charaktere ohne weiteren Klick.
- Wiederkehrende Type-IDs benötigen nach erfolgreicher Auflösung keinen erneuten Namensabruf.
- Die Schema-6-zu-7-Migration erzeugt vorab eine geprüfte Sicherung.
- Netzwerkfehler dürfen den letzten vollständigen Bestand nicht löschen; die Oberfläche bleibt cache-first.

## Verifikation

- Frontendtests sichern genau einen Startabgleich und die Sortierparameter ab.
- ESI-Tests prüfen Hostbindung, begrenzten JSON-POST, fehlende Autorisierung und Payload-Cache.
- Backendtests prüfen 1.000er-Pakete, strenge Kategorien, Persistenz und Sortierung vor Pagination.
- Die Windows-A0-Abnahme prüft Migration und Datenerhalt auf dem Zielgerät.

## Referenzen

- [ADR-006: Cache-first-Synchronisierung](0006-cache-first-sync.md)
- [ADR-013: Updatefeste Anwendungsdaten](0013-update-stable-application-data.md)
- [Charakter-Asset-Sync](../asset-sync.md)
- [Asset-Oberfläche und CSV-Export](../asset-ui.md)
