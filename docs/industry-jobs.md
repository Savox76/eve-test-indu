# Persönliche Industrieaufträge und Korrelation

Paket 24 synchronisiert für jeden aktivierten Charakter den ESI-Endpunkt `/characters/{character_id}/industry/jobs/` mit `include_completed=true`. Der Scope `esi-industry.read_character_jobs.v1` gehört bereits zum automatisch angeforderten Paket `industry-core`.

Jeder Charakter erhält einen eigenen `character_industry_jobs`-Lauf. Erst ein vollständig abgerufener und streng geprüfter Datensatz veröffentlicht den Snapshot `character_industry_jobs:<character_id>`. Fehler, widersprüchliche Felder und doppelte Job-IDs markieren den Lauf als fehlgeschlagen und lassen den letzten vollständigen Snapshot unverändert. Der Programmstart und eine erfolgreiche Charakteranmeldung aktualisieren zuerst Assets und Blueprints und anschließend die Jobs; manuelle Folgeläufe bleiben möglich.

## Sichtbare Jobdaten

Die zweisprachige Ansicht unter **Blueprints & Jobs** zeigt:

- Blueprint und Produkt mit lokal aufgelöstem Typnamen,
- Charakter, Aktivität und ESI-Status,
- Läufe, erfolgreiche Läufe und Kosten,
- Start, geplantes Ende und Abschluss,
- Anlage, Ausgabelocation und Datenalter; seit Paket 26 außerdem den belegten Anlagen-/Systemnamen und den zur Aktivität passenden Systemkostenindex,
- die getrennten Blueprint-, Asset- und Quellnachweise.

Suche, Besitzer-, Status-, Aktivitäts- und Korrelationsfilter sowie die Sortierung werden vor der Seitenteilung im lokalen Sidecar angewendet. Pro Anfrage werden höchstens 200 und in der Oberfläche standardmäßig 100 Jobs übertragen. Die angezeigte Aktiv-Zahl bezieht sich auf das gesamte gefilterte Ergebnis, nicht nur auf die sichtbare Seite.

## Korrelation statt unbelegter Kausalität

Die Anwendung unterscheidet die Belege ausdrücklich:

- `current` oder `historical`: Die exakte Blueprint-Item-ID wurde im aktuellen oder in einem älteren vollständigen Blueprint-Snapshot desselben Charakters gefunden.
- `linked`: Genau eine passende eingehende Asset-Änderung wurde gefunden. Produkt-Type-ID und Abschlusszeit liegen im Beobachtungsfenster; ein exakter Treffer der Ausgabelocation wird bevorzugt.
- `ambiguous`: Mehrere Asset-Änderungen bleiben plausible Kandidaten und werden nicht willkürlich auf einen Treffer reduziert.
- `unmatched`: Daten liegen vor, reichen aber für keine Zuordnung aus.
- `unavailable`: Der erforderliche vollständige Quellnachweis fehlt.
- `pending`: Der Job ist aktiv, pausiert oder bereit und daher noch nicht abschließend korrelierbar.
- `not-applicable`: Der Jobstatus oder die vorhandenen Jobfelder erlauben keine Produkt-Asset-Zuordnung.

Die Asset-Historie zeigt dieselbe Zuordnung in Gegenrichtung und nennt die passende Job-ID. Die gespeicherten Delta-Fingerabdrücke und Quellwerte werden dadurch nicht verändert; die Korrelation wird beim Lesen aus den geprüften Snapshots abgeleitet. Eine Übereinstimmung ist ein nachvollziehbarer technischer Beleg, aber kein stärkerer Kausalitätsnachweis als die von ESI gelieferten IDs, Zeiten und Orte erlauben.

ESI bestimmt, welche abgeschlossenen persönlichen Jobs noch zurückgegeben werden. Deshalb ist die lokale Historie ab dem ersten erfolgreichen Lauf vollständig für die jeweils erhaltenen Antworten, kann aber keine bereits vor der ersten Synchronisierung von ESI entfernten Jobs rekonstruieren.

Die in Jobzeilen ergänzten Anlagenwerte stammen ausschließlich aus dem letzten vollständigen [Anlagen-Snapshot](industry-facilities.md). Fehlt dieser Beleg oder ist eine Spielerstruktur nicht auflösbar, bleiben Name und Kostenindex unbekannt; die Jobdaten selbst werden nicht verworfen und es wird kein Wert geschätzt.
