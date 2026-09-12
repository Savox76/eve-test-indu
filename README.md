# New Eden Foundry

New Eden Foundry wird eine lokale Desktop-Anwendung für nachvollziehbare EVE-Online-Industrieplanung. Sie führt Charakterdaten, Assets, Blueprints, Jobs, Marktinformationen, Projekte und PI in einem cache-first Arbeitsablauf zusammen.

## Projektstatus

**Technische Preview – `v0.0.5-preview.23`.** Assets, persönliche Blueprints, Industrieaufträge und Skillstände aller aktivierten Charaktere werden charaktergetrennt synchronisiert. Assets starten in einer nach Gegenstand gruppierten Bestandsübersicht mit Drill-down auf Einzelpositionen. Blueprint-Snapshot-Status, klare Jobzustände mit Restzeit und Anlagenfilter für Highsec, Lowsec und Nullsec machen fehlende oder laufende Daten sichtbar. Fertigungs- und Reaktionsziele zeigen Vorprodukte zuerst und das gewählte Zielprodukt als letzten Schritt. Bestand, Reservierungen, Blueprint-ME, Charakter-, Anlagen- und Rigmodifikatoren, Steuern und Preise bleiben bei der Bruttomaterialplanung ausdrücklich unberücksichtigt.

Charakteridentitäten, Aliasse, Gruppen, Scope-Status, Forschungs- und Produktionspläne stammen aus SQLite; Refresh Tokens bleiben im Windows-Anmeldespeicher und Access Tokens ausschließlich im Sidecar-Prozess. Installer und Portable speichern Datenbank, Backups und Exporte sichtbar in `data` direkt neben der Haupt-EXE. Die App prüft automatisch und auf Knopfdruck, ob im gewählten Kanal ein vollständiges neueres GitHub Release bereitsteht, und zeigt den passenden Installer- oder Portable-Hinweis. Download und Installation bleiben bis zu einer produktiv signierten Updatekette bewusst manuell. `v0.0.5-preview.23` übernimmt die Korrekturen aus `.22` und akzeptiert zusätzlich den vom lokalen Kern vorgesehenen frischen Cache ohne eigenes Ablaufdatum. Dadurch bleibt ein vorhandener Datenkern beim Versionsstart verfügbar, statt mit `sidecar-ready-invalid` abgewiesen zu werden. Sie ist der aktuelle Kandidat für die [verbindliche Windows-A0-Abnahme](docs/windows-a0-acceptance.md).

Registrierungswerte stehen im [verbindlichen Registrierungsprofil](docs/sso-registration.md); die Betriebsgrenzen beschreiben die [PKCE-Dokumentation](docs/sso-pkce-login.md), die [Tokenprüfung](docs/sso-token-validation.md), die [Tokenablage](docs/token-security.md), die [Charakterverwaltung](docs/character-management.md), der [zentrale ESI-Client](docs/esi-client.md), der [Asset-Sync](docs/asset-sync.md), die [Standortauflösung](docs/location-resolution.md), die [Asset-Oberfläche mit CSV-Export](docs/asset-ui.md), die [Asset-Deltas](docs/asset-deltas.md), der [Blueprint-Bestand](docs/blueprint-inventory.md), die [Industrieaufträge](docs/industry-jobs.md), die [Charakter-Skills](docs/character-skills.md), die [Industrieanlagen](docs/industry-facilities.md), die [Forschungsplanung](docs/research-planning.md), die [Industrie-Slotübersicht](docs/industry-slots.md), die [Blueprint-Aktivitätsbasis](docs/blueprint-activity-basis.md) und die [Produktionsplanung](docs/production-planning.md). Die Anwendung enthält kein Client Secret und gibt weder Tokens noch `state`, Verifier oder Autorisierungscode an Oberfläche oder Logs weiter.

## Verbindliche Grundlagen

- Windows-first, Einzelplatz und local-first
- Tauri-2-Desktop-Schale mit React/TypeScript
- lokaler Python/FastAPI-Sidecar
- SQLite ohne Redis, PostgreSQL oder Docker im Endnutzerbetrieb
- EVE SSO über Authorization Code mit PKCE und Systembrowser
- keine echten Nutzerdaten in Repository, Tests, Dokumentation oder Screenshots; ausschließlich synthetische Testdaten und prüfsummengebundene öffentliche EVE-Stammdaten
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

Die portable ZIP enthält Hauptprogramm und Sidecar im konstanten Ordner `New Eden Foundry Portable` und benötigt die Microsoft Edge WebView2 Runtime. „Portable“ bedeutet hier einen vollständig entpackbaren, verschiebbaren Programmordner auf dem Desktop, einem USB-Stick oder an jedem anderen beschreibbaren Ort – niemals den Installationsordner, den Start direkt im ZIP oder eine einzelne EXE. Beim ersten Start entsteht dort `data\foundry.sqlite3`. Für ein Update die App schließen, `data` zusätzlich sichern und entweder nur die ausgelieferten Programmdateien am bisherigen Ort ersetzen oder `data` in einen neu entpackten portablen Ordner übernehmen. EVE-Refresh-Tokens bleiben getrennt im Windows-Anmeldespeicher. Zu jeder Variante gehört eine gleichnamige `.sha256`-Datei.

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
