# New Eden Foundry

New Eden Foundry wird eine lokale Desktop-Anwendung für nachvollziehbare EVE-Online-Industrieplanung. Sie führt Charakterdaten, Assets, Blueprints, Jobs, Marktinformationen, Projekte und PI in einem cache-first Arbeitsablauf zusammen.

## Projektstatus

**Technische Preview – `v0.0.5-preview.11`.** Assets, Blueprints, persönliche Industrieaufträge und die vollständigen Skillstände aller aktivierten Charaktere werden beim Programmstart charaktergetrennt synchronisiert. Danach werden der öffentliche NPC-Anlagenkatalog, aktivitätsspezifische Systemkostenindizes und in persönlichen Jobs beobachtete Spielerstrukturen als vollständiger Anlagen-Snapshot ergänzt. Die Forschungsplanung verbindet diese vollständigen Quellen zu persistenten ME-/TE-Zielen, Prioritäten, Slotzuständen und realen Job-/Anlagenbelegen. Eine gemeinsame Industrie-Slotübersicht stellt außerdem Fertigungs-, Reaktions- und Wissenschaftskapazität der Charaktere ihrer aktuellen Belegung und dem belegbaren Arbeitsvorrat gegenüber. Die echten Ansichten sind durchsuchbar, filterbar und sortierbar; fehlende Snapshots sowie unbekannte Struktur-/Rigboni, Forschungszeiten und Gesamtkosten werden nicht als Nullwerte geschätzt. Jede EVE-Anmeldung fordert automatisch alle aktuell benötigten SSO-Pakete an, während bestehende Charaktere bei späterer Scope-Erweiterung erhalten bleiben und sichtbar zur erneuten Anmeldung auffordern.

Charakteridentitäten, Aliasse, Gruppen, Scope-Status und Forschungspläne stammen weiterhin aus SQLite; Refresh Tokens bleiben im Windows-Anmeldespeicher und Access Tokens ausschließlich im Sidecar-Prozess. Manuelle Folgeläufe bleiben in den Asset-, Blueprint-, Job-, Skill- und Anlagen-Arbeitsbereichen verfügbar. Installierte Ausgaben speichern ihre Daten updatefest im benutzerspezifischen App-Datenordner; portable Ausgaben behalten den sichtbaren `data`-Ordner im konstanten Verzeichnis `New Eden Foundry Portable`. `v0.0.5-preview.11` ist der aktuelle Kandidat für die [verbindliche Windows-A0-Abnahme](docs/windows-a0-acceptance.md).

Registrierungswerte stehen im [verbindlichen Registrierungsprofil](docs/sso-registration.md); die Betriebsgrenzen beschreiben die [PKCE-Dokumentation](docs/sso-pkce-login.md), die [Tokenprüfung](docs/sso-token-validation.md), die [Tokenablage](docs/token-security.md), die [Charakterverwaltung](docs/character-management.md), der [zentrale ESI-Client](docs/esi-client.md), der [Asset-Sync](docs/asset-sync.md), die [Standortauflösung](docs/location-resolution.md), die [Asset-Oberfläche mit CSV-Export](docs/asset-ui.md), die [Asset-Deltas](docs/asset-deltas.md), der [Blueprint-Bestand](docs/blueprint-inventory.md), die [Industrieaufträge](docs/industry-jobs.md), die [Charakter-Skills](docs/character-skills.md), die [Industrieanlagen](docs/industry-facilities.md), die [Forschungsplanung](docs/research-planning.md) und die [Industrie-Slotübersicht](docs/industry-slots.md). Die Anwendung enthält kein Client Secret und gibt weder Tokens noch `state`, Verifier oder Autorisierungscode an Oberfläche oder Logs weiter.

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

Die portable ZIP enthält Hauptprogramm und Sidecar im konstanten Ordner `New Eden Foundry Portable` und benötigt die Microsoft Edge WebView2 Runtime. Beim ersten Start entsteht dort `data\foundry.sqlite3`. Spätere ZIPs werden nach dem Schließen in denselben übergeordneten Ordner entpackt, sodass `data` erhalten bleibt. Beim einmaligen Wechsel von einer älteren versionsabhängigen ZIP muss der bisherige `data`-Ordner kopiert werden. EVE-Refresh-Tokens bleiben getrennt im Windows-Anmeldespeicher. Zu jeder Variante gehört eine gleichnamige `.sha256`-Datei.

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
