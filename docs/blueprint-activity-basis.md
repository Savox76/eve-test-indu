# Blueprint-Aktivitätsbasis

Paket 29 erweitert den rebuildbaren SDE-Bestand um die für Fertigung und Reaktionen benötigten Blueprintaktivitäten. Der aktive Stand enthält je Blueprint und Aktivität die unveränderte SDE-Basiszeit sowie sämtliche Produkt- und Materialmengen. Jede Abfrage nennt die Buildnummer, aus der diese Werte gemeinsam stammen.

## Importvertrag

`import_industry_sde` übernimmt den Paket-17-Bestand aus Gruppen, Typen und Orten zusammen mit normalisierten Blueprintaktivitäten in **einer** SQLite-Transaktion. Eine Aktivität besitzt exakt diese Felder:

```json
{
  "blueprint_type_id": 100,
  "activity": "manufacturing",
  "time_seconds": 6000,
  "products": [{"type_id": 101, "quantity": 1}],
  "materials": [{"type_id": 102, "quantity": 2850}]
}
```

Zulässig sind ausschließlich `manufacturing` und `reaction`. IDs, Zeiten und Mengen sind positive, für JSON/JavaScript verlustfrei darstellbare Ganzzahlen. Jeder Blueprint, jedes Produkt und jedes Material muss im selben importierten Typbestand vorkommen. Leere Produkt- oder Materiallisten, doppelte Aktivitäten, doppelte Typen innerhalb einer Liste, unbekannte Felder und nicht unterstützte Aktivitätsarten verwerfen das gesamte Paket.

Die Eingabestruktur ist die streng geprüfte, interne Normalform. Ein vorgeschalteter SDE-Adapter darf die offiziellen YAML- oder JSON-Lines-Dateien lesen und muss daraus nur diese beiden Aktivitätsarten übergeben. Invention, Kopieren und Forschung werden nicht stillschweigend als Fertigung behandelt.

## Atomarer Datenstand

Die Tabellen `sde_blueprint_activities`, `sde_blueprint_products` und `sde_blueprint_materials` sind abgeleitete Daten. Sie gehören wie `sde_types`, `sde_groups` und `sde_locations` nicht zum versionierten Anwendungsschema und dürfen vollständig neu aufgebaut werden.

Beim Import werden Referenzdaten, Aktivitäten, Produkte, Materialien und beide Buildmarker gemeinsam ersetzt. Erst nach allen Fremdschlüssel- und Tabellenprüfungen werden `sde_build_number` und `sde_blueprint_activity_build_number` veröffentlicht. Ein Validierungs-, Schreib- oder Constraintfehler rollt die gesamte Transaktion zurück; der letzte gültige Stand bleibt lesbar. Ein absichtlicher Minimalimport aus Paket 17 entfernt einen eventuell älteren Aktivitätsbestand samt Aktivitäts-Buildmarker, damit nie neue Referenzdaten mit alten Rezepten kombiniert werden.

## Begrenzte Abfrage

Die authentifizierte interne Route `POST /sde/blueprint-activities/query` filtert wahlweise nach höchstens 200 Blueprint-IDs, Produkt-IDs und den beiden Aktivitätsarten. Sie überträgt maximal 200 Aktivitäten pro Seite und liefert für jede Zeile:

- Blueprint-ID und lokal importierten Namen,
- Aktivitätsart und unveränderte Basiszeit in Sekunden,
- alle Produkt-IDs, Namen und Mengen,
- alle Material-IDs, Namen und Mengen,
- die gemeinsame Aktivitäts-Buildnummer auf Seitenebene.

Ohne vollständig importierten Aktivitätsstand ist `buildNumber` `null` und die Seite leer. Ein vorhandener allgemeiner SDE-Buildmarker wird nicht als Nachweis für Blueprintaktivitäten verwendet.

## Fachliche Grenze

Die Werte sind eine reproduzierbare Datenbasis, noch keine Produktionsprognose. Paket 29 wendet weder Blueprint-ME, Runs, Materialrundung, Charakter-Skills, Anlagen-/Rigboni noch Systemkosten, Steuern oder Preise an. Paket 30 verwendet diese unveränderten Werte für deterministische Produktionsschritte und Bruttomaterial, weist die weiterhin fehlenden Modifikatoren aber ausdrücklich aus.

## Quelle und Aktualisierung

Quelle ist der offizielle [EVE Static Data Export](https://developers.eveonline.com/docs/services/static-data/). Der Anbieter veröffentlicht eine aktuelle Buildnummer, buildbezogene Archive und unveränderliche Daten-URLs für automatisierte Abrufe. Der verwendete Build wird deshalb als SDE-Wert gespeichert und nicht aus einem lokalen Zeitstempel abgeleitet.
