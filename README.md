# New Eden Foundry

New Eden Foundry wird eine lokale Desktop-Anwendung für nachvollziehbare EVE-Online-Industrieplanung. Sie führt Charakterdaten, Assets, Blueprints, Jobs, Marktinformationen, Projekte und PI in einem cache-first Arbeitsablauf zusammen.

## Projektstatus

**Technische Preview – `v0.0.4-preview.1`.** Die Desktop-App besitzt jetzt ein sicheres Updater-Skelett: „Offiziell“, „Beta“ und „Vorschau / Test“ sind wählbar, die Präferenz bleibt lokal in `data\foundry.sqlite3`, und ein gebündeltes Ed25519-signiertes Testmanifest wird vor der Statusfreigabe geprüft. Öffentliche Downloads und automatische Installation sind in diesem Schritt ausdrücklich deaktiviert. Cache-first Startzustände, der geschützte Sidecar sowie gemeinsame und getrennte Mehrcharakter-Übersichten bleiben die technische Grundlage.

Die Mehrcharakter-Oberfläche arbeitet weiterhin mit drei klar synthetischen Figuren und liest diese Vorschauwerte noch nicht aus SQLite. EVE SSO, ESI, SDE, echte Synchronisierung und fachliche Berechnungen sind noch nicht angeschlossen. Eine neue Installation meldet deshalb korrekt, dass noch keine lokalen Daten vorhanden sind. Versionen werden weiterhin manuell über [GitHub Releases](https://github.com/Savox76/eve-test-indu/releases) bezogen; das vollständige Windows-Installationsgate bleibt Voraussetzung für die erste technische Alpha.

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

Die portable ZIP enthält Hauptprogramm und Sidecar und benötigt die Microsoft Edge WebView2 Runtime, die auf unterstützten aktuellen Windows-10- und Windows-11-Systemen normalerweise vorhanden ist. Beim ersten Start entsteht im entpackten Programmordner `data\foundry.sqlite3`; der Zielordner muss daher beschreibbar sein. Beim Update einer vorhandenen Datenbank wird eine erforderliche Migrationssicherung automatisch unter `data\backups` angelegt. Zum Umziehen oder manuellen Sichern wird die geschlossene Anwendung einschließlich des kompletten Ordners `data` kopiert. Spätere Zugangsdaten bleiben getrennt im Windows-Anmeldespeicher. Zu jeder Variante gehört eine gleichnamige `.sha256`-Datei zur Integritätsprüfung.

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
