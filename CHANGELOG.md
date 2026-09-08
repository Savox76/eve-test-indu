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
