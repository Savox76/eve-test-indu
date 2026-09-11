# ADR-018: Einheitlicher Datenordner neben der Anwendung

- **Status:** Angenommen
- **Datum:** 11. September 2026
- **Entscheider:** Projektverantwortlicher
- **Ersetzt:** ADR-013

## Kontext

Der ab `v0.0.5-preview.4` für installierte Ausgaben verwendete Tauri-AppData-Pfad
war zwar versionsstabil, machte den tatsächlichen Speicherort aber unsichtbar und
unterschied sich vom nachvollziehbaren Verhalten der portablen Ausgabe. Beim
Gerätetest von `.13` auf `.14` erschwerte diese Trennung außerdem die Zuordnung
zwischen Installer-Update, lokaler Datenübernahme und einer nachgelagerten
fehlgeschlagenen EVE-Synchronisierung.

## Entscheidung

- Installierte und portable Ausgaben verwenden ausschließlich `data` direkt
  neben `New Eden Foundry.exe`.
- Der Installer bleibt im Modus `currentUser`; sein Standardordner unter
  `%LOCALAPPDATA%\New Eden Foundry` ist ohne Administratorrechte beschreibbar.
- Beim ersten Start ab `v0.0.5-preview.15` wird ein vorhandener Datenstand aus
  Tauri `app_local_data_dir` vollständig in einen temporären Ordner neben der EXE
  kopiert und anschließend atomar als `data` veröffentlicht.
- Existiert dort bereits ein älterer `data`-Ordner, wird er vor der Übernahme als
  `data-before-appdata-migration` erhalten. Der AppData-Quellbestand wird nicht
  gelöscht. Ein Marker verhindert, dass er bei späteren Starts erneut über einen
  neueren Programmordner-Datenstand kopiert wird.
- Schlägt die Übernahme fehl, startet die App nicht mit einer leeren Datenbank.
- Ab `v0.0.5-preview.16` werden kurzzeitige Dateisperren begrenzt wiederholt. Ist nur
  eine unwichtige Zusatzdatei betroffen, wird die SQLite-Datenbank samt vorhandenem
  WAL zwingend übernommen; erreichbare Backups und Exporte werden ergänzt. Nicht
  erreichbare Zusatzdateien bleiben im unveränderten AppData-Quellbestand, statt den
  kompletten Anwendungsstart zu blockieren.
- Ab `v0.0.5-preview.17` wird die Sidecar-Standardeingabe nach dem Shutdown-Befehl
  geschlossen. Beim nächsten Programmstart werden ausschließlich kurzzeitige
  Sidecar-, Datenbank- und Loopback-Fehler begrenzt wiederholt; dauerhafte
  Speicher- und Migrationsfehler bleiben sofort sichtbar.
- Ein normales Update oder eine Deinstallation ohne Löschbestätigung lässt
  `data` bestehen. Nur die ausdrücklich ausgewählte Installer-Option zum Löschen
  der Anwendungsdaten entfernt auch den programmordnergebundenen Datenbestand.
- EVE-Refresh-Tokens bleiben als Geheimnisse im Windows-Anmeldespeicher und sind
  weiterhin nicht Bestandteil des verschiebbaren Ordners.

## Folgen

Der sichtbare Datenaufbau ist für Installer und Portable identisch. Ein kompletter
portabler Ordner kann an einen beliebigen beschreibbaren Ort oder auf einen
USB-Stick kopiert werden. Bei einem Wechsel auf einen anderen Windows-Rechner
müssen Charaktere wegen des getrennten Anmeldespeichers erneut autorisiert werden.

## Verifikation

- Rust-Tests prüfen Erstinitialisierung, atomare AppData-Übernahme, Sicherung eines
  vorhandenen Programmordner-Datenstands und die nur einmalige Migration.
- Windows-CI baut Installer und Portable, schließt die installierte Anwendung über
  ihr Hauptfenster und prüft einen zweiten Start mit demselben Datenordner und einer
  neuen Sidecar-Instanz.
- Die Windows-A0-Abnahme prüft `.14` auf `.15`, Datenerhalt, Löschoption und einen
  vollständig eigenständigen portablen Start außerhalb des Installationsordners.

## Referenzen

- [ADR-010 – Sichtbare Datenhaltung im Programmordner](0010-program-folder-storage.md)
- [ADR-013 – Updatefeste Anwendungsdaten](0013-update-stable-application-data.md)
- [Tauri – Windows Installer](https://v2.tauri.app/distribute/windows-installer/)
