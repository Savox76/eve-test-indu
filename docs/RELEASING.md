# Release-Regeln

## Grundsatz

Eine Version wird nur bewusst, reproduzierbar und nach vollständig grünen Pflichtprüfungen veröffentlicht. GitHub-Actions-Artefakte sind weder Zwischenspeicher noch Vertriebsweg.

## Release-Reife

- **Alpha:** interne technische oder fachliche Erprobung; bekannte Lücken sind zulässig und dokumentiert.
- **Beta:** Kernabläufe sind nutzbar; Migration, Wiederherstellung und Update werden geprüft.
- **Stable:** alle zugehörigen Plattform-, Daten-, Sicherheits- und Nutzer-Gates sind erfüllt.

## Lokale Updatekanäle

Seit `v0.0.4-preview.1` kann die Desktop-App die Kanalpräferenz `stable`, `beta` oder `preview` lokal speichern. Das gebündelte Ed25519-signierte Testmanifest verweist weiterhin ausschließlich auf `updates.invalid`, und der Laufzeitstatus erzwingt `publicDistribution: false`.

Seit `v0.0.5-preview.13` prüft ein davon getrennter Hinweisweg beim Start und auf Nutzerwunsch die öffentliche Release-Liste des festen GitHub-Repositorys. Berücksichtigt werden nur zum Kanal passende Releases mit Installer, portabler ZIP und beiden exakt benannten SHA-256-Dateien. Die App öffnet ausschließlich die aus der validierten Version selbst gebildete GitHub-Release-URL. Sie lädt, entpackt und installiert kein Paket automatisch.

Eine spätere Aktivierung benötigt ein eigenes geprüftes Arbeitspaket mit Produktionsendpunkt, getrennt verwaltetem privatem Produktionsschlüssel, Signierung der tatsächlichen Updatepakete, Rollback-Regeln und bestandenem Windows-Update-Gate. Ein privater Schlüssel darf niemals in Repository, Anwendung, portable ZIP oder GitHub-Actions-Log gelangen. Der öffentliche Prüfschlüssel darf in der Anwendung liegen.

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

Für Architektur-Gate A0 gilt das verbindliche, datensparsame Verfahren unter [`windows-a0-acceptance.md`](windows-a0-acceptance.md). Ein CI-Build oder eine reine Paket-Inhaltsprüfung darf dort nicht als bestandene Geräteabnahme eingetragen werden.

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

Die portable ZIP enthält den konstanten Hauptordner `New Eden Foundry Portable` mit `New Eden Foundry.exe`, `foundry-sidecar.exe` und den deutsch-englischen Nutzungshinweisen. Der Workflow öffnet das erzeugte Archiv und prüft diese Einträge, bevor eine Version freigegeben wird. Die ZIP muss vollständig in einen beschreibbaren Ordner entpackt werden; ein Start direkt aus der Archivvorschau wird nicht unterstützt.

„Portable“ bedeutet hier, dass die Anwendung ohne Installation und ohne Administratorrechte gestartet werden kann. Die Fachdatenbank und ihre Backups liegen im Unterordner `data` des Programmordners und werden beim Kopieren dieses vollständigen Ordners mitgeführt. Vor Kopie oder Sicherung muss die App geschlossen sein. Geheimnisse wie spätere EVE-Refresh-Tokens bleiben dagegen im Windows-Anmeldespeicher und sind deshalb nicht Bestandteil eines portablen Ordnertransfers.

Der portable Archivinhalt verwendet dauerhaft den Hauptordner `New Eden Foundry Portable`, damit spätere Versionen in denselben übergeordneten Ordner entpackt werden können, ohne `data` zu ersetzen. Installierte Ausgaben verwenden dagegen den stabilen benutzerspezifischen Tauri-App-Datenordner; ein vorhandener Altbestand neben der EXE wird beim ersten Start sicher übernommen.

Für ein portables Update wird die Anwendung vollständig geschlossen. Danach wird `data` zusätzlich gesichert und die neue ZIP in denselben übergeordneten Ordner entpackt; bei einer Ersetzungsabfrage werden nur die ausgelieferten Programmdateien ersetzt. Da das Release-Archiv keinen `data`-Ordner enthält, bleibt der bestehende lokale Datenstand erhalten. Anschließend werden Versionsanzeige, Datenbankmigration und vorhandene Charaktere beziehungsweise Pläne geprüft. Der automatische Release-Hinweis zeigt genau diesen Ablauf.

Der Installer arbeitet im Modus `currentUser`. Ein Update ersetzt nur ausgelieferte Programmdateien und lässt den nicht gebündelten Ordner `data` stehen. Auch eine Deinstallation lässt diesen Datenordner bewusst zurück; für eine vollständige Löschung muss er anschließend manuell entfernt werden, bis eine bestätigungspflichtige Löschfunktion existiert.

Steht beim ersten Start einer neuen Version eine Datenbankmigration an, erzeugt der lokale Kern zuvor über die SQLite-Backup-API einen konsistenten Snapshot unter `data\backups`. Integrität, Fremdschlüssel, Schema-Version und SHA-256 werden geprüft, bevor die Migration beginnt. Scheitert die Migration, wird dieser Stand automatisch wiederhergestellt; scheitert bereits die Sicherung, bleibt das Schema unverändert und der Start wird abgebrochen. Die fünf neuesten automatisch erzeugten Migrationssicherungen bleiben erhalten. Eine manuelle Wiederherstellung darf nur bei vollständig geschlossener App erfolgen.

Als selbst hochgeladene Release-Dateien sind ausschließlich Dateien erlaubt, die zur Installation, portablen Ausführung, Integritäts- oder Signaturprüfung oder zum Update der freigegebenen Anwendung benötigt werden. Debug-Dumps, echte Nutzerdaten und beliebige CI-Zwischenstände werden nicht hochgeladen.

Solange die öffentliche Updateverteilung deaktiviert ist, enthält ein Release genau die beiden Windows-Pakete und ihre beiden SHA-256-Dateien. Das interne Testmanifest und seine Testsignatur bleiben Bestandteil des Sidecars und werden nicht als eigenständige Release-Dateien veröffentlicht.

Das Repository und seine Release-Seiten sind öffentlich. GitHub ergänzt bei jedem Release automatisch ZIP- und Tarball-Links auf den Quellcode des Tags. Diese automatisch bereitgestellten Quellcodearchive sind keine GitHub-Actions-Artefakte und können für ein öffentliches Repository nicht als geheimer Vertriebsweg behandelt werden.
