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
- „Portable“ umfasst nicht das Mitführen künftiger Nutzerdaten oder Zugangsdaten im Programmordner.
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
