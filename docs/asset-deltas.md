# Asset-Deltas und Jobkorrelation

Paket 21 erzeugt nach jedem vollständig abgeschlossenen Charakter-Asset-Sync einen nachvollziehbaren Vergleich zum vorherigen vollständigen Snapshot. Der erste vollständige Stand eines Charakters wird als leere Baseline festgehalten. Deltas sind abgeleitete lokale Snapshots; SQLite-Schema 6 bleibt unverändert.

## Atomare Veröffentlichung

Asset-Snapshot, Delta-Snapshot und der Status `completed` desselben `character_assets`-Laufs werden in einer gemeinsamen `BEGIN IMMEDIATE`-Transaktion veröffentlicht. Scheitert ESI-Pagination, Payload-Validierung, Delta-Bildung oder das Schreiben, wird die gesamte Transaktion zurückgerollt und der Lauf als `failed` markiert. Ein unvollständiger Lauf kann daher weder den aktuellen Bestand ersetzen noch eine scheinbare Änderung erzeugen.

Der Ressourcen-Schlüssel `asset_deltas:<character_id>` bleibt charaktergetrennt. Jeder Delta-Snapshot referenziert:

- vorherige und aktuelle Asset-Snapshot-ID,
- vorherige und aktuelle Asset-Sync-Run-ID,
- Anfang und Ende des Beobachtungsfensters,
- eine Baseline-Kennung und eine geprüfte Zusammenfassung.

## Änderungsarten

Eine stabile `item_id` wird zwischen den beiden vollständigen Ständen verglichen. Pro betroffenem Item entsteht ein Ereignis mit einer oder mehreren Arten:

- `added`: Item ist im neuen Snapshot hinzugekommen,
- `removed`: Item ist im neuen Snapshot nicht mehr vorhanden,
- `quantity`: Menge desselben Items hat sich geändert,
- `location`: Location-ID, Location-Typ oder Hangar-/Bereichs-Flag hat sich geändert.

Ein Wechsel der `type_id` bei gleicher `item_id` wird als widersprüchliche Identität abgewiesen. Unveränderte Items erzeugen kein Ereignis. Jedes Ereignis erhält einen deterministischen SHA-256-Fingerabdruck über Charakter, Snapshotpaar und alle Vorher-/Nachher-Werte. Beim Lesen wird dieser Fingerabdruck erneut geprüft; manipulierte oder beschädigte Delta-Snapshots schlagen geschlossen fehl.

## Belegbasierte Jobkorrelation

Seit Paket 24 werden persönliche Industrieaufträge separat vollständig synchronisiert. Eingehende Asset-Änderungen können beim Lesen mit ausgelieferten Jobs desselben Charakters korreliert werden. Grundlage bleiben die stabilen Delta-Belege:

- Korrelationsschlüssel aus `character_id:type_id`,
- Richtung `inbound`, `outbound` oder `neutral` aus der Mengenänderung,
- signierte Mengendifferenz,
- vorherige und neue Position,
- vollständiges Beobachtungsfenster,
- Quell-Sync-Run und beide Snapshot-IDs,
- unveränderten deterministischen Ereignisfingerabdruck.

Produkt-Type-ID und Jobabschluss müssen zum Typ und Beobachtungsfenster des Deltas passen; eine exakte Ausgabelocation wird bevorzugt. Ein eindeutiger Kandidat wird mit Job-ID als `linked` angezeigt, mehrere plausible Jobs als `ambiguous`. Fehlende Jobdaten bleiben `unavailable`, nicht passende Änderungen `unmatched` oder `not-applicable`. Die Ableitung verändert weder gespeicherte Deltas noch deren Fingerabdrücke.

## Sichtbare Historie und Grenzen

Die DE/EN-Asset-Oberfläche zeigt Summen sowie Typ, Besitzer, Änderungsarten, Menge vorher/nachher, Standort vorher/nachher, Zeitfenster, Jobzuordnung und Quellnachweis. Suche, Besitzerfilter und Änderungsartfilter laufen im Sidecar. Die Desktop-Brücke akzeptiert höchstens 200 Ereignisse pro Anfrage; die Oberfläche verwendet 50 Ereignisse pro Seite und rendert nur dieses Fenster.

Die Zustände Desktop-Kern nicht verfügbar, kein Baseline-Nachweis, keine Treffer, Laden und Lesefehler werden getrennt dargestellt. Typname und Alias dienen der aktuellen Anzeige; Type-ID, Character-ID, Item-ID und Fingerabdruck bleiben die stabilen historischen Identitäten.

Ein synthetischer Regressionstest erzeugt 10.000 Mengenänderungen und stellt sicher, dass Abfrage und Desktop-Transport trotzdem nur das angeforderte 50-Ereignis-Fenster zurückgeben.
