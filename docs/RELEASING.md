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
3. Windows-Installer und portable ZIP im freigegebenen Workflow erzeugen und dort inhaltlich prüfen.
4. Keine Zwischenprodukte über Actions-Artefakte hoch- oder herunterladen.
5. Signaturen und Update-Manifeste prüfen, soweit der Kanal sie bereits verlangt.
6. GitHub Release aus einem bewusst gesetzten Tag erstellen.
7. Nur die freigegebenen Pakete, Prüfsummen, Signaturen und Update-Manifeste direkt an dieses GitHub Release anhängen.
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

Jedes Windows-Release enthält mindestens:

- den NSIS-Installer `New.Eden.Foundry_<VERSION>_x64-setup.exe`,
- die portable ZIP `New.Eden.Foundry_<VERSION>_x64-portable.zip`,
- für beide Pakete jeweils eine gleichnamige `.sha256`-Datei.

Die portable ZIP enthält einen versionsbezogenen Ordner mit `New Eden Foundry.exe` und den deutsch-englischen Nutzungshinweisen. Der Workflow öffnet das erzeugte Archiv und prüft diese Einträge, bevor eine Version freigegeben wird. Die ZIP muss vollständig entpackt werden; ein Start direkt aus der Archivvorschau wird nicht unterstützt.

„Portable“ bedeutet hier, dass die Anwendung ohne Installation und ohne Administratorrechte gestartet werden kann. Es bedeutet nicht, dass Nutzerdaten oder Zugangsdaten im Programmordner mitgeführt werden. Künftige lokale Daten bleiben im Windows-Benutzerprofil und Geheimnisse im Windows-Anmeldespeicher. Ein vollständig selbstenthaltener USB-Modus wäre eine eigene, sicherheitsrelevante Produktentscheidung.

Als selbst hochgeladene Release-Dateien sind ausschließlich Dateien erlaubt, die zur Installation, portablen Ausführung, Integritäts- oder Signaturprüfung oder zum Update der freigegebenen Anwendung benötigt werden. Debug-Dumps, echte Nutzerdaten und beliebige CI-Zwischenstände werden nicht hochgeladen.

Das Repository und seine Release-Seiten sind öffentlich. GitHub ergänzt bei jedem Release automatisch ZIP- und Tarball-Links auf den Quellcode des Tags. Diese automatisch bereitgestellten Quellcodearchive sind keine GitHub-Actions-Artefakte und können für ein öffentliches Repository nicht als geheimer Vertriebsweg behandelt werden.
