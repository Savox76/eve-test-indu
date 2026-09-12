# Blueprint-Bestand

Paket 23 synchronisiert für jeden aktivierten Charakter den ESI-Endpunkt `/characters/{character_id}/blueprints/` vollständig paginiert. Der dafür benötigte Scope `esi-characters.read_blueprints.v1` gehört zum automatisch angeforderten Paket `industry-core`. Das ist der persönliche Charakterbestand; Corporation-Blueprints gehören nicht zu diesem ESI-Endpunkt und werden derzeit nicht angezeigt.

Jeder Lauf besitzt einen eigenen `sync_runs`-Nachweis. Erst nach erfolgreichem Abruf und strenger Prüfung aller Seiten wird ein vollständiger Snapshot `character_blueprints:<character_id>` veröffentlicht. Die ESI-Mengenwerte `-1` für ein einzelnes Original, `-2` für eine Kopie und positive Werte für einen Blueprint-Stapel werden ausdrücklich akzeptiert; positive Stapel werden als Originalbestand dargestellt. Null, Werte kleiner als `-2`, ungültige Datensätze und doppelte Item-IDs markieren den Lauf als fehlgeschlagen und lassen den letzten vollständigen Snapshot unverändert.

Die zweisprachige Oberfläche gruppiert den Bestand standardmäßig nach Blueprint-Typ und zeigt Anzahl, BPO-/BPC-Verteilung, ME-/TE-Spanne sowie Besitzer- und Ortsanzahl. Ein Klick auf den Blueprint-Namen öffnet die dazugehörigen Einzelpositionen mit:

- echten Blueprint-Namen mit Type-ID,
- Besitzer,
- Original (BPO) oder Kopie (BPC),
- Material- und Zeiteffizienz,
- verbleibende Läufe,
- Inventarbereich, Location-ID und Datenalter.

Suche, Besitzer- und BPO/BPC-Filter sowie die Sortierung werden vor der Seitenteilung im lokalen Sidecar angewendet. Einzelne Anfragen übertragen höchstens 200 Datensätze; die Gruppenansicht liest die begrenzten Seiten vollständig ein und rendert nur eine Zeile je Typ. Der Hintergrundlauf startet zusammen mit dem Asset-Abgleich beim Programmstart und nach erfolgreicher Charakteranmeldung; eine manuelle Aktualisierung bleibt verfügbar.

Oberhalb der Tabelle zeigt die App für jeden aktivierten Charakter einen eigenen Snapshot-Status. **Verfügbar** nennt Blueprint-Anzahl und Datenalter – auch ein erfolgreicher leerer Snapshot ist dadurch von einem Fehler unterscheidbar. **Kein Snapshot** fordert zur Aktualisierung und bei einem Berechtigungsfehler zur erneuten Anmeldung auf. Das Suchfeld bleibt unabhängig davon immer sichtbar und sucht Blueprintname, Besitzer, Ort sowie IDs.
