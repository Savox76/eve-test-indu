# Asset-Standortauflösung – Paket 19

Die Standortauflösung verarbeitet immer den letzten vollständig abgeschlossenen Asset-Snapshot eines einzelnen Charakters. Das Ergebnis wird als eigener Snapshot `asset_locations:<character_id>` veröffentlicht. Der zugrunde liegende Asset-Snapshot und dessen Sync-Run bleiben im Ergebnis referenziert.

## Pfadmodell

Jeder Assetpfad wird von außen nach innen gespeichert:

`Sonnensystem → Station oder Struktur → äußerer Container → innerer Container`

Der Pfad enthält nicht das Asset selbst. Containerbezeichnungen stammen aus dem atomar importierten SDE-Typbestand. Statische Standorte werden bevorzugt aus dem SDE-Bestand gelesen; nur fehlende Stationen und dynamische Spielerstrukturen benötigen einen ESI-Aufruf.

## Statuswerte

| Status | Bedeutung |
| --- | --- |
| `resolved` | Der Standort und alle vorhandenen Containerstufen wurden aufgelöst. |
| `restricted` | Eine Spielerstruktur ist für den Charakter nicht lesbar oder der notwendige Scope fehlt. Bekannte Containerstufen bleiben erhalten. |
| `unresolved` | Ein Standort, ein externer Container oder ein SDE-Eintrag fehlt. |
| `cycle` | Die Containerbeziehungen enthalten einen Zyklus und werden kontrolliert beendet. |

Fehlercodes wie `structure_forbidden`, `structure_scope_missing`, `container_missing` und `container_cycle` sind stabil und enthalten weder ESI-Rohantworten noch Zugangsdaten.

## Stationen und Strukturen

- NPC-Stationen werden aus dem SDE-Bestand oder über `/universe/stations/{station_id}/` aufgelöst.
- Spielerstrukturen werden charakterbezogen über `/universe/structures/{structure_id}/` mit `esi-universe.read_structures.v1` gelesen.
- Eine ESI-Antwort mit HTTP 403 ist ein erwartbarer Fachzustand. Die Struktur wird als `restricted` gespeichert; der gesamte Lauf bleibt erfolgreich und verwendbar.
- Ohne den Struktur-Scope wird kein aussichtsloser ESI-Aufruf ausgeführt. Der Standort erhält `structure_scope_missing`.
- Ein vorübergehender Netzwerk-, Retry- oder Circuit-Breaker-Fehler bricht dagegen den neuen Lauf ab und erhält den letzten vollständigen Standort-Snapshot.

## Sicherheits- und Vollständigkeitsgrenze

Die Auflösung arbeitet ausschließlich auf einem vollständigen Asset-Snapshot. Externe Aufrufe erfolgen über den zentralen ESI-Client. Erst nachdem alle Assets aufgelöst oder mit einem stabilen Fachstatus versehen wurden, werden Ergebnis-Snapshot und Sync-Run atomar abgeschlossen. Ein technischer Abbruch veröffentlicht keinen Teilstand.

Die synthetischen Golden-Fälle prüfen verschachtelte Container, gemeinsame Stationswurzeln, Struktur-403, fehlenden Struktur-Scope, zyklische Container und den Erhalt des letzten vollständigen Standortstands bei einem Folgefehler.
