# ADR-008: Jita-first mit austauschbaren Marktadaptern

- **Status:** Angenommen
- **Datum:** 7. September 2026
- **Entscheider:** Projektverantwortlicher

## Kontext

Ein Markt-MVP benötigt eine klare Referenz, darf aber weder fünf fest verdrahtete Handelsplätze noch einen Community-Datenanbieter zur dauerhaften fachlichen Wahrheit machen. Unterschiedliche Quellen besitzen andere Aktualität, Tiefe und Ausfallmodi.

## Entscheidung

Der erste Marktpfad verwendet Jita als vorkonfiguriertes Referenzprofil. Handelsorte und Datenquellen liegen hinter getrennten Schnittstellen.

- Das Preisprofil bestimmt Hub beziehungsweise Reichweite, Orderseite, Mindestmenge, Tiefe, Gebührenannahmen, Datenquelle und maximal zulässiges Alter.
- Jita-spezifische IDs oder Filter stehen in Konfiguration beziehungsweise Stammdaten, nicht verteilt in Fachformeln.
- Offizielle ESI-Daten sind die primäre Livequelle, soweit der benötigte Anwendungsfall abgedeckt ist.
- Community-Anbieter sind optionale Adapter mit Herkunft, Datenalter, Fallback- und Fehlerstatus; sie sind nie alleinige Wahrheit.
- Weitere Hubs werden über Konfiguration/Profile ergänzt, nicht durch Kopieren von Marktlogik.
- Ein Live-Check ist eine ausdrücklich ausgelöste, begrenzte Aktion und überschreibt nicht unbemerkt reproduzierbare Planungswerte.
- Build-vs-Buy und Scanner speichern das verwendete Preisprofil zusammen mit dem Ergebnis.

## Folgen

Das MVP ist bewusst enger als eine universelle Marktanalyse. Adapterverträge und Preisprofile müssen früh stabilisiert werden. Ein neuer Hub benötigt Konfigurations-, Daten- und UX-Tests, aber keine neue Solverimplementierung.

## Verifikation

- Derselbe synthetische Orderbestand liefert über jeden konformen Adapter dasselbe normalisierte Ergebnis.
- Golden-Fälle prüfen Tiefe, Reichweite, Mindestmenge, veraltete Daten und Provider-Ausfall.
- Keine Fachformel enthält einen fest codierten Hub oder Anbieter.

## Referenzen

- [EVE Developer Documentation – ESI](https://developers.eveonline.com/docs/services/esi/)
- [Lebender Masterplan](../MASTERPLAN.md)
