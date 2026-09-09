# New Eden Foundry

New Eden Foundry wird eine lokale Desktop-Anwendung für nachvollziehbare EVE-Online-Industrieplanung. Sie führt Charakterdaten, Assets, Blueprints, Jobs, Marktinformationen, Projekte und PI in einem cache-first Arbeitsablauf zusammen.

## Projektstatus

**Technische Preview – `v0.0.4-preview.5`.** Die Desktop-App führt den echten EVE-SSO-Dialog bis zur geprüften Charakteridentität aus und bewahrt den danach erhaltenen Refresh Token pro Charakter im Windows-Anmeldespeicher auf. Neue und rotierte Werte werden zweistufig geschrieben und zurückgelesen, bevor der bisherige aktive Wert ersetzt wird. Access Tokens bleiben ausschließlich im Speicher des Sidecars. Verbundene Charaktere erscheinen dauerhaft in der echten Charakterliste; alle sichtbaren Texte können global in fünf gespeicherten Stufen skaliert werden.

Verbundene Identitäten und Scope-Status stammen aus SQLite; Geheimnisse werden dort nie abgelegt. Die Fachwerte der Mehrcharakter-Vorschau bleiben dagegen klar synthetisch. Der zentrale ESI-Client, SDE, echte Synchronisierung und fachliche Berechnungen sind noch nicht angeschlossen. Eine neue Installation meldet korrekt, dass noch keine lokalen Fachdaten vorhanden sind. Versionen werden weiterhin manuell über [GitHub Releases](https://github.com/Savox76/eve-test-indu/releases) bezogen; das vollständige Windows-Installationsgate bleibt Voraussetzung für die erste technische Alpha.

Registrierungswerte stehen im [verbindlichen Registrierungsprofil](docs/sso-registration.md); Ablauf und Sicherheitsgrenze beschreiben die [PKCE-Betriebsdokumentation](docs/sso-pkce-login.md), die [Token-/Charakterprüfung](docs/sso-token-validation.md) und die [Tokenablage mit Rotation](docs/token-security.md). Die Anwendung enthält kein Client Secret und gibt weder Tokens noch `state`, Verifier oder Autorisierungscode an Oberfläche oder Logs weiter. Die Bedienung der Schriftstufen beschreibt [appearance.md](docs/appearance.md).

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
