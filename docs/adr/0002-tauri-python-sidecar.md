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
- Das Token wird weder als Kommandozeilenargument noch im Log geführt. Der konkrete IPC-Transport wird im Architektur-Gate A0 durch einen Test festgeschrieben.
- Der Sidecar meldet seine Bereitschaft und den gewählten Port maschinenlesbar; eine fehlerhafte oder verspätete Bereitschaft bricht kontrolliert ab.
- Jede lokale HTTP-Anfrage einschließlich `/health` wird authentifiziert. CORS ist nicht als Sicherheitsgrenze anzusehen.
- Die WebView erhält nur die minimal nötigen Tauri-Capabilities. Beliebige Shell-Ausführung ist ausgeschlossen.
- Beim Beenden der App wird der Kindprozess kontrolliert beendet; ein verwaister Prozess gilt als Fehler.

## Folgen

Für jedes freigegebene Zielsystem muss ein passender Sidecar gebaut und zusammen mit Tauri paketiert werden. Startprotokoll, Prozessüberwachung, Port-/Token-Handshake und Shutdown benötigen Integrations- und Pakettests. Der interne API-Vertrag wird versioniert.

## Verifikation

Architektur-Gate A0 muss auf Windows Start, dynamischen Port, Ablehnung ohne beziehungsweise mit falschem Token, paralleles SQLite-Lesen, Shutdown und Installation beweisen. Scheitert das Gate, wird diese ADR ersetzt, bevor Fachmodule auf dem Sidecar aufbauen.

## Referenzen

- [Tauri – Embedding External Binaries](https://v2.tauri.app/develop/sidecar/)
- [Tauri – Capabilities](https://v2.tauri.app/security/capabilities/)
- [FastAPI](https://fastapi.tiangolo.com/)
