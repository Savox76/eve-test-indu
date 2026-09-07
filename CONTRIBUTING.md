# Mitarbeit an New Eden Foundry

## Arbeitsfluss

1. Für jede Änderung einen kurzen Branch von `main` erstellen.
2. Kleine, nachvollziehbare Commits schreiben.
3. Einen Pull Request mit Zweck, Testnachweis und Risiken eröffnen.
4. Erst mergen, wenn alle Pflichtprüfungen grün sind und kein Blocker offen ist.

Direkte Änderungen an `main` sind nicht Teil des Projektprozesses.

Empfohlene Branch-Präfixe sind `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`, `perf/` und `esi/`.

## Commit-Konvention

Commits verwenden Conventional-Commit-Präfixe:

- `feat:` neue Nutzerfunktion
- `fix:` Fehlerbehebung
- `perf:` messbare Leistungsverbesserung
- `refactor:` interne Änderung ohne beabsichtigte Funktionsänderung
- `docs:` reine Dokumentationsänderung
- `chore:` Werkzeug-, Build- oder Pflegeänderung
- `esi:` ESI-, SSO-, Scope- oder Compatibility-Anpassung

## Pull-Request-Gate

Vor dem Merge müssen, soweit für die Änderung einschlägig, folgende Punkte erfüllt sein:

- Abnahmekriterien und Grenzfälle sind umgesetzt.
- Passende Unit-, Integrations- oder Golden-Tests sind vorhanden.
- Alle Pflichtchecks sind grün.
- Es gibt keinen ungeklärten kritischen Sicherheitsfund.
- ADR, Masterplan, Nutzerhilfe und `CHANGELOG.md` sind aktuell.
- Repository, Tests, Logs und Screenshots enthalten ausschließlich synthetische Daten.
- GitHub Actions lädt keine Workflow-Artefakte hoch oder herunter.
- Es gibt keinen offenen Blocker im Pull Request.

## Daten und Geheimnisse

Die Regel in [docs/policies/synthetic-data.md](docs/policies/synthetic-data.md) ist verbindlich. Echte Charakter-, Corporation-, Alliance-, Asset-, Wallet-, Standort- oder Token-Daten dürfen nie committed werden. Ein versehentlich offengelegtes Geheimnis muss sofort widerrufen beziehungsweise rotiert werden; bloßes Löschen aus dem letzten Commit reicht nicht.

## Releases

Releases folgen [docs/RELEASING.md](docs/RELEASING.md). Insbesondere werden keine Actions-Artefakte als Zwischenspeicher verwendet. Installationsdateien dürfen ausschließlich an eine bewusst freigegebene GitHub-Release-Version angehängt werden.
