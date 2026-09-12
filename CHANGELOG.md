# Änderungsprotokoll

Alle bemerkenswerten Änderungen an New Eden Foundry werden hier festgehalten. Die Überschriften entsprechen der verbindlichen Struktur der GitHub Release Notes.

## Unveröffentlicht

### Neu hinzugefügt

Keine.

### Geändert

Keine.

### Behobene Fehler

Keine.

### Bekannte Einschränkungen

- Paket 22 wartet nach Veröffentlichung des korrigierten Abnahmekandidaten auf das vollständige Windows-A0-Protokoll.

### Update und Datenbankmigration

Keine.

## 0.0.5-preview.19 – 12. September 2026

### Neu hinzugefügt

- Windows-CI und Release-Pipeline scannen Sidecar, Installer und Portable-ZIP mit aktualisierten Microsoft-Defender-Signaturen und stoppen bei einer Erkennung.

### Geändert

- Der Python-Sidecar wird als entpackter Laufzeitordner statt als selbstentpackende `onefile`-EXE ausgeliefert.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.19`.

### Behobene Fehler

- Der von Windows Defender blockierte `.18`-Download wird durch einen Paketaufbau ohne temporäre `onefile`-Extraktion ersetzt.

### Bekannte Einschränkungen

- Die Preview ist noch nicht produktiv code-signiert; SmartScreen kann deshalb weiterhin vor einem unbekannten Herausgeber warnen.
- Paket 22 wartet nach Veröffentlichung des korrigierten Abnahmekandidaten auf das vollständige Windows-A0-Protokoll.

### Update und Datenbankmigration

- Das Datenbankschema bleibt bei Version 9; bestehende Charaktere, Einstellungen, Pläne und Snapshots werden unverändert weiterverwendet.
- Die Portable-ZIP muss vollständig einschließlich `foundry-sidecar-lib` entpackt werden. Bei einem neuen Zielordner wird der bisherige `data`-Ordner vor dem ersten Start übernommen.

## 0.0.5-preview.18 – 11. September 2026

### Neu hinzugefügt

- Assets öffnen in einer nach Typ gruppierten Bestandsübersicht mit Gesamtmenge, Positions-, Besitzer- und Standortverteilung sowie einem Drill-down auf die passenden Einzelpositionen.
- Jeder aktivierte Charakter erhält in der Blueprint-Ansicht einen sichtbaren Status für vorhandene oder fehlende persönliche Snapshots.
- Industrieanlagen können anhand des offiziellen SDE-Sicherheitsstatus nach Highsec, Lowsec, Nullsec oder unbekannt gefiltert werden.

### Geändert

- Laufende Industrieaufträge zeigen ihre verbleibende Zeit; abholbereite und bereits abgeholte Aufträge besitzen unterschiedliche Bezeichnungen.
- Fertigungs- und Reaktionspläne listen Vorprodukte in ausführbarer Reihenfolge vor dem hervorgehobenen Zielprodukt.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.18`.

### Behobene Fehler

- Fehlende Blueprint-Snapshots waren bisher nur als leere Tabelle erkennbar und verhinderten dadurch auch ohne verständlichen Hinweis die ME-/TE-Planung.
- Produktionsschritt 1 bezeichnete bisher das Zielprodukt, obwohl seine Vorprodukte zuerst hergestellt werden müssen.
- Ein bestehender offizieller SDE-Build wird einmalig erneut importiert, wenn der neue Sicherheitsstatus in der abgeleiteten Standorttabelle noch fehlt.

### Bekannte Einschränkungen

- Der Blueprint-Snapshot enthält persönliche BPOs und BPCs; Corporation-Blueprints sind noch nicht angebunden.
- EVE-Refresh-Tokens bleiben im Windows-Anmeldespeicher und müssen auf einem anderen Rechner erneut autorisiert werden.
- Download und Installation bleiben bis zu einer produktiv signierten Update- und Rollback-Kette manuell.
- Paket 22 benötigt weiterhin das vollständige Windows-A0-Protokoll auf dem Zielgerät.

### Update und Datenbankmigration

- Das Anwendungsschema bleibt bei Version 9. Die neue nullable SDE-Spalte wird ausschließlich in der abgeleiteten, wiederaufbaubaren Standorttabelle ergänzt.
- Vorhandene Charaktere, Einstellungen, Forschungs- und Produktionspläne sowie Snapshots werden nicht ersetzt. Ein Regressionstest aktualisiert denselben SDE-Build und prüft ausdrücklich den Erhalt vorhandener Nutzerdaten.
- `.16` oder `.17` vollständig schließen und `.18` installieren. Die Installer-Option zum Löschen der Anwendungsdaten muss abgewählt bleiben.
- Portable vollständig in einen neuen beschreibbaren Ordner entpacken und vor dem ersten Start den gesicherten bisherigen `data`-Ordner in diesen neuen Ordner übernehmen.

## 0.0.5-preview.17 – 11. September 2026

### Neu hinzugefügt

- Der verpflichtende Windows-Pakettest schließt die installierte Anwendung über ihr Hauptfenster, wartet auf das vollständige Prozessende und startet denselben Datenstand ein zweites Mal.
- Bei einem Startfehler zeigt die Oberfläche zusätzlich den bereinigten technischen Fehlercode an.

### Geändert

- Beim normalen Beenden wird die Sidecar-Steuerleitung nach dem Shutdown-Befehl geschlossen, damit der lokale Dienst auch bei einem verzögerten Befehlsleser sicher ein Ende-Signal erhält.
- Kurzzeitige Sidecar-, Datenbank- und Loopback-Startfehler werden begrenzt erneut versucht; dauerhafte Speicher-, Migrations- und Paketfehler schlagen weiterhin sofort und sichtbar fehl.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.17`.

### Behobene Fehler

- Ein unmittelbar nach einem normalen Schließen erneut gestarteter Installer-Build kann nicht mehr durch einen noch auslaufenden lokalen Dienst beziehungsweise eine kurzzeitig belegte SQLite-Datei dauerhaft im Zustand „Lokaler Kern gestört“ bleiben.
- Der bisherige Windows-Test konnte einen funktionierenden ersten Start bestätigen, ohne das saubere Beenden und Wiederöffnen desselben installierten Datenordners zu prüfen.

### Bekannte Einschränkungen

- EVE-Refresh-Tokens bleiben im Windows-Anmeldespeicher und müssen auf einem anderen Rechner erneut autorisiert werden.
- Vollautomatische Installation bleibt bis zu einer produktiv signierten Update- und Rollback-Kette deaktiviert.
- Paket 22 benötigt weiterhin das vollständige Windows-A0-Protokoll auf dem Zielgerät.

### Update und Datenbankmigration

- Das Datenbankschema bleibt bei Version 9; es gibt keine neue fachliche Datenmigration.
- `.16` vollständig schließen und `.17` installieren. Die Installer-Option zum Löschen der Anwendungsdaten muss abgewählt bleiben; der vorhandene `data`-Ordner wird direkt weiterverwendet.

## 0.0.5-preview.16 – 11. September 2026

### Neu hinzugefügt

- Der Windows-Workflow installiert den erzeugten NSIS-Installer und startet Hauptanwendung sowie Sidecar wirklich, bevor ein Release veröffentlicht werden darf.
- Der Laufzeittest hält während der Übernahme absichtlich eine unwichtige Exportdatei gesperrt und prüft, dass die eigentliche Datenbank trotzdem sicher übernommen wird.

### Geändert

- Die `.13/.14`-Übernahme wiederholt kurzzeitig gesperrte Kopiervorgänge und fällt bei einem Problem mit unwichtigen Zusatzdateien auf die Datenbank, ihr WAL sowie erreichbare Backups und Exporte zurück.
- Sidecar-Startfehler werden nicht mehr zu einer allgemeinen Meldung zusammengefasst, sondern als Speicher-, Datenbank-, Windows-Start- oder Loopback-Fehler angezeigt.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.16`.

### Behobene Fehler

- Eine gesperrte Exportdatei oder ein ungültiger Zusatzpfad kann den ersten installierten Start nach `.15` nicht mehr vollständig blockieren.
- Ein vom Sidecar gemeldeter Datenbank- oder Schreibfehler bleibt bis zur Oberfläche erhalten und wird nicht mehr fälschlich als unbekannter Sidecar-Fehler ausgegeben.

### Bekannte Einschränkungen

- Nicht erreichbare unwichtige Zusatzdateien bleiben sicher im unveränderten alten AppData-Ordner; die für Charaktere, Einstellungen, Pläne und Cache maßgebliche SQLite-Datenbank wird weiterhin zwingend und atomar übernommen.
- EVE-Refresh-Tokens bleiben im Windows-Anmeldespeicher und müssen auf einem anderen Rechner erneut autorisiert werden.
- Vollautomatische Installation bleibt bis zu einer produktiv signierten Update- und Rollback-Kette deaktiviert.

### Update und Datenbankmigration

- Das Datenbankschema bleibt bei Version 9.
- `.15` vollständig schließen und `.16` installieren; die Datenlöschung muss abgewählt bleiben. `.16` verwendet einen bereits erfolgreich markierten Programmordner direkt weiter oder wiederholt eine zuvor gescheiterte Übernahme.
- Der AppData-Quellbestand wird weiterhin nicht gelöscht.

## 0.0.5-preview.15 – 11. September 2026

### Neu hinzugefügt

- Einmalige, atomare Übernahme des bisherigen `.13/.14`-Datenbestands aus Tauri AppData in den sichtbaren `data`-Ordner direkt neben der installierten EXE.
- Ein vorhandener älterer Programmordner-Datenstand wird vor der Übernahme separat als `data-before-appdata-migration` gesichert.
- Der Installer entfernt den programmordnergebundenen Datenstand nur bei ausdrücklich ausgewählter Datenlöschung.

### Geändert

- Installer und Portable verwenden denselben nachvollziehbaren Aufbau mit `data\foundry.sqlite3` neben der Haupt-EXE.
- Portable Hinweise nennen Desktop, USB-Stick und beliebige eigene Ordner ausdrücklich als mögliche, vom Installationsordner unabhängige Speicherorte.
- Der Installer-Hinweis erklärt, dass die Datenlöschung bei einem Update abgewählt bleiben muss.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.15`.

### Behobene Fehler

- Die installierte Ausgabe versteckt Datenbank, Backups und Exporte nicht mehr in einem getrennten Bundle-ID-AppData-Ordner.
- Ein vorhandener AppData-Stand wird nicht bei jedem Start erneut über neuere Daten im Programmordner kopiert.
- Ein Übernahmefehler kann nicht unbemerkt mit einer leeren Datenbank fortfahren.

### Bekannte Einschränkungen

- EVE-Refresh-Tokens bleiben aus Sicherheitsgründen im Windows-Anmeldespeicher und werden beim Kopieren einer portablen Ausgabe auf einen anderen Rechner nicht übertragen.
- Der Release-Hinweis lädt und installiert weiterhin nichts automatisch; Paketsignatur und Rollback fehlen noch.
- Paket 22 wartet auf den vollständigen Windows-A0-Test dieses Korrekturkandidaten.

### Update und Datenbankmigration

- Das Anwendungsschema bleibt bei Version 9.
- Beim ersten installierten Start wird der bisherige `.14`-Datenordner automatisch kopiert, atomar veröffentlicht und am alten Ort als zusätzliche Rückfallkopie belassen.
- Beim Update darf die Installer-Option zum Löschen der Anwendungsdaten nicht ausgewählt werden.
- Portable Installationen bleiben vollständig eigenständig; ihr vorhandener `data`-Ordner wird gesichert beziehungsweise in den neuen portablen Ordner übernommen.

## 0.0.5-preview.14 – 11. September 2026

### Neu hinzugefügt

- Der auf EVE-SDE-Build `3503375` festgelegte und per SHA-256 geprüfte Produktionskatalog wird mitgeliefert und beim ersten Start automatisch atomar installiert.
- Fehlgeschlagene Asset-, Blueprint- und Job-Abrufe nennen jetzt Charakter, Teilbereich und einen konkreten lokalen beziehungsweise ESI-Fehlercode.

### Geändert

- Cache ohne explizites Ablaufdatum gilt erst ab einem Datenalter von zwei Stunden als veraltet.
- Forschungspläne kennzeichnen ausdrücklich, dass sie lokale Arbeitslisten sind und weder Daten an EVE senden noch Jobs starten.
- Der Updatehinweis erklärt die portable Ausgabe als vollständig zu entpackenden Programmordner und grenzt sie von einem Start im ZIP oder einer Einzel-EXE ab.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.14`.

### Behobene Fehler

- Produktionsprodukte und Blueprints können ohne vorherigen manuellen SDE-Import gesucht und als Ziel gespeichert werden.
- Ein erfolgreicher Asset-Snapshot wird nicht mehr als vollständig fehlgeschlagen gemeldet, wenn nur Typnamen- oder Standortanreicherung scheitert.
- Deaktivierte Charaktere bleiben lokal gespeichert, verschwinden aber aus Asset-, Delta-, Blueprint- und Jobansichten.
- Alle aktivierten Charaktere stehen in Blueprint- und Jobfiltern, auch wenn für einen davon noch kein vollständiger Snapshot vorliegt.
- Fehlende Schriftgrößenvariablen im Produktionsbereich wurden ergänzt; die gespeicherte globale Schriftstufe bleibt nach einem Datenbankneustart erhalten.

### Bekannte Einschränkungen

- Bruttomaterial und Basiszeit berücksichtigen noch keinen Bestand, keine Reservierungen, kein Blueprint-ME, keine Skills, Anlagen-/Rigboni, Systemkosten, Steuern oder Preise.
- Der Release-Hinweis lädt und installiert nichts automatisch. Die automatische Ersetzung bleibt bis zu produktiv signierten Paketen, Rollback und bestandenem Windows-Update-Gate gesperrt.
- Paket 22 wartet weiterhin auf das vollständige Windows-A0-Protokoll.

### Update und Datenbankmigration

- Das Anwendungsschema bleibt bei Version 9; der SDE-Bestand ist vollständig abgeleitet und verändert keine Nutzerdaten.
- Installer- und Portable-Update behalten `data`, Charaktere, Einstellungen, Forschungs- und Produktionspläne sowie vollständige Snapshots bei.
- Es werden keine zusätzlichen ESI-Scopes benötigt.

## 0.0.5-preview.13 – 11. September 2026

### Neu hinzugefügt

- Paket 30: persistente Fertigungs- und Reaktionsziele mit Charakter, exaktem Rezept, Zielmenge, Priorität und Notiz.
- Deterministische, zyklensichere Auflösung gemeinsamer Zwischenprodukte in Produktionsschritte, ganzzahlig gerundete Läufe, Überschuss, SDE-Basiszeit und äußeren Bruttomaterialbedarf.
- Zweisprachiger Produktionsarbeitsbereich mit Suche, Filtern, Sortierung, Seitenteilung und vollständiger Zielverwaltung.
- Automatischer und manueller Hinweis auf das neueste vollständige GitHub Release im gewählten Kanal samt ausgabespezifischer Updateanleitung.

### Geändert

- Die Industrie-Slotübersicht bezieht Fertigungs- und Reaktionsziele als geplanten, laufenden oder blockierten Arbeitsvorrat ein.
- Die Desktop-Laufzeit unterscheidet installierte und portable Ausgaben anhand des portablen Paketmarkers.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.13`.

### Behobene Fehler

- Gemeinsamer Zwischenproduktbedarf wird vor der Laufberechnung aggregiert und nicht je Elternschritt separat überrundet.
- Alternative Rezepte werden stabil nach Aktivität und Blueprint-ID gewählt und die Entscheidung bleibt sichtbar.
- Fehlende oder später veränderte SDE-Rezepte löschen gespeicherte Ziele nicht.
- Unvollständige Releases ohne beide Pakete und Prüfsummen erzeugen keinen Updatehinweis.

### Bekannte Einschränkungen

- Die offizielle SDE-Bezugs- und Importpipeline ist noch nicht Teil des Endnutzerstarts. Ohne eine bereits importierte Aktivitätsbasis zeigt der Produktionsbereich deshalb den belegbaren Zustand „SDE fehlt“; Kettenberechnung und Zielverwaltung sind mit synthetischen Vertragsdaten automatisiert geprüft.
- Bruttomaterial und Basiszeit berücksichtigen noch keinen Bestand, keine Reservierungen, kein Blueprint-ME, keine Skills, Anlagen-/Rigboni, Systemkosten, Steuern oder Preise.
- Der Release-Hinweis lädt und installiert nichts automatisch. Die automatische Ersetzung bleibt bis zu produktiv signierten Paketen, Rollback und bestandenem Windows-Update-Gate gesperrt.
- Paket 22 wartet weiterhin auf das vollständige Windows-A0-Protokoll.

### Update und Datenbankmigration

- Beim ersten Start migriert die App Schema 8 auf Schema 9 und ergänzt die lokale Tabelle `production_plans` samt Indizes.
- Vor der Migration wird automatisch eine geprüfte Sicherung angelegt; vorhandene Charaktere, Einstellungen, Credentials, Forschungspläne und Snapshots bleiben erhalten.
- Für ein portables Update die App schließen, `data` sichern und die neue ZIP in denselben übergeordneten Ordner entpacken. Der konstante Programmordner wird aktualisiert, der nicht ausgelieferte `data`-Ordner bleibt bestehen.
- Es werden keine zusätzlichen ESI-Scopes benötigt.

## 0.0.5-preview.12 – 11. September 2026

### Neu hinzugefügt

- Paket 29: build-versionierte Blueprint-Aktivitätsbasis für Fertigung und Reaktionen mit vollständigen Produkt-/Materialmengen und unveränderten SDE-Basiszeiten.
- Rebuildbare SQLite-Tabellen für Aktivitäten, Produkte und Materialien mit geprüften Typreferenzen und aktivitätsspezifischen Suchindizes.
- Authentifizierte, streng begrenzte Abfrage nach Blueprint-, Produkt- und Aktivitätsfilter einschließlich gemeinsamer Aktivitäts-Buildnummer.

### Geändert

- Der atomare SDE-Import ersetzt Gruppen, Typen, Orte und Blueprintaktivitäten in einer gemeinsamen Transaktion.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.12`.

### Behobene Fehler

- Ungültige, leere, doppelte oder unvollständig referenzierte Blueprintrezepte können keinen Teilbestand und keinen neuen Buildmarker veröffentlichen.
- Ein späterer Minimalimport kann keine veralteten Aktivitäten unter einer neuen allgemeinen SDE-Buildnummer zurücklassen.
- Ohne vollständig belegten Aktivitätsimport wird ein allgemeiner SDE-Build nicht länger als Blueprint-Aktivitätsstand ausgegeben.

### Bekannte Einschränkungen

- Paket 29 stellt die unveränderte Fertigungs-/Reaktionsbasis bereit; Produktionsziele, Kettenauflösung, Bestand und Reservierungen folgen in Paket 30.
- ME, Runs, Rundung, Charakter-, Anlagen- und Rigmodifikatoren, Systemkosten, Steuern und Preise werden noch nicht auf die Basiswerte angewendet.
- Paket 22 wartet weiterhin auf das vollständige Windows-A0-Protokoll.

### Update und Datenbankmigration

- Keine Änderung am Anwendungsschema 8. Die neuen SDE-Tabellen sind vollständig rebuildbare, abgeleitete Daten.
- Bestehende Charaktere, Aliasse, Gruppen, Credentials, Forschungspläne und vollständige Snapshots bleiben erhalten; es werden keine zusätzlichen ESI-Scopes benötigt.

## 0.0.5-preview.11 – 11. September 2026

### Neu hinzugefügt

- Paket 28: gemeinsame, charaktergetrennte Übersicht der Fertigungs-, Reaktions- und Wissenschaftsslots.
- Belegbare Kapazität aus aktuell wirksamen Slot-Skills sowie reale Belegung durch aktive, pausierte und abholbereite persönliche Industrieaufträge.
- Wissenschafts-Arbeitsvorrat aus persistenten Forschungsplänen mit geplanten, laufenden, blockierten und abgeschlossenen Einträgen.
- Zweisprachige Kartenansicht mit Slotstatus, Jobaufschlüsselung, nächstem aktiven Jobende, Datenalter und stabilen Skill-/Job-Snapshot- und Sync-Run-IDs.

### Geändert

- Änderungen an Blueprint-, Job-, Skill- oder Forschungsdaten laden die abgeleitete Slotübersicht neu.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.11`.

### Behobene Fehler

- Fehlende Skill- oder Job-Snapshots erscheinen nicht als Kapazität null, leere Belegung oder freie Slots.
- Fertigungs-, Reaktions- und Wissenschaftsjobs werden über feste ESI-Aktivitätsgruppen getrennt gezählt; pausierte und abholbereite Jobs bleiben korrekt belegt.
- Kapazität und Belegung bleiben charakterbezogen und werden nicht zwischen verbundenen Charakteren verrechnet.

### Bekannte Einschränkungen

- Persistente Fertigungs- und Reaktionspläne folgen erst mit der Produktionsplanung; in diesen Bereichen besteht der belegbare Arbeitsvorrat derzeit aus aktuellen Jobs.
- Ein pausierter oder abholbereiter Job belegt einen Slot, liefert aber keinen prognostizierten Endzeitpunkt.
- Paket 22 wartet weiterhin auf das vollständige Windows-A0-Protokoll.

### Update und Datenbankmigration

- Keine Schemaänderung. Bestehende Charaktere, Aliasse, Gruppen, Credentials, Forschungspläne und vollständige Snapshots bleiben erhalten.
- Es werden keine zusätzlichen ESI-Scopes benötigt und keine vorhandenen Charaktere müssen wegen Paket 28 erneut angemeldet werden.

## 0.0.5-preview.10 – 11. September 2026

### Neu hinzugefügt

- Paket 27: persistente, charakter- und BPO-genaue Forschungspläne mit nächster ME-/TE-Aktivität, Zielwerten, Priorität und Notiz.
- Zweisprachige Forschungsansicht mit Zuständen für bereit, wartend, laufend, fertig, ungeprüft und fehlendes Blueprint sowie Suche, Filtern, Sortierung und begrenzten Seiten.
- Belegbare Wissenschaftsslot-Kapazität aus den aktuell wirksamen Skillständen und Belegung aus persönlichen Forschungs-, Kopier- und Erfindungsjobs.
- Reale Jobkosten, Start, Ende und Anlagenbeleg für laufende Forschung sowie stabile Blueprint-, Skill- und Job-Snapshot-/Run-IDs.

### Geändert

- Ein erfolgreicher Blueprint-, Skill-, Job- oder Anlagenabgleich aktualisiert anschließend auch den abgeleiteten Forschungsstand.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.10`.

### Behobene Fehler

- Ein gespeicherter Plan geht nicht verloren, wenn sein BPO vorübergehend nicht mehr im aktuellen vollständigen Blueprint-Snapshot erscheint.
- Fehlende Skill-, Anlagen- oder Modifikatordaten werden nicht als freie Slots, Nullkosten oder geschätzte Forschungsdauer ausgegeben.
- Aktive Forschung wird nur bei einer exakten Charakter- und Blueprint-Item-Zuordnung als laufender Plan dargestellt.

### Bekannte Einschränkungen

- Forschungsdauer und Gesamtkosten vor dem Einbau werden noch nicht berechnet. Die vollständigen SDE-Aktivitätswerte und alle anwendbaren Charakter-, Anlagen-, Service-, Rig-, Steuer- und Systemmodifikatoren müssen dafür gemeinsam belegbar sein.
- Die zuletzt vom Charakter für dieselbe Aktivität verwendete Anlage ist nur ein historischer Beleg und keine Zusage aktueller Verfügbarkeit.
- Paket 22 wartet weiterhin auf das vollständige Windows-A0-Protokoll.

### Update und Datenbankmigration

- Beim ersten Start migriert die App Schema 7 auf Schema 8 und ergänzt ausschließlich die lokale Tabelle `research_plans`.
- Vor der Migration wird automatisch eine geprüfte Sicherung angelegt. Charaktere, Aliasse, Gruppen, Credentials, Einstellungen und vollständige Snapshots bleiben erhalten.
- Bestehende Charaktere mit dem vollständigen Scope-Satz benötigen keine erneute Anmeldung.

## 0.0.5-preview.9 – 11. September 2026

### Neu hinzugefügt

- Paket 26: vollständiger globaler Snapshot des öffentlichen NPC-Anlagenkatalogs und der aktivitätsspezifischen Systemkostenindizes aus ESI.
- Beobachtete Spielerstrukturen aus persönlichen Job-Snapshots mit charakterbezogener Auflösung und sichtbaren Zuständen für Verfügbarkeit, fehlenden Scope, ACL-403 und unbekannte Anlagen.
- Zweisprachige Anlagenansicht mit offiziellen Namen, System und Region, Eigentümer, Typ, Kostenaktivität, Jobnutzung, Datenalter, Suche, Filtern, Sortierung und stabilen Snapshot-/Run-IDs.

### Geändert

- Der automatische Gesamtabgleich aktualisiert nach Assets, Blueprints, Skills und Jobs zuletzt den Anlagen-Snapshot, damit neu beobachtete Spielerstrukturen im selben Lauf berücksichtigt werden.
- Persönliche Jobzeilen zeigen Anlagenname, Sonnensystem und den zur Aktivität passenden Systemkostenindex aus demselben geprüften Anlagenstand.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.9`.

### Behobene Fehler

- Anlagen-IDs in persönlichen Jobs bleiben bei vorhandenem Anlagenbeleg nicht länger ohne lesbaren Stations- oder Strukturnamen.
- Fehlende Strukturrechte und in ESI nicht gelieferte Kostenbestandteile werden nicht als Null oder geschätzter Bonus ausgegeben.
- Fehlgeschlagene oder widersprüchliche öffentliche Teilabrufe können den letzten vollständigen Anlagen-Snapshot nicht überschreiben.

### Bekannte Einschränkungen

- Der öffentliche ESI-Anlagenkatalog enthält NPC-Anlagen; Spielerstrukturen können nur ergänzt werden, nachdem sie in einem vollständigen persönlichen Job-Snapshot beobachtet wurden.
- ESI liefert keine Struktur-/Rigboni und für den aktuellen öffentlichen Katalog keine verlässlich nutzbare Anlagensteuer. Diese Werte bleiben ausdrücklich unbekannt; der Systemkostenindex allein ist noch keine vollständige Jobkostenrechnung.
- Paket 22 wartet weiterhin auf das vollständige Windows-A0-Protokoll.

### Update und Datenbankmigration

- Keine Schemaänderung. Bestehende Charaktere, Aliasse, Gruppen, Credentials und Snapshots bleiben erhalten.
- Charaktere mit dem vollständigen Scope-Satz aus `v0.0.5-preview.6` benötigen keine erneute Anmeldung.

## 0.0.5-preview.8 – 11. September 2026

### Neu hinzugefügt

- Paket 25: vollständiger charaktergetrennter Sync trainierter Charakter-Skills einschließlich trainiertem und aktuell wirksamem Level sowie verteilter und freier Skillpunkte.
- Zweisprachige Skillansicht mit echten Typnamen, Besitzer, Datenalter, Suche, Besitzer-/Level-/Aktivzustandsfiltern, Sortierung, begrenzten Seiten und stabilen Snapshot-/Run-IDs.

### Geändert

- Der automatische Startabgleich aktualisiert nun Assets, Blueprints und Skills parallel vor den persönlichen Industrieaufträgen.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.8`.

### Behobene Fehler

- Fehlgeschlagene, unvollständige, doppelte oder rechnerisch widersprüchliche Skillantworten können den letzten vollständigen Skillstand nicht überschreiben.
- Temporär eingeschränkte oder verstärkte aktive Level werden getrennt vom trainierten Level dargestellt, statt die beiden Werte gleichzusetzen.

### Bekannte Einschränkungen

- ESI weist darauf hin, dass der Skill-Endpunkt nach abgeschlossenen Einträgen in der Skill-Warteschlange bis zur nächsten Charakteranmeldung im Spiel veraltet sein kann; eine Echtzeitüberlagerung mit der Warteschlange folgt in einem späteren Paket.
- Paket 22 wartet weiterhin auf das vollständige Windows-A0-Protokoll.

### Update und Datenbankmigration

- Keine Schemaänderung. Bestehende Charaktere, Aliasse, Gruppen, Credentials und Snapshots bleiben erhalten.
- Charaktere mit dem vollständigen Scope-Satz aus `v0.0.5-preview.6` benötigen keine erneute Anmeldung.

## 0.0.5-preview.7 – 11. September 2026

### Neu hinzugefügt

- Paket 24: vollständiger charaktergetrennter Sync persönlicher Industrieaufträge einschließlich der von ESI verfügbaren abgeschlossenen Jobs.
- Zweisprachige Jobansicht mit echten Typnamen, Besitzer, Aktivität, Status, Läufen, Kosten, Zeit, Datenalter, Suche, Filtern, Sortierung und begrenzten Seiten.
- Belegbasierte Korrelation mit exakten aktuellen oder historischen Blueprint-Items und passenden eingehenden Asset-Änderungen einschließlich stabiler Quell-IDs.

### Geändert

- Der automatische Startabgleich aktualisiert Assets und Blueprints vor den Industrieaufträgen, damit die Korrelation die frischesten vollständigen Quellen nutzt.
- Eindeutige Jobzuordnungen und Job-IDs erscheinen nun auch in der Asset-Historie, ohne gespeicherte Delta-Fingerabdrücke zu verändern.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.7`.

### Behobene Fehler

- Mehrere plausible Asset-Kandidaten bleiben sichtbar mehrdeutig, statt willkürlich als eindeutiger Treffer angezeigt zu werden.
- Fehlgeschlagene oder ungültige Jobabrufe können den letzten vollständigen Snapshot nicht überschreiben.
- Die Aktiv-Zahl umfasst das gesamte gefilterte Ergebnis statt nur der sichtbaren Seite.

### Bekannte Einschränkungen

- ESI bestimmt die verfügbare Historie abgeschlossener Jobs; vor dem ersten erfolgreichen Lauf nicht mehr gelieferte Jobs können nicht rekonstruiert werden.
- Paket 22 wartet weiterhin auf das vollständige Windows-A0-Protokoll.

### Update und Datenbankmigration

- Keine Schemaänderung. Bestehende Charaktere, Aliasse, Gruppen, Credentials und Snapshots bleiben erhalten.
- Charaktere mit dem vollständigen Scope-Satz aus `v0.0.5-preview.6` benötigen keine erneute Anmeldung.

## 0.0.5-preview.6 – 10. September 2026

### Neu hinzugefügt

- Paket 23: echter, vollständig paginierter Blueprint-Sync für alle aktivierten Charaktere mit atomaren charaktergetrennten Snapshots.
- Zweisprachige BPO/BPC-Ansicht mit echten Typnamen, Besitzer, ME/TE, Läufen, Inventarbereich, Datenalter, Suche, Filtern, Sortierung und begrenzten Seiten.
- Sichtbarer Status **Anmeldung nötig** mit direkter erneuter EVE-SSO-Anmeldung, wenn einem gespeicherten Charakter aktuelle Scopes oder sein Credential fehlen.

### Geändert

- Neue und erneute Charakteranmeldungen fordern automatisch alle fünf aktuell registrierten SSO-Berechtigungspakete an; die manuelle Paketauswahl entfällt.
- Der Hintergrundabgleich beim Programmstart und nach einer Charakteranmeldung aktualisiert nun Assets und Blueprints.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.6`.

### Behobene Fehler

- Später ergänzte App-Berechtigungen führen nicht länger zu einer schwer erkennbaren Teilfunktion: betroffene Charaktere werden eindeutig markiert und bleiben bis zur idempotenten Neuanmeldung gespeichert.
- Fehlgeschlagene oder unvollständige Blueprint-Abrufe können den letzten vollständigen Bestand nicht überschreiben.

### Bekannte Einschränkungen

- Persönliche Industrieaufträge und deren Korrelation mit Blueprint- und Asset-Änderungen folgen in Paket 24.
- Paket 22 wartet weiterhin auf das vollständige Windows-A0-Protokoll.

### Update und Datenbankmigration

- Keine Schemaänderung. Bestehende Charaktere, Aliasse, Gruppen, Credentials und Snapshots bleiben erhalten.
- Charaktere mit einem älteren Scope-Satz müssen einmal über den sichtbaren Hinweis erneut angemeldet werden.

## 0.0.5-preview.5 – 10. September 2026

### Neu hinzugefügt

- Automatischer Asset-Abgleich für alle aktivierten Charaktere beim Programmstart und nach einer neuen Charakterverbindung.
- Öffentliche ESI-Typnamensauflösung in begrenzten Paketen mit dauerhaftem lokalen Cache.
- Auf- und absteigende Sortierung aller Spalten der Asset-Tabelle vor der serverseitigen Seitenteilung.

### Geändert

- Der manuelle Befehl **Assets aktualisieren** bleibt als zusätzlicher Folgelauf erhalten.
- CSV-Exporte übernehmen die gewählte Sortierung.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.5`; diese Preview ersetzt den vorherigen Windows-Abnahmekandidaten.

### Behobene Fehler

- Assets zeigen nach dem nächsten erfolgreichen Abgleich echte Itemnamen statt `Type #<ID>`, sofern ESI die Inventartyp-ID auflösen kann.
- Bereits verbundene aktivierte Charaktere müssen nach einem normalen Update nicht erneut hinzugefügt und ihre Assets nicht zuerst manuell geladen werden.

### Bekannte Einschränkungen

- Ein vor `v0.0.5-preview.4` bereits verlorener Datenordner lässt sich nicht rekonstruieren; der betroffene Charakter muss einmal neu verbunden werden.
- Paket 22 wartet weiterhin auf das vollständige Windows-A0-Protokoll.

### Update und Datenbankmigration

- Beim ersten Start migriert die App Schema 6 auf Schema 7 und ergänzt ausschließlich den ableitbaren Typnamenscache `resolved_type_names`.
- Vor der Migration wird wie bisher automatisch eine geprüfte Sicherung angelegt; Charaktere, Tokens und vollständige Snapshots bleiben unverändert.

## 0.0.5-preview.4 – 10. September 2026

### Neu hinzugefügt

- Ein echter, manuell auslösbarer Asset-Sync lädt alle aktivierten Charaktere, löst ihre Standorte auf und aktualisiert Bestand und Änderungen direkt in der Asset-Ansicht.

### Geändert

- Installationen speichern Daten dauerhaft im benutzerspezifischen Windows-App-Datenordner statt neben der austauschbaren Programmdatei.
- Die portable Ausgabe verwendet den versionsunabhängigen Ordner `New Eden Foundry Portable`, damit ein Update im gleichen Zielordner den vorhandenen `data`-Ordner behält.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.4`; diese Preview ersetzt den vorherigen Windows-Abnahmekandidaten.

### Behobene Fehler

- Charaktere, Einstellungen und lokale Snapshots gehen nach einem Installer-Update nicht mehr durch einen wechselnden Programmordner verloren.
- Ein vorhandener alter `data`-Ordner wird bei der ersten installierten Ausführung sicher kopiert und atomar übernommen; das Original bleibt als Rückfallebene erhalten.
- Die Asset-Ansicht bleibt nicht länger leer, weil der zuvor fehlende Aufruf vom Desktop über den Sidecar bis zum ESI-Asset- und Standortlauf geschlossen wurde.

### Bekannte Einschränkungen

- Bereits vor dieser Korrektur durch einen Installer entfernte lokale Daten können nicht automatisch rekonstruiert werden; der Charakter muss in diesem Fall einmal neu verbunden werden und bleibt danach erhalten.
- Paket 22 wartet weiterhin auf den vollständigen Windows-A0-Gerätetest einschließlich Update und Entfernung.

### Update und Datenbankmigration

- SQLite-Schema 6 bleibt unverändert. Nur der Speicherort der installierten Ausgabe wird einmalig migriert.
- Portable Nutzer kopieren bei diesem einmaligen Übergang den bisherigen `data`-Ordner in `New Eden Foundry Portable`; spätere Updates können denselben Zielordner verwenden.

## 0.0.5-preview.3 – 10. September 2026

### Neu hinzugefügt

- Charakterbezogene Asset-Standortauflösung für SDE-Standorte, NPC-Stationen und Spielerstrukturen.
- Root-first-Containerpfade mit SDE-Typnamen und kontrollierter Erkennung zyklischer Beziehungen.
- Vollständige Standort-Snapshots mit Referenz auf den zugrunde liegenden Asset-Snapshot und zusammengefassten Statuswerten.
- Synthetische Golden-Fälle für Station, verschachtelte Container, Struktur-403, fehlenden Scope, Zyklen und Folgefehler.
- Echte zweisprachige Asset-Oberfläche mit Suche, Besitzer- und Standortstatusfilter, Mengen, Datenalter und root-first Standortpfaden.
- Serverseitig begrenzte 100-Zeilen-Seiten sowie ein synthetischer 100.000-Positionen-Regressionstest.
- Gefilterter, atomarer UTF-8-CSV-Export nach `data\exports` mit Formelneutralisierung.
- Atomare, charaktergetrennte Asset-Deltas mit Baseline, deterministischem Ereignis-Fingerabdruck und vollständigem Snapshot-/Run-Nachweis.
- Zweisprachiger Änderungsverlauf für hinzugekommene, entfernte, mengenveränderte und verschobene Assets mit Suche, Besitzer- und Änderungsartfilter.
- Korrelationsbelege aus Charakter, Typ, Richtung, Mengendifferenz und Beobachtungsfenster für die spätere Zuordnung von Industrie-Jobs.
- Synthetischer Regressionstest mit 10.000 Delta-Ereignissen und begrenztem 50-Ereignis-Antwortfenster.

### Geändert

- Eine nicht lesbare Spielerstruktur ist jetzt ein stabiler eingeschränkter Fachzustand und kein Fehler des gesamten Standortlaufs.
- Wiederholte Stationen oder Strukturen werden innerhalb eines Auflösungslaufs nur einmal abgefragt.
- Die Asset-Oberfläche verwendet nur den letzten vollständigen Snapshot je Charakter und lädt höchstens 100 Zeilen pro sichtbarer Seite.
- Der lokale Antwortschutz erlaubt bounded Asset-Seiten, während große CSV-Inhalte als Datei geschrieben und nicht durch die Desktop-Brücke übertragen werden.
- Die Asset-Synchronisierung veröffentlicht Bestand und Delta gemeinsam oder rollt beide zurück; die Historie überträgt höchstens 50 Ereignisse pro sichtbarer Seite.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.3`; diese Preview ist der reproduzierbare Windows-Abnahmekandidat für Paket 22.
- Das verbindliche A0-Protokoll prüft Installation, zweiten Start, Update, Datenerhalt, Portable-Ausgabe und Entfernung vor der ersten `0.2.0`-Alpha.

### Behobene Fehler

- Fehlende Container und zyklische Containerbeziehungen können die Auflösung nicht mehr unkontrolliert abbrechen oder endlos rekursiv laufen.
- Ein technischer Fehler während der Standortauflösung veröffentlicht keinen Teilstand und überschreibt keinen letzten vollständigen Snapshot.
- Standortpfade eines älteren Snapshots können nach einem neueren Asset-Sync nicht versehentlich mit den neuen Positionen verbunden werden; bis zur passenden Auflösung erscheint `pending`.
- Beschädigte vollständige Asset- oder Standort-Snapshots sowie unsichere CSV-Zielpfade werden geschlossen abgewiesen.
- Fehlgeschlagene oder widersprüchliche Asset-Folgeläufe können keine falschen Änderungen erzeugen; manipulierte Delta-Fingerabdrücke werden beim Lesen abgewiesen.

### Bekannte Einschränkungen

- Schutzregeln für `main` sind noch nicht aktiviert.
- Spielerstrukturen ohne erteilten Scope oder ohne Zugriffsrecht bleiben absichtlich ohne Namen und werden als eingeschränkt markiert.
- Asset-Deltas sind für die spätere Industrie-Jobkorrelation vorbereitet, werden aber bis zum Jobs-Sync bewusst als `unmatched` angezeigt.
- Die erste `0.2.0`-Alpha bleibt bis zur vollständig bestandenen manuellen Windows-A0-Abnahme gesperrt.
- Öffentliche Updateverteilung und Codesignierung sind weiterhin deaktiviert; Windows kann vor dem unbekannten Herausgeber warnen.

### Update und Datenbankmigration

- Keine Anwendungsmigration; SQLite-Schema 6 bleibt unverändert. Standort- und Delta-Daten bleiben ableitbare Snapshots, CSV-Dateien liegen unter `data\exports`.
- Installer-Updates lassen den nicht gebündelten `data`-Ordner bestehen; für portable Updates wird er erst nach vollständigem Schließen der App übernommen.

## 0.0.5-preview.2 – 10. September 2026

### Neu hinzugefügt

- Minimaler SDE-Bestand für Typen, Gruppen und Orte mit atomarem Austausch und eindeutiger SDE-Buildnummer.
- Multi-Character-Asset-Synchronisierung über den zentralen ESI-Client mit `esi-assets.read_assets.v1`.
- Vollständige Asset-Pagination über `X-Pages` sowie charaktergetrennte Sync-Runs und Snapshots.
- Tests für atomaren SDE-Import, Pagination, vollständige Asset-Snapshots und abgebrochene Läufe.

### Geändert

- Abgeleitete SDE-Tabellen bleiben bewusst außerhalb der versionierten Anwendungsmigration und können vollständig neu aufgebaut werden.
- Asset-Daten werden erst veröffentlicht, wenn alle Seiten eines Charakterlaufs vollständig validiert wurden.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.2`.
- Der Masterplan markiert Pakete 17 und 18 als abgeschlossen; Paket 19 Standortauflösung ist der nächste Fachschritt.

### Behobene Fehler

- Ein fehlerhafter SDE-Import kann den letzten gültigen SDE-Bestand nicht mehr teilweise überschreiben.
- Ein Netzwerkfehler oder Abbruch mitten in der Asset-Pagination erzeugt keinen unvollständigen gültigen Snapshot.
- Doppelte Asset-`item_id` über mehrere Seiten werden als inkonsistenter Lauf verworfen.
- Der letzte vollständig abgeschlossene Asset-Cache bleibt bei einem Folgfehler für Cache-First/Offline-Nutzung erhalten.

### Bekannte Einschränkungen

- Die Asset-Synchronisierung stellt in Paket 18 den Backend-Kern bereit; Standortauflösung und die vollständige Asset-Oberfläche folgen in Paketen 19 und 20.
- SDE- und Asset-Daten werden noch nicht als vollständig produktive Fachansicht in der React-Oberfläche dargestellt; vorhandene Fachkennzahlen bleiben dort teilweise synthetisch.
- Der sichere Refresh-Token-Speicher ist in dieser Windows-first Preview nur unter Windows verfügbar.
- Codesignierung, das manuelle Windows-Laufzeitgate und der Schutz von `main` bleiben offen.

### Update und Datenbankmigration

- Keine neue Anwendungsmigration; SQLite-Schema 6 bleibt unverändert.
- SDE-Tabellen sind abgeleitete Daten und werden beim Import atomar angelegt beziehungsweise ersetzt.
- Vorhandene Charaktere, Gruppen, Einstellungen, Refresh Tokens und bereits vollständige Cache-Snapshots bleiben erhalten.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen.

## 0.0.5-preview.1 – 10. September 2026

### Neu hinzugefügt

- Zentraler `EsiClient` als einzige HTTP-Vertrauensgrenze für alle künftigen EVE-ESI-Aufrufe.
- Charaktergetrennte In-Memory-Caches mit `Cache-Control`, `Expires`, `ETag`, `Last-Modified` und bedingter 304-Revalidierung.
- Begrenzte Wiederholungen für Netzwerkfehler und ausgewählte transiente HTTP-Status einschließlich `Retry-After`.
- Gemeinsames ESI-Fehlerbudget und Circuit Breaker mit sichtbarem, geheimnisfreiem Sidecar-Status.
- Deterministische Tests für Header, Auth-Isolation, Cache, Retry, Budget, Circuit, Zielbegrenzung, JSON-Grenzen und Token-Redigierung.

### Geändert

- Charaktergebundene ESI-Aufrufe beziehen Access Tokens ausschließlich über den bestehenden `CharacterTokenService`.
- Jede ESI-Anfrage setzt `X-Compatibility-Date: 2026-09-09` und einen beschreibenden User-Agent mit Produkt, Repository und Kontakt.
- ESI-Ziele sind auf relative Pfade unter `https://esi.evetech.net` begrenzt; Redirects werden abgewiesen.
- Masterplan 2.4 markiert Arbeitspaket 16 als abgeschlossen und den minimalen SDE-Import als nächsten Schritt.
- Die sichtbare Versionsnummer wurde auf `v0.0.5-preview.1` aktualisiert.

### Behobene Fehler

- Fachmodule können Cache-, Retry- oder Rate-Limit-Regeln nicht mehr unbemerkt voneinander abweichend implementieren.
- Abgelaufene Cacheeinträge werden mit Servervalidatoren geprüft, statt bekannte Antworten unnötig neu zu laden oder still zu leeren.
- Ein erschöpftes ESI-Fehlerbudget und wiederholte transiente Fehler stoppen weitere Aufrufe kontrolliert.
- Transportfehler geben keine Access Tokens, Antwortinhalte oder frei steuerbaren Ziel-URLs aus.

### Bekannte Einschränkungen

- Paket 16 liefert die zentrale Transport- und Resilienzschicht; SDE-Import, Endpoint-Pagination und fachliche Synchronisierung folgen ab Paket 17.
- Fachkennzahlen der Oberfläche bleiben bis zur jeweiligen Synchronisierungsanbindung synthetisch.
- Der sichere Refresh-Token-Speicher ist in dieser Windows-first Preview nur unter Windows verfügbar.
- Öffentliche Updateverteilung, Codesignierung, das manuelle Windows-Laufzeitgate und der Schutz von `main` bleiben offen.

### Update und Datenbankmigration

- Keine Datenbankmigration; Schema-Version 6 und alle vorhandenen Charakter-, Gruppen- und Einstellungsdaten bleiben erhalten.
- Bestehende Refresh Tokens verbleiben im Windows-Anmeldespeicher. ESI-Antwortcaches aus Paket 16 sind absichtlich prozesslokal und beginnen nach jedem Start leer.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen.

## 0.0.4-preview.6 – 10. September 2026

### Neu hinzugefügt

- Vollständiger Charaktereditor für lokalen Alias, Aktivstatus und optionale Kontogruppe.
- Editor für lokale Kontogruppen mit Anlegen, Umbenennen und Löschen ohne Verlust zugeordneter Charaktere.
- Verständliche Credential- und Scopepaket-Status pro Charakter einschließlich bestätigter und erforderlicher Scope-Anzahl.
- Zweistufig bestätigter vollständiger Löschablauf für Charakter, Scopes, Sync-Historie, Cache-Snapshots, Prozess-Token und Refresh Token.
- Automatisierte Backend-, IPC-, Migrations- und Oberflächentests für alle Verwaltungs- und Fehlerpfade.

### Geändert

- Das SQLite-Schema wurde auf Version 6 angehoben und speichert optionale lokale Charakteraliase.
- Die echte Charakterliste verwendet den Alias als primären Anzeigenamen, hält den verifizierten EVE-Namen aber sichtbar.
- Mehrfachvalidierung in React, Tauri und Sidecar begrenzt IDs, Alias, Gruppen und abgeleitete Statuswerte.
- Masterplan 2.3 markiert Arbeitspaket 15 als abgeschlossen und den zentralen ESI-Client als nächsten Schritt.
- Die sichtbare Versionsnummer wurde auf `v0.0.4-preview.6` aktualisiert; `Savoxmedia` bleibt ausschließlich als Ersteller der App neben der Version genannt.

### Behobene Fehler

- Verbundene Charaktere können jetzt deaktiviert oder lokal organisiert werden, ohne erneut autorisiert werden zu müssen.
- Beim Löschen eines Charakters bleiben keine abhängigen SQLite-Datensätze oder prozesslokalen Token-Leases zurück.
- Ein Fehler beim Löschen des Windows-Credentials entfernt den zugehörigen SQLite-Charakter nicht mehr teilweise.
- Das Löschen einer Kontogruppe lässt zugeordnete Charaktere korrekt als nicht gruppiert bestehen.

### Bekannte Einschränkungen

- Der zentrale ESI-Client und damit die echte Synchronisierung folgen in Arbeitspaket 16; Fachkennzahlen bleiben bis dahin synthetisch.
- Auf Linux und macOS ist absichtlich keine Ersatzablage aktiv; die Windows-first Preview meldet den Credential-Backend dort als nicht verfügbar.
- Öffentliche Updateverteilung und Codesignierung bleiben deaktiviert; das manuelle Windows-Laufzeitgate und der Schutz von `main` sind offen.

### Update und Datenbankmigration

- Beim ersten Start migriert die App Schema 5 auf Schema 6 und ergänzt `characters.alias`; vorher wird automatisch eine geprüfte Sicherung unter `data\backups` angelegt.
- Vorhandene Charaktere, Gruppen, Scopes, Einstellungen und Refresh Tokens bleiben erhalten; Aliasse beginnen leer.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen. Refresh Tokens verbleiben getrennt im Windows-Anmeldespeicher des aktuellen Nutzers.

## 0.0.4-preview.5 – 9. September 2026

### Neu hinzugefügt

- Charaktergebundene Refresh-Token-Ablage im Windows-Anmeldespeicher ohne Datei- oder SQLite-Rückfall.
- Verifizierter Zwei-Slot-Austausch für Erstablage und Rotation einschließlich Wiederaufnahme nach unterbrochenem Schreiben.
- Prozesslokaler Access-Token-Cache mit rechtzeitiger, charaktergebundener Erneuerung und Konfliktschutz für parallele Rotationen.
- Automatisierte Sicherheits- und Integrationsprüfungen für Ablage, Rotation, Redigierung, Identität und Fehlerpfade.

### Geändert

- Ein erfolgreicher SSO-Rückruf gilt erst nach geprüfter Identität, erfolgreicher SQLite-Speicherung und bestätigter Aktivierung des Refresh Tokens als verbunden.
- Access Tokens verbleiben ausschließlich im Sidecar-Speicher; Refresh Tokens werden ausschließlich über den Windows-Anmeldespeicher gelesen und ersetzt.
- Der Sidecar meldet den verfügbaren Credential-Backend-Status, ohne Eintragsnamen oder Geheimnisse preiszugeben.
- Masterplan 2.2 markiert Arbeitspaket 14 als abgeschlossen und die vollständige Charakterverwaltung als nächsten Schritt.
- Die sichtbare Versionsnummer wurde auf `v0.0.4-preview.5` aktualisiert; `Savoxmedia` bleibt ausschließlich als Ersteller der App neben der Version genannt.

### Behobene Fehler

- Nach einer erfolgreichen Autorisierung wird der Refresh Token nicht mehr verworfen; der verbundene Charakter kann künftig ohne erneute Browseranmeldung ein Access Token erhalten.
- Ein fehlgeschlagener Austausch überschreibt den letzten aktiven Refresh Token nicht.
- Eine veraltete parallele Rotation kann einen bereits erneuerten Refresh Token nicht zurücksetzen.
- Tokenwerte erscheinen auch vollqualifiziert verpackt weder in Objekt-Repräsentationen noch in öffentlichen Fehlertexten.

### Bekannte Einschränkungen

- Die Verwaltungsoberfläche für Alias, Aktivstatus, Gruppen, Scope-Status und vollständiges Löschen folgt in Arbeitspaket 15.
- Der zentrale ESI-Client und damit die echte Synchronisierung folgen in Arbeitspaket 16; Fachkennzahlen bleiben bis dahin synthetisch.
- Auf Linux und macOS ist absichtlich keine Ersatzablage aktiv; die aktuelle Windows-first Preview meldet den Credential-Backend dort als nicht verfügbar.
- Öffentliche Updateverteilung und Codesignierung bleiben deaktiviert; das manuelle Windows-Laufzeitgate und der Schutz von `main` sind offen.

### Update und Datenbankmigration

- Keine Datenbankmigration; Schema-Version 5 und alle Daten unter `data` bleiben erhalten.
- Bereits in `v0.0.4-preview.4` verbundene Charaktere besitzen noch keinen Refresh Token und müssen einmal erneut verbunden werden.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen. Refresh Tokens verbleiben getrennt im Windows-Anmeldespeicher des aktuellen Nutzers.

## 0.0.4-preview.4 – 9. September 2026

### Neu hinzugefügt

- Echter PKCE-Codeaustausch ohne Client Secret und strikte JWT-Prüfung über EVE-Metadaten und JWKS.
- Prüfung von `RS256`-Signatur, Schlüssel-ID, Issuer, beiden Audience-Werten, Ablauf, Charakter-ID, Name und bestätigten Scopes.
- Sichtbare, dauerhaft aus SQLite geladene Liste aller erfolgreich verbundenen EVE-Charaktere.
- Globale Schriftgröße in fünf Stufen für alle derzeit sichtbaren Oberflächentexte.
- Automatisierte Positiv- und Negativtests für Token-, Identitäts-, Persistenz- und Darstellungskette.

### Geändert

- Ein Callback wechselt zunächst in den sichtbaren Prüfzustand; nur eine vollständig validierte EVE-Identität erreicht den Zustand `connected`.
- Erneute Autorisierung aktualisiert denselben Charakter idempotent und erhält eine bestehende lokale Kontogruppenzuordnung.
- Die Schriftgrößenstufe wird ohne neue Datenbankmigration in `app_settings` im Programmordner gespeichert.
- Masterplan 2.1 markiert Arbeitspaket 13 als abgeschlossen und Schlüsselbund/Rotation als nächsten Schritt.
- Die sichtbare Versionsnummer wurde auf `v0.0.4-preview.4` aktualisiert; `Savoxmedia` bleibt ausschließlich als Ersteller der App neben der Version genannt.

### Behobene Fehler

- Ein im Browser erfolgreich autorisierter Charakter bleibt nach einem erneuten Login nicht mehr unsichtbar, sondern erscheint sofort und nach Neustarts in der echten Charakterliste.
- Ungeprüfte, manipulierte, abgelaufene oder für einen anderen Client ausgestellte Tokens können keinen Charakterdatensatz erzeugen.
- Alle sichtbaren Textbereiche reagieren gemeinsam auf eine Schriftgrößenänderung.

### Bekannte Einschränkungen

- Eine Autorisierung aus `v0.0.4-preview.3` muss wiederholt werden, weil Paket 12 den einmaligen Code bewusst verworfen hat.
- Access und Refresh Token werden nach der Identitätsprüfung noch verworfen; Schlüsselbundspeicherung und Rotation folgen in Paket 14.
- Fachkennzahlen bleiben synthetisch; ESI, SDE, echte Synchronisierung und Berechnungen sind noch nicht angeschlossen.
- Öffentliche Updateverteilung und Codesignierung bleiben deaktiviert; das manuelle Windows-Laufzeitgate und der Schutz von `main` sind offen.

### Update und Datenbankmigration

- Keine Datenbankmigration; Schema-Version 5 und alle Daten unter `data` bleiben erhalten.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen.

## 0.0.4-preview.3 – 9. September 2026

### Neu hinzugefügt

- Echter EVE-SSO-Autorisierungsstart im Systembrowser für jeweils einen Charakter.
- Kurzlebiger Callback-Listener an `http://127.0.0.1:17891/oauth/callback` mit kryptografischem `state`, neuem PKCE-Verifier und `S256`-Challenge je Versuch.
- Auswahl minimaler Funktions-Scopes pro Charakter sowie sichtbare Zustände für Warten, Erfolg, EVE-Ablehnung, Timeout und Abbruch.
- Durchgängige Backend-, Sidecar-, native IPC- und Oberflächentests einschließlich Frozen-Smoke-Prüfung.

### Geändert

- Tauri öffnet nur vollständig geprüfte EVE-Autorisierungs-URLs und gibt keine PKCE-Geheimnisse an die Weboberfläche weiter.
- Mehrere Charaktere werden weiterhin einzeln autorisiert; gemeinsame und getrennte Übersichten bleiben unverändert vorbereitet.
- Masterplan 2.0 führt Arbeitspaket 12 als abgeschlossen und JWT-Validierung als nächsten Schritt.
- Die sichtbare Versionsnummer wurde auf `v0.0.4-preview.3` aktualisiert; `Savoxmedia` bleibt ausschließlich als Ersteller der App neben der Version genannt.

### Behobene Fehler

- Falsche, fehlende oder doppelte `state`- und Code-Parameter können keinen erfolgreichen lokalen Rückruf mehr erzeugen.
- Timeout, Abbruch, Fehler und App-Ende lassen keinen aktiven Callback-Listener und keine temporären PKCE-Werte zurück.
- Der Frozen-Smoke-Test erhält mehr Zeit für einen sauberen Prozess-Shutdown unter paralleler Windows-CI-Last.

### Bekannte Einschränkungen

- Paket 12 endet nach dem verifizierten Browser-Rückruf. Codeaustausch, JWT-Validierung und dauerhafte Charakterzuordnung folgen in Paket 13; der Autorisierungscode wird in dieser Preview bewusst verworfen.
- Die Mehrcharakter-Oberfläche verwendet weiterhin synthetische Fachwerte und liest ihre Inhalte noch nicht aus SQLite.
- ESI, SDE, echte Synchronisierung und Fachberechnungen sind noch nicht angeschlossen.
- Öffentliche Updateverteilung und Codesignierung bleiben deaktiviert; das manuelle Windows-Laufzeitgate und der Schutz von `main` sind offen.

### Update und Datenbankmigration

- Keine Datenbankmigration; Schema-Version 5 und alle Daten unter `data` bleiben unverändert.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen.

## 0.0.4-preview.2 – 9. September 2026

### Neu hinzugefügt

- Verbindliches öffentliches EVE-SSO-App-Profil mit fester Loopback-Callback-URI, öffentlicher Client-ID und Entwicklerkontakt.
- Minimale Scopepakete für Industrie, private Strukturen, Markt, Projekte und Planetary Industry.
- Strikte Profil-, Sidecar- und Frozen-Pakettests gegen Callback-, Scope- und Client-ID-Drift.
- ADR-012 und dokumentierte Portalwerte für reproduzierbare spätere Abgleiche.

### Geändert

- Sidecar und Selbsttest melden das gebündelte SSO-Profil als registriert.
- Der feste Browser-Callback-Port ist ausdrücklich vom dynamischen internen Sidecar-Port getrennt.
- Arbeitspaket 11 ist abgeschlossen; als Nächstes folgt der eigentliche PKCE-Login.
- Die sichtbare Versionsnummer wurde auf `v0.0.4-preview.2` aktualisiert.

### Behobene Fehler

- Callback-URI, öffentliche Client-ID und Scope-Menge können nicht mehr unbemerkt zwischen Portalvorlage, Code, Paket und Tests auseinanderlaufen.
- Ein fehlender oder ungültiger Client-ID-Wert wird nicht als abgeschlossene Registrierung gemeldet.

### Bekannte Einschränkungen

- Die Registrierung ist vollständig, aber eine echte EVE-Anmeldung folgt erst mit PKCE-, Callback- und JWT-Implementierung in den nächsten Arbeitspaketen.
- Die Mehrcharakter-Oberfläche arbeitet weiterhin mit synthetischen Daten.
- ESI, SDE, echte Synchronisierung und Fachberechnungen fehlen noch.
- Öffentliche Updateverteilung und Codesignierung bleiben deaktiviert; das manuelle Windows-Laufzeitgate und der Schutz von `main` sind offen.

### Update und Datenbankmigration

- Keine Datenbankmigration; Schema-Version 5 und alle Daten unter `data` bleiben unverändert.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen.

## 0.0.4-preview.1 – 9. September 2026

### Neu hinzugefügt

- Wählbare, lokal gespeicherte Updatekanäle „Offiziell“, „Beta“ und „Vorschau / Test“.
- Schema-Version 5 mit `app_settings` und sicherem Standardkanal `stable`.
- Gebündeltes Ed25519-signiertes, nicht auslieferndes Testmanifest samt strenger Struktur- und Zielprüfung.
- Backend-, Sidecar-, IPC-, UI- und Frozen-Pakettests für Kanalwahl und Vertrauensgrenze.

### Geändert

- Kanaländerungen laufen ausschließlich über den authentifizierten Sidecar und bleiben nach einem Neustart in der Datenbank im Programmordner erhalten.
- Laufzeitstatus und Oberfläche unterscheiden Manifestprüfung und öffentliche Verteilung ausdrücklich.
- Der Sidecar-Build bündelt Testmanifest, Signatur und die fest versionierte Kryptografie-Abhängigkeit.
- Die sichtbare Versionsnummer wurde auf `v0.0.4-preview.1` aktualisiert.

### Behobene Fehler

- Nicht vertrauenswürdige, mehrdeutige oder auf einen öffentlichen Host verweisende Testmetadaten werden vor Verwendung abgewiesen.
- Die Browser-Vorschau kann keinen erfolgreichen nativen Kanalwechsel vortäuschen.

### Bekannte Einschränkungen

- Es gibt noch keinen öffentlichen Updater, Netzwerkabruf, Download oder automatische Installation; die Auswahl speichert derzeit nur die spätere Kanalpräferenz.
- Die Mehrcharakter-Oberfläche verwendet weiterhin synthetische Werte und liest ihre Fachinhalte noch nicht aus SQLite.
- EVE SSO, ESI, SDE, echte Synchronisierung und Fachberechnungen fehlen noch.
- Installer und portable EXE sind noch nicht code-signiert.
- Das manuelle Windows-Laufzeitgate und die Schutzregeln für `main` sind noch offen.

### Update und Datenbankmigration

- Schema 4 wird nach automatischer Sicherung auf Schema 5 migriert und um lokale Anwendungseinstellungen ergänzt.
- Bestehende Charakter- und Cache-Daten bleiben erhalten; die Updatekanal-Präferenz startet einmalig mit `stable`.
- Eine frische Installation legt direkt Schema-Version 5 an.

## 0.0.3-preview.3 – 9. September 2026

### Neu hinzugefügt

- Cache-first-Startzustände für Laden, Aktualisieren, leer, aktuell, veraltet, offline und fehlerhaft.
- Zweisprachiges Statusband mit echtem lokalen Datenalter und verständlicher Zustandsbeschreibung.
- Schema-Version 4 mit optionalem Ablaufzeitpunkt je Cache-Snapshot.
- Tests für Cache-Ablauf, Offlinebetrieb, Folgfehler, laufende Aktualisierung und ungültige Metadaten.

### Geändert

- Sidecar und Tauri-Schale übertragen und prüfen den aus SQLite abgeleiteten Cachezustand.
- Die native App simuliert keine erfolgreiche Aktualisierung mehr, solange ESI noch nicht angeschlossen ist.
- Programmordner-, Datenbank- und Sidecarfehler werden verständlich und ohne absolute lokale Pfade erklärt.
- Die sichtbare Versionsnummer wurde auf `v0.0.3-preview.3` aktualisiert.

### Behobene Fehler

- Ein fehlgeschlagener Folgelauf lässt einen vorhandenen vollständigen Cache nicht mehr leer erscheinen.
- Interne Synchronisierungsfehler werden vor der UI-Ausgabe auf stabile Codes reduziert.

### Bekannte Einschränkungen

- Die Mehrcharakter-Oberfläche verwendet weiterhin synthetische Werte und liest ihre Fachinhalte noch nicht aus SQLite.
- EVE SSO, ESI, SDE, echte Synchronisierung und Fachberechnungen fehlen noch.
- Installer und portable EXE sind noch nicht code-signiert.
- Das manuelle Windows-Laufzeitgate und die Schutzregeln für `main` sind noch offen.

### Update und Datenbankmigration

- Schema 3 wird nach automatischer Sicherung auf Schema 4 migriert und um `expires_at` für Cache-Snapshots ergänzt.
- Bestehende Snapshots ohne bestätigten Ablaufzeitpunkt bleiben erhalten und gelten vorsichtshalber als veraltet.
- Eine frische Installation legt direkt Schema-Version 4 an.

## 0.0.3-preview.2 – 9. September 2026

### Neu hinzugefügt

- Konsistente SQLite-Sicherung vor jeder ausstehenden Migration unter `data\backups`.
- Prüfung von Integrität, Fremdschlüsseln, Schema-Version und SHA-256 vor Beginn einer Migration.
- Automatische Wiederherstellung des geprüften Ausgangsstands bei fehlgeschlagener Migration oder Abschlussprüfung.
- Schema-Version 3 mit lokaler Sicherungshistorie und Aufbewahrung der fünf neuesten Migrationssnapshots.
- Automatisierte Fehler- und Wiederherstellungstests einschließlich beschädigter Sicherungen.

### Geändert

- Der native Bereitschaftsstatus kennzeichnet die aktive Migrationssicherung.
- Sidecar-, Backend-, Portable- und Release-Dokumentation beschreiben den vollständigen Sicherungsablauf.
- Der Release-Workflow verwendet bereits vor der SHA-256-Erzeugung den endgültigen öffentlichen Installer-Dateinamen.
- Die sichtbare Versionsnummer wurde auf `v0.0.3-preview.2` aktualisiert.

### Behobene Fehler

- Eine Migration kann nicht mehr ohne vorherige erfolgreiche Sicherung beginnen.
- Nach einem Migrationsfehler bleibt kein teilweise aktualisiertes Schema als einsatzbereit zurück.
- Eine beschädigte Sicherung kann die aktuelle Datenbank nicht ersetzen.
- Der Dateiname innerhalb der Installer-Prüfsumme stimmt nun mit dem GitHub-Assetnamen überein.

### Bekannte Einschränkungen

- Die Oberfläche verwendet weiterhin synthetische Mehrcharakterdaten und liest noch nicht aus SQLite.
- EVE SSO, ESI, SDE, Synchronisierung und fachliche Berechnungen fehlen noch.
- Eine manuelle Auswahl älterer Sicherungen in der Oberfläche ist noch nicht vorhanden.
- Installer und portable EXE sind noch nicht code-signiert.
- Die portable ZIP benötigt eine vorhandene Microsoft Edge WebView2 Runtime und einen beschreibbaren Zielordner.
- Schutzregeln für `main` sind noch nicht aktiviert.

### Update und Datenbankmigration

- Eine vorhandene Schema-Version-2-Datenbank aus `v0.0.3-preview.1` wird nach automatischer Sicherung auf Schema-Version 3 aktualisiert. Es ist keine manuelle Aktion erforderlich.
- Eine frische Installation legt direkt Schema-Version 3 an und erzeugt deshalb keinen unnötigen Migrationssnapshot.
- Installer-Updates und Deinstallation lassen `data` einschließlich `data\backups` stehen. Bei einer portablen Aktualisierung die App schließen und den vollständigen Ordner `data` übernehmen.

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
