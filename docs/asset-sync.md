# Charakter-Asset-Sync – Paket 18

Der Asset-Sync lädt für jeden aktivierten Charakter `/characters/{character_id}/assets/` mit dem Scope `esi-assets.read_assets.v1`.

## Vollständigkeit

- `X-Pages` steuert die Pagination; jede Seite wird genau für den jeweiligen Charakter geladen.
- Erst wenn alle Seiten erfolgreich validiert wurden, wird ein neuer `cached_snapshots`-Datensatz veröffentlicht.
- Ein abgebrochener oder fehlerhafter Lauf wird als `failed` in `sync_runs` protokolliert und veröffentlicht niemals einen Teilstand.
- Der letzte vollständig abgeschlossene Snapshot bleibt dadurch für Cache-First/Offline-Nutzung erhalten.
- Doppelte `item_id` über mehrere Seiten werden als inkonsistenter Lauf verworfen.

## Multi-Character

`sync_enabled_characters` ermittelt alle lokal aktivierten Charaktere. Jeder Charakter besitzt einen eigenen Sync-Run und einen eigenen Ressourcen-Schlüssel `character_assets:<character_id>`. Tokens und ESI-Cache bleiben durch den zentralen ESI-Client charaktergebunden.

## Fehler

ESI-Fehler werden nur über ihre bereinigten Fehlercodes in `sync_runs.error_code` gespeichert. Access-/Refresh-Tokens und Rohantworten werden nicht persistiert.
