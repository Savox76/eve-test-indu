# Industrieanlagen und Systemkosten

Paket 26 synchronisiert die Anlagenbasis, die der spätere Produktionssolver für eine belegbare Anlagenwahl und getrennte Kostenkomponenten benötigt. Maßgeblich sind die aktuelle offizielle [ESI-Spezifikation im API Explorer](https://developers.eveonline.com/api-explorer) und die fest gesetzte Compatibility-Date des zentralen Clients.

## Quellen und vollständiger Snapshot

Ein globaler `industry_facilities`-Lauf liest zunächst vollständig:

- `/industry/facilities/` für den öffentlichen NPC-Anlagenkatalog,
- `/industry/systems/` für die aktivitätsspezifischen Systemkostenindizes,
- `/universe/names/` in Paketen von höchstens 1.000 IDs für Stationen, Systeme, Regionen, Eigentümer und Anlagentypen.

Anschließend werden Anlagen-IDs aus den letzten vollständigen persönlichen Job-Snapshots ergänzt. Spielerstrukturen werden nur dann über `/universe/structures/{structure_id}/` aufgelöst, wenn mindestens einer der beobachtenden Charaktere den Scope `esi-universe.read_structures.v1` besitzt. Ein fehlender Scope, ein ACL-bedingtes `403` oder ein `404` bleiben als eigene Fachzustände sichtbar und brechen den öffentlichen Katalog nicht ab.

Erst wenn beide öffentlichen Listen, alle erwarteten Namen und sämtliche beobachteten Strukturzustände streng geprüft sind, veröffentlicht eine Transaktion den Snapshot `industry_facilities`. Ein fehlgeschlagener Folgelauf markiert nur seinen Sync-Lauf als fehlgeschlagen und lässt den letzten vollständigen Anlagenstand unverändert.

Da dieser globale Snapshot Namen von Spielerstrukturen enthalten kann, die nur über persönliche Jobs entdeckt wurden, wird er beim vollständigen Löschen eines Charakters vorsorglich mit entfernt. Der nächste Anlagenabgleich baut den öffentlichen und für die verbleibenden Charaktere noch belegbaren Stand neu auf.

## Sichtbare Daten

Die zweisprachige Ansicht unter **Blueprints & Jobs** zeigt:

- Anlagenname, ID, NPC-Station oder beobachtete Spielerstruktur,
- Anlagentyp, Eigentümer, Sonnensystem und – sofern öffentlich bekannt – Region,
- den ausgewählten Systemkostenindex für Produktion, Reaktion, Kopieren, Erfindung sowie ME-/TE-Forschung,
- öffentliche, verfügbare, ACL-eingeschränkte, scope-bedingt eingeschränkte und unbekannte Zustände,
- Anzahl der persönlichen Jobs und der darunter aktiven Jobs,
- Snapshot-ID, Sync-Run-ID und Datenalter.

Suche, Anlagenart, Zugriffszustand, Kostenaktivität, der Filter **Nur in Jobs verwendet** und die Sortierung werden vor der Seitenteilung im lokalen Sidecar angewendet. Pro Anfrage werden höchstens 200 und in der Oberfläche standardmäßig 100 Anlagen übertragen. Die persönlichen Jobzeilen verwenden denselben Snapshot für Anlagenname, System und passenden Kostenindex.

## Bewusste Kostengrenze

Der Systemkostenindex ist nur eine einzelne belegte Eingabe für spätere Jobkosten und kein fertiger Baupreis. Der öffentliche Anlagenendpunkt liefert derzeit keine verlässliche Anlagensteuer für die zurückgegebenen Stationen; die Strukturroute liefert weder Service-Modul- noch Rigboni. Paket 26 speichert und zeigt solche Werte deshalb als unbekannt, statt sie zu erraten oder aus Community-Diensten zu übernehmen.

Manuell gepflegte Strukturprofile, aktivitätsspezifische Zuschläge und die eigentliche Decimal-basierte Kostenformel werden erst dann ergänzt, wenn ihr Eingabemodell und ihre Golden-Fälle gemeinsam feststehen. Dadurch bleiben Systemkostenindex, Anlagensteuer, Strukturbonus und Rigbonus später getrennt nachvollziehbar.

## Aktualisierungsreihenfolge

Beim Programmstart und nach einer erfolgreichen Charakteranmeldung werden Assets, Blueprints und Skills zuerst parallel aktualisiert. Danach folgen die persönlichen Jobs und zuletzt der Anlagen-Snapshot, damit neu beobachtete Spielerstrukturen im selben Gesamtlauf aufgelöst werden können. Manuelle Folgeläufe bleiben in der Job- und Anlagenansicht getrennt möglich.
