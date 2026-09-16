# Produktionsplanung

Paket 30 ergänzt lokale, updatefeste Fertigungs- und Reaktionsziele. Paket 31 gleicht deren äußeren Materialbedarf mit vollständigen persönlichen Asset-Snapshots ab. Paket 32 reserviert denselben Bestand konfliktfrei zwischen allen Zielen eines Charakters. Paket 33 ordnet einem Ziel optional ein konkretes persönliches Blueprint-Item zu und wendet dessen belegten ME-Wert auf den Wurzel-Fertigungsschritt an. Paket 34 bezieht zusätzlich dessen belegten TE-Wert in die Blueprint-Zeit des Zielschritts ein. Paket 35 wendet die aktuell wirksamen Industrie- und Reaktions-Skills des ausführenden Charakters auf jeden passenden Schritt an. Paket 36 erweitert die persönliche Blueprintzuordnung und ihre ME-/TE-Wirkung auf jeden Fertigungsschritt der Kette. Paket 37 verbindet jeden Schritt mit einem belegten persönlichen Job und dessen Anlagenstand. Paket 38 lässt vorhandene Vorprodukte die Kette verkürzen und bindet Bestand sowie Reservierungen wahlweise an eine Produktionsstation und ein Materiallager. Die Planung verwendet ausschließlich vollständige, belegte Snapshots, verändert keine Daten in EVE und startet keine Industrieaufträge.

## Persistentes Ziel

Ein Ziel enthält:

- den ausführenden Charakter,
- das exakte Blueprint-/Aktivitäts-/Produkt-Rezept,
- optional die Item-ID eines persönlichen BPO oder BPC für das Zielrezept,
- optional je Fertigungs-Vorproduktschritt die Item-ID eines persönlichen BPO oder BPC,
- optional eine Produktionsstation oder Struktur und darin ein direktes Hangarlager oder einen Container,
- je produzierbarem Vorprodukt die Versorgung aus Bestand, Fertigung oder einer Kombination daraus,
- eine positive Zielmenge,
- eine Priorität von 0 bis 999,
- eine optionale Notiz bis 240 Zeichen.

Die Tabelle `production_plans` gehört ab Schema 9 zum Anwendungskern. Schema 10 ergänzt die optionale `blueprint_item_id` des Zielrezepts. Schema 11 ergänzt `production_plan_step_blueprints` für die expliziten Zuordnungen der Fertigungs-Vorproduktschritte. Schema 12 ergänzt die optionale Anlage und das Materiallager sowie `production_plan_step_supply_modes` für die Versorgungswahl. Eine konkrete physische Blueprint-Item-ID darf innerhalb eines Ziels und zielübergreifend höchstens einmal zugeordnet sein. Beim Löschen eines Ziels oder vollständigen Löschen des Charakters werden die Schrittzuordnungen und Versorgungsmodi über Fremdschlüssel mitgelöscht. Ein späterer SDE-Neuaufbau löscht die Ziele dagegen nicht: fehlt danach der Aktivitätsstand oder das gespeicherte Rezept, bleibt das Ziel mit einem ausdrücklichen Fehlerzustand sichtbar.

## Versorgungsmodi und Produktionsort

Das Zielprodukt wird immer gebaut. Für jedes produzierbare Vorprodukt stehen drei explizite Modi zur Verfügung:

| Modus | Wirkung |
| --- | --- |
| `stock-first` | Der konfliktfrei freie Bestand wird zuerst eingesetzt; nur die ungedeckte Restmenge wird gebaut. Ist alles vorhanden, entfällt der Schritt samt Blueprintbedarf. |
| `stock-only` | Das Vorprodukt wird ausschließlich als vorhandenes Material behandelt. Es wird kein Produktionsschritt und kein Blueprint benötigt; nicht vorhandene Einheiten bleiben als Fehlmenge sichtbar. |
| `build` | Vorhandener Bestand dieses Vorprodukts wird ignoriert und die vollständige benötigte Menge gebaut. |

`supplyDecisions` nennt je Vorprodukt benötigte, verfügbare, verwendete, zu bauende und fehlende Menge sowie die daraus folgende Blueprintpflicht. Die stabile Regel lautet `stock-first-before-recursive-build`: Bestand wird vor der rekursiven Auflösung der untergeordneten Materialien abgezogen. So verkürzen vorhandene T1-Gegenstände und andere Zwischenprodukte tatsächlich die Fertigungskette, statt nur am Ende als Rohmaterialbestand aufzutauchen.

Anlagen- und Lageroptionen werden ausschließlich aus dem zum letzten vollständigen Asset-Snapshot gehörenden, root-first aufgelösten Standortstand des ausführenden Charakters gebildet. Eine Anlage kann als gesamter Standort, als direkter Stations-/Strukturhangar oder über einen echten Lagercontainer gewählt werden. Der in EVE vergebene Containername steht in der Auswahl zuerst; die Item-ID macht gleichnamige Container eindeutig. Bei einem Container zählen auch dessen aufgelöste Untercontainer. Schiffe, Schiffsladeräume und Container innerhalb eines Schiffes werden weder als Materiallager angeboten noch bei einer gewählten Station als produktionsverfügbarer Bestand angerechnet. Dieselbe Auswahl begrenzt sowohl den angezeigten Bestand als auch die zielübergreifende Reservierungsbuchung; Bestand außerhalb der Auswahl bleibt als ausgeschlossen belegt. Ohne Anlagenwahl bleibt aus Kompatibilitätsgründen der gesamte persönliche Bestand des Charakters die Quelle.

Die gespeicherte Wahl bleibt auch sichtbar, wenn ein späterer Snapshot die Anlage oder den Container nicht mehr auflösen kann. `facility-missing` und `material-location-missing` verhindern eine stillschweigende Umdeutung. Beim Speichern einer neuen Auswahl muss sie im aktuellen vollständigen Standortstand vorhanden sein.

## Persönliche Blueprintzuordnung, ME und TE

Die Kandidaten stammen ausschließlich aus dem letzten vollständig abgeschlossenen persönlichen Blueprint-Snapshot des ausführenden Charakters und müssen exakt zum Blueprint-Typ des jeweiligen Rezepts passen. BPOs sind stets laufgeeignet; ein BPC ist nur geeignet, wenn seine verbleibenden Läufe mindestens die für diesen Schritt benötigten Läufe decken. Geeignete und ungeeignete Kandidaten bleiben je Schritt mit Item-ID, BPO/BPC, ME, TE, Läufen, Standort sowie Snapshot-, Lauf- und Zeitbeleg sichtbar. Eine verschwundene, typfalsche oder nach einer Mengenänderung nicht mehr laufgeeignete gespeicherte Zuordnung wird nicht stillschweigend ersetzt. Beim Speichern wird die vollständige Liste atomar ersetzt und gegen die aktuell aufgelöste Kette geprüft.

Für jedes direkte Material eines zugewiesenen Fertigungsschritts gilt mit ganzzahlig exakter Rechnung:

$$q_{ME}=\max\left(r,\left\lceil\frac{q_{Basis}\cdot r\cdot(100-ME)}{100}\right\rceil\right)$$

Dabei ist $r$ die Laufzahl des konkreten Schritts und $q_{Basis}$ die SDE-Materialmenge je Lauf. Die Untergrenze von einer Einheit je Material und Lauf wird damit vor einer unzulässigen Abrundung geschützt. Diese Einzelmaterialrundung erfolgt vor der erneuten Auflösung veränderter Zwischenproduktmengen. Unmodifizierter Bedarf, wirksamer Bedarf und Ersparnis werden parallel ausgegeben. ME wird weder auf Reaktionen noch auf einen anderen Schritt übertragen; ohne explizite Zuordnung bleibt der jeweilige Schritt bei ME 0.

Für die Blueprint-Zeit jedes zugewiesenen Fertigungsschritts gilt:

$$t_{TE}=\max\left(1,\left\lceil\frac{t_{Basis}\cdot r\cdot(100-TE)}{100}\right\rceil\right)$$

$t_{Basis}$ ist die unveränderte SDE-Zeit je Lauf. Die TE-Berechnung wird einmal auf den vollständigen Job des konkreten Schritts angewendet und auf eine volle Sekunde aufgerundet. Jeder Schritt nennt unveränderte SDE-Basiszeit, Blueprint-Zeit und Ersparnis. Nicht zugewiesene Schritte bleiben bei TE 0; Reaktionen erhalten weiterhin keinen Blueprint-TE-Modifikator.

## Persönliche Charakter-Skillzeit

Paket 35 liest ausschließlich den letzten vollständig abgeschlossenen Skill-Snapshot des ausführenden Charakters. Ein neuerer fehlgeschlagener oder unvollständiger Lauf ersetzt ihn nicht. Verwendet wird das von ESI gemeldete **aktive** Level; dadurch werden zeitweise begrenzte Skillstufen nicht mit dem bloß trainierten Level verwechselt. Ein in einem vollständigen Snapshot fehlender Skill gilt als aktive Stufe 0. Fehlt der vollständige Snapshot selbst, bleibt die persönliche Zeit `null` und die Oberfläche zeigt `Skill-Snapshot fehlt`, statt Stufe 0 zu erfinden.

Für einen Fertigungsschritt gilt jobweit:

$$t_{Char}=\max\left(1,\left\lceil t_{Basis}\cdot r\cdot\frac{100-TE}{100}\cdot\frac{100-4I}{100}\cdot\frac{100-3A}{100}\right\rceil\right)$$

$I$ ist das aktive Level von **Industry** (Type 3380), $A$ das aktive Level von **Advanced Industry** (Type 3388). Für eine Reaktion gilt ohne Blueprint-TE:

$$t_{Char}=\max\left(1,\left\lceil t_{Basis}\cdot r\cdot\frac{100-4R}{100}\right\rceil\right)$$

$R$ ist das aktive Level von **Reactions** (Type 45746). Die Faktoren werden multiplikativ auf die ungerundete vollständige Jobzeit angewendet und erst am Ende auf volle Sekunden aufgerundet. Dadurch entsteht kein zusätzlicher Rundungsfehler durch eine vorzeitig gerundete Blueprint-Zeit. Jeder Schritt nennt die wirksamen Skill-IDs, Namen, aktiven Level und Prozentwerte sowie Blueprint-Zeit, persönliche Skillzeit und Skill-Ersparnis. Snapshot-ID, Sync-Lauf und Beobachtungszeit belegen die verwendete Charakterquelle.

| Zuordnungszustand | Bedeutung |
| --- | --- |
| `ready` | Das zugewiesene Item ist vorhanden, typgerecht und laufgeeignet. |
| `unassigned` | Es ist bewusst kein Blueprint-Item zugeordnet. |
| `snapshot-missing` | Ein vollständiger persönlicher Blueprint-Snapshot fehlt. |
| `missing` | Die gespeicherte Item-ID fehlt im aktuellen vollständigen Snapshot. |
| `type-mismatch` | Das Item existiert, gehört aber nicht zum Zielrezept. |
| `runs-insufficient` | Ein zugeordnetes BPC besitzt zu wenige verbleibende Läufe. |

## Deterministische Auflösung

Die Wurzel verwendet immer das vom Nutzer gewählte exakte Rezept. Für ein produzierbares Zwischenprodukt gilt die stabile Auswahlregel:

1. Fertigung vor Reaktion,
2. danach die kleinste Blueprint-Typ-ID.

Existieren Alternativen, zeigt die Oberfläche Anzahl und ausgewähltes Blueprint. Gemeinsamer Bedarf mehrerer Elternschritte wird zuerst zusammengeführt. Erst danach werden die benötigten Läufe mit ganzzahligem Aufrunden berechnet. Dadurch wird ein gemeinsames Zwischenprodukt nicht pro Elternzweig separat überrundet.

Jeder Schritt nennt Rezept, Aktivität, benötigte Menge, Ausgabemenge je Lauf, Läufe, produzierte Menge, Überschuss, unveränderte SDE-Basiszeit und direkte Materialien. Die sichtbare Herstellungsreihenfolge beginnt bei den tiefsten Vorprodukten und endet bewusst mit dem ausgewählten Zielprodukt. Backend und Frontend prüfen deshalb den letzten Schritt als gewähltes Wurzelziel. Das Ziel wird zusätzlich hervorgehoben; die Nummern sind damit als ausführbare Reihenfolge und nicht als Abhängigkeitsbaum zu lesen. Alle Mengen und Zeiten bleiben innerhalb der verlustfrei in JavaScript darstellbaren Ganzzahlgrenze; Überläufe werden abgewiesen.

## Persönlicher Job- und Anlagenbeleg

Paket 37 verwendet pro ausführendem Charakter ausschließlich den letzten vollständig abgeschlossenen persönlichen Industriejob-Snapshot. Für jeden Produktionsschritt werden nur Jobs mit passender Blueprint-Typ-ID und Aktivität berücksichtigt. Die Auswahl ist stabil:

1. ein Job mit der explizit zugeordneten Blueprint-Item-ID,
2. danach ein aktiver, pausierter oder abholbereiter Job desselben Blueprint-Typs,
3. danach der jüngste typgleiche Job nach Startzeit und Job-ID.

Der gewählte Job belegt Job-ID, Status und Anlagen-ID. Diese Anlage wird ausschließlich im letzten vollständig abgeschlossenen globalen Anlagen-Snapshot nachgeschlagen. Ist sie dort vorhanden, zeigt der Schritt Anlagenname und -art, Zugriffszustand, Sonnensystem, Sicherheitsraum, den für Fertigung oder Reaktion passenden Systemkostenindex sowie Snapshot-, Sync-Lauf- und Zeitbelege beider Quellen. Die Zustände `job-snapshot-missing`, `job-missing`, `facility-snapshot-missing`, `facility-missing` und `facility-unavailable` unterscheiden fehlende Quellen und eingeschränkte Strukturen ausdrücklich. Auf Zielebene bedeutet `ready`, dass alle Schritte eine verfügbare Anlage belegen; `partial` gilt bei mindestens einem belegten Schritt, `missing` bei keinem und `not-applicable` bei einer nicht auflösbaren Rezeptkette.

Ein historischer oder aktiver Job ist ein nachvollziehbarer persönlicher Anlagenbeleg, aber keine automatische Auswahl für einen künftigen Auftrag. Der Systemkostenindex wird als belegte Eingabe angezeigt und noch nicht in Zeit oder Kosten eingerechnet.

## Bruttomaterial und Zustände

`grossMaterials` enthält alle Mengen, die aus Bestand oder Einkauf bereitgestellt werden müssen. Dazu gehören äußere Materialien ohne verwendetes Rezept sowie der aus Bestand gedeckte Anteil eines Vorprodukts. Nur tatsächlich zu bauende Zwischenmengen erscheinen als Produktionsschritt; `producedByPlan` kennzeichnet diese Beziehung in den direkten Schrittmaterialien.

## Bestandsabgleich, Reservierung und Fehlmengen

Als physischer Bestand zählt ausschließlich der letzte vollständig abgeschlossene Asset-Snapshot des im Ziel gewählten ausführenden Charakters. Ein fehlgeschlagener, abgebrochener oder noch laufender neuerer Sync ersetzt diesen Stand nicht. Fehlt ein vollständiger Snapshot, bleiben Reservierung und Fehlmenge unbekannt; die Oberfläche zeigt ausdrücklich `Asset-Snapshot fehlt` statt erfundener Mengen.

Die Reservierung wird bei jeder Abfrage über **alle** gespeicherten Ziele berechnet, bevor Suche, Filter, Sortierung oder Seitenauswahl angewendet werden. Sie folgt pro Charakter und Material einer festen Reihenfolge:

1. höhere numerische Priorität zuerst,
2. bei gleicher Priorität das ältere Erstellungsdatum zuerst,
3. bei weiterhin gleichem Rang die kleinere Ziel-ID zuerst.

Nur vollständig auflösbare Ziele reservieren Bestand. Charaktere bleiben voneinander getrennt. Eine geänderte Priorität, Zielmenge, Charakterzuordnung oder ein neuer vollständiger Asset-Snapshot berechnet die Reservierungen sofort neu; eine zusätzliche persistente Reservierungstabelle ist deshalb nicht erforderlich.

Für jedes äußere Material weist die Antwort den gesamten physischen Bestand, bereits durch vorrangige Ziele reservierte Menge, die Reservierung für das aktuelle Ziel, den danach noch freien Bestand und die endgültige Fehlmenge aus. Die Fehlmenge wird nachvollziehbar getrennt in:

- `inventoryShortageQuantity`: Material, das selbst ohne andere Ziele physisch fehlen würde,
- `reservationConflictQuantity`: zusätzliche Fehlmenge, weil vorrangige Ziele den Bestand bereits reservieren.

Die endgültige Fehlmenge ist die Summe beider Werte. Höchstens 50 vorrangige Zielbelege werden je Material übertragen; Anzahl und reservierte Gesamtmenge bleiben auch bei gekürzter Belegliste vollständig.

Angerechnete Bestände werden nach Standortpfad und EVE-Bereich zusammengefasst. Jede Gruppe nennt Charakter, Quellstandort, Standortstatus, Bereich, Menge, Positionszahl sowie Asset-Snapshot-, Sync-Lauf- und Beobachtungszeitpunkt. Höchstens 50 Standortgruppen je Material und Kategorie werden übertragen; Gesamtmenge, Positions- und Gruppenzahl bleiben auch bei einer gekürzten Detailansicht vollständig. Fehlt der exakt zum Asset-Snapshot gehörende Standort-Snapshot, bleibt die Menge anrechenbar und ihr Standortstatus nachvollziehbar `pending`.

Passende Bestände anderer aktivierter Charaktere werden nicht stillschweigend zusammengelegt. Bei einer gewählten Produktions- oder Materialquelle erscheinen außerdem Bestände desselben Charakters außerhalb dieser Auswahl getrennt als bewusst nicht angerechneter Bestand mit denselben Quellenangaben. Dadurch bleibt sichtbar, wo Material vorhanden wäre, ohne die Charakter- oder Standortgrenze aufzuheben.

| Bestandszustand | Bedeutung |
| --- | --- |
| `covered` | Die konfliktfreie Reservierung deckt den Bruttobedarf des Ziels vollständig. |
| `shortage` | Ein vollständiger Snapshot liegt vor und mindestens eine physische oder reservierungsbedingte Fehlmenge ist größer als null. |
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

Paket 38 berechnet Bruttobedarf einschließlich des belegten Blueprint-ME jedes tatsächlich gebauten Fertigungsschritts, die mit dessen belegtem TE veränderte Blueprint-Zeit, die persönliche Skillzeit, gewählte Bestandsquellen und konfliktfreie zielbezogene Reservierungen. Vorhandene Vorprodukte können die Kette teilweise oder vollständig ersetzen. Zusätzlich werden passende persönliche Job- und Anlagenbelege samt aktivitätsspezifischem Systemkostenindex dargestellt. Noch nicht einbezogen werden:

- persönliche Blueprint-ME-/TE-Modifikatoren für Reaktionen,
- Anlagen-, Service- und Rigboni,
- Systemkosten, Steuern und Preise.

Die API bestätigt die aktiven Verträge mit `inventoryApplied: true`, `reservationsApplied: true`, `reservationRule: priority-desc-created-asc-plan-id-asc`, `blueprintMaterialEfficiencyApplied: true`, `materialEfficiencyRule: max-runs-ceil-base-runs-percent`, `blueprintTimeEfficiencyApplied: true`, `timeEfficiencyRule: max-one-ceil-base-runs-percent`, `blueprintChainAssignmentsApplied: true`, `blueprintChainAssignmentRule: explicit-per-recipe-unique-item`, `characterSkillTimeApplied: true`, `characterSkillTimeRule: job-wide-ceil-industry-4-advanced-industry-3-reactions-4-active-levels`, `facilityEvidenceApplied: true`, `facilityEvidenceRule: assigned-blueprint-before-active-before-latest-owner-job`, `supplyModesApplied: true` und `supplyModeRule: stock-first-before-recursive-build`. Die verbleibende Modifikatorgrenze bleibt `remainingModifiersApplied: false`. Auch die ausgewiesene persönliche Skillzeit darf ohne Anlagen-/Rigboni weiterhin nicht als reale Fertigstellungszeit oder Kostenprognose verstanden werden.

## Arbeitsvorrat und Bedienung

Die Produktionsplanung befindet sich unter **Produktion & Reaktionen**. Die Auswahl des ausführenden Charakters stammt direkt aus der Liste aktivierter Charaktere und hängt weder von vorhandenen Zielen noch von einer erfolgreichen Zielabfrage ab. Beim Anlegen und Bearbeiten können die Produktionsstation und das darin verwendete Materiallager gewählt werden. Nach der ersten Auflösung lässt sich die Quelle jedes Vorprodukts umstellen; die Anzeige nennt unmittelbar Bestandseinsatz, Restbau, Fehlmenge und Blueprintpflicht. Produkt- und Ziellisten unterstützen Suche, Aktivitäts-, Besitzer- und Statusfilter, Sortierung und begrenzte Seiten. Ein Ziel kann angelegt, geändert und bewusst entfernt werden.

Die Industrie-Slotübersicht zählt ein auflösbares Ziel als **laufend**, wenn derselbe Charakter einen aktiven, pausierten oder abholbereiten Job mit passender Aktivität und Blueprint-Typ-ID besitzt. Sonst ist es **geplant**. Nicht auflösbare Ziele sind **blockiert**. Ein Fertigzustand wird nicht aus Bestand oder Jobhistorie erfunden und bleibt daher null.

Die authentifizierten internen Routen `/production-plans/catalog`, `/production-plans/query`, `/production-plans/save` und `/production-plans/delete` besitzen strikte, begrenzte Verträge. Sidecar, Tauri und Frontend validieren ihre Antworten unabhängig voneinander.

## Quelle

Rezepte, Mengen und Basiszeiten stammen aus dem offiziellen [EVE Static Data Export](https://developers.eveonline.com/docs/services/static-data/). Jede aufgelöste Planung nennt die gemeinsam verwendete SDE-Buildnummer.

Die Skill-IDs und ihre Zeitboni sind in `types.jsonl` desselben festgeschriebenen offiziellen SDE-Builds 3503375 beschrieben. Die persönlichen aktiven Level stammen aus dem vollständigen charakterbezogenen ESI-Skill-Snapshot.

Die Windows-Ausgaben ab `v0.0.5-preview.14` liefern den geprüften Produktionsausschnitt des festgelegten offiziellen SDE-Builds mit. Er wird beim ersten Start automatisch installiert. Bei identischer Buildnummer wird er nur dann erneut verarbeitet, wenn eine neue abgeleitete Spalte – beispielsweise der Sicherheitsstatus ab `.18` – noch nicht befüllt ist. Die Produkt- und Blueprintsuche benötigt deshalb keinen manuellen Vorbereitungsschritt.
