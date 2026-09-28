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
- den offiziellen SDE-Sicherheitsstatus des belegten Sonnensystems und seine Einordnung als Highsec (ab 0,45), Lowsec (über 0 bis unter 0,45) oder Nullsec (bis 0); ohne belegtes System bleibt der Zustand unbekannt,
- den ausgewählten Systemkostenindex für Produktion, Reaktion, Kopieren, Erfindung sowie ME-/TE-Forschung,
- öffentliche, verfügbare, ACL-eingeschränkte, scope-bedingt eingeschränkte und unbekannte Zustände,
- Anzahl der persönlichen Jobs und der darunter aktiven Jobs,
- bei öffentlichen NPC-Stationen die offizielle feste Anlagensteuer von 0,25 Prozent; bei Spielerstrukturen bleibt der vom Eigentümer gesetzte Satz unbekannt,
- Snapshot-ID, Sync-Run-ID und Datenalter.

Suche, Anlagenart, Zugriffszustand, Sicherheitsraum, Kostenaktivität, der Filter **Nur in Jobs verwendet** und die Sortierung werden vor der Seitenteilung im lokalen Sidecar angewendet. Der Sicherheitsraum kann auf Highsec, Lowsec, Nullsec oder unbekannt begrenzt werden. Pro Anfrage werden höchstens 200 und in der Oberfläche standardmäßig 100 Anlagen übertragen. Die persönlichen Jobzeilen verwenden denselben Snapshot für Anlagenname, System und passenden Kostenindex.

Der Sicherheitsstatus wird aus dem mitgelieferten offiziellen SDE-Ausschnitt gelesen. Bei einem Update wird die abgeleitete SDE-Tabelle atomar um die neue Spalte ergänzt und bei gleicher Buildnummer genau einmal neu befüllt; Charaktere, Einstellungen, Pläne und Snapshots in `foundry.sqlite3` werden dabei nicht ersetzt.

Seit Paket 37 verwendet die Produktionsplanung denselben letzten vollständigen Anlagen-Snapshot als schrittgenauen Beleg. Ein passender persönlicher Industriejob liefert die Anlagen-ID; angezeigt werden der aufgelöste Zugriffszustand, das System, der Sicherheitsraum, der aktivitätsspezifische Systemkostenindex und die Quellen-IDs. Diese Verknüpfung belegt eine persönlich verwendete Anlage, wählt aber keine künftige Anlage automatisch aus und wendet keinen Anlagenmodifikator an.

## Bewusste Kostengrenze

Der Systemkostenindex ist nur eine einzelne belegte Eingabe für spätere Jobkosten und kein fertiger Baupreis. Der öffentliche Anlagenendpunkt liefert derzeit kein Steuerfeld. Paket 51 ergänzt deshalb ausschließlich für eindeutig öffentliche NPC-Stationen den von CCP offiziell festgelegten Satz von 0,25 Prozent. Die Strukturroute liefert weder die vom Eigentümer gesetzte Steuer noch Service-Modul- oder Rigboni; diese Werte werden weiterhin nicht geschätzt oder aus Community-Diensten übernommen.

Die Eigentümersteuer einer Spielerstruktur und deren Material-/Zeitprofil bleiben ausdrückliche Eingaben. Dadurch bleiben Systemkostenindex, NPC-Anlagensteuer, Struktursteuer, Strukturbonus und Rigbonus getrennt nachvollziehbar.

## Aktualisierungsreihenfolge

Beim Programmstart und nach einer erfolgreichen Charakteranmeldung werden Assets, Blueprints und Skills zuerst parallel aktualisiert. Danach folgen die persönlichen Jobs und zuletzt der Anlagen-Snapshot, damit neu beobachtete Spielerstrukturen im selben Gesamtlauf aufgelöst werden können. Manuelle Folgeläufe bleiben in der Job- und Anlagenansicht getrennt möglich.
