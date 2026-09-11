# ADR-013: Updatefeste Anwendungsdaten

- **Status:** Ersetzt durch ADR-018
- **Datum:** 10. September 2026
- **Entscheider:** Projektverantwortlicher
- **Ersetzt:** ADR-010 für installierte Ausgaben und portable Updateordner

## Kontext

Der programmordnergebundene Speicher aus ADR-010 erwies sich im Windows-Gerätetest als nicht updatefest: Eine neue installierte Version konnte einen anderen Programmordner verwenden und erschien dann ohne die zuvor verbundenen Charaktere. Außerdem erzeugte jedes portable Archiv einen neuen, versionsabhängigen Ordner. Die Datenbank und ihre abgeleiteten Snapshots müssen Versionswechsel überleben, ohne Geheimnisse in Dateien zu verlagern.

## Entscheidung

- Die installierte App verwendet Tauri `app_local_data_dir` als stabilen benutzerspezifischen Wurzelordner. Darunter bleiben Datenbank, Backups und Exporte in `data`.
- Wenn am alten EXE-Ort ein `data`-Ordner existiert und am stabilen Ziel noch keiner vorhanden ist, kopiert die App ihn ohne symbolische Links in einen temporären Zielordner und veröffentlicht ihn anschließend per Umbenennung. Das Original wird nicht gelöscht. Bei Fehlern startet der lokale Kern geschlossen statt mit einer leeren Datenbank.
- Die portable Ausgabe wird durch `PORTABLE-README-DE-EN.txt` neben der EXE erkannt und behält weiterhin ihren sichtbaren `data`-Ordner neben der EXE.
- Portable Archive enthalten den versionsunabhängigen Hauptordner `New Eden Foundry Portable`.
- Refresh Tokens bleiben ausschließlich im Windows-Anmeldespeicher.

## Folgen

Installer-Updates verwenden dauerhaft dieselben Charaktere, Einstellungen und Snapshots. Eine Deinstallation kann benutzerspezifische Anwendungsdaten zurücklassen; eine spätere bestätigungspflichtige Löschfunktion bleibt erforderlich. Beim einmaligen Wechsel eines bestehenden portablen Versionsordners muss `data` manuell in den neuen stabilen Ordner kopiert werden.

## Verifikation

- Rust- und Windows-CI kompilieren die Speicherpfadauswahl und das sichere Kopierverfahren.
- Pakettests prüfen den konstanten portablen Hauptordner und den Marker.
- Die Windows-A0-Abnahme prüft Update, erneuten Start und Datenerhalt ausdrücklich mit einem verbundenen Charakter.

## Referenzen

- [ADR-003 – SQLite-Persistenz](0003-sqlite-persistence.md)
- [ADR-010 – Sichtbare Datenhaltung im Programmordner](0010-program-folder-storage.md)
- [Tauri – Path resolver](https://v2.tauri.app/reference/javascript/api/namespacepath/)
