# Blueprint-Bestand

Paket 23 synchronisiert für jeden aktivierten Charakter den ESI-Endpunkt `/characters/{character_id}/blueprints/` vollständig paginiert. Der dafür benötigte Scope `esi-characters.read_blueprints.v1` gehört zum automatisch angeforderten Paket `industry-core`.

Jeder Lauf besitzt einen eigenen `sync_runs`-Nachweis. Erst nach erfolgreichem Abruf und strenger Prüfung aller Seiten wird ein vollständiger Snapshot `character_blueprints:<character_id>` veröffentlicht. Fehler, ungültige Datensätze und doppelte Item-IDs markieren den Lauf als fehlgeschlagen und lassen den letzten vollständigen Snapshot unverändert.

Die zweisprachige Oberfläche zeigt:

- echten Blueprint-Namen mit Type-ID,
- Besitzer,
- Original (BPO) oder Kopie (BPC),
- Material- und Zeiteffizienz,
- verbleibende Läufe,
- Inventarbereich, Location-ID und Datenalter.

Suche, Besitzer- und BPO/BPC-Filter sowie die Sortierung werden vor der Seitenteilung im lokalen Sidecar angewendet. Pro Anfrage werden höchstens 200, in der Oberfläche standardmäßig 100 Datensätze übertragen. Der Hintergrundlauf startet zusammen mit dem Asset-Abgleich beim Programmstart und nach erfolgreicher Charakteranmeldung; eine manuelle Aktualisierung bleibt verfügbar.

