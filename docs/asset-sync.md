# Charakter-Asset-Sync – Paket 18

Der Asset-Sync lädt für jeden aktivierten Charakter `/characters/{character_id}/assets/` mit dem Scope `esi-assets.read_assets.v1`.

## Vollständigkeit

- `X-Pages` steuert die Pagination; jede Seite wird genau für den jeweiligen Charakter geladen.
- Erst wenn alle Seiten erfolgreich validiert wurden, wird ein neuer `cached_snapshots`-Datensatz veröffentlicht.
- Ein abgebrochener oder fehlerhafter Lauf wird als `failed` in `sync_runs` protokolliert und veröffentlicht niemals einen Teilstand.
- Der letzte vollständig abgeschlossene Snapshot bleibt dadurch für Cache-First/Offline-Nutzung erhalten.
- Doppelte `item_id` über mehrere Seiten werden als inkonsistenter Lauf verworfen.
- Derselbe atomare Abschluss veröffentlicht zusätzlich eine leere Baseline oder ein Delta zum vorherigen vollständigen Snapshot. Ein Fehler der Delta-Bildung rollt auch den neuen Asset-Snapshot zurück.
- Derselbe atomare Abschluss veröffentlicht zusätzlich eine leere Baseline oder ein Delta zum vorherigen vollständigen Snapshot. Ein Fehler der Delta-Bildung rollt auch den neuen Asset-Snapshot zurück.

## Multi-Character

`sync_enabled_characters` ermittelt alle lokal aktivierten Charaktere. Jeder Charakter besitzt einen eigenen Sync-Run und einen eigenen Ressourcen-Schlüssel `character_assets:<character_id>`. Tokens und ESI-Cache bleiben durch den zentralen ESI-Client charaktergebunden.

## Fehler

ESI-Fehler werden nur über ihre bereinigten Fehlercodes in `sync_runs.error_code` gespeichert. Access-/Refresh-Tokens und Rohantworten werden nicht persistiert.

Die genaue Änderungssemantik und die vorbereiteten Korrelationsbelege beschreibt [Asset-Deltas und vorbereitete Jobkorrelation](asset-deltas.md).

Die genaue Änderungssemantik und die vorbereiteten Korrelationsbelege beschreibt [Asset-Deltas und vorbereitete Jobkorrelation](asset-deltas.md).
