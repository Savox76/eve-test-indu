# Asset-Oberfläche und CSV-Export

Paket 20 bindet die Asset-Ansicht an die letzten vollständig abgeschlossenen, charaktergetrennten Asset-Snapshots und die dazu passenden Standort-Snapshots. Die Ansicht verwendet keine synthetischen Fachwerte, sobald der lokale Desktop-Kern bereit ist.

Beim Programmstart und nach einer neuen Charakterverbindung startet die App den echten ESI-Lauf für alle aktivierten Charaktere automatisch im Hintergrund. Mit **Assets aktualisieren** lässt er sich zusätzlich manuell anstoßen. Nach Abschluss werden Bestand und Änderungsverlauf neu geladen. Teilfehler werden sichtbar gemeldet, während erfolgreiche Charakterläufe erhalten bleiben.

## Bestandsübersicht und Einzelpositionen

Die Asset-Seite öffnet standardmäßig eine nach Typ gruppierte Bestandsübersicht. Sie zeigt je Gegenstand die Gesamtmenge, Zahl der EVE-Positionen, Verteilung auf Charaktere, Zahl der tatsächlichen Asset-Orte, vorkommende Standortzustände und das älteste Datenalter. **Einzelpositionen anzeigen** übernimmt den Typnamen als Suche und wechselt gezielt in die Detailansicht.

Suche sowie Besitzer- und Standortstatusfilter gelten in beiden Ansichten. Erst werden die passenden Positionen gefiltert, anschließend wird die Bestandsübersicht gruppiert. Damit beantworten Summen und Verteilungen immer genau die aktuell gewählte Suche.

Jede Einzelposition zeigt:

- den lokal gespeicherten SDE- oder ESI-Typnamen sowie Type- und Item-ID,
- lokalen Alias beziehungsweise Charakternamen als Besitzer,
- root-first Standort- und Containerpfad,
- Standortstatus `resolved`, `restricted`, `unresolved`, `cycle` oder `pending`,
- EVE-Hangar beziehungsweise Bereich, Menge und Datenalter.

Ein Standort-Snapshot wird nur verwendet, wenn seine `assetSnapshotId` exakt dem angezeigten Asset-Snapshot entspricht. Nach einem neueren Asset-Sync bleibt der Standort daher sichtbar `pending`, bis Paket 19 genau diesen neuen Stand vollständig aufgelöst hat. Alte Pfade werden nicht auf neue Assets übertragen.

## Suche und Filter

Die serverseitige Suche berücksichtigt Typname, Besitzer, Standortpfad, Hangar/Bereich, Type-ID und Item-ID. Besitzer- und Standortstatusfilter lassen sich kombinieren. Sichtbare Spalten können auf- oder absteigend sortiert werden; die Sortierung erfolgt vor der Seitenteilung. Suche, Filterung, Gruppierung, Summenbildung und stabile Sortierung erfolgen im lokalen Python-Sidecar; die React-Oberfläche erhält nie den vollständigen Snapshot.

## 100.000-Zeilen-Vertrag

- Die Standardseite enthält höchstens 100 Positionen.
- Der Sidecar akzeptiert technisch höchstens 200 Positionen pro Anfrage.
- Die Tabelle rendert nur die aktuelle Seite und verwendet einen eigenen scrollbaren Bereich mit fixierter Kopfzeile.
- Suchtexte werden um 250 Millisekunden verzögert, damit schnelles Tippen keine Anfrage pro Tastendruck auslöst.
- Ein synthetischer Regressionstest veröffentlicht 100.000 Positionen, prüft die korrekte Gesamtzahl und stellt sicher, dass nur das angeforderte 100-Zeilen-Fenster die IPC-Grenze passiert.

Damit wachsen DOM und lokale HTTP-Antwort mit der Seitengröße und nicht mit der Größe des EVE-Bestands. Die lokale Suche muss weiterhin den Snapshot auswerten; der begrenzte Transport und das begrenzte Rendering halten die Interaktion flüssig.

## CSV-Export

`Treffer als CSV` exportiert die aktuell angewendete Suche, Besitzer- und Standortfilter sowie Sortierung. Der Sidecar schreibt die vollständige Ergebnismenge atomar als UTF-8-CSV mit BOM unter:

```text
<Programmordner>\data\exports\assets-YYYYMMDD-HHMMSS.csv
```

Die Desktop-Brücke erhält nur Dateiname, relativen Pfad und Zeilenzahl. Auch ein Export mit 100.000 Zeilen überschreitet daher nicht das begrenzte IPC-Antwortfenster. Textfelder, die Tabellenkalkulationen als Formel interpretieren könnten (`=`, `+`, `-` oder `@`), werden mit einem führenden Apostroph neutralisiert. Eine temporäre Datei wird nach erfolgreichem Schreiben und `fsync` atomar an ihr Ziel verschoben; ein Teilstand wird nicht als fertige CSV veröffentlicht.

## Fehler- und Leerzustände

Die Oberfläche unterscheidet Desktop-Kern nicht verfügbar, Laden, noch kein vollständiger Snapshot, keine Filtertreffer, Lesefehler und Exportfehler. Das Datenalter des ältesten einbezogenen Besitzers bleibt in aggregierten Ergebnissen sichtbar. Beschädigte angeblich vollständige Snapshots werden abgewiesen, statt unvollständige oder inkonsistente Zeilen anzuzeigen.

Unter der Bestandsansicht zeigt Paket 21 zusätzlich den [nachvollziehbaren Asset-Änderungsverlauf](asset-deltas.md). Er verwendet dasselbe Suchfeld und denselben Besitzerfilter, ergänzt einen Filter nach Änderungsart und überträgt höchstens 50 Ereignisse pro sichtbarer Seite.
