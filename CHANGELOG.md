# Änderungsprotokoll

Alle bemerkenswerten Änderungen an New Eden Foundry werden hier festgehalten. Die Überschriften entsprechen der verbindlichen Struktur der GitHub Release Notes.

## Unveröffentlicht

### Neu hinzugefügt

- Keine.

### Geändert

- Keine.

### Behobene Fehler

- Keine.

### Bekannte Einschränkungen

- Schutzregeln für `main` sind noch nicht aktiviert.

### Update und Datenbankmigration

- Keine.

## 0.0.3-preview.1 – 8. September 2026

### Neu hinzugefügt

- Gebündelter FastAPI-Sidecar mit dynamischem Loopback-Port, versioniertem Startprotokoll und neuem 256-Bit-Sitzungstoken je App-Start.
- Produktive SQLite-Anlage unter `data\foundry.sqlite3` sowie vorbereiteter Backup-Ordner `data\backups`, jeweils direkt im Programmordner.
- Single-Instance-Fokus, Kindprozessüberwachung und kontrollierter Sidecar-Shutdown.
- Native Start-, Bereit- und Fehlerzustände in der Oberfläche.
- Frozen-Smoke-Test und Paketprüfung für den mitgelieferten Windows-Sidecar.
- ADR-010 für die sichtbare Datenhaltung im Programmordner.

### Geändert

- `Savoxmedia` erscheint ausschließlich als Ersteller der App neben der Versionsnummer.
- Installer und portable ZIP enthalten Hauptprogramm und Sidecar; die portable ZIP enthält zusätzlich deutsch-englische Nutzungshinweise.
- Python-Laufzeit- und Build-Abhängigkeiten sind getrennt und exakt versioniert.
- Die sichtbare Versionsnummer wurde auf `v0.0.3-preview.1` aktualisiert.

### Behobene Fehler

- Der lokale Kern verwendet bei einem nicht beschreibbaren Programmordner keinen versteckten Ersatzpfad.
- Fehlende oder falsche Sitzungstokens werden auch am Health-Endpunkt abgewiesen und nicht ausgegeben.
- Die missverständliche Darstellung von `Savoxmedia` als lokales Benutzerprofil wurde entfernt.

### Bekannte Einschränkungen

- Die Oberfläche verwendet weiterhin synthetische Mehrcharakterdaten und liest noch nicht aus SQLite.
- EVE SSO, ESI, SDE, Synchronisierung, automatische Migrations-Backups und fachliche Berechnungen fehlen noch.
- Installer und portable EXE sind noch nicht code-signiert.
- Die portable ZIP benötigt eine vorhandene Microsoft Edge WebView2 Runtime und einen beschreibbaren Zielordner.
- Schutzregeln für `main` sind noch nicht aktiviert.

### Update und Datenbankmigration

- Frühere Previews erzeugten keine produktive Datenbank. Der erste Start legt Schema-Version 2 unter `<Programmordner>\data\foundry.sqlite3` neu an.
- Installer-Updates und Deinstallation lassen den nicht gebündelten Ordner `data` stehen. Bei einer portablen Aktualisierung die geschlossene App samt vollständigem Ordner `data` kopieren.

## 0.0.2-preview.2 – 8. September 2026

### Neu hinzugefügt

- Schema-Version 2 mit lokalen Kontogruppen, eindeutig identifizierten Charakteren und getrennt gespeicherten SSO-Scopes je Charakter.
- Atomare Charakteraktualisierung, damit eine erneute Autorisierung denselben Charakter aktualisiert und keine Dublette erzeugt.
- Auswahl zwischen einer gemeinsamen Übersicht aller Charaktere und einer eigenen Übersicht für jeden Charakter.
- Synthetische Mehrcharakter-Vorschau mit zwei lokalen Kontogruppen, drei Charakteren und jeweils eigenen Kennzahlen, Jobs, Hinweisen und Aktivitäten.
- ADR-009 als verbindliche Grundlage für charaktergebundene EVE-Zugänge und lokale Accountorganisation.

### Geändert

- Synchronisierungsläufe können jetzt eindeutig einem Charakter zugeordnet werden.
- Der Datenstand der Gesamtübersicht richtet sich nach dem ältesten enthaltenen Charakterstand und bleibt sichtbar.
- `Savoxmedia` wurde als Projektbezeichnung von synthetischen EVE-Charakteren getrennt; die eindeutige Kennzeichnung als App-Ersteller folgt in `v0.0.3-preview.1`.
- Die sichtbare Versionsnummer wurde auf `v0.0.2-preview.2` aktualisiert.

### Behobene Fehler

- Charakterbezogene Jobs, Hinweise und Aktivitäten behalten in der Gesamtansicht ihre sichtbare Besitzerzuordnung.
- Das Löschen einer lokalen Kontogruppe entfernt nicht versehentlich die darin einsortierten Charakterdatensätze.
- Das Löschen eines Charakters entfernt dessen lokale Scopes, Synchronisierungsläufe und Cache-Snapshots vollständig.

### Bekannte Einschränkungen

- Kontogruppen und Charakterübersichten verwenden in dieser Preview noch synthetische Daten und sind noch nicht mit der Oberfläche der SQLite-Datenbank verbunden.
- Jeder echte Charakter muss später separat über EVE SSO autorisiert werden; EVE stellt der Anwendung keine bestätigte Accountgruppierung bereit.
- FastAPI-Sidecar, Single Instance, lokaler Port-/Token-Handshake, EVE SSO, ESI und SDE fehlen noch.
- Installer und portable EXE sind noch nicht code-signiert.
- Die portable ZIP benötigt eine vorhandene Microsoft Edge WebView2 Runtime.
- Schutzregeln für `main` sind noch nicht aktiviert.

### Update und Datenbankmigration

- Beim normalen App-Start existiert weiterhin keine produktive Nutzerdatenbank; daher ist für Preview-Nutzer keine Migration erforderlich.
- Entwicklungsdatenbanken mit Schema-Version 1 werden ohne Verlust bestehender Metadaten auf Schema-Version 2 aktualisiert.
- Automatische Migrations-Backups und Wiederherstellung folgen mit Arbeitspaket 08 und sind noch nicht Teil dieser Preview.

## 0.0.2-preview.1 – 8. September 2026

### Neu hinzugefügt

- Erste versionierte SQLite-Basismigration für Metadaten, Synchronisierungsläufe und synthetische Cache-Snapshots.
- Automatische Aktivierung und Prüfung von Foreign Keys, WAL-Modus und `busy_timeout` auf jeder Backend-Verbindung.
- Lokaler Backend-Selbsttest für Schema-Version und Datenbankintegrität ohne Netzwerkdienst.
- Tauri-IPC-Befehl, über den die Oberfläche den echten Status und die Version der nativen Desktop-Schale erkennt.
- Automatisierte Tests für Migration, Integrität, Fremdschlüssel, paralleles Lesen im WAL-Modus und die Browser-/Desktop-Statusanzeige.

### Geändert

- Die Qualitäts- und Release-Prüfungen testen nun Frontend und Python-Backend gemeinsam.
- Die Statusanzeige unterscheidet zwischen Browser-Vorschau, verbundener Tauri-Schale, laufender Prüfung und fehlgeschlagener nativer Statusabfrage.
- Die sichtbare Versionsnummer wurde auf `v0.0.2-preview.1` aktualisiert.

### Behobene Fehler

- Die Browser-Vorschau behauptet nicht länger, mit einem nativen Desktop-Kern verbunden zu sein.

### Bekannte Einschränkungen

- Das Python-Backend ist noch kein gebündelter Sidecar und wird von der Desktop-Anwendung noch nicht gestartet.
- Die SQLite-Grundlage wird noch nicht für Nutzerdaten verwendet; die Oberfläche zeigt weiterhin ausschließlich synthetische Vorschauwerte.
- Single Instance, lokaler Port-/Token-Handshake, EVE SSO, ESI, SDE, Synchronisierung und fachliche Berechnungen fehlen noch.
- Installer und portable EXE sind noch nicht code-signiert.
- Die portable ZIP benötigt eine vorhandene Microsoft Edge WebView2 Runtime.
- Schutzregeln für `main` sind noch nicht aktiviert.

### Update und Datenbankmigration

- Keine Nutzerdatenmigration erforderlich. Diese Vorschau legt beim normalen App-Start weiterhin keine Nutzerdatenbank an.
- Eine installierte ältere Preview kann bestehen bleiben; die portable ZIP vollständig in einen eigenen Ordner entpacken.

## 0.0.1-preview.2 – 8. September 2026

### Neu hinzugefügt

- Portable Windows-ZIP mit ausführbarer Anwendung und deutsch-englischen Nutzungshinweisen.
- Separate SHA-256-Prüfsummen für Installer und portable ZIP.
- Paketprüfung, die den Installer, das ZIP und dessen erwartete Inhalte vor dem Merge validiert.

### Geändert

- Der Release-Workflow leitet Version, Tag, Notes und Kanal nun aus den versionierten Projektdateien ab und funktioniert damit für künftige Releases ohne fest verdrahtete Versionsnummer.
- Jedes Windows-Release veröffentlicht ab jetzt Installer und portable ZIP direkt am GitHub Release; Actions-Artefakte bleiben weiterhin ausgeschlossen.
- Die sichtbare Versionsnummer der Design Preview wurde auf `v0.0.1-preview.2` aktualisiert.

### Behobene Fehler

- Keine.

### Bekannte Einschränkungen

- Keine EVE-Anbindung und keine produktive Fachlogik.
- Installer und portable EXE sind noch nicht code-signiert.
- Die portable ZIP benötigt eine vorhandene Microsoft Edge WebView2 Runtime.
- Die damalige Planung eines vom Programmordner getrennten Datenorts wurde später durch ADR-010 ersetzt; ab `v0.0.3-preview.1` liegt die Fachdatenbank unter `data` im Programmordner.
- Schutzregeln für `main` sind noch nicht aktiviert.

### Update und Datenbankmigration

- Keine Datenbankmigration erforderlich; diese Design Preview legt weiterhin keine Nutzerdatenbank an.
- `v0.0.1-preview.1` kann installiert bleiben. Die portable Fassung wird unabhängig davon in einen eigenen Ordner entpackt.

## 0.0.1-preview.1 – 8. September 2026

### Neu hinzugefügt

- Erste installierbare Windows-Designvorschau mit Tauri 2, React und TypeScript.
- Synthetische Foundry-Übersicht, vollständige Modulnavigation, Suche sowie DE/EN-Umschaltung.
- UI-Tests, Frontend-Buildprüfung und direkte Veröffentlichung des NSIS-Installers an ein GitHub Prerelease.
- Lebender Masterplan, ADR-Grundlage und Repository-Richtlinien für Phase 0.

### Geändert

- Das zentrale öffentliche Repository `Savox76/eve-test-indu` übernimmt Quellcode, Dokumentation, Issues, Actions und Releases.
- Die öffentliche Sichtbarkeit ermöglicht Branchschutz auf GitHub Free; Quellcode und Release-Seiten sind dadurch öffentlich zugänglich.
- Der Projektstatus unterscheidet nun ausdrücklich zwischen Design Preview und funktionaler Alpha.

### Behobene Fehler

- Der Release-Gate-Ausdruck ist als gültiger YAML-Skalar quotiert und wird vor künftigen Veröffentlichungen durch die Repository-Prüfung abgesichert.

### Bekannte Einschränkungen

- Keine EVE-Anbindung und keine produktive Fachlogik.
- Noch nicht code-signierter Windows-Installer.
- Schutzregeln für `main` sind noch nicht aktiviert.

### Update und Datenbankmigration

- Keine Migration erforderlich; es gibt keine Vorgängerversion und noch keine Nutzerdatenbank.
