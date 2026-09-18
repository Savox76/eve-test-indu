# Release-Regeln

## Grundsatz

Eine Version wird nur bewusst, reproduzierbar und nach vollständig grünen Pflichtprüfungen veröffentlicht. GitHub-Actions-Artefakte sind weder Zwischenspeicher noch Vertriebsweg.

## Verbindliches Versionsmodell

- **Normales Release:** `vX.Y.Z`, in `package.json` ohne Namenszusatz und auf GitHub als normale, aktuelle Veröffentlichung markiert. Abgeschlossene Arbeitspakete werden grundsätzlich so veröffentlicht. Nur diese Releases werden vom Update-Manager angeboten.
- **Beta:** `vX.Y.Z-beta.N` mit fortlaufender positiver Nummer, in Repository, Tag und Release-Titel ausdrücklich als `BETA` erkennbar und auf GitHub als Pre-Release markiert. Eine Beta dient ausschließlich der manuellen Vorabprüfung und wird vom Update-Manager immer übersprungen.
- Andere Vorabkennzeichen wie `alpha`, `preview` oder `rc` sind für neue Versionen nicht zulässig. Historische Releases bleiben unverändert erhalten.
- Nach erfolgreicher Beta-Prüfung wird die Zielversion ohne `-beta.N` als normales Release veröffentlicht. Die normale Version darf notwendige Korrekturen aus der Beta-Abnahme enthalten.

Der Release-Workflow lehnt Versionen ab, die diesem Schema nicht entsprechen. Er versieht Betas mit einem eindeutigen `BETA`-Titel und dem GitHub-Pre-Release-Status; normale Releases werden als `Latest` veröffentlicht.

## Update-Erkennung

Seit `v0.2.0` besitzt die Desktop-App genau einen öffentlichen Updatepfad für normale Releases. Ein gespeicherter historischer Kanalwert `beta` oder `preview` wird bei der Datenbankmigration auf `stable` zurückgesetzt; die Kanalwahl entfällt aus der Oberfläche.

Beim Start und auf Nutzerwunsch prüft die App die öffentliche Release-Liste des festen GitHub-Repositorys. Berücksichtigt werden ausschließlich suffixlose Versionen, die auf GitHub nicht als Pre-Release markiert sind und Installer, portable ZIP sowie beide exakt benannten SHA-256-Dateien vollständig enthalten. Beide Bedingungen verhindern, dass eine Beta durch ein falsch gesetztes GitHub-Merkmal als normales Update erscheint. Die App öffnet ausschließlich die aus der validierten Version selbst gebildete GitHub-Release-URL. Sie lädt, entpackt und installiert kein Paket automatisch.

Das historische Ed25519-signierte Offline-Testmanifest verweist weiterhin ausschließlich auf `updates.invalid`; der Laufzeitstatus erzwingt `publicDistribution: false`. Es ist nur ein Kryptografie-Test und kein auswählbarer Veröffentlichungsweg.

Eine spätere Aktivierung benötigt ein eigenes geprüftes Arbeitspaket mit Produktionsendpunkt, getrennt verwaltetem privatem Produktionsschlüssel, Signierung der tatsächlichen Updatepakete, Rollback-Regeln und bestandenem Windows-Update-Gate. Ein privater Schlüssel darf niemals in Repository, Anwendung, portable ZIP oder GitHub-Actions-Log gelangen. Der öffentliche Prüfschlüssel darf in der Anwendung liegen.

## Pflichtablauf

1. Zielversion, Release-Art (normal oder Beta) und enthaltenen Commit festlegen.
2. Sämtliche Pflichtchecks auf dem Release-Commit erfolgreich abschließen.
3. Windows-Installer und portable ZIP im freigegebenen Workflow erzeugen und dort inhaltlich prüfen.
4. Keine Zwischenprodukte über Actions-Artefakte hoch- oder herunterladen.
5. Signaturen und Update-Manifeste prüfen, soweit die Release-Art sie bereits verlangt.
6. GitHub Release aus einem bewusst gesetzten Tag erstellen; Betas als Pre-Release, normale Versionen als `Latest`.
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

Die portable ZIP enthält den konstanten Hauptordner `New Eden Foundry Portable` mit `New Eden Foundry.exe`, `foundry-sidecar.exe`, dem zugehörigen Ordner `foundry-sidecar-lib` und den deutsch-englischen Nutzungshinweisen. Der Python-Sidecar wird bewusst als transparentes PyInstaller-Verzeichnis statt als selbstentpackende `onefile`-EXE ausgeliefert, um unnötige Antiviren-Heuristiken und temporär ausgeführten eingebetteten Code zu vermeiden. Der Workflow öffnet das erzeugte Archiv und prüft diese Einträge, bevor eine Version freigegeben wird. Die ZIP muss vollständig in einen beschreibbaren Ordner entpackt werden; ein Start direkt aus der Archivvorschau wird nicht unterstützt.

„Portable“ bedeutet hier, dass die Anwendung ohne Installation und ohne Administratorrechte gestartet werden kann. Die Fachdatenbank und ihre Backups liegen im Unterordner `data` des Programmordners und werden beim Kopieren dieses vollständigen Ordners mitgeführt. Vor Kopie oder Sicherung muss die App geschlossen sein. Geheimnisse wie spätere EVE-Refresh-Tokens bleiben dagegen im Windows-Anmeldespeicher und sind deshalb nicht Bestandteil eines portablen Ordnertransfers.

Der portable Archivinhalt verwendet dauerhaft den Hauptordner `New Eden Foundry Portable`. Er darf auf dem Desktop, einem USB-Stick oder an jedem anderen beschreibbaren Ort liegen und ist vollständig vom Installationsordner unabhängig. Installierte und portable Ausgaben verwenden jeweils `data` direkt neben ihrer Haupt-EXE. Beim einmaligen Wechsel ab `v0.0.5-preview.15` übernimmt die installierte App den bisherigen Tauri-AppData-Bestand atomar in ihren Programmordner und behält Quellbestand sowie einen gegebenenfalls vorhandenen älteren Programmordner-Datenstand als Sicherung.

Für ein portables Update wird die Anwendung vollständig geschlossen. Danach wird `data` zusätzlich gesichert. Die neue ZIP kann in einen neuen beliebigen Zielordner entpackt und der bisherige `data`-Ordner dorthin kopiert werden. Alternativ wird sie am bisherigen Speicherort entpackt und nur die ausgelieferten Programmdateien werden ersetzt. Das Release-Archiv enthält keinen `data`-Ordner. Anschließend werden Versionsanzeige, Datenbankmigration und vorhandene Charaktere beziehungsweise Pläne geprüft.

Der Installer arbeitet im Modus `currentUser`. Ein Update ersetzt nur ausgelieferte Programmdateien und lässt den nicht gebündelten Ordner `data` stehen. Bei der vom neuen Installer gestarteten Entfernung der Vorversion darf die Option zum Löschen der Anwendungsdaten nicht gewählt werden. Bei einer bewussten Deinstallation entfernt diese bestätigungspflichtige Option ab `v0.0.5-preview.15` sowohl den alten Tauri-AppData-Bestand als auch `data` und etwaige Sicherungen neben der EXE.

Ab `v0.0.5-preview.16` führt `scripts/smoke_installed_application.ps1` den erzeugten Installer im `currentUser`-Modus tatsächlich aus. Der Test legt einen synthetischen Vorversions-Datenstand an, hält eine unwichtige Exportdatei während der Übernahme gesperrt, startet die installierte Hauptanwendung und verlangt eine laufende Sidecar-Instanz sowie die migrierte Datenbank direkt neben der EXE. Ab `v0.0.5-preview.17` schließt er das Hauptfenster regulär, wartet auf das Ende von Anwendung und Sidecar, startet erneut und prüft dabei eine erhaltene Datenbankmarkierung sowie eine neue Sidecar-Prozess-ID. Ab `v0.0.5-preview.20` erzeugt er zusätzlich einen synthetischen laufenden Sync, beendet den Sidecar hart und verlangt bei weiterlaufender Hauptanwendung einen neuen Sidecar-Prozess, den Status `cancelled`, den stabilen Grund `sidecar-interrupted` sowie eine erfolgreiche SQLite-Integritätsprüfung. Ab `v0.0.5-preview.21` liest er außerdem den PE-Header der installierten Haupt-EXE und verlangt den Subsystemwert `2` (`IMAGE_SUBSYSTEM_WINDOWS_GUI`), damit kein zusätzliches Konsolenfenster den kontrollierten Shutdown umgehen kann. Dieser vollständige Absturz-Erststart-Beenden-Neustart-Test ist sowohl für Pull Requests als auch unmittelbar vor der Release-Veröffentlichung verpflichtend.

Zusätzlich scannt Microsoft Defender ab `v0.0.5-preview.19` den gebauten Sidecar samt Laufzeitdateien sowie anschließend Installer und Portable-ZIP mit aktuellen Signaturen. Eine Erkennung stoppt Pull Request und Release; der Workflow legt niemals eine Defender-Ausnahme an und gibt keine erkannte Datei automatisch frei.

Steht beim ersten Start einer neuen Version eine Datenbankmigration an, erzeugt der lokale Kern zuvor über die SQLite-Backup-API einen konsistenten Snapshot unter `data\backups`. Integrität, Fremdschlüssel, Schema-Version und SHA-256 werden geprüft, bevor die Migration beginnt. Scheitert die Migration, wird dieser Stand automatisch wiederhergestellt; scheitert bereits die Sicherung, bleibt das Schema unverändert und der Start wird abgebrochen. Die fünf neuesten automatisch erzeugten Migrationssicherungen bleiben erhalten. Eine manuelle Wiederherstellung darf nur bei vollständig geschlossener App erfolgen.

Als selbst hochgeladene Release-Dateien sind ausschließlich Dateien erlaubt, die zur Installation, portablen Ausführung, Integritäts- oder Signaturprüfung oder zum Update der freigegebenen Anwendung benötigt werden. Debug-Dumps, echte Nutzerdaten und beliebige CI-Zwischenstände werden nicht hochgeladen.

Solange die öffentliche Updateverteilung deaktiviert ist, enthält ein Release genau die beiden Windows-Pakete und ihre beiden SHA-256-Dateien. Das interne Testmanifest und seine Testsignatur bleiben Bestandteil des Sidecars und werden nicht als eigenständige Release-Dateien veröffentlicht.

Das Repository und seine Release-Seiten sind öffentlich. GitHub ergänzt bei jedem Release automatisch ZIP- und Tarball-Links auf den Quellcode des Tags. Diese automatisch bereitgestellten Quellcodearchive sind keine GitHub-Actions-Artefakte und können für ein öffentliches Repository nicht als geheimer Vertriebsweg behandelt werden.
