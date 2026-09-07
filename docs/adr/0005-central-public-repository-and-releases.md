# ADR-005: Zentrales öffentliches Repository ohne Actions-Artefakte

- **Status:** Angenommen
- **Datum:** 7. September 2026
- **Entscheider:** Projektverantwortlicher
- **Ersetzt:** die Masterplan-Annahme getrennter privater Source-, Release- und Website-Flächen

## Kontext

Der ursprüngliche Masterplan trennte privaten Quellcode, Binärvertrieb und eine spätere Produktseite. Danach wurde verbindlich festgelegt, dass sich die gesamte Projektarbeit in `Savox76/eve-test-indu` abspielt und GitHub Actions keine Artefakte speichert. Am 7. September 2026 wurde das Repository bewusst öffentlich gemacht, damit GitHub-Free-Branchschutz genutzt werden kann.

## Entscheidung

`Savox76/eve-test-indu` ist das einzige Repository für:

- Quellcode und Dokumentation,
- Issues, Planung und Pull Requests,
- GitHub Actions und Pflichtprüfungen,
- Tags, Release Notes und freigegebene Release-Dateien.

Das Repository ist öffentlich. Quellcode, Git-Historie, Issues, Pull Requests, Actions-Ergebnisse und Release-Seiten sind damit allgemein einsehbar. Zusätzlich gelten:

- Änderungen an `main` erfolgen ausschließlich über Pull Requests.
- Ein Merge ist nur bei vollständig grünen Pflichtchecks und ohne offenen Blocker zulässig.
- Conventional Commits mit `feat`, `fix`, `perf`, `refactor`, `docs`, `chore` und `esi` strukturieren Änderungen.
- GitHub-Actions-Artefakte sind untersagt. Workflows verwenden weder Upload- noch Download-Actions für Workflow-Artefakte.
- Build- und Testergebnisse bleiben flüchtig im jeweiligen Job oder werden innerhalb desselben Workflows direkt weitergereicht, ohne Actions-Artefaktspeicher.
- Installationsdateien, Signaturen und Update-Manifeste werden nur für eine freigegebene Version direkt an das zugehörige GitHub Release angehängt.
- Jedes Release dokumentiert neu hinzugefügte Funktionen, Änderungen, behobene Fehler, bekannte Einschränkungen sowie Update- und Datenbankmigrationshinweise.
- Eine getrennte Produktseite oder ein zweites Release-Repository ist nicht vorgesehen und benötigt eine neue Entscheidung.

## Folgen

Releases und ihre selbst hochgeladenen Installationsdateien sind öffentlich erreichbar. GitHub stellt zusätzlich bei jedem Release automatisch ZIP- und Tarball-Archive des Quellcodes am Tag bereit. Diese Archive sind keine Actions-Artefakte und gehören zum öffentlichen Repository-Modell.

Die öffentliche Sichtbarkeit verschärft die Pflicht, ausschließlich synthetische Daten zu verwenden und Geheimnisse vor jedem Push auszuschließen. Eine spätere Rückkehr zu privatem Quellcode oder eine getrennte Website wäre eine neue Architekturentscheidung.

Ohne Actions-Artefakte muss der Release-Workflow Pakete in einem zusammenhängenden freigegebenen Lauf bauen, prüfen und direkt an den Release-Datensatz übertragen. Fehlgeschlagene oder nicht freigegebene Zwischenstände werden nicht aufbewahrt.

## Verifikation

- Repository-Policy-Check weist Workflow-Artefakt-Actions zurück.
- Secret-Scan läuft bei Pull Requests und Änderungen an `main` mit deaktiviertem SARIF-Artefakt-Upload.
- Branch-Regeln verlangen Pull Request und grüne Checks.
- Release-Checkliste enthält alle verpflichtenden Notes-Abschnitte.
- Repository und Releases sind öffentlich, solange kein ersetzendes ADR angenommen ist.

## Referenzen

- [Release-Regeln](../RELEASING.md)
- [GitHub-Einstellungen](../runbooks/github-settings.md)
- [Gitleaks Action](https://github.com/gitleaks/gitleaks-action)
