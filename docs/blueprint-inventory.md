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

## Bestandsweiter Rentabilitätsvergleich (Pakete 49–50)

Die Rentabilität liest alle Blueprint-Positionen aktivierter Charaktere direkt aus ihren letzten vollständigen Blueprint-Snapshots. Produktionsziele sind nicht erforderlich. Besitzer und Suchtext grenzen die Auswahl ein. Gleiche Blueprint-Typen werden über alle gewählten Besitzer vor der Seitenteilung zusammengefasst. Die Seitennavigation zeigt den gesamten gefilterten Bestand, höchstens 25 Typen je Seite; bei vielen Rezeptmaterialien wird eine Seite vor dem Marktlimit von 250 Typen beendet.

Die Oberfläche berechnet automatisch einen Produktionslauf und zeigt Nettogewinn pro produzierter Einheit (auf zwei Dezimalstellen gerundet) sowie Nettomarge. Es gibt keine Vergleichslauf-Eingabe mehr; eine früher gespeicherte Laufzahl wird ignoriert. Größere Produktionsaufträge können durch Rundung und Ordertiefe abweichende Stückkosten haben.

Als Grundlage dient die nutzbare Variante mit höchstem ME, danach TE; bei Gleichstand hat ein Original Vorrang. Besitzer-ID und Item-ID lösen verbleibende Gleichstände stabil auf. Erschöpfte Kopien verdrängen keine nutzbare Variante. Der verwendete Besitzer, BPO/BPC und ME/TE sind in der Zeile sichtbar. Aufklappbare Details fassen Positionen nach Besitzer, Art, ME/TE und Laufverfügbarkeit zusammen. Die Anzahl bezeichnet Snapshot-Positionen, nicht die Menge gestapelter Originale. Pro Typ werden höchstens 100 Varianten übertragen; vollständige Positions-/Variantenzahlen und die ausgelassene Variantenzahl bleiben sichtbar. Einzelpositionen sind weiterhin im Blueprint-Bestand zugänglich.

Produktionsanlage, Anlagensteuer und Materialbonus werden separat eingestellt und gespeichert. Der Materialbonus startet ausdrücklich bei 0 Prozent. ME und der angegebene Materialbonus werden vor einer einzigen Aufrundung kombiniert; TE wird angezeigt, beeinflusst aber keine ISK-Kosten dieser Rechnung. Der Verkaufscharakter bestimmt die automatischen Handelsgebühren.

Alle direkten Rezeptmaterialien werden an der jeweiligen Handelsstation gekauft und mit verfügbarer Sell-Order-Tiefe bewertet. Es wird keine mehrstufige Eigenfertigung angenommen und kein kostenloser Lagerbestand abgezogen. Die Gebührenrechnung entspricht der Produktionsplanung einschließlich Systemkosten, ausdrücklich angegebener Anlagensteuer, SCC, Brokergebühr und Verkaufssteuer. Blueprint-/BPC-Anschaffung, Transport und erneute Einstellgebühren sind nicht enthalten.

„Rentabilitätsdaten aktualisieren“ lädt die benötigten Preise der angezeigten Seite für Jita, Amarr, Dodixie, Hek und Rens sowie Skills, Standings und Industrieanlagen einschließlich angepasster Preise. Alle Antworten werden abgewartet. Fehlgeschlagene Quellen und fehlgeschlagene Charakterabrufe werden angezeigt; erfolgreiche Teilaktualisierungen werden trotzdem neu ausgewertet. Auch eine Standing-Aktualisierung löst eine neue Auswertung aus. Frühere vollständige Abrufe anderer Seiten bleiben nutzbar: pro Typ gilt die jüngste Beobachtung, auch wenn sie ein leeres Orderbuch enthält. Der älteste beitragende Zeitstempel bestimmt das angezeigte Datenalter; veraltete Daten werden gekennzeichnet. Fehlen Produktpreise oder die vollständige Materialdeckung, bleibt die Rechnung nicht berechenbar und nennt den Grund. Fehlen nur Anlagenkosten oder Handelsgebühren, zeigt die Oberfläche Erlöse abzüglich der belegten Kosten als neutral markiertes vorläufiges Ergebnis mit ausdrücklichem Hinweis auf die noch ausgelassenen Kostenarten. Dafür erscheinen weder Nettomarge noch eine Beste-Station-Markierung. Ein unbekannter Kostenwert bleibt im Datenvertrag `null`.

Für vollständigen Nettogewinn müssen Produktionsanlage und tatsächliche Anlagensteuer ausgewählt sein; ein leeres Steuerfeld bedeutet unbekannt, nicht 0 %. Der Verkaufscharakter benötigt gültige Skill- und Standing-Snapshots. Die Oberfläche zeigt passende Hinweise zur Auswahl, Aktualisierung oder erneuten Anmeldung im Setup. Ein gespeicherter nicht mehr aktivierter Verkäufer wird durch den ersten verfügbaren Charakter ersetzt.

Es werden keine Produktionsziele gespeichert, vorhandene Ziele geändert oder Materialien reserviert. Rezepte ohne unterstützte Fertigung/Reaktion, erschöpfte Kopien und Rezepte mit mehreren unterschiedlichen Produkten bleiben sichtbar und nicht berechenbar.
