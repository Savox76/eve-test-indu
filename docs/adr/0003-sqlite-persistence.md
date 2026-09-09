# ADR-003: SQLite mit Foreign Keys, WAL, Wartezeit und Migrations-Backups

- **Status:** Teilweise ersetzt durch ADR-010
- **Datum:** 7. September 2026
- **Entscheider:** Projektverantwortlicher

## Kontext

Eine Einzelplatzanwendung benötigt transaktionale lokale Persistenz, schnelle Suche und paralleles Lesen während eines Hintergrund-Syncs. Ein externer Datenbankdienst widerspricht dem local-first Betriebsmodell.

## Entscheidung

Die ursprüngliche Entscheidung sah eine SQLite-Datei im betriebssystemspezifischen Anwendungsdatenverzeichnis vor. **Dieser Speicherort wurde durch [ADR-010](0010-program-folder-storage.md) ersetzt.** Foreign Keys, WAL, Wartezeit, Migrationen und Backups aus dieser ADR gelten unverändert weiter.

Jede Verbindung setzt und prüft mindestens:

- `PRAGMA foreign_keys = ON`
- `PRAGMA journal_mode = WAL`
- `PRAGMA busy_timeout = 5000`

Zusätzlich gelten folgende Regeln:

- Schemaänderungen laufen ausschließlich über nummerierte, vorwärts gerichtete Migrationen.
- Vor einer Migration wird eine konsistente Sicherung der vorhandenen Datenbank erzeugt.
- Erst erfolgreiche Migration und Integritätsprüfung ersetzen den bisherigen Stand.
- Die Sicherung verwendet die SQLite-Backup-API, wird zunächst als temporäre Datei geschrieben und nach `quick_check`, `foreign_key_check`, Schema- und SHA-256-Prüfung atomar unter `data\backups` veröffentlicht.
- Scheitert eine Sicherung, beginnt die Migration nicht. Scheitert die Migration oder ihre Abschlussprüfung, wird der geprüfte vorherige Stand automatisch wiederhergestellt.
- Die Datenbankhistorie vermerkt Dateiname, Quell- und Ziel-Schema, SHA-256, Größe und Erstellungszeit. Automatisch werden die fünf neuesten Migrationssicherungen aufbewahrt.
- Synchronisierung schreibt in kurzen Transaktionen; UI-Lesen darf nicht unnötig blockiert werden.
- Ein vollständiger Sync wird atomar als aktuell markiert. Abgebrochene Läufe erzeugen keinen falschen Snapshot und keine Deltas.
- Backups, WAL-Checkpointing, Wiederherstellung und maximaler Speicherverbrauch werden als Betriebsfunktionen getestet.

## Folgen

WAL erzeugt zusätzliche `-wal`- und `-shm`-Dateien und setzt ein lokales Dateisystem voraus. Schreibkonkurrenz muss im Datenzugriff zentral gesteuert werden. SQL- und Migrationslogik bleibt SQLite-spezifisch; ein späterer Serverbetrieb wäre eine neue Architektur.

## Verifikation

- Automatisierte Tests prüfen die drei PRAGMAs auf jeder produktiven Verbindung.
- Ein Integrationsfall liest während eines simulierten Sync-Schreibvorgangs.
- Eine Testmigration kann aus ihrer Sicherung kontrolliert wiederhergestellt werden.
- Fehlerfälle prüfen, dass eine fehlgeschlagene Sicherung das Schema nicht verändert, eine fehlgeschlagene Migration automatisch zurückgesetzt und eine beschädigte Sicherung nie eingespielt wird.
- `foreign_key_check` und ein geeigneter Integritätscheck sind nach Migration grün.

## Referenzen

- [SQLite – Write-Ahead Logging](https://www.sqlite.org/wal.html)
- [SQLite – Foreign Key Support](https://www.sqlite.org/foreignkeys.html)
- [SQLite – PRAGMA busy_timeout](https://www.sqlite.org/pragma.html#pragma_busy_timeout)
- [SQLite – Online Backup API](https://www.sqlite.org/backup.html)
