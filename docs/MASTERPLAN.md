# Masterplan – New Eden Foundry

**Fassung:** 1.1 (lebendes Repository-Dokument)

**Stand:** 7. September 2026

**Status:** In Umsetzung – Phase 0

**Geltungsbereich:** `Savox76/eve-test-indu`

Dieses Dokument ist die laufend gepflegte Projektgrundlage. Architekturänderungen benötigen ein ADR. Änderungen an Funktionsumfang oder Reihenfolge werden hier, in den Abnahmekriterien und im Backlog gemeinsam nachvollzogen.

## 1. Zielbild

New Eden Foundry ist eine lokale Desktop-Anwendung für EVE-Online-Industrieplanung. Sie soll verstreute Daten in einen belastbaren Ablauf verwandeln:

**Bestand verstehen → Bedarf planen → Optionen vergleichen → Einkauf oder Bau vorbereiten → Fortschritt prüfen.**

Jede wirtschaftliche Berechnung nennt ihre Eingaben und ihren Datenstand. Bekannte Cache-Daten bleiben bei einem Fremdsystemausfall sichtbar und werden eindeutig als veraltet markiert.

## 2. Produktprinzipien

- **Local-first:** eine Person, eine Installation, lokale Datenbank; kein eigener Cloud-Dienst ist Voraussetzung.
- **Nachvollziehbar:** Preisprofil, Blueprint, ME/TE, Struktur, Charakterwerte, Bestand und Rundung sind sichtbar.
- **Sicher:** PKCE statt ausgeliefertem Client Secret, minimale Scopes, Betriebssystem-Schlüsselbund und redigierte Logs.
- **Robust:** cache-first, explizite Datenalterung und kontrollierte Wiederholung bei ESI-Ausfällen.
- **Handlungsnah:** Ergebnisse führen zu Einkaufslisten, Bauketten und Projektfortschritt.
- **Testbar:** synthetische Fixtures und Golden-Fälle sind die einzige Basis für Tests, Dokumentation und Screenshots.
- **Zweisprachig vorbereitet:** sichtbare Texte werden von Beginn an aus deutschen und englischen Katalogen geladen.

## 3. Umfang bis 1.0

Geplant sind:

1. Übersicht und Status
2. Assets und Standortauflösung
3. Blueprints, Forschung und Jobs
4. Produktion und Reaktionen
5. T2-Kopieren und Invention
6. Markt, Preisprofile und Scanner
7. Projekte, Fittings und Doktrinen
8. Planetary Industry

EVE Mail, Discord-Integration, Buyback-Automatisierung, T3 und Mehrbenutzerbetrieb sind nicht Teil des 1.0-Kerns. Sie benötigen später einen belegten Nutzen, eine Scope-Prüfung und gegebenenfalls ein neues ADR.

## 4. Betriebsmodell

- Windows ist die erste freigegebene Plattform.
- Eine zweite gestartete Instanz fokussiert die vorhandene Instanz und startet keinen zweiten Sidecar.
- Die UI startet aus dem Cache und zeigt Start-, Offline-, veraltete und fehlerhafte Zustände ausdrücklich.
- Deinstallation und Entfernen eines Charakters haben klar getrennte Regeln für Daten, Backups und Schlüsselbund-Einträge.
- Linux und macOS erhalten erst nach Windows eigene Freigabe-Gates.

## 5. Zielarchitektur

| Bereich | Entscheidung |
|---|---|
| Desktop-Schale | Tauri 2 / Rust |
| Oberfläche | React / TypeScript, DE/EN-i18n |
| Lokaler Dienst | Python / FastAPI als gebündelter Sidecar |
| Persistenz | SQLite mit Foreign Keys, WAL, `busy_timeout`, Migrationen und Backups |
| Lokale Kommunikation | ausschließlich Loopback, dynamischer interner Port, kurzlebiges Sitzungstoken |
| Anmeldung | EVE SSO, Authorization Code mit PKCE, Systembrowser |
| Tokenablage | Betriebssystem-Schlüsselbund |
| Fremddaten | ESI und SDE hinter zentralen Adaptern und Cache-Regeln |

Redis, PostgreSQL, Docker oder ein separat zu betreibender Server gehören nicht zum Endnutzerbetrieb.

### Architektur-Gate A0

Vor breiter Fachentwicklung muss ein vertikaler Windows-Prototyp beweisen:

- Tauri startet, überwacht und beendet den Sidecar zuverlässig.
- Der Sidecar bindet nur an Loopback und meldet einen vom Betriebssystem gewählten Port.
- Jede lokale Anfrage benötigt ein pro Start neu erzeugtes Sitzungstoken.
- UI-Lesezugriff und Hintergrund-Sync arbeiten kontrolliert parallel auf SQLite.
- Ein erzeugtes Windows-Paket lässt sich installieren, starten und entfernen.

Scheitert dieser Durchstich, wird die Sidecar-Entscheidung vor weiterem Fachcode neu bewertet.

## 6. SSO- und Datenschutzgrenze

- Desktop-Anmeldung nutzt PKCE mit `S256`; es wird kein Client Secret ausgeliefert.
- Anmeldung erfolgt im Systembrowser direkt bei EVE.
- Ein fester, im EVE Developers Portal registrierter Loopback-Callback ist vom dynamischen internen API-Port getrennt.
- `state`, Callback-Timeout und Abbruch werden geprüft.
- Access Tokens werden anhand der veröffentlichten Metadaten und JWKS validiert.
- Refresh-Token-Rotation gilt erst nach erfolgreicher atomarer Ablage im Schlüsselbund als abgeschlossen.
- Scopes werden funktionsweise und so spät wie möglich angefordert.
- Die exakte Callback-URI, öffentliche Client-ID, Scopepakete und der Entwicklerkontakt werden vor SSO-Implementierung dokumentiert.

## 7. Daten und Synchronisierung

SQLite ist die lokale fachliche Quelle. Jeder Lauf besitzt Start, Ende, Status, Datenquelle und Datenstand. Nur vollständig erfolgreiche Läufe dürfen einen konsistenten Snapshot als aktuell markieren oder Deltas erzeugen.

Der ESI-Client kapselt mindestens Compatibility-Date, User-Agent, Pagination, ETag/Expires, Fehlerbudget, `Retry-After`, Backoff und Circuit Breaker. Veraltete Daten werden nicht stillschweigend durch leere Ergebnisse ersetzt.

Der SDE-Import ist versioniert und atomar. Typen, Gruppen, Kategorien, Blueprints und benötigte Orte werden anhand der importierten Buildnummer reproduzierbar ausgewertet.

## 8. Berechnungsregeln

- Geld, Mengen, Wahrscheinlichkeiten und Zwischenwerte verwenden `Decimal`, nicht binäre Fließkommawerte.
- Runden erfolgt nur an fachlich definierten Grenzen.
- Blueprint-, Jobkosten-, Invention-, Reaktions- und PI-Formeln besitzen benannte Golden-Fälle.
- Build-vs-Buy zeigt beide Alternativen, Quellen, Gebühren, Transportannahmen, Zeit und Unsicherheit.
- Bestand wird nur nach expliziten Regeln einbezogen und reserviert; Doppelverwendung muss verhindert werden.
- Ergebnisse tragen einen Fingerabdruck ihrer Eingaben, damit sie reproduzierbar und als veraltet erkennbar bleiben.

## 9. Repository- und Releasevertrag

`Savox76/eve-test-indu` ist das einzige private Repository für Quellcode, Dokumentation, Issues, Pull Requests, GitHub Actions und Releases. Die frühere Annahme getrennter Source-, Release- und Website-Repositories ist aufgehoben; [ADR-005](adr/0005-central-private-repository-and-releases.md) dokumentiert die Entscheidung.

- Arbeit erfolgt auf kurzen Feature-Branches und über Pull Requests.
- `main` soll vor Direktänderung, Löschung und Force Push geschützt sein.
- Pflichtchecks müssen vor dem Merge vollständig grün sein.
- GitHub Actions speichert **keine** Workflow-Artefakte; `upload-artifact` und `download-artifact` sind untersagt.
- Build-Ausgaben bleiben innerhalb eines Workflows flüchtig.
- Freigegebene Installer, Signaturen und Update-Manifeste dürfen ausschließlich direkt an das zugehörige GitHub Release angehängt werden.
- Jedes Release beschreibt: neu hinzugefügt, geändert, behobene Fehler, bekannte Einschränkungen sowie Update und Datenbankmigration.
- Ein Release entsteht nur aus einem bewusst freigegebenen Tag nach vollständig grünen Pflichtprüfungen.

Die Einzelheiten stehen in [RELEASING.md](RELEASING.md).

## 10. Definition of Done

Eine Änderung ist fertig, wenn:

- fachliche Kriterien und relevante Grenzfälle umgesetzt sind,
- passende Tests vorhanden und alle Pflichtchecks grün sind,
- kein ungeklärter kritischer Sicherheitsfund und kein Blocker offen ist,
- Fehler-, Leer-, Lade-, Offline- und Datenalterzustände berücksichtigt sind,
- DE/EN-Kataloge vollständig sind,
- bei Entscheidungsänderungen ADR und Masterplan aktualisiert wurden,
- Nutzerhilfe und Änderungsprotokoll der sichtbaren Änderung entsprechen,
- der Pull Request geprüft wurde und erst dann nach `main` gelangt.

## 11. Roadmap

| Phase | Inhalt | Ergebnis |
|---|---|---|
| 0 – Entscheidungen | ADRs, Repository, synthetische Demo, CI-Grundschutz, registrierbare SSO-Parameter | freigegebene Architekturgrundlage |
| 1 – Vertikaler Kern | Tauri, Sidecar, Port/Token, SQLite, Migration, Single Instance, Installer | 0.1.0 interne Technik-Alpha |
| 2 – SSO & Charaktere | PKCE, Callback, JWT, Keyring, Rotation, Charakterverwaltung | 0.1.x |
| 3 – Sync & Assets | ESI-Client, Cache, Limits, SDE-Basis, Assets, Orte, Suche, Deltas | 0.2.0 Alpha |
| 4 – Blueprints & Jobs | BPO/BPC, ME/TE, Jobs, Skills, Anlagen, Forschung | 0.3.0 |
| 5 – Produktion | Solver, Bestand, Reservierung, Kosten, Zeit, Reaktionen, Multibuy | 0.4.0 Beta |
| 6 – T2-Invention | Kopieren, Datacores, Decryptoren, Wahrscheinlichkeit, BPC-Lager | 0.5.0 Beta |
| 7 – Markt | Jita-Adapter, Tiefe, Historie, Reichweite, Scanner, Fallback | 0.6.0 Beta |
| 8 – Projekte | Fittings, Doktrinen, Bauprojekte, Fortschritt und Reservierung | 0.7.0 Beta |
| 9 – PI | Kolonien, Timer, Lager, Versorgung, P0–P4, CPU/Powergrid | 0.8.0 Beta |
| 10 – Härtung | Performance, Barrierearmut, Updates, Migrationen, Windows-Gate | 1.0.0 Stable |

Die Reihenfolge ist verbindlicher als eine Kalenderangabe.

## 12. Konkretes Start-Backlog

| Nr. | Arbeitspaket | Fertig, wenn |
|---:|---|---|
| 01 | ADR-Set und Repo-Schutz | ADRs 001–008 liegen vor; `main` geschützt; Secret-Scan blockiert; synthetische Datenregel dokumentiert |
| 02 | Monorepo-Skelett | Tauri, Frontend und Backend bauen in CI; Versionen kommen aus einer Quelle |
| 03 | Demo-Datensatz | erfundene Charaktere, Assets, Container, Blueprints, Jobs und PI-Fälle sind einzige Screenshotquelle |
| 04 | Tauri-Fenster und Single Instance | zweiter Start fokussiert die erste Instanz und erzeugt keinen zweiten Sidecar |
| 05 | Sidecar-Build je Target | Windows-Sidecar wird gefunden, gestartet, überwacht und sauber beendet |
| 06 | Lokaler Handshake | dynamischer Port und Sitzungstoken schützen `/health`; Anfrage ohne Token wird abgewiesen |
| 07 | SQLite-Grundlage | Foreign Keys, WAL, `busy_timeout`, Basismigration und Integritätscheck automatisiert geprüft |
| 08 | Migration-Backup | Testmigration erzeugt eine konsistente Sicherung und kann wiederhergestellt werden |
| 09 | Startzustände | UI startet cache-first und zeigt Sidecar-, DB- und Offlinefehler verständlich |
| 10 | Updater-Skelett | Kanal wählbar; signiertes Testmanifest geprüft; noch keine öffentliche Verteilung |
| 11 | SSO-App-Registrierung | exakte Callback-URI, Client-ID, Scopes und Entwicklerkontakt dokumentiert |
| 12 | PKCE-Login | Systembrowser, `state`, Challenge/Verifier, Timeout und Abbruch getestet |
| 13 | JWT-Validierung | JWKS, Issuer, Audience, Ablauf und Charakter-ID geprüft |
| 14 | Keyring und Rotation | Refresh Token atomar gespeichert/ersetzt und nie geloggt |
| 15 | Charakterverwaltung | verbinden, Alias, deaktivieren, Scope-Status und vollständiges Löschen funktionieren |
| 16 | Zentraler ESI-Client | Compatibility-Date, User-Agent, Cacheheader, Retry, Budget und Circuit Breaker gekapselt |
| 17 | SDE-Minimalimport | Typen, Gruppen und Orte atomar importiert und über Buildnummer identifiziert |
| 18 | Asset-Sync | mehrere Charaktere, Pagination und abgebrochene Läufe korrekt behandelt |
| 19 | Standortauflösung | Containerpfad, Station, Struktur-403 und Zyklen bestehen synthetische Golden-Fälle |
| 20 | Asset-UI | Suche, Filter, Besitzer, Standort, Menge, Datenalter und CSV bei 100.000 Zeilen flüssig |
| 21 | Asset-Deltas | nur vollständige Läufe erzeugen nachvollziehbare Änderungen; Jobkorrelation vorbereitet |
| 22 | Erste Alpha-Freigabe | Phase-3-Gates grün; Installation und Update auf freigegebenem Windows-Testgerät bestanden |

### Aktueller Stand

- **In Arbeit:** 01 – ADR-Set und Repo-Schutz
- **Nicht begonnen:** 02–22
- Breite Fachentwicklung beginnt erst nach Freigabe der Phase-0-Grundlage und erfolgreichem Architektur-Gate A0.

## 13. Entscheidungs- und Quellenrang

Bei Widersprüchen gilt in dieser Reihenfolge:

1. geltendes Recht und Plattformregeln,
2. aktuelle offizielle EVE-/ESI-/SSO-Dokumentation,
3. aktuelle offizielle Framework- und Datenbankdokumentation,
4. angenommene Repository-ADRs und ausführbare Tests,
5. dieser Masterplan,
6. Community-Dienste und Vergleichswerkzeuge.

## 14. Pflege

- Architekturänderung: neues oder ersetzendes ADR plus Auswirkungsprüfung auf Roadmap und Gates.
- Scopeänderung: Umfang, Abnahmekriterien und Roadmap gemeinsam aktualisieren.
- API-/Compatibility-Anpassung: Code, Tests und ESI-Notizen aktualisieren; Masterplan nur bei verändertem Produktverhalten.
- Release: `CHANGELOG.md` und strukturierte GitHub Release Notes aktualisieren.
- Statusänderung: aktuelles Arbeitspaket und Datum in diesem Dokument fortschreiben.
