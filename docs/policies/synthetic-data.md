# Richtlinie für synthetische Daten

**Status:** verbindlich

**Gültig ab:** 7. September 2026

## Grundsatz

Repository, Git-Historie, Issues, Pull Requests, Tests, Dokumentation, Logs und Screenshots dürfen ausschließlich erfundene Daten enthalten. Daten aus einem echten EVE-Konto dürfen auch dann nicht committed werden, wenn das Repository privat ist.

## Verbotene reale Daten

Insbesondere nicht zulässig sind:

- echte Charakter-, Corporation- oder Alliance-Namen und -IDs,
- Asset-, Blueprint-, Job-, Wallet-, Vertrags-, Markt- oder PI-Daten eines Spielers,
- Struktur- und Containerbezeichnungen, die Rückschlüsse auf reale Aktivitäten erlauben,
- Access Tokens, Refresh Tokens, Sitzungstoken, Authorization Codes und Schlüsselbund-Ausgaben,
- Client Secrets, Signierschlüssel, Zertifikate oder lokale Konfigurationsdateien,
- unveränderte Diagnosepakete oder Bildschirmaufnahmen einer realen Installation.

Öffentliche, statische EVE-Stammdaten aus einer zulässigen SDE-Quelle sind keine Nutzerdaten. Ihre Herkunft und Version müssen jedoch dokumentiert werden.

Ausdrücklich freigegebene Projekt-, Marken- oder Urheberbezeichnungen sind UI-Texte und keine EVE-Fixtures. Sie dürfen keine tatsächliche Charakter-, Corporation-, Alliance- oder Accountzugehörigkeit behaupten. `Savoxmedia` erscheint deshalb ausschließlich als Ersteller der App neben der Versionsnummer und nicht als EVE-Identität.

## Regeln für Fixtures

- Personen, Organisationen, Strukturen, Projekte und Orte erhalten klar erfundene Namen.
- Interne synthetische Entitäts-IDs sind negativ. Adapter verhindern, dass negative IDs an ESI gesendet werden.
- Zeiten, Mengen, Preise und Erfolgswahrscheinlichkeiten werden bewusst konstruiert und nicht aus einem echten Konto übernommen.
- Jeder Fixture-Satz enthält `synthetic: true` und eine kurze Beschreibung des geprüften Grenzfalls, sobald das Dateiformat dies zulässt.
- Screenshots werden ausschließlich aus dem versionierten Demo-Datensatz erzeugt.
- Ein Test darf nie einen Live-ESI-Aufruf benötigen; Netzwerkzugriffe werden durch aufgezeichnete synthetische Antworten oder Fakes ersetzt.

## Review-Check

Vor dem Commit werden neue Fixtures und Bilder darauf geprüft, dass Namen, IDs, Zeitstempel und Freitext vollständig erfunden sind. Der Secret-Scan ist zusätzlich auszuführen, erkennt aber keine personenbezogenen EVE-Daten zuverlässig und ersetzt deshalb nicht die manuelle Prüfung.

## Fund echter Daten

1. Weitergabe stoppen und betroffenen Pull Request nicht mergen.
2. Tokens oder Schlüssel sofort widerrufen beziehungsweise rotieren.
3. Repository-Eigentümer privat informieren.
4. Reichweite einschließlich Git-Historie, Actions-Logs und Release-Dateien prüfen.
5. Daten kontrolliert bereinigen und den Vorfall ohne sensible Inhalte dokumentieren.
