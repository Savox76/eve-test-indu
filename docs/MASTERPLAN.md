# Masterplan – New Eden Foundry

**Fassung:** 4.0 (lebendes Repository-Dokument)

**Stand:** 19. September 2026

**Status:** Paket 42 – gruppierte Asset-Änderungen und historische Standortpfade technisch abgeschlossen

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
- **Mehrcharakterfähig:** jeder Charakter bleibt technisch und fachlich getrennt; Einzelansichten und eine nachvollziehbare Gesamtübersicht entstehen aus derselben Datenbasis.

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
- Datenbank und Backups liegen sichtbar unter `data` im Programmordner. Ein nicht beschreibbarer Ordner ist ein Startfehler; es gibt keinen versteckten Ausweichpfad.
- Die UI startet aus dem Cache und zeigt Start-, Offline-, veraltete und fehlerhafte Zustände ausdrücklich.
- Der gewählte Updatekanal wird lokal gespeichert. Ein öffentlicher GitHub-Release-Abruf informiert über ein vollständig veröffentlichtes neueres Paket und zeigt die passende Installer- oder Portable-Anleitung. Download und Installation bleiben bis zur produktiv signierten Updatekette deaktiviert; das signierte Offline-Testmanifest bleibt als Kryptografie-Gate erhalten.
- Die globale Schriftgröße ist in fünf Stufen wählbar und wird als nicht geheime Einstellung in derselben Datenbank im Programmordner gespeichert.
- Updates und Deinstallation ersetzen beziehungsweise entfernen Programmdateien, lassen `data` jedoch stehen. Das Entfernen eines Charakters und eine spätere vollständige Datenlöschung bleiben davon getrennte, bewusste Vorgänge.
- Linux und macOS erhalten erst nach Windows eigene Freigabe-Gates.

## 5. Zielarchitektur

| Bereich | Entscheidung |
|---|---|
| Desktop-Schale | Tauri 2 / Rust |
| Oberfläche | React / TypeScript, DE/EN-i18n |
| Lokaler Dienst | Python / FastAPI als gebündelter Sidecar |
| Persistenz | `data\foundry.sqlite3` im Programmordner; SQLite mit Foreign Keys, WAL, `busy_timeout`, Migrationen und Backups |
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

Die automatisierten Komponenten- und Paketprüfungen decken Sidecar-Build, Handshake, Tokenpflicht, Datenbankort, Integrität, Migrationssicherung, Wiederherstellung und Shutdown ab. Installation, zweiter Fensterstart, Update und Entfernung bleiben bis zur manuellen Abnahme auf einem freigegebenen Windows-Testgerät offene Teile dieses Gates.

Scheitert dieser Durchstich, wird die Sidecar-Entscheidung vor weiterem Fachcode neu bewertet.

## 6. SSO- und Datenschutzgrenze

- Desktop-Anmeldung nutzt PKCE mit `S256`; es wird kein Client Secret ausgeliefert.
- Anmeldung erfolgt im Systembrowser direkt bei EVE.
- Ein fester, im EVE Developers Portal registrierter Loopback-Callback ist vom dynamischen internen API-Port getrennt.
- `state`, Callback-Timeout und Abbruch werden geprüft.
- Access Tokens werden anhand der veröffentlichten Metadaten und JWKS validiert.
- Refresh-Token-Rotation gilt erst nach erfolgreicher atomarer Ablage im Schlüsselbund als abgeschlossen.
- Jede Charakteranmeldung fordert automatisch den vollständigen aktuell benötigten Scope-Satz an. Scope-Drift nach einem Update wird sichtbar und führt über eine geführte erneute Anmeldung zur idempotenten Autorisierung desselben Charakters.
- Jeder Charakter wird separat autorisiert. Frei benannte lokale Kontogruppen ordnen Charaktere mehreren gewünschten Accountstrukturen zu, ohne EVE-Accountnamen oder Zugangsdaten zu speichern.
- Die Gesamtübersicht aggregiert alle aktiv verbundenen Charaktere; jede Einzelübersicht erhält Datenalter, Scope- und Fehlerstatus des gewählten Charakters.
- Die exakte Callback-URI, öffentliche Client-ID, Scopepakete und der Entwicklerkontakt werden vor SSO-Implementierung dokumentiert.

## 7. Daten und Synchronisierung

SQLite unter `<Programmordner>\data\foundry.sqlite3` ist die lokale fachliche Quelle. Vor jeder ausstehenden Schemaänderung erzeugt die Anwendung über die SQLite-Backup-API einen konsistenten Snapshot unter `data\backups`, prüft Integrität, Fremdschlüssel, Schema und SHA-256 und bewahrt die fünf neuesten Migrationssicherungen auf. Eine fehlgeschlagene Sicherung verhindert die Migration; eine fehlgeschlagene Migration oder Abschlussprüfung stellt den geprüften Ausgangsstand automatisch wieder her. Jeder Synchronisierungslauf besitzt Start, Ende, Status, Datenquelle, Datenstand und – soweit eigentümerbezogen – eine Charakter-ID. Nur vollständig erfolgreiche Läufe dürfen einen konsistenten Snapshot als aktuell markieren oder Deltas erzeugen. Der Startpfad unterscheidet anhand des lokal gespeicherten Ablaufzeitpunkts Laden, Aktualisieren, leer, aktuell, veraltet, offline und fehlerhaft; fehlgeschlagene Folgeläufe löschen keinen vollständigen Snapshot. Gemeinsame Auswertungen behalten die Einzelbeiträge und ihre Datenalterung nachvollziehbar bei.

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

`Savox76/eve-test-indu` ist das einzige öffentliche Repository für Quellcode, Dokumentation, Issues, Pull Requests, GitHub Actions und Releases. Die frühere Annahme getrennter Source-, Release- und Website-Repositories ist aufgehoben; [ADR-005](adr/0005-central-public-repository-and-releases.md) dokumentiert die Entscheidung.

- Arbeit erfolgt auf kurzen Feature-Branches und über Pull Requests.
- `main` soll vor Direktänderung, Löschung und Force Push geschützt sein.
- Pflichtchecks müssen vor dem Merge vollständig grün sein.
- GitHub Actions speichert **keine** Workflow-Artefakte; `upload-artifact` und `download-artifact` sind untersagt.
- Build-Ausgaben bleiben innerhalb eines Workflows flüchtig.
- Jedes Windows-Release stellt sowohl einen Installer als auch eine portable ZIP mit jeweils eigener SHA-256-Prüfsumme bereit.
- Freigegebene Installer, portable Pakete, Prüfsummen, Signaturen und Update-Manifeste dürfen ausschließlich direkt an das zugehörige GitHub Release angehängt werden.
- GitHub stellt bei jedem Release automatisch Quellcodearchive des zugehörigen Tags bereit; diese sind keine Actions-Artefakte.
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
| 23 | Blueprint-Bestand | BPO/BPC werden charaktergetrennt vollständig synchronisiert und mit Namen, ME/TE, Läufen, Besitzer, Ort, Alter, Suche, Filter und Sortierung angezeigt |
| 24 | Charakter-Jobs | persönliche Industrieaufträge werden vollständig synchronisiert, mit Blueprint- und Asset-Änderungen nachvollziehbar korreliert und nach Status dargestellt |
| 25 | Charakter-Skills | vollständige trainierte und aktive Skillstände werden charaktergetrennt synchronisiert und als Grundlage für spätere Machbarkeits- und Lückenprüfungen dargestellt |
| 26 | Anlagen- und Systemkostenbasis | öffentlicher NPC-Anlagenkatalog und Systemkostenindizes werden atomar synchronisiert; in persönlichen Jobs beobachtete Spielerstrukturen behalten nachvollziehbare Scope-/ACL-Zustände |
| 27 | Forschungsplanung | persistente ME-/TE-Ziele werden aus echten BPO-, Skill-, Job- und Anlagenständen mit belegbaren Zuständen und ohne unbelegte Zeit-/Kostenprognose dargestellt |
| 28 | Industrie-Slotübersicht | Fertigungs-, Reaktions- und Wissenschaftskapazitäten werden charaktergetrennt mit realer Belegung und Arbeitsvorrat in einer gemeinsamen Übersicht dargestellt |
| 29 | Blueprint-Aktivitätsbasis | Produkte, Materialien und Basiszeiten der für Fertigung und Reaktionen benötigten SDE-Blueprintaktivitäten werden build-versioniert und atomar importiert |
| 30 | Produktionsplanung | Persistente Fertigungs- und Reaktionsziele werden aus der Blueprint-Aktivitätsbasis deterministisch in Produktionsschritte und Bruttomaterialbedarf aufgelöst |
| 31 | Bestandsabgleich und Fehlmengen | Vollständige Asset-Snapshots werden nachvollziehbar auf äußere Bruttomaterialien angerechnet; verfügbare Mengen, ungedeckter Bedarf und bewusst ausgeschlossene Bestände bleiben charakter- und standortbezogen belegbar |
| 32 | Bestandsreservierungen | Bestände werden zielbezogen und konfliktfest reserviert; Priorität und eindeutige Regeln verhindern eine unbemerkte Doppelverwendung zwischen Produktionszielen |
| 33 | Blueprintzuordnung und ME-Materialbedarf | Ein Produktionsziel kann eine vorhandene persönliche Blueprintkopie nachvollziehbar zuordnen; deren ME-Wert verändert den Materialbedarf nach den belegten EVE-Rundungsregeln, während fehlende oder ungeeignete Kopien sichtbar bleiben |
| 34 | Blueprint-TE und Zeitbasis | Der TE-Wert des zugeordneten persönlichen Blueprints verändert die Zeitbasis des Wurzel-Fertigungsschritts mit exakter jobweiter Aufrundung; Basiszeit, Blueprint-Zeit und Ersparnis bleiben getrennt nachvollziehbar |
| 35 | Persönliche Charakter-Skillzeit | Aktive Industry-, Advanced-Industry- und Reactions-Level verändern jeden passenden Produktionsschritt aus einem vollständig belegten Skill-Snapshot |
| 36 | Blueprintzuordnung für Fertigungsketten | Jeder Fertigungsschritt kann ein persönliches BPO oder laufgeeignetes BPC eindeutig zuordnen; dessen ME/TE wirkt schrittgenau und berechnet die Kette neu |
| 37 | Anlagen- und Jobbelege für Produktionsketten | Jeder Produktionsschritt verbindet den stärksten passenden persönlichen Job mit dem vollständigen Anlagen-Snapshot; Anlage, Systemkostenindex und Quellenzustände bleiben sichtbar, ohne unbekannte Modifikatoren zu erfinden |
| 38 | Bestandsquellen und Produktionsorte | Vorprodukte können vollständig oder teilweise aus persönlichem Bestand stammen; Produktionsstation und echte, persönlich benannte Materialcontainer sind wählbar, updatefest und begrenzen Bestandsabgleich sowie Reservierungen ohne Schiffsladeräume nachvollziehbar |
| 39 | Explizite Anlagenprofile und Anlagenzeit | Ein bewusst gespeichertes, aktivitätsgebundenes Material-/Zeitprofil der gewählten Anlage wirkt mit ME/TE und Charakter-Skills vor genau einer Aufrundung; unbekannte Boni bleiben sichtbar unkonfiguriert statt geschätzt |
| 40 | Zielübergreifende Einkaufsliste und EVE-Multibuy | Die konfliktfreien Fehlmengen aller aktuell gefilterten Ziele werden typweise aggregiert, unvollständige Quellstände sichtbar ausgeschlossen und als direkt kopierbare EVE-Multibuy-Liste ausgegeben |
| 41 | Belegte Installationskostenbasis | Offizielle angepasste ESI-Preise, aktivitätsspezifischer Systemkostenindex und eine ausdrücklich gespeicherte Anlagensteuer ergeben je gebautem Schritt eine quellenbelegte Kostenbasis; fehlende Preise oder Belege bleiben sichtbar statt geschätzt |
| 42 | Gruppierte Asset-Änderungen und historische Standortpfade | Asset-Änderungen werden vor Pagination nach Besitzer, Typ und Snapshotvergleich gruppiert; aufklappbare Einzelereignisse zeigen die exakt historischen Standortpfade und behandeln rohe ESI-Bereichsflags nur als sekundären Nachweis |

### Aktueller Stand

- **In Arbeit:** 01 – ADR-Set und Repo-Schutz; der dokumentarische und technische Grundschutz steht, der Branchschutz auf GitHub ist noch offen.
- **Abgeschlossen:** 02 – Tauri, Frontend und der zielsystemspezifisch eingefrorene Python-Sidecar bauen in CI; alle Komponenten lesen ihre Produktversion aus `package.json`.
- **Vorbereitend umgesetzt:** 03 – die freigegebene Tauri-/React-Gestaltung verwendet weiterhin ausschließlich einen synthetischen UI-Datensatz.
- **Technisch umgesetzt, Windows-Abnahme offen:** 04–06 – Single Instance, gebündelter Sidecar, dynamischer Loopback-Port, 256-Bit-Sitzungstoken, Bereitschaftsprotokoll, Prozessüberwachung und Shutdown sind implementiert. Automatisierte Quell-, Frozen- und Pakettests sichern den Kern ab; das vollständige installierte Windows-Laufzeitgate bleibt offen.
- **Abgeschlossen:** 07 – die SQLite-Grundlage aktiviert und prüft Foreign Keys, WAL und `busy_timeout`, wendet eine versionierte Basismigration an und führt automatisierte Integritäts- sowie Parallelzugriffstests aus.
- **Abgeschlossen:** 08 – ausstehende Migrationen erzeugen zuerst einen konsistenten, eigenständigen und SHA-256-geprüften Snapshot unter `data\backups`. Sicherungsfehler lassen das Schema unverändert; Migrationsfehler lösen eine geprüfte automatische Wiederherstellung aus. Die fünf neuesten Snapshots bleiben erhalten.
- **Abgeschlossen:** 09 – der lokale Startpfad bewertet nur Snapshots vollständig abgeschlossener Läufe und zeigt Laden, Aktualisieren, leer, aktuell, veraltet, offline und fehlerhaft zweisprachig mit Datenalter. Vorhandene Cache-Daten bleiben bei Ablauf oder Folgfehlern sichtbar; echte Nutzdaten folgen mit ESI.
- **Abgeschlossen:** 10 – die Desktop-Oberfläche kann `stable`, `beta` und `preview` wählen und speichert die Präferenz in Schema 5. Ein gebündeltes Ed25519-signiertes Testmanifest wird streng und offline geprüft. Seit ADR-017 fragt ein getrennter Hinweisweg die öffentliche GitHub-Release-Liste ab, berücksichtigt nur vollständige Releases und öffnet ausschließlich die fest abgeleitete Release-Seite; Download und Installation bleiben deaktiviert.
- **Abgeschlossen:** 11 – Callback-URI, öffentliche Client-ID, Entwicklerkontakt und funktionsbezogene Scopepakete sind im EVE Developers Portal registriert, verbindlich dokumentiert, maschinenlesbar hinterlegt, im Sidecar-Paket enthalten und gegen Drift getestet.
- **Abgeschlossen:** 12 – die Desktop-App startet EVE SSO im Systembrowser, erzeugt je Versuch unabhängigen kryptografischen `state` und PKCE-Verifier mit `S256`, prüft den Rückruf am festen Callback und beendet Listener und Geheimnisse bei Fehler, Drei-Minuten-Timeout, Abbruch oder App-Ende. Jeder Charakter wird einzeln autorisiert; seit ADR-015 wird dabei der vollständige aktuell benötigte Paketsatz automatisch angefordert.
- **Abgeschlossen:** 13 – der Sidecar tauscht den einmaligen Code ohne Client Secret per PKCE aus, bezieht Token- und JWKS-Endpunkte aus streng begrenzten EVE-Metadaten und prüft `RS256`-Signatur, Schlüssel-ID, Issuer, beide Audience-Werte, Ablauf, Charakter-Subject, Name und Scopes. Nur danach werden Identität und Scope-Status idempotent in SQLite gespeichert und in der echten Charakterliste angezeigt.
- **Abgeschlossen:** 14 – der ausschließlich nach erfolgreicher JWT-Prüfung erhaltene Refresh Token wird pro Charakter in einem verifizierten Zwei-Slot-Verfahren im Windows-Anmeldespeicher aktiviert. Der bisherige aktive Wert bleibt bei Schreibfehlern erhalten; unterbrochene und konkurrierende Rotationen werden ohne Tokenverlust behandelt. Access Tokens verbleiben nur im Sidecar-Speicher, Geheimnisse erreichen weder SQLite noch API-Antworten oder Logs, und nicht unterstützte Schlüsselbundumgebungen schlagen geschlossen fehl.
- **Abgeschlossen:** 15 – verbundene Charaktere lassen sich mit lokalem Alias, Aktivstatus und frei benannten Kontogruppen verwalten. Credential- und Scopepaket-Status werden charakterbezogen angezeigt. Der zweistufig bestätigte Löschablauf entfernt Identität, Scopes, Sync-Historie, Cache-Snapshots, Prozess-Token und Refresh Token; Credential-Fehler rollen die SQLite-Löschung zurück.
- **Abgeschlossen:** 16 – `EsiClient` bildet die einzige HTTP-Vertrauensgrenze für ESI. Er erzwingt festen Host, Compatibility-Date, User-Agent und charaktergetrennte Autorisierung, verarbeitet Cacheheader und bedingte 304-Antworten, begrenzt JSON und Wiederholungen und kapselt Retry-After, ESI-Fehlerbudget sowie Circuit Breaker. Der authentifizierte Sidecar-Status macht diese Policy ohne Zugangsdaten sichtbar.
- **Abgeschlossen:** 17 – der minimale SDE-Bestand für Typen, Gruppen und Orte wird als abgeleitete Datenbasis atomar aufgebaut und über eine eindeutige Buildnummer identifiziert. Ein fehlerhafter Import lässt den vorherigen gültigen Stand unangetastet und verändert das Anwendungsschema nicht.
- **Abgeschlossen:** 18 – aktivierte Charaktere können Assets über den zentralen ESI-Client vollständig paginiert synchronisieren. Jeder Charakter erhält einen eigenen Lauf und Snapshot; nur vollständige Läufe werden veröffentlicht, während Abbruch und Fehler den letzten gültigen Cache erhalten.
- **Abgeschlossen:** 19 – der letzte vollständige Asset-Snapshot jedes Charakters wird in root-first Standort- und Containerpfade aufgelöst. SDE-Standorte und Typnamen werden lokal genutzt, Stationen und erlaubte Spielerstrukturen über den zentralen ESI-Client ergänzt. Struktur-403 und fehlende Scopes bleiben als eingeschränkte Fachzustände sichtbar; fehlende Container und Zyklen erhalten stabile Fehlercodes. Nur vollständig verarbeitete Läufe veröffentlichen einen neuen Standort-Snapshot.
- **Abgeschlossen:** 20 – die zweisprachige Asset-Oberfläche liest ausschließlich die letzten vollständigen charaktergetrennten Snapshots. Standardmäßig gruppiert sie gleiche Typen zu einer Bestandsübersicht mit Mengen-, Besitzer- und Standortverteilung; ein Drill-down öffnet die passenden Einzelpositionen. Suche sowie Besitzer- und Standortstatusfilter laufen serverseitig; höchstens 100 Zeilen werden gleichzeitig übertragen und gerendert. Ein synthetischer 100.000-Zeilen-Test sichert den begrenzten Transport. Der gefilterte CSV-Export schreibt atomar und formelneutralisiert unter `data\exports`.
- **Abgeschlossen:** 21 – jeder vollständige Charakter-Asset-Sync veröffentlicht atomar eine Baseline oder ein Delta zum vorherigen vollständigen Snapshot. Hinzufügungen, Entfernungen, Mengen- und Standortänderungen tragen deterministische Fingerabdrücke, Snapshot-/Run-IDs und ein Beobachtungsfenster. Die zweisprachige Historie ist serverseitig such- und filterbar und überträgt höchstens 50 Ereignisse pro Seite. Charakter-/Typ-Schlüssel, Richtung und Mengendifferenz bereiten die spätere Jobkorrelation vor, ohne bereits unbelegte Zuordnungen zu behaupten.
- **Zusätzlich umgesetzt:** Die vollständige sichtbare Oberfläche unterstützt fünf globale Schriftgrößenstufen; die Auswahl bleibt in der bestehenden `app_settings`-Tabelle am updatefesten Datenort erhalten.
- **Abgeschlossen:** 22 – Das vollständige Windows-A0-Protokoll für `v0.0.5-preview.28` bestätigt auf einem realen Windows-x64-Gerät Installation ohne Administratorrechte und Konsolenfenster, Einzelinstanz, Kern- und Datenbankbereitschaft, persistente Einstellungen und Fenstergröße, Update und Datenerhalt, Sidecar-Wiederherstellung, sauberes Beenden, Portable-Ausgabe und Deinstallation. Die vollständig grünen Pflichtprüfungen sichern zusätzlich Paketstruktur, Microsoft-Defender-Scan, Migration, Neustart, Rust-Verträge und Geheimnissuche. Der geprüfte Stand wird als `v0.2.0-alpha.1` freigegeben.
- **Abgeschlossen:** 23 – vollständige persönliche, charaktergetrennte Blueprint-Snapshots werden automatisch und manuell aktualisiert. Die BPO/BPC-Ansicht bietet Namen, ME/TE, Läufe, Besitzer, Bereich, Datenalter, Suche, Filter und einen Status je Charakter, der verfügbare und fehlende Snapshots unterscheidet. Corporation-Blueprints sind ausdrücklich nicht enthalten. Unvollständige Läufe überschreiben keinen gültigen Bestand.
- **Abgeschlossen:** 24 – persönliche Industrieaufträge werden vollständig und charaktergetrennt synchronisiert. Die zweisprachige Ansicht unterscheidet laufende, abholbereite und bereits abgeholte Jobs; laufende Jobs zeigen eine automatisch aktualisierte Restzeit. Exakte Blueprint-Item-IDs und passende eingehende Asset-Änderungen werden mit aktuellen oder historischen Belegen korreliert; Mehrdeutigkeit und fehlende Quellen bleiben sichtbar.
- **Abgeschlossen:** 25 – vollständige charaktergetrennte Skill-Snapshots zeigen echte Namen, trainiertes und aktuell wirksames Level, Skillpunkte, Besitzer, Datenalter und stabile Quell-IDs. Suche, Besitzer-, Level- und Aktivzustandsfilter sowie Sortierung und begrenzte Seiten laufen im lokalen Sidecar. Fehlgeschlagene oder ungültige Abrufe lassen den letzten vollständigen Stand unverändert.
- **Abgeschlossen:** 26 – der öffentliche NPC-Anlagenkatalog, aktivitätsspezifische Systemkostenindizes und ihre offiziellen Namen werden in einem vollständigen globalen Snapshot veröffentlicht. Der offizielle SDE-Sicherheitsstatus ordnet belegte Systeme in Highsec, Lowsec oder Nullsec ein und ist filterbar. Tatsächlich in persönlichen Jobs beobachtete Spielerstrukturen werden charakterbezogen mit verfügbarem, fehlendem Scope, ACL-403 oder unbekanntem Zustand ergänzt.
- **Abgeschlossen:** 27 – persistente, charakter- und BPO-genaue ME-/TE-Pläne verbinden aktuelle Blueprintstände, wirksame Forschungs-Skills, persönliche Jobs und Anlagenbelege. Die Ansicht zeigt Ziele, Priorität, Notiz, Wissenschaftskapazität und belastbare Zustände; fehlende Quellen bleiben ungeprüft und Dauer oder Gesamtkosten werden ohne vollständige SDE- und Modifikatorbasis nicht geschätzt. Schema 8 bewahrt Pläne auch dann, wenn ein BPO im aktuellen Snapshot fehlt.
- **Abgeschlossen:** 28 – eine gemeinsame, begrenzte Übersicht stellt pro Charakter Fertigungs-, Reaktions- und Wissenschaftskapazität aus aktuell wirksamen Skills der realen Belegung durch aktive, pausierte und abholbereite Jobs gegenüber. Forschungspläne und seit Paket 30 Produktionsziele ergänzen den belegbaren Arbeitsvorrat; fehlende Skill- oder Job-Snapshots bleiben unabhängig voneinander unbekannt. Die Ansicht führt Datenalter und stabile Quellen-IDs.
- **Abgeschlossen:** 29 – Gruppen, Typen, Orte und die Fertigungs-/Reaktionsaktivitäten der Blueprintbasis werden unter derselben SDE-Buildnummer atomar ersetzt. Strikte Validierung sichert Blueprint-, Produkt- und Materialreferenzen, positive Basiswerte und vollständige Rezepte; ein Fehler lässt sämtliche Tabellen und den letzten Aktivitäts-Buildmarker unverändert. Eine authentifizierte, nach Blueprint, Produkt und Aktivität filterbare Abfrage überträgt höchstens 200 vollständige Aktivitäten und weist die verwendete Buildnummer aus. Seit `v0.0.5-preview.14` wird der aus dem offiziellen, prüfsummengebundenen EVE-SDE-Build abgeleitete Bestand automatisch mitgeliefert und beim ersten Start atomar installiert. Die abgeleiteten Tabellen verändern das Anwendungsschema nicht.
- **Abgeschlossen:** 30 – persistente Fertigungs- und Reaktionsziele werden aus dem exakten Wurzelrezept und einer stabilen Zwischenprodukt-Auswahl deterministisch aufgelöst. Gemeinsamer Bedarf wird vor ganzzahliger Laufberechnung aggregiert; die sichtbare Herstellungsreihenfolge beginnt mit den tiefsten Vorprodukten und endet mit dem gewählten Zielprodukt. Schritte, Überschuss, SDE-Basiszeit, äußeres Bruttomaterial, Alternativen, Zyklen und fehlende SDE-Stände bleiben nachvollziehbar. Schema 9 speichert Zielmenge, Priorität und Notiz updatefest.
- **Abgeschlossen:** 31 – der letzte vollständig abgeschlossene Asset-Snapshot des ausführenden Charakters wird je äußerem Bruttomaterial angerechnet. Bedarf, verfügbarer Bestand und echte Fehlmenge bleiben mit Snapshot-, Sync-, Zeit-, Standort- und Bereichsbelegen nachvollziehbar; ein fehlender Snapshot bleibt unbekannt. Bestände anderer aktivierter Charaktere werden separat als bewusst ausgeschlossen ausgewiesen. Standortdetails sind pro Material und Kategorie auf 50 Gruppen begrenzt, während vollständige Mengen-, Positions- und Gruppensummen erhalten bleiben. Reservierungen und Modifikatoren werden nicht vorweggenommen.
- **Abgeschlossen:** 32 – der bekannte persönliche Bestand wird je Charakter und Material über alle auflösbaren Ziele konfliktfrei reserviert. Die stabile Reihenfolge ist höhere Priorität, älteres Erstellungsdatum und kleinere Ziel-ID. Jedes Ziel zeigt physischen Bestand, vorrangig reservierte Menge, eigene Reservierung, danach freien Bestand sowie getrennte physische und reservierungsbedingte Fehlmengen. Suche, Filter, Sortierung und Seitenauswahl verändern die globale Reservierung nicht; ein neuer Snapshot oder eine Zieländerung berechnet sie unmittelbar neu. Das Schema bleibt bei Version 9.
- **Abgeschlossen:** 33 – Produktionsziele können genau ein vorhandenes persönliches BPO oder BPC zuordnen. Der belegte ME-Wert verändert ausschließlich direkte Materialien des Wurzel-Fertigungsschritts mit ganzzahliger Aufrundung und einer Einheit Mindestbedarf je Material und Lauf; daraus veränderte Zwischenproduktläufe werden erneut deterministisch aufgelöst. Unmodifizierter Bedarf und Ersparnis bleiben parallel sichtbar. Fehlende Snapshots, verschwundene oder typfalsche Items und zu wenige BPC-Läufe bleiben nachvollziehbare Zustände. Schema 10 speichert die eindeutige optionale Item-ID.
- **Abgeschlossen:** 34 – Der belegte TE-Wert des zugeordneten persönlichen BPO oder BPC verändert ausschließlich die Blueprint-Zeit des Wurzel-Fertigungsschritts. Die Berechnung erfolgt jobweit mit exakter Ganzzahlarithmetik und Aufrundung auf volle Sekunden; SDE-Basiszeit, Blueprint-Zeit und Ersparnis bleiben je Schritt und als Summe parallel sichtbar. Reaktionen und automatisch ausgewählte Zwischen-Blueprints bleiben unverändert.
- **Abgeschlossen:** 35 – Der letzte vollständig abgeschlossene Skill-Snapshot des ausführenden Charakters liefert die aktuell wirksamen Stufen für Industry, Advanced Industry und Reactions. Fertigung wendet 4 % Industry und 3 % Advanced Industry je Stufe, Reaktionen 4 % Reactions je Stufe multiplikativ auf die ungerundete vollständige Jobzeit an; auf volle Sekunden wird erst am Ende aufgerundet. Jeder passende Schritt und die Gesamtsicht weisen Blueprint-Zeit, persönliche Skillzeit, Ersparnis, Skillwerte sowie Snapshot-, Lauf- und Zeitbeleg aus. Fehlt ein vollständiger Skill-Snapshot, bleibt die persönliche Zeit ausdrücklich unbekannt; fehlgeschlagene neuere Läufe verdrängen keinen gültigen Stand.
- **Abgeschlossen:** 36 – Jeder Fertigungs-Vorproduktschritt eines Produktionsziels kann ein persönliches BPO oder laufgeeignetes BPC aus dem letzten vollständigen Blueprint-Snapshot des ausführenden Charakters zuordnen. ME und TE wirken ausschließlich auf das exakte zugehörige Rezept; geänderte Zwischenbedarfe, Laufzahlen, Zeiten, Bruttomaterialien, Reservierungen und Fehlmengen werden deterministisch neu berechnet. Jede physische Item-ID bleibt innerhalb eines Ziels und zielübergreifend eindeutig. Schema 11 speichert die Zuordnungen updatefest und löscht sie mit dem Ziel.
- **Abgeschlossen:** 37 – Jeder aufgelöste Produktionsschritt erhält den stärksten passenden Anlagenbeleg aus dem letzten vollständigen persönlichen Job-Snapshot des ausführenden Charakters und dem letzten vollständigen globalen Anlagen-Snapshot. Ein Job mit exakt zugeordnetem Blueprint-Item hat Vorrang vor einem aktiven und danach vor dem jüngsten typgleichen Job. Anlage, Zugriffsstatus, Sonnensystem, Sicherheitsraum, aktivitätsspezifischer Systemkostenindex sowie beide Quellenstände bleiben sichtbar; fehlende und nicht auflösbare Belege werden nicht ersetzt oder geschätzt. Das Schema bleibt bei Version 11.
- **Abgeschlossen:** 38 – Jedes produzierbare Vorprodukt kann updatefest als `Bestand zuerst`, `Nur Bestand` oder `Vollständig bauen` geplant werden. Vorhandene T1- und andere Zwischenprodukte verkürzen dadurch die rekursive Fertigungskette; `Nur Bestand` erzeugt keinen Produktionsschritt und benötigt keinen Blueprint, weist aber eine mögliche Restfehlmenge aus. Eine gewählte persönliche Station oder Struktur und optional deren direkter Hangar beziehungsweise ein echter Lagercontainer begrenzen Bestandsabgleich und konfliktfreie Reservierungen exakt auf diese Quelle. Der tatsächliche EVE-Containername und die eindeutige Item-ID werden angezeigt; Schiffe und deren Laderäume werden an einer gewählten Anlage weder als Container angeboten noch als Produktionsbestand angerechnet. Ohne Auswahl bleibt das bisherige Verhalten über alle persönlichen Lagerorte erhalten. Schema 12 speichert Anlagen-, Lager- und Versorgungswahl updatefest.
- **Abgeschlossen:** 39 – Eine gewählte Produktionsanlage kann ein bewusst eingegebenes Material- und Zeitprofil in Hundertstelprozent erhalten. Der Materialfaktor wird mit dem schrittgenauen Blueprint-ME, der Zeitfaktor mit Blueprint-TE und aktiven Charakter-Skills multipliziert; erst danach wird je Material beziehungsweise Job einmal ganzzahlig aufgerundet. Das Profil gilt nur für Schritte derselben Aktivität, zeigt abweichende Aktivitäten ausdrücklich und wird niemals aus ESI, Jobs oder Strukturtypen geraten. Bestehende Ziele bleiben nach Schema-13-Migration unverändert und zeigen das Profil als nicht konfiguriert. Anlagenzeit und zusätzliche Ersparnis bleiben je Schritt und als belegbare Summe sichtbar.
- **Abgeschlossen:** 40 – Die Produktionsabfrage aggregiert nach Anwendung von Suche, Besitzer-, Aktivitäts- und Statusfilter alle bereits konfliktfrei berechneten Fehlmengen stabil nach Typ-ID. Physische Fehlmenge und durch vorrangige Ziele gebundene Menge bleiben getrennt; die Oberfläche zeigt Materialarten, Gesamtmenge und beteiligte Ziele und kopiert den vollständigen belegten Ausschnitt im EVE-Multibuy-Format. Ziele ohne auflösbares Rezept oder vollständigen Asset-Snapshot werden gezählt und ausdrücklich als nicht enthalten markiert. Sortierung und Seitenauswahl verändern die Einkaufsliste nicht. Das Schema bleibt bei Version 13.
- **Abgeschlossen:** 41 – Der vollständige Anlagen-Snapshot enthält zusätzlich die offiziellen angepassten Preise aus ESI. Für jeden tatsächlich gebauten Schritt wird der geschätzte Eingabewert aus unveränderten SDE-Basismaterialmengen und Läufen gebildet; Systemkostenindex und ausdrücklich gespeicherte Anlagensteuer werden getrennt aufgerundet und samt Preis-, Anlagen- und Systembeleg ausgewiesen. Zielebene und Oberfläche aggregieren ausschließlich berechenbare Schritte und unterscheiden `ready`, `partial`, `unconfigured`, `unavailable` und `not-applicable`. Schema 14 ergänzt die optionale Anlagensteuer in Basispunkten; bestehende Ziele bleiben bewusst unkonfiguriert.
- **Abgeschlossen:** 42 – Der Asset-Änderungsverlauf gruppiert standardmäßig alle gefilterten Ereignisse vor der Seitenteilung nach Besitzer, Typ und Snapshotvergleich. Gruppen weisen betroffene Items, Ereignisse, Mengen, Standorte und Jobkorrelationszustände aus und laden ihre exakt gefilterten Einzelereignisse begrenzt nach. Die historischen, zum jeweiligen Asset-Snapshot gehörenden vollständigen Standortpfade werden als Hauptangabe gezeigt; Location-ID und das rohe ESI-Flag wie `AutoFit` bleiben sekundäre Belege. Ein Umschalter erhält die ungegruppte Ereignisansicht. Das Schema bleibt bei Version 14.
- **Als Nächstes:** Das nächste Fachpaket wird separat festgelegt. Marktpreise, Handelsort, SCC-Zuschlag, automatisch erkannte Struktur-/Service-/Rigmodifikatoren, Transport und belastbare Endtermine bleiben bis zu eigenen Fachverträgen ausgeschlossen.
- Architektur-Gate A0 ist vollständig erfüllt; `v0.2.0-alpha.1` bildet die erste freigegebene Alpha-Grundlage für die folgenden Produktionspakete.

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
