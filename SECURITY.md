# Sicherheit

## Status

Das Projekt befindet sich vor der ersten Alpha. Es gibt noch keine unterstützte Produktversion.

## Schwachstellen melden

Sicherheitsrelevante Beobachtungen bitte nicht in einem öffentlichen Issue veröffentlichen. Für dieses öffentliche Repository ist bevorzugt ein privater Security Advisory unter **Security → Advisories** zu verwenden. Falls dieser Weg nicht verfügbar ist, den Repository-Eigentümer direkt über GitHub kontaktieren und zunächst keine vertraulichen Details öffentlich teilen.

Eine Meldung sollte betroffene Version oder Commit, reproduzierbare Schritte, erwartete Auswirkung und vorhandene Gegenmaßnahmen enthalten. Echte Tokens, Zugangsdaten oder persönliche EVE-Daten dürfen auch in der Meldung nicht unnötig kopiert werden.

## Umgang mit Geheimnissen

- Es werden keine Client Secrets mit der Desktop-Anwendung ausgeliefert.
- Refresh Tokens liegen ausschließlich im Betriebssystem-Schlüsselbund.
- Tokens, Sitzungsschlüssel und personenbezogene Nutzdaten erscheinen nicht in Logs.
- Lokale Beispielkonfigurationen werden nicht committed.
- Bei Offenlegung wird das Geheimnis zuerst widerrufen oder rotiert, danach wird die Historie bewertet und bereinigt.

Der CI-Secret-Scan ist eine zusätzliche Schranke, ersetzt aber keine Prüfung der Änderung.
