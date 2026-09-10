# Architecture Decision Records

ADRs halten Entscheidungen fest, die Architektur, Sicherheit, Datenmodell, Betrieb oder Produktgrenzen dauerhaft beeinflussen. Angenommene ADRs werden nicht stillschweigend umgeschrieben. Ändert sich eine Entscheidung, ersetzt ein neues ADR das alte und nennt die Auswirkungen.

| ADR | Entscheidung | Status |
|---|---|---|
| [001](0001-desktop-local-first.md) | Desktop-first, Einzelplatz und local-first | Angenommen |
| [002](0002-tauri-python-sidecar.md) | Tauri-Schale mit Python-Sidecar und abgesicherter Loopback-API | Angenommen |
| [003](0003-sqlite-persistence.md) | SQLite mit Foreign Keys, WAL, Wartezeit und Migrations-Backups | Teilweise ersetzt durch ADR-010 |
| [004](0004-eve-sso-pkce.md) | EVE SSO mit PKCE, Systembrowser und Betriebssystem-Schlüsselbund | Angenommen |
| [005](0005-central-public-repository-and-releases.md) | Zentrales öffentliches Repository ohne Actions-Artefakte | Angenommen |
| [006](0006-cache-first-sync.md) | Cache-first-Synchronisierung mit sichtbarer Datenalterung | Angenommen |
| [007](0007-decimal-and-golden-tests.md) | Decimal- und Golden-Test-Pflicht für wirtschaftliche Berechnungen | Angenommen |
| [008](0008-jita-first-market-adapters.md) | Jita-first mit austauschbaren Marktadaptern | Angenommen |
| [009](0009-multi-character-scopes-and-local-account-groups.md) | Charaktergebundene EVE-Zugänge mit lokalen Kontogruppen und Gesamtansicht | Angenommen |
| [010](0010-program-folder-storage.md) | Sichtbare Datenhaltung im Programmordner | Teilweise ersetzt durch ADR-013 |
| [011](0011-signed-update-channel-skeleton.md) | Lokale Updatekanäle und signiertes Testmanifest ohne Verteilung | Angenommen |
| [012](0012-fixed-eve-sso-registration-profile.md) | Festes öffentliches EVE-SSO-Registrierungsprofil | Angenommen |
| [013](0013-update-stable-application-data.md) | Updatefeste Anwendungsdaten für Installer und Portable | Angenommen |
| [014](0014-automatic-asset-refresh-and-type-name-cache.md) | Cache-first Startabgleich und persistente öffentliche Typnamen | Angenommen |
| [015](0015-automatic-required-sso-scopes.md) | Vollständige benötigte SSO-Pakete automatisch anfordern und Scope-Drift sichtbar machen | Angenommen |

Neue ADRs verwenden vierstellige laufende Nummern und die Abschnitte **Kontext**, **Entscheidung**, **Folgen**, **Verifikation** und **Referenzen**.
