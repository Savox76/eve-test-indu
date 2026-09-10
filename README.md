# New Eden Foundry

New Eden Foundry wird eine lokale Desktop-Anwendung für nachvollziehbare EVE-Online-Industrieplanung. Sie führt Charakterdaten, Assets, Blueprints, Jobs, Marktinformationen, Projekte und PI in einem cache-first Arbeitsablauf zusammen.

## Projektstatus

**Technische Preview – `v0.0.5-preview.2`.** Der zentrale ESI-Client ist jetzt mit dem ersten echten Fachsync und der ersten echten Fachansicht verbunden: Typen, Gruppen und Orte können als atomarer SDE-Bestand aufgebaut werden, aktivierte Charaktere können ihre Assets vollständig paginiert und charaktergetrennt synchronisieren, Standort- und Containerpfade werden belastbar aufgelöst und die Asset-Oberfläche macht diese vollständigen Snapshots durchsuchbar und filterbar. Nur vollständig abgeschlossene Läufe werden als gültiger Snapshot veröffentlicht.

Charakteridentitäten, Aliasse, Gruppen und Scope-Status stammen weiterhin aus SQLite; Refresh Tokens bleiben im Windows-Anmeldespeicher und Access Tokens ausschließlich im Sidecar-Prozess. Paket 20 zeigt Besitzer, Standort, Menge und Datenalter, kombiniert Suche und Filter und schreibt auch große CSV-Ergebnisse atomar unter `data\exports`. Serverseitig begrenzte 100-Zeilen-Fenster halten die Oberfläche bei einem synthetisch geprüften Bestand von 100.000 Positionen flüssig. Versionen werden weiterhin manuell über [GitHub Releases](https://github.com/Savox76/eve-test-indu/releases) bezogen; das vollständige Windows-Installationsgate bleibt Voraussetzung für die erste technische Alpha.

Registrierungswerte stehen im [verbindlichen Registrierungsprofil](docs/sso-registration.md); die Betriebsgrenzen beschreiben die [PKCE-Dokumentation](docs/sso-pkce-login.md), die [Tokenprüfung](docs/sso-token-validation.md), die [Tokenablage](docs/token-security.md), die [Charakterverwaltung](docs/character-management.md), der [zentrale ESI-Client](docs/esi-client.md), der [Asset-Sync](docs/asset-sync.md), die [Standortauflösung](docs/location-resolution.md) und die [Asset-Oberfläche mit CSV-Export](docs/asset-ui.md). Die Anwendung enthält kein Client Secret und gibt weder Tokens noch `state`, Verifier oder Autorisierungscode an Oberfläche oder Logs weiter.

## Verbindliche Grundlagen

- Windows-first, Einzelplatz und local-first
- Tauri-2-Desktop-Schale mit React/TypeScript
- lokaler Python/FastAPI-Sidecar
- SQLite ohne Redis, PostgreSQL oder Docker im Endnutzerbetrieb
- EVE SSO über Authorization Code mit PKCE und Systembrowser
- ausschließlich synthetische Daten in Repository, Tests, Dokumentation und Screenshots
- Windows-Releases enthalten Installer und portable ZIP sowie je eine SHA-256-Prüfsumme
- keine GitHub-Actions-Artefakte; freigegebene Binärdateien liegen ausschließlich direkt an einem GitHub Release
- Merge nach `main` nur über Pull Request und vollständig grüne Pflichtprüfungen

Der lebende Projektplan steht in [docs/MASTERPLAN.md](docs/MASTERPLAN.md). Architekturentscheidungen werden als [ADRs](docs/adr/README.md) gepflegt.

## Windows herunterladen

Auf der [GitHub-Release-Seite](https://github.com/Savox76/eve-test-indu/releases) gibt es zwei Varianten:

| Variante | Verwendung |
| --- | --- |
| `*_x64-setup.exe` | Empfohlene Installation für den normalen Windows-Betrieb. |
| `*_x64-portable.zip` | Vollständig entpacken und danach `New Eden Foundry.exe` starten; keine Installation und keine Administratorrechte erforderlich. |

Die portable ZIP enthält Hauptprogramm und Sidecar und benötigt die Microsoft Edge WebView2 Runtime, die auf unterstützten aktuellen Windows-10- und Windows-11-Systemen normalerweise vorhanden ist. Beim ersten Start entsteht im entpackten Programmordner `data\foundry.sqlite3`; der Zielordner muss daher beschreibbar sein. Beim Update einer vorhandenen Datenbank wird eine erforderliche Migrationssicherung automatisch unter `data\backups` angelegt. Zum Umziehen oder manuellen Sichern wird die geschlossene Anwendung einschließlich des kompletten Ordners `data` kopiert. EVE-Refresh-Tokens bleiben getrennt im Windows-Anmeldespeicher des angemeldeten Nutzers und werden nicht mit dem portablen Ordner übertragen. Zu jeder Variante gehört eine gleichnamige `.sha256`-Datei zur Integritätsprüfung.

## Lokale Entwicklung

Voraussetzungen sind Node.js 24, Python 3.13 sowie für das Desktop-Paket die aktuellen Rust- und Tauri-Systemvoraussetzungen.

```powershell
npm ci
python -m pip install -r backend/requirements-runtime.txt
npm run dev
```

Die Qualitätsprüfung läuft mit:

```powershell
npm run typecheck
npm test
npm run build
python scripts/check_repository_policy.py
```

Ein lokaler Selbsttest der SQLite-Grundlage lässt sich zusätzlich ausführen mit:

```powershell
python -m backend.new_eden_foundry_backend --database .\foundry-development.sqlite3
```

## Repository

`Savox76/eve-test-indu` ist die einzige öffentliche Projektfläche für Quellcode, Dokumentation, Issues, GitHub Actions und Releases. Quellcode, Entwicklungshistorie und veröffentlichte Releases sind damit öffentlich einsehbar.

## Mitwirken

Arbeitsweise, Commit-Konvention und Abnahmeregeln stehen in [CONTRIBUTING.md](CONTRIBUTING.md). Sicherheitsmeldungen folgen [SECURITY.md](SECURITY.md).

## Rechtlicher Hinweis

New Eden Foundry ist ein unabhängiges Drittanbieterprojekt und nicht mit CCP Games verbunden. EVE Online und zugehörige Marken gehören ihren jeweiligen Rechteinhabern.
