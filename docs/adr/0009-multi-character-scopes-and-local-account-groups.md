# ADR-009: Charaktergebundene EVE-Zugänge mit lokalen Kontogruppen und Gesamtansicht

- **Status:** Angenommen
- **Datum:** 8. September 2026
- **Entscheider:** Projektverantwortlicher

## Kontext

New Eden Foundry soll mehrere EVE-Accounts und alle dafür relevanten Charaktere gemeinsam bedienen können. EVE SSO stellt einer Drittanwendung jedoch keinen frei verwendbaren Account-Datensatz bereit: Im Anmeldeablauf wählt die Person einen Charakter, und das ausgestellte Token gilt nur für diesen Charakter und die bestätigten Scopes. Der JWT-Claim `sub` identifiziert entsprechend genau einen Charakter.

Eine technische Gleichsetzung von EVE-Login, Account und Charakter wäre deshalb unzuverlässig und würde unnötig sensible Anmeldestrukturen nachbilden. Gleichzeitig braucht die Produktionsplanung sowohl klar getrennte Charakteransichten als auch eine belastbare Zusammenfassung über alle verbundenen Charaktere.

## Entscheidung

- Jeder Charakter wird separat über EVE SSO autorisiert und anhand seiner numerischen EVE-Charakter-ID eindeutig gespeichert.
- Refresh Token und Scope-Status gehören immer zum einzelnen Charakter. Zugangsdaten, Accountname und EVE-Passwort werden weder erfragt noch gespeichert.
- Mehrere Charaktere dürfen optional in frei benannte, ausschließlich lokale **Kontogruppen** einsortiert werden. Diese Gruppen bilden die vom Nutzer gewünschte Accountstruktur ab, behaupten aber keine von EVE bestätigte Accountzugehörigkeit.
- Ein erneutes Verbinden derselben Charakter-ID aktualisiert Name, Kontogruppe und Scopes atomar und erzeugt keinen doppelten Charakter.
- Das Entfernen einer Kontogruppe löscht keinen Charakter und keine Autorisierung; die betroffenen Charaktere werden lediglich als nicht gruppiert geführt.
- Das bewusste Löschen eines Charakters entfernt dagegen dessen lokale Scopes, Synchronisierungsläufe und abhängige Cache-Snapshots vollständig; Schlüsselbunddaten werden im späteren Löschablauf ebenfalls entfernt.
- Eigentümerbezogene Daten und Synchronisierungsläufe tragen eine Charakter-ID. Gemeinsame Auswertungen aggregieren diese Datensätze, ohne den Eigentümerbezug zu verlieren.
- Die Oberfläche bietet mindestens zwei Ebenen: **Alle Charaktere** als gemeinsame Gesamtübersicht und eine eigene Übersicht je Charakter. Lokale Kontogruppen strukturieren die Auswahl.
- Datenalter, fehlende Scopes und fehlgeschlagene Synchronisierungen bleiben pro Charakter sichtbar. Die Gesamtübersicht darf unvollständige Charakterdaten nicht als Nullwerte ausgeben oder still aus der Summe entfernen.

## Folgen

Ein EVE-Account mit mehreren Charakteren benötigt mehrere bewusste SSO-Anmeldevorgänge. Kontogruppen erleichtern anschließend die lokale Organisation, ersetzen aber keine EVE-Anmeldung. Spätere Asset-, Blueprint-, Job-, Markt-, Projekt- und PI-Tabellen müssen den Eigentümerbezug durchgängig erhalten, damit Einzel- und Gesamtansicht aus derselben Datenbasis reproduzierbar entstehen.

Der feste Betreibername in der aktuellen Vorschau ist keine EVE-Identität. Sobald lokale Einstellungen implementiert werden, wird er als editierbare lokale Anzeige behandelt.

## Verifikation

- Migrationstests aktualisieren eine Schema-Version-1-Datenbank ohne Datenverlust auf das Mehrcharakter-Schema.
- Backendtests prüfen mit negativen synthetischen IDs mehrere Kontogruppen, mehrere Charaktere, getrennte Scopes, idempotentes Wiederverbinden, ungültige Gruppenzuordnung und das gruppenunabhängige Fortbestehen eines Charakters.
- UI-Tests wechseln zwischen Gesamt- und Charakterübersicht und prüfen unterschiedliche Kennzahlen sowie den sichtbaren Betreibername.
- Spätere SSO-Integrationstests weisen nach, dass Token, Scopes, Fehler und Datenalter nie zwischen Charakteren vermischt werden.

## Referenzen

- [EVE Developer Documentation – Single Sign-On](https://developers.eveonline.com/docs/services/sso/)
- [ADR-004 – EVE SSO mit PKCE](0004-eve-sso-pkce.md)
- [ADR-006 – Cache-first-Synchronisierung](0006-cache-first-sync.md)
