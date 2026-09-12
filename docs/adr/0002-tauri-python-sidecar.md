# ADR-002: Tauri-Schale mit Python-Sidecar und abgesicherter Loopback-API

- **Status:** Angenommen
- **Datum:** 7. September 2026
- **Entscheider:** Projektverantwortlicher

## Kontext

Die Oberfläche benötigt eine kleine Desktop-Schale und sicheren Zugriff auf lokale Funktionen. Die fachliche Logik profitiert von Pythons Daten- und Optimierungsökosystem. Ein dauerhaft installierter Systemdienst oder ein fester lokaler Port würde zusätzliche Betriebs- und Angriffsfläche schaffen.

## Entscheidung

Die Desktop-Schale wird mit Tauri 2 und Rust gebaut, die Oberfläche mit React/TypeScript. Fachlogik, ESI/SDE-Zugriff, Synchronisierung und Berechnungen laufen in einem gebündelten Python/FastAPI-Sidecar.

- Tauri besitzt den Sidecar-Lebenszyklus und startet höchstens einen Kindprozess.
- Der Sidecar bindet ausschließlich an `127.0.0.1` und lässt den Port durch das Betriebssystem wählen.
- Tauri erzeugt je Start ein kryptografisch zufälliges Sitzungstoken mit mindestens 256 Bit Entropie.
- Das Token wird weder als Kommandozeilenargument noch im Log geführt. Tauri übergibt eine einzelne versionierte JSON-Startnachricht mit Token und Programmordner ausschließlich über die Standardeingabe des Kindprozesses.
- Der Sidecar meldet seine Bereitschaft und den gewählten Port maschinenlesbar; eine fehlerhafte oder verspätete Bereitschaft bricht kontrolliert ab.
- Jede lokale HTTP-Anfrage einschließlich `/health` wird authentifiziert. CORS ist nicht als Sicherheitsgrenze anzusehen.
- Die WebView erhält nur die minimal nötigen Tauri-Capabilities. Beliebige Shell-Ausführung ist ausgeschlossen.
- Beim Beenden der App wird der Kindprozess kontrolliert beendet; ein verwaister Prozess gilt als Fehler.
- Das Single-Instance-Plugin wird vor allen anderen Plugins registriert. Ein zweiter Windows-Start fokussiert die bestehende Hauptinstanz und erreicht daher keinen zweiten Sidecar-Start.

## Folgen

Für jedes freigegebene Zielsystem muss ein passender Sidecar gebaut und zusammen mit Tauri paketiert werden. Der Windows-x64-Sidecar wird mit PyInstaller im `onedir`-Modus erzeugt und von Tauri zusammen mit seinem Ordner `foundry-sidecar-lib` als Ressource neben der Haupt-EXE installiert. Die frühere selbstentpackende `onefile`-Ausgabe wurde nach einer Defender-Erkennung von `v0.0.5-preview.18` verworfen: Der entpackte Aufbau vermeidet beim Start temporär extrahierten eingebetteten Code und lässt die tatsächlich ausgelieferten Laufzeitdateien prüfen. Startprotokoll, Prozessüberwachung, Port-/Token-Handshake und Shutdown benötigen Integrations-, Defender- und Pakettests. Der interne API-Vertrag wird versioniert.

## Verifikation

Architektur-Gate A0 muss auf Windows Start, dynamischen Port, Ablehnung ohne beziehungsweise mit falschem Token, paralleles SQLite-Lesen, Shutdown und Installation beweisen. Scheitert das Gate, wird diese ADR ersetzt, bevor Fachmodule auf dem Sidecar aufbauen.

## Referenzen

- [Tauri – Embedding External Binaries](https://v2.tauri.app/develop/sidecar/)
- [Tauri – Capabilities](https://v2.tauri.app/security/capabilities/)
- [FastAPI](https://fastapi.tiangolo.com/)
