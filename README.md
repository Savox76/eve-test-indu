# New Eden Foundry

New Eden Foundry wird eine lokale Desktop-Anwendung für nachvollziehbare EVE-Online-Industrieplanung. Sie führt Charakterdaten, Assets, Blueprints, Jobs, Marktinformationen, Projekte und PI in einem cache-first Arbeitsablauf zusammen.

## Projektstatus

**Alpha – `v0.2.0-alpha.11`.** Das Windows-Architektur-Gate A0 ist auf einem realen Windows-x64-Gerät bestanden. Assets und persönliche Blueprints starten in kompakten, nach Typ gruppierten Übersichten mit einheitlich transparenter Tabellendarstellung und Drill-down auf Positionen. Charakterverbindung, Berechtigungen und Kontogruppen liegen in einem eigenen Setup-Bereich; im Arbeitsbereich erscheint nur noch ein Hinweis, wenn eine Neuanmeldung nötig ist. Produktion zeigt mehrstufige Ziele in ausführbarer Reihenfolge und reserviert äußere Materialien aus dem letzten vollständigen Asset-Snapshot konfliktfrei über alle Ziele desselben Charakters. Vorhandene T1- und andere Vorprodukte können je Schritt aus Bestand verwendet, zuerst aufgebraucht oder bewusst vollständig neu gebaut werden; bei reiner Bestandsversorgung entfällt der zugehörige Blueprintschritt. Produktionsstation und optionaler Hangar beziehungsweise Container begrenzen Bestand und Reservierungen exakt auf den gewählten Standort. Die Materiallager-Auswahl verwendet tatsächlich in EVE vergebene Containernamen, bietet nur echte Container direkt auf der gewählten Station oder Struktur an und rechnet Schiffsladeräume dort nicht als verfügbaren Produktionsbestand an. Ein ausdrücklich gespeichertes Material-/Zeitprofil der gewählten Anlage wird aktivitätsgebunden mit ME, TE und aktiven Charakter-Skills vor genau einer Aufrundung kombiniert; unbekannte Struktur- oder Rigboni bleiben sichtbar unkonfiguriert. Ein vorhandenes persönliches BPO oder laufgeeignetes BPC kann dem Zielrezept und jedem tatsächlich gebauten Fertigungs-Vorproduktschritt eindeutig zugeordnet werden; seine belegten ME- und TE-Werte verändern Materialbedarf und Blueprint-Zeit genau dieses Schritts mit nachvollziehbarer Rundung und ausgewiesener Ersparnis. Jeder Produktionsschritt verbindet außerdem den stärksten passenden persönlichen Industriejob mit dem belegten Anlagen-Snapshot und zeigt Anlage, Systemkostenindex, Jobzustand und Quellen-IDs, ohne daraus unbekannte Boni abzuleiten. Die aktiven Stufen von Industry, Advanced Industry und Reactions aus dem letzten vollständigen Skill-Snapshot verkürzen jeden passenden Schritt; persönliche Zeit, Ersparnis und Quellenbeleg bleiben sichtbar. Fehlt der Skill-Snapshot, wird keine Stufe 0 erfunden und die persönliche Zeit bleibt unbekannt. Fehlende, typfalsche oder laufungeeignete Blueprint-Zuordnungen bleiben sichtbar. Physischer Bestand, vorrangig gebundene Menge, eigene Reservierung, danach freier Bestand und getrennte physische beziehungsweise reservierungsbedingte Fehlmengen bleiben nachvollziehbar. Bestände anderer Charaktere werden weiterhin bewusst nicht angerechnet. Der Desktop-Status akzeptiert auch frische Synchronisationsstände ohne eigenes Ablaufdatum, sodass Charaktere, Assets und Aktualisierung nach einem Neustart verfügbar bleiben. Eine einheitliche Typografieskala hält auch kompakte Beschriftungen in der Grundansicht lesbar. Der ME-/TE-Plan blendet vollständig erforschte BPOs standardmäßig aus und erkennt auch gestapelte Originale. Arbeitsbereich, Sprache, fachliche Filter-/Sortierauswahlen und die Größe des Programmfensters bleiben lokal erhalten.

Charakteridentitäten, Aliasse, Gruppen, Scope-Status, Forschungs- und Produktionspläne stammen aus SQLite; Refresh Tokens bleiben im Windows-Anmeldespeicher und Access Tokens ausschließlich im Sidecar-Prozess. Installer und Portable speichern Datenbank, Backups und Exporte sichtbar in `data` direkt neben der Haupt-EXE. Die App prüft automatisch und auf Knopfdruck, ob im gewählten Kanal ein vollständiges neueres GitHub Release bereitsteht, und zeigt den passenden Installer- oder Portable-Hinweis. Download und Installation bleiben bis zu einer produktiv signierten Updatekette bewusst manuell. `v0.2.0-alpha.11` ergänzt Paket 39 mit expliziten, aktivitätsgebundenen Anlagenprofilen und nachvollziehbarer Anlagenzeit; das Datenbankschema ist Version 13.

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
