# Erforderliche GitHub-Einstellungen

**Ziel:** `main` kann nur über einen geprüften Pull Request mit grünen Pflichtchecks geändert werden.

## Sollzustand für `main`

- Pull Request vor Merge erforderlich
- Branch muss vor Merge aktuell sein
- Pflichtchecks: `repository-policy` und `secret-scan`
- offene Review-Konversationen müssen gelöst sein
- Force Push nicht erlaubt
- Löschen des Branches nicht erlaubt
- Umgehung der Regeln auch für Administratoren deaktiviert, sofern verfügbar

Da das Projekt derzeit solo geführt wird, wird zunächst keine Fremdfreigabe als zwingende Mindestanzahl konfiguriert. Eine Review bleibt fachlicher Bestandteil der Definition of Done; bei weiteren Mitwirkenden wird die erforderliche Freigabezahl neu entschieden.

## Weitere Repository-Einstellungen

- bevorzugte Merge-Art: Squash Merge
- Arbeitsbranch nach Merge automatisch löschen
- Merge Commit und Rebase Merge deaktivieren
- Standardberechtigungen des `GITHUB_TOKEN`: nur Lesen; Schreibrechte nur jobweise und minimal
- Releases nur aus bewusst ausgelöstem, freigegebenem Workflow

## Aktueller Status

Das Repository wurde am 7. September 2026 öffentlich gemacht. GitHub-Free-Branchschutz ist damit verfügbar, wurde für `main` aber noch nicht aktiviert. Bis die obigen Regeln aktiv sind, gilt Arbeitspaket 01 nicht als vollständig abgenommen und der vorbereitende Pull Request bleibt ungemergt.

## Prüfung

Nach der Konfiguration:

1. direkten Push nach `main` mit einer gefahrlosen Teständerung ablehnen lassen,
2. Pull Request ohne Pflichtchecks nicht mergebar,
3. Pull Request mit fehlschlagendem `secret-scan` nicht mergebar,
4. Pull Request mit beiden grünen Checks mergebar,
5. Ergebnis und Datum in `docs/MASTERPLAN.md` dokumentieren.
