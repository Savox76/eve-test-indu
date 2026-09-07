# ADR-001: Desktop-first, Einzelplatz und local-first

- **Status:** Angenommen
- **Datum:** 7. September 2026
- **Entscheider:** Projektverantwortlicher

## Kontext

Die Anwendung verarbeitet persönliche EVE-Daten und unterstützt einen einzelnen Spieler bei wiederkehrenden Industrieentscheidungen. Ein zentraler Server würde Betrieb, Anmeldung, Datenschutz, Kosten und Ausfallrisiken erhöhen, bevor ein Mehrbenutzernutzen belegt ist.

## Entscheidung

New Eden Foundry wird als lokale Desktop-Anwendung für genau einen interaktiven Nutzer pro Installation gebaut.

- Windows ist die erste unterstützte Plattform.
- Anwendungsdaten, Cache, Einstellungen und fachliche Historie liegen lokal.
- ESI und SSO sind externe Abhängigkeiten; ein eigener Cloud-Dienst ist keine Voraussetzung.
- Im Endnutzerbetrieb gibt es weder Docker noch Redis, PostgreSQL oder einen separat zu administrierenden Server.
- Mehrere EVE-Charaktere eines Nutzers sind zulässig; Mehrbenutzer-, Rollen- oder Teamverwaltung ist nicht Teil des Kerns.
- Offline- und Fremdsystemfehler werden sichtbar behandelt, ohne bekannte Daten zu verwerfen.

## Folgen

Installation, Updates, Backups, Schlüsselbund und Dateirechte sind Produktfunktionen. Datenfreigabe zwischen Geräten sowie gemeinschaftliche Planung sind zunächst ausgeschlossen. Linux und macOS benötigen später eigene Plattform-Gates.

## Verifikation

- Eine freigegebene Windows-Installation funktioniert ohne lokal installierte Entwicklerwerkzeuge oder Datenbankdienste.
- Netzwerkentzug lässt die Anwendung mit klar markierten Cache-Daten starten.
- Eine zweite Instanz erzeugt keinen zweiten lokalen Dienst.

## Referenzen

- [Lebender Masterplan](../MASTERPLAN.md)
- [Tauri – Process Model](https://v2.tauri.app/concept/process-model/)
