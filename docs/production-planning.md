# Produktionsplanung

Paket 30 ergänzt lokale, updatefeste Fertigungs- und Reaktionsziele. Paket 31 gleicht deren äußeren Materialbedarf mit vollständigen persönlichen Asset-Snapshots ab. Die Planung verwendet ausschließlich die vollständig importierte Blueprint-Aktivitätsbasis aus Paket 29, verändert keine Daten in EVE und startet keine Industrieaufträge.

## Persistentes Ziel

Ein Ziel enthält:

- den ausführenden Charakter,
- das exakte Blueprint-/Aktivitäts-/Produkt-Rezept,
- eine positive Zielmenge,
- eine Priorität von 0 bis 999,
- eine optionale Notiz bis 240 Zeichen.

Die Tabelle `production_plans` gehört ab Schema 9 zum Anwendungskern. Beim vollständigen Löschen des Charakters werden dessen Ziele über den Fremdschlüssel mitgelöscht. Ein späterer SDE-Neuaufbau löscht die Ziele dagegen nicht: fehlt danach der Aktivitätsstand oder das gespeicherte Rezept, bleibt das Ziel mit einem ausdrücklichen Fehlerzustand sichtbar.

## Deterministische Auflösung

Die Wurzel verwendet immer das vom Nutzer gewählte exakte Rezept. Für ein produzierbares Zwischenprodukt gilt die stabile Auswahlregel:

1. Fertigung vor Reaktion,
2. danach die kleinste Blueprint-Typ-ID.

Existieren Alternativen, zeigt die Oberfläche Anzahl und ausgewähltes Blueprint. Gemeinsamer Bedarf mehrerer Elternschritte wird zuerst zusammengeführt. Erst danach werden die benötigten Läufe mit ganzzahligem Aufrunden berechnet. Dadurch wird ein gemeinsames Zwischenprodukt nicht pro Elternzweig separat überrundet.

Jeder Schritt nennt Rezept, Aktivität, benötigte Menge, Ausgabemenge je Lauf, Läufe, produzierte Menge, Überschuss, unveränderte SDE-Basiszeit und direkte Materialien. Die sichtbare Herstellungsreihenfolge beginnt bei den tiefsten Vorprodukten und endet bewusst mit dem ausgewählten Zielprodukt. Backend und Frontend prüfen deshalb den letzten Schritt als gewähltes Wurzelziel. Das Ziel wird zusätzlich hervorgehoben; die Nummern sind damit als ausführbare Reihenfolge und nicht als Abhängigkeitsbaum zu lesen. Alle Mengen und Zeiten bleiben innerhalb der verlustfrei in JavaScript darstellbaren Ganzzahlgrenze; Überläufe werden abgewiesen.

## Bruttomaterial und Zustände

`grossMaterials` enthält nur die äußeren Materialien, für die innerhalb der ausgewählten Kette kein Rezept verwendet wird. Zwischenprodukte erscheinen stattdessen als eigene Schritte.

## Bestandsabgleich und Fehlmengen

Für jedes äußere Material gilt `fehlend = max(0, Bruttobedarf - verfügbar)`. Als verfügbar zählt ausschließlich der letzte vollständig abgeschlossene Asset-Snapshot des im Ziel gewählten ausführenden Charakters. Ein fehlgeschlagener, abgebrochener oder noch laufender neuerer Sync ersetzt diesen Stand nicht. Fehlt ein vollständiger Snapshot, bleiben verfügbar und fehlend unbekannt; die Oberfläche zeigt ausdrücklich `Asset-Snapshot fehlt` statt eine erfundene Fehlmenge von null oder der gesamten Bedarfsmenge.

Angerechnete Bestände werden nach Standortpfad und EVE-Bereich zusammengefasst. Jede Gruppe nennt Charakter, Quellstandort, Standortstatus, Bereich, Menge, Positionszahl sowie Asset-Snapshot-, Sync-Lauf- und Beobachtungszeitpunkt. Höchstens 50 Standortgruppen je Material und Kategorie werden übertragen; Gesamtmenge, Positions- und Gruppenzahl bleiben auch bei einer gekürzten Detailansicht vollständig. Fehlt der exakt zum Asset-Snapshot gehörende Standort-Snapshot, bleibt die Menge anrechenbar und ihr Standortstatus nachvollziehbar `pending`.

Passende Bestände anderer aktivierter Charaktere werden nicht stillschweigend zusammengelegt. Sie erscheinen getrennt als bewusst nicht angerechneter Bestand mit denselben Quellenangaben. Dadurch bleibt sichtbar, wo Material vorhanden wäre, ohne die technische und fachliche Charaktertrennung aufzuheben.

| Bestandszustand | Bedeutung |
| --- | --- |
| `covered` | Der bekannte Bestand des ausführenden Charakters deckt den Bruttobedarf vollständig. |
| `shortage` | Ein vollständiger Snapshot liegt vor und mindestens eine echte Fehlmenge ist größer als null. |
| `snapshot-missing` | Für den ausführenden Charakter fehlt ein vollständiger Asset-Snapshot; eine Fehlmenge ist nicht belastbar. |
| `not-applicable` | Die Rezeptkette selbst ist nicht auflösbar, daher wird kein Bestand angerechnet. |

| Zustand | Bedeutung |
| --- | --- |
| `ready` | Rezeptkette ist vollständig und deterministisch aufgelöst. |
| `sde-unavailable` | Keine vollständige Blueprint-Aktivitätsbasis ist veröffentlicht. |
| `recipe-missing` | Das gespeicherte Wurzelrezept existiert im aktuellen SDE-Stand nicht mehr. |
| `cycle` | Die ausgewählte Rezeptkette enthält einen Zyklus. |
| `complexity-limit` | Mehr als 500 Produktionsschritte wären erforderlich. |

Neue Ziele mit Zyklus oder überschrittener Komplexitätsgrenze werden nicht gespeichert. Bereits gespeicherte Ziele bleiben bei einer später veränderten SDE-Basis mit dem entsprechenden Zustand sichtbar.

## Bewusste Berechnungsgrenze

Paket 31 berechnet Bruttobedarf, SDE-Basiszeit, verfügbaren persönlichen Bestand und echte Fehlmengen. Noch nicht einbezogen werden:

- Reservierungen zwischen mehreren Zielen,
- Blueprint-ME und konkrete Blueprint-Kopien,
- Charakter-Skills,
- Anlagen-, Service- und Rigboni,
- Systemkosten, Steuern und Preise.

Die API bestätigt den aktiven Bestandsvertrag mit `inventoryApplied: true` und die verbleibende Modifikatorgrenze mit `modifiersApplied: false`. Solange Reservierungen fehlen, kann derselbe bekannte Bestand mehrere Ziele jeweils einzeln decken; die Summen sind deshalb noch keine konfliktfreie gemeinsame Einkaufsliste. SDE-Basiszeiten dürfen weiterhin nicht als reale Fertigstellungszeit oder Kostenprognose verstanden werden.

## Arbeitsvorrat und Bedienung

Die Produktionsplanung befindet sich unter **Produktion & Reaktionen**. Die Auswahl des ausführenden Charakters stammt direkt aus der Liste aktivierter Charaktere und hängt weder von vorhandenen Zielen noch von einer erfolgreichen Zielabfrage ab. Produkt- und Ziellisten unterstützen Suche, Aktivitäts-, Besitzer- und Statusfilter, Sortierung und begrenzte Seiten. Ein Ziel kann angelegt, geändert und bewusst entfernt werden.

Die Industrie-Slotübersicht zählt ein auflösbares Ziel als **laufend**, wenn derselbe Charakter einen aktiven, pausierten oder abholbereiten Job mit passender Aktivität und Blueprint-Typ-ID besitzt. Sonst ist es **geplant**. Nicht auflösbare Ziele sind **blockiert**. Ein Fertigzustand wird nicht aus Bestand oder Jobhistorie erfunden und bleibt daher null.

Die authentifizierten internen Routen `/production-plans/catalog`, `/production-plans/query`, `/production-plans/save` und `/production-plans/delete` besitzen strikte, begrenzte Verträge. Sidecar, Tauri und Frontend validieren ihre Antworten unabhängig voneinander.

## Quelle

Rezepte, Mengen und Basiszeiten stammen aus dem offiziellen [EVE Static Data Export](https://developers.eveonline.com/docs/services/static-data/). Jede aufgelöste Planung nennt die gemeinsam verwendete SDE-Buildnummer.

Die Windows-Ausgaben ab `v0.0.5-preview.14` liefern den geprüften Produktionsausschnitt des festgelegten offiziellen SDE-Builds mit. Er wird beim ersten Start automatisch installiert. Bei identischer Buildnummer wird er nur dann erneut verarbeitet, wenn eine neue abgeleitete Spalte – beispielsweise der Sicherheitsstatus ab `.18` – noch nicht befüllt ist. Die Produkt- und Blueprintsuche benötigt deshalb keinen manuellen Vorbereitungsschritt.
