# ADR-010: Sichtbare Datenhaltung im Programmordner

- **Status:** Angenommen; zwischenzeitlich durch ADR-013 geändert, mit ADR-018 wiederhergestellt
- **Datum:** 8. September 2026
- **Entscheider:** Projektverantwortlicher
- **Ersetzt:** den Speicherort aus ADR-003; die übrigen SQLite-Regeln bleiben bestehen

## Kontext

Die Anwendung soll ohne externen Datenbankdienst funktionieren und ihre lokale Datenbank nicht an einem versteckten oder betriebssystemspezifischen Ort ablegen. Bei der installierten und bei der portablen Ausgabe soll direkt erkennbar sein, welche Dateien zur Anwendung gehören. Gleichzeitig benötigt SQLite im WAL-Modus Schreibzugriff auf das Verzeichnis der Datenbank, weil dort zusätzlich `-wal`- und `-shm`-Dateien entstehen.

## Entscheidung

- Die einzige produktive Datenbank liegt relativ zur Haupt-EXE unter `data\foundry.sqlite3`.
- Automatisch erzeugte Migrationssicherungen liegen ausschließlich unter `data\backups`; die fünf neuesten werden aufbewahrt.
- Tauri bestimmt den Programmordner aus dem Verzeichnis der laufenden Haupt-EXE und übergibt ihn dem Sidecar über dessen geschützte Standardeingabe.
- Existiert `data` noch nicht, wird der Ordner beim Start angelegt. Ist der Programmordner nicht beschreibbar, startet der lokale Kern nicht und die Oberfläche zeigt einen Fehler. Es gibt keinen stillen Ersatzpfad in AppData, Temp oder im Benutzerprofil.
- Symbolische Umleitungen für `data`, Datenbank oder Backup-Ordner werden abgewiesen.
- Der Windows-Installer bleibt eine Installation für den aktuellen Benutzer, damit sein Programmordner ohne Administratorrechte beschreibbar ist.
- Die portable ZIP muss vollständig in einen beschreibbaren Ordner entpackt werden. Wird der vollständige Ordner einschließlich `data` verschoben, wandert die Datenbank mit.
- EVE-Refresh-Tokens und andere Geheimnisse bleiben von dieser Entscheidung ausgenommen. Refresh Tokens werden pro Charakter im Windows-Anmeldespeicher des aktuellen Nutzers gehalten und nicht mit dem Programmordner übertragen.
- Updates ersetzen nur ausgelieferte Programmdateien. Der nicht gebündelte Ordner `data` bleibt erhalten. Eine bewusste vollständige Datenlöschung wird später als eigene, bestätigungspflichtige Funktion umgesetzt.

## Folgen

Der Speicherort ist transparent und die portable Ausgabe kann Programm und Fachdaten gemeinsam transportieren. Die Anwendung darf jedoch nicht aus einem schreibgeschützten Ordner, direkt aus einer ZIP-Vorschau oder aus einem administrativ geschützten Installationsverzeichnis gestartet werden. Vor dem manuellen Kopieren oder Sichern des Ordners muss die Anwendung geschlossen sein, damit SQLite-WAL-Dateien konsistent behandelt werden.

Eine Deinstallation entfernt die ausgelieferten Programmdateien, lässt den unbekannten Ordner `data` aber stehen. Bis eine bestätigte Löschfunktion verfügbar ist, muss dieser Restordner für eine vollständige Entfernung manuell gelöscht werden.

## Verifikation

- Backendtests prüfen den exakten Pfad, die Anlage von `data` und `data\backups`, einen Schreibtest ohne Ausweichpfad sowie die Ablehnung symbolischer Umleitungen.
- Der eingefrorene Sidecar-Smoke-Test startet mit einem temporären Programmordner, prüft Schema und Integrität an exakt dieser Stelle und beendet den Prozess kontrolliert.
- Pakettests prüfen, dass Haupt-EXE und Sidecar gemeinsam im Installer beziehungsweise in der portablen ZIP liegen.
- Ein Windows-Freigabegate prüft zusätzlich Installation, Update, portablen Start und das Fortbestehen von `data`.

## Referenzen

- [Tauri – Resources](https://v2.tauri.app/develop/resources/)
- [Tauri – Windows Installer](https://v2.tauri.app/distribute/windows-installer/)
- [SQLite – Write-Ahead Logging](https://www.sqlite.org/wal.html)
- [ADR-003 – SQLite-Persistenz](0003-sqlite-persistence.md)
- [ADR-004 – EVE SSO mit PKCE und Schlüsselbund](0004-eve-sso-pkce.md)
