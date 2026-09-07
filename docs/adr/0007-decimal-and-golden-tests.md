# ADR-007: Decimal- und Golden-Test-Pflicht für wirtschaftliche Berechnungen

- **Status:** Angenommen
- **Datum:** 7. September 2026
- **Entscheider:** Projektverantwortlicher

## Kontext

Industrieentscheidungen kombinieren Stückzahlen, Materialeffizienz, Zeit, Gebühren, Steuern, Wahrscheinlichkeiten und Marktpreise. Binäre Fließkommaarithmetik und uneinheitliches Zwischenrunden können sichtbare und schwer nachvollziehbare Abweichungen erzeugen.

## Entscheidung

Alle wirtschaftlichen und mengenbezogenen Berechnungen verwenden dezimale Arithmetik und explizite fachliche Rundungsregeln.

- Geld, Mengenfaktoren, Wahrscheinlichkeiten, Gebühren und Zwischenwerte werden als `Decimal` oder als exakt skalierte Ganzzahlen modelliert.
- Eingaben aus JSON, CSV oder SQLite werden ohne Zwischenkonvertierung über binäres `float` eingelesen.
- Rundung findet nur an dokumentierten Spiel- oder Anzeigegrenzen statt; Rundungsmodus und Einheit stehen am Rechenschritt.
- Jede Formel liefert neben dem Ergebnis eine nachvollziehbare Aufschlüsselung ihrer Eingaben und Zwischenstufen.
- Blueprint-Material, ME/TE, Jobkosten, Steuern, Reaktionen, Invention und PI besitzen synthetische Golden-Fälle.
- Golden-Fälle enthalten Quelle beziehungsweise Herleitung, Eingabefingerabdruck und erwartete Ergebnisse.
- Änderungen einer Formel oder Rundungsregel benötigen aktualisierte Tests, Changelog und bei fachlicher Bedeutungsänderung ein ADR.

## Folgen

Bibliotheks- und API-Grenzen, die nur Fließkommawerte liefern, brauchen kontrollierte Konvertierung. Performanceoptimierungen dürfen Exaktheit und Erklärbarkeit nicht verändern. Anzeigeformatierung bleibt von der internen sprachneutralen Repräsentation getrennt.

## Verifikation

- Tests schlagen bei unbeabsichtigten `float`-Eingaben in Rechenkernen fehl.
- Golden-Fälle prüfen exakte Werte und definierte Rundungsgrenzen.
- Gleiche Eingaben erzeugen unabhängig von Sprache und Plattform gleiche fachliche Ergebnisse.

## Referenzen

- [Python – decimal](https://docs.python.org/3/library/decimal.html)
- [Richtlinie für synthetische Daten](../policies/synthetic-data.md)
