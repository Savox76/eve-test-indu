# Release-Regeln

## Grundsatz

Eine Version wird nur bewusst, reproduzierbar und nach vollständig grünen Pflichtprüfungen veröffentlicht. GitHub-Actions-Artefakte sind weder Zwischenspeicher noch Vertriebsweg.

## Kanäle

- **Alpha:** interne technische oder fachliche Erprobung; bekannte Lücken sind zulässig und dokumentiert.
- **Beta:** Kernabläufe sind nutzbar; Migration, Wiederherstellung und Update werden geprüft.
- **Stable:** alle zugehörigen Plattform-, Daten-, Sicherheits- und Nutzer-Gates sind erfüllt.

## Pflichtablauf

1. Zielversion, Kanal und enthaltenen Commit festlegen.
2. Sämtliche Pflichtchecks auf dem Release-Commit erfolgreich abschließen.
3. Installer beziehungsweise Pakete im freigegebenen Workflow erzeugen und dort prüfen.
4. Keine Zwischenprodukte über Actions-Artefakte hoch- oder herunterladen.
5. Signaturen und Update-Manifeste prüfen, soweit der Kanal sie bereits verlangt.
6. GitHub Release aus einem bewusst gesetzten Tag erstellen.
7. Nur die freigegebenen Installationsdateien, Signaturen und Update-Manifeste direkt an dieses GitHub Release anhängen.
8. Installation, Start und gegebenenfalls Migration auf dem freigegebenen Windows-Testgerät prüfen.

Ein fehlgeschlagener Pflichtcheck, ein offener Blocker oder ein ungeklärter kritischer Sicherheitsfund stoppt die Veröffentlichung.

## Verbindliche Release Notes

Jedes GitHub Release enthält alle folgenden Überschriften. Ein leerer Bereich wird ausdrücklich mit „Keine“ dokumentiert.

```markdown
## Neu hinzugefügt

- ...

## Geändert

- ...

## Behobene Fehler

- ...

## Bekannte Einschränkungen

- ...

## Update und Datenbankmigration

- ...
```

Die Notes beschreiben Nutzerwirkung und notwendige Handlungen. Reine Commitlisten reichen nicht aus.

## Release-Dateien

Erlaubt sind ausschließlich Dateien, die zur Installation, Signaturprüfung oder zum Update der freigegebenen Anwendung benötigt werden. Quellcode-Snapshots, Debug-Dumps, echte Nutzerdaten und beliebige CI-Zwischenstände werden nicht als zusätzliche Release-Dateien hochgeladen.

Bis zu einer anderslautenden ADR-Entscheidung bleiben Repository und Releases privat.
