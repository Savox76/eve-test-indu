# Industrie-Slotübersicht

Paket 28 führt die charaktergetrennten Fertigungs-, Reaktions- und Wissenschaftsslots in einer gemeinsamen lokalen Übersicht zusammen. Die Ansicht verwendet ausschließlich bereits vollständig veröffentlichte Skill- und Job-Snapshots sowie die persistenten Forschungspläne aus Paket 27. Sie startet keine Jobs und verändert keine Daten in EVE.

## Kapazität und Belegung

| Bereich | Kapazität | Belegte ESI-Aktivitäten |
| --- | --- | --- |
| Fertigung | `1 + Mass Production + Advanced Mass Production` | Fertigung (`1`) |
| Reaktionen | `1 + Mass Reactions + Advanced Mass Reactions` | Reaktionen (`9`, `11`) |
| Wissenschaft | `1 + Laboratory Operation + Advanced Laboratory Operation` | ME-/TE-Forschung, Kopieren, Erfindung und Reverse Engineering (`3`, `4`, `5`, `7`, `8`) |

Für die Kapazität gilt jeweils das aktuell wirksame Skilllevel des letzten vollständigen Charakter-Snapshots. Als belegt zählen aktive, pausierte und abholbereite persönliche Jobs. Ein aktiver Job liefert zusätzlich den frühesten bekannten Endzeitpunkt je Bereich; abholbereite und pausierte Jobs bleiben belegt, besitzen aber keine behauptete Fertigstellungsprognose.

## Belegbare Zustände

| Zustand | Bedeutung |
| --- | --- |
| Slots frei | Kapazität und Belegung sind bekannt, mindestens ein Slot ist frei. |
| Voll belegt | Die bekannte Belegung entspricht genau der bekannten Kapazität. |
| Über Kapazität | Der letzte Job-Snapshot enthält mehr belegende Jobs als der aktuelle Skill-Snapshot erlaubt, beispielsweise nach einer Änderung wirksamer Skilllevel. |
| Daten fehlen | Mindestens eine der beiden notwendigen Quellen fehlt; der freie Wert bleibt unbekannt. |

Skill-Kapazität und Jobbelegung werden unabhängig voneinander belegt. Ein vorhandener Skill-Snapshot bei fehlendem Job-Snapshot zeigt daher die Kapazität, aber weder null belegte noch freie Slots. Umgekehrt wird eine bekannte Belegung ohne Skill-Snapshot nicht als Kapazitätswert ausgegeben. Die Gesamtansicht verwendet den ältesten vorhandenen Quellenzeitpunkt als konservatives Datenalter.

## Arbeitsvorrat

Die aktuelle Jobbelegung zeigt je Bereich aktive, pausierte und abholbereite Arbeit. Für Wissenschaft ergänzt die Übersicht den gespeicherten Forschungs-Arbeitsvorrat aus Paket 27:

- **geplant:** Ziel offen und derzeit nicht als laufender Forschungsjob belegt,
- **laufend:** ein aktiver, pausierter oder abholbereiter ME-/TE-Job verweist auf das geplante BPO,
- **blockiert:** das BPO oder der vollständige Skillstand fehlt,
- **fertig:** beide gespeicherten ME-/TE-Ziele sind erreicht.

Paket 30 ergänzt denselben Arbeitsvorrat für persistente Fertigungs- und Reaktionsziele:

- **geplant:** die Rezeptkette ist auflösbar und kein passender laufender Job belegt das Ziel,
- **laufend:** derselbe Charakter besitzt einen aktiven, pausierten oder abholbereiten Job mit passender Aktivität und Blueprint-Typ-ID,
- **blockiert:** SDE-Basis oder Rezept fehlt beziehungsweise die Kette ist zyklisch oder zu groß,
- **fertig:** bleibt null, solange kein eigener Bestands- und Reservierungsvertrag den Zielabschluss belegen kann.

Damit wird Arbeitsvorrat sichtbar, ohne aus Jobhistorie oder vorhandenem Bestand einen zukünftigen oder fertigen Zustand zu erfinden.

## Quellen und Vertrauensgrenzen

Jeder Charaktereintrag führt die vorhandenen Skill- und Job-Snapshot- sowie Sync-Run-IDs. Ungültige Skill-IDs, Teilwerte, widersprüchliche Summen, unbekannte Aktivitätsreihenfolgen und unplausible Kapazitätszustände werden an Sidecar-, Tauri- und Frontendgrenze abgewiesen.

Die interne Route `/industry-slots/query` akzeptiert nur Charakter-ID, Offset und Limit. Sie überträgt höchstens 200 Charaktere je Anfrage; die Oberfläche verwendet 50. Filterung und Seitenteilung erfolgen im lokalen Sidecar. Paket 28 benötigt weder eine Schemaänderung noch zusätzliche ESI-Scopes oder einen eigenen Synchronisierungslauf: Nach Blueprint-, Skill-, Job- oder Forschungsplanänderungen wird die abgeleitete Ansicht aus den aktuellen vollständigen Quellen neu geladen.
