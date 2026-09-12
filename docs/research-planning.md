# Forschungsplanung

Paket 27 verbindet die letzten vollständigen Blueprint-, Skill-, Job- und Anlagen-Snapshots zu einer lokalen, updatefesten ME-/TE-Arbeitsliste. Grundlage sind die offiziellen [EVE Static Data Export-Daten](https://developers.eveonline.com/docs/services/static-data/) und die über den zentralen ESI-Client synchronisierten persönlichen Daten. Die Planung verändert keine Daten im Spiel und startet keine Jobs.

## Persistenter Plan

Für jedes aktuelle BPO kann genau ein Plan gespeichert werden. Er enthält:

- nächste Aktivität: Materialeffizienz oder Zeiteffizienz,
- Zielwert ME 0–10 und TE 0–20,
- Priorität 0–999,
- optionale Notiz bis 240 Zeichen.

Die Tabelle `research_plans` gehört ab Schema 8 zum Anwendungskern. Ihr Schlüssel besteht aus Charakter- und Blueprint-Item-ID; dadurch bleiben gleichartige BPOs getrennt. Verschwindet ein gespeichertes BPO aus einem späteren vollständigen Snapshot, bleibt der Plan als **Blueprint fehlt** sichtbar und kann bewusst entfernt werden. Beim vollständigen Löschen des Charakters werden seine Pläne über den Fremdschlüssel mitgelöscht.

## Belegbare Zustände

| Zustand | Bedeutung |
| --- | --- |
| Nicht geplant | Aktuelles BPO ohne gespeicherten Plan |
| Bereit | Ziel noch offen, Skillstand belegt und mindestens ein Forschungsslot frei |
| Wartend | Ziel noch offen, aber alle belegbaren Wissenschaftsslots sind belegt |
| Läuft | Ein aktiver, pausierter oder abholbereiter ME-/TE-Job verweist auf genau dieses Blueprint-Item |
| Fertig | Der aktuelle vollständige Blueprint-Snapshot erreicht beide gespeicherten Ziele |
| Ungeprüft | Kein vollständiger Skill-Snapshot liegt für die Kapazitätsprüfung vor |
| Blueprint fehlt | Der gespeicherte Plan besitzt kein BPO im aktuellen vollständigen Snapshot |

Die Wissenschaftskapazität ist `1 + Laboratory Operation + Advanced Laboratory Operation` auf Basis der aktuell wirksamen Skilllevel. Als belegt zählen aktive, pausierte und abholbereite Jobs der ESI-Aktivitäten Forschung, Kopieren und Erfindung. `Research` und `Metallurgy` werden mit ihren aktuellen Leveln angezeigt, aber ohne vollständige Zeitformel nicht isoliert in eine Prognose umgerechnet.

## Job- und Anlagenbeleg

Ein laufender Plan zeigt die reale Job-ID, Aktivität, den von ESI gelieferten Status, Start, Ende und die tatsächlichen Jobkosten. Anlage, Sonnensystem und Systemkostenindex stammen aus demselben geprüften Anlagenstand. Ohne laufenden Job kann die zuletzt vom Charakter für dieselbe Forschungsaktivität verwendete Anlage als historische Orientierung erscheinen; sie wird ausdrücklich als **zuletzt dort genutzt** und nicht als Auswahl oder Verfügbarkeitsgarantie markiert.

Jede Zeile führt die vorhandenen Snapshot- und Sync-Run-IDs für Blueprint, Skill und Jobs. Ungültige, unvollständige oder widersprüchliche Quellen werden an Sidecar- und Tauri-Grenze abgewiesen.

## Bewusste Prognosegrenze

Vor dem Einbau werden noch keine Forschungsdauer und keine Gesamtkosten ausgegeben. Dafür fehlen im aktuellen Modell die vollständigen SDE-Aktivitätswerte je Blueprint sowie alle anwendbaren Charakter-, Anlagen-, Service-, Rig-, Steuer- und Systemmodifikatoren. Ein Systemkostenindex oder ein einzelnes Skilllevel wäre keine belastbare Gesamtrechnung.

Ein späteres Paket darf Prognosen erst freischalten, wenn diese Eingaben getrennt, versioniert und mit Decimal-basierten Golden-Fällen geprüft sind. Bis dahin zeigt die Oberfläche reale laufende Jobwerte und `estimatesAvailable: false`, statt unbekannte Komponenten als Null anzunehmen.

## Bedienung und Aktualisierung

Die Forschungsplanung befindet sich unter **Blueprints & Jobs**. Standardmäßig werden vollständig erforschte, im Bestand vorhandene BPOs mit ME 10 und TE 20 ausgeblendet; der Schalter **Vollständig erforschte anzeigen** nimmt sie wieder auf. Positive ESI-Stapelmengen gelten dabei wie `-1` als Originalbestand, nur `-2` ist eine Kopie. Suche, Besitzer-, Status- und Gespeichert-Filter sowie Sortierung und Seitenteilung laufen im lokalen Sidecar; pro Anfrage werden höchstens 200 und in der Oberfläche standardmäßig 100 Zeilen übertragen. Nach einem Blueprint-, Skill-, Job- oder Anlagenabgleich wird die Ansicht neu geladen, damit Zustand, Slots und Belege denselben aktuellen lokalen Datenstand verwenden.
