# Windows-Abnahme A0 für Paket 22

Diese Abnahme ist der letzte externe Nachweis vor der ersten `0.2.0`-Alpha. Sie wird auf einem freigegebenen Windows-10- oder Windows-11-x64-Testgerät mit einer vorhandenen Preview und dem Korrekturkandidaten `v0.0.5-preview.14` durchgeführt. Automatisierte CI-Pakettests ersetzen diesen Lauf nicht.

## Vorbereitung

1. Beide Installer und ihre gleichnamigen `.sha256`-Dateien ausschließlich von den GitHub Releases laden.
2. In PowerShell für beide Installer `Get-FileHash -Algorithm SHA256 <Datei>` ausführen und mit der jeweiligen Prüfsummendatei vergleichen.
3. Eine vorhandene Anwendung vollständig schließen und den bestehenden `data`-Ordner separat sichern. Der Test darf keine echten Zugangsdaten, Datenbanken oder Screenshots davon im öffentlichen Repository ablegen.

## Verbindlicher Testlauf

| Nr. | Prüfung | Bestanden, wenn |
| ---: | --- | --- |
| 1 | Installation `v0.0.5-preview.2` | Der Current-User-Installer beendet sich erfolgreich und die Anwendung startet ohne Entwicklerwerkzeuge. |
| 2 | Lokaler Kern | Die Oberfläche meldet Desktop-Kern, Sidecar und Datenbank als bereit; die installierte Ausgabe verwendet den stabilen benutzerspezifischen App-Datenordner. |
| 3 | Zweiter Start | Ein zweiter Programmstart erzeugt keine zweite unabhängige Instanz und fokussiert das vorhandene Fenster. |
| 4 | Ausgangsdaten | Mindestens ein Charakter wird verbunden, **Assets aktualisieren** liefert einen Bestand und eine ungefährliche lokale Einstellung wird gespeichert. |
| 5 | Installer-Update | Nach vollständigem Schließen wird `v0.0.5-preview.14` über dieselbe Installation installiert und zeigt anschließend die neue Versionsnummer. |
| 6 | Datenerhalt | Datenbank, Einstellungen, Charakterliste, Forschungspläne und letzte vollständige Snapshots sind nach dem Update weiterhin vorhanden; die automatische Migration auf Schema 9 ist abgeschlossen. |
| 7 | Portable Ausgabe | Die ZIP wird vollständig in einen beschreibbaren Ordner entpackt; Hauptprogramm und Sidecar starten ohne Installation. |
| 8 | Entfernung | Nach dem Schließen beendet die Deinstallation die Anwendung und entfernt ausgelieferte Programmdateien. Benutzerspezifische Daten bleiben wie dokumentiert erhalten. |
| 9 | Sauberer Abschluss | Nach Deinstallation laufen weder Hauptprogramm noch Sidecar weiter; eine erneute Installation öffnet den beibehaltenen Datenstand wieder. |

## Ergebnis melden

Für jeden Punkt genügt `bestanden` oder eine kurze Fehlerbeschreibung. Zusätzlich werden nur folgende technische Angaben benötigt:

- Windows-Version und Buildnummer aus `winver`
- Testdatum
- getestete Ausgangs- und Zielversion
- Installer oder Portable bei einem Fehler
- Nummer des fehlgeschlagenen Prüfpunkts und sichtbarer Fehlertext

Keine Tokens, Datenbanken, Charakterdetails oder sonstigen echten Nutzdaten mitsenden. Erst wenn alle neun Punkte bestanden sind und die Pflichtchecks des Kandidaten grün bleiben, darf Paket 22 als abgeschlossen markiert und die erste `0.2.0`-Alpha freigegeben werden.
