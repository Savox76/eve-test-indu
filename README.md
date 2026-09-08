# New Eden Foundry

New Eden Foundry wird eine lokale Desktop-Anwendung für nachvollziehbare EVE-Online-Industrieplanung. Sie führt Charakterdaten, Assets, Blueprints, Jobs, Marktinformationen, Projekte und PI in einem cache-first Arbeitsablauf zusammen.

## Projektstatus

**Technische Preview – `v0.0.2-preview.2`.** Die Windows-Vorschau unterstützt jetzt eine gemeinsame Übersicht und getrennte Ansichten für mehrere Charaktere aus mehreren lokalen Kontogruppen. Im Backend speichert Schema-Version 2 diese Zuordnung und die pro Charakter gewährten SSO-Scopes. Die Tauri-Schale meldet weiterhin ihren echten Laufzeitstatus über IPC; Installer und portable ZIP bleiben beide verfügbar.

Die neue Mehrcharakter-Oberfläche arbeitet weiterhin mit drei klar synthetischen Figuren. SQLite wird noch nicht von der App gestartet oder für Nutzerdaten verwendet; FastAPI-Sidecar, EVE SSO, ESI, SDE und fachliche Berechnungen sind noch nicht angeschlossen. Die Vorschau ist als Prerelease unter [GitHub Releases](https://github.com/Savox76/eve-test-indu/releases) vorgesehen; die erste technische Alpha entsteht erst nach dem vollständigen vertikalen Architektur-Durchstich.

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

Die portable ZIP benötigt die Microsoft Edge WebView2 Runtime, die auf unterstützten aktuellen Windows-10- und Windows-11-Systemen normalerweise vorhanden ist. „Portable“ beschreibt die Auslieferung ohne Installation: Künftige lokale Daten bleiben im Windows-Benutzerprofil und Zugangsdaten im Windows-Anmeldespeicher. Es handelt sich nicht um einen spurenlosen USB-Modus. Zu jeder Variante gehört eine gleichnamige `.sha256`-Datei zur Integritätsprüfung.

## Lokale Entwicklung

Voraussetzungen sind Node.js 24 sowie für das Desktop-Paket die aktuellen Rust- und Tauri-Systemvoraussetzungen.

```powershell
npm ci
npm run dev
```

Die Qualitätsprüfung läuft mit:

```powershell
npm run typecheck
npm test
npm run build
python scripts/check_repository_policy.py
```

Ein lokaler Selbsttest der neuen SQLite-Grundlage lässt sich zusätzlich ausführen mit:

```powershell
python -m backend.new_eden_foundry_backend --database .\foundry-development.sqlite3
```

## Repository

`Savox76/eve-test-indu` ist die einzige öffentliche Projektfläche für Quellcode, Dokumentation, Issues, GitHub Actions und Releases. Quellcode, Entwicklungshistorie und veröffentlichte Releases sind damit öffentlich einsehbar.

## Mitwirken

Arbeitsweise, Commit-Konvention und Abnahmeregeln stehen in [CONTRIBUTING.md](CONTRIBUTING.md). Sicherheitsmeldungen folgen [SECURITY.md](SECURITY.md).

## Rechtlicher Hinweis

New Eden Foundry ist ein unabhängiges Drittanbieterprojekt und nicht mit CCP Games verbunden. EVE Online und zugehörige Marken gehören ihren jeweiligen Rechteinhabern.
