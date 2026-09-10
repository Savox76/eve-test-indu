# Änderungsprotokoll

Alle bemerkenswerten Änderungen an New Eden Foundry werden hier festgehalten. Die Überschriften entsprechen der verbindlichen Struktur der GitHub Release Notes.

## Unveröffentlicht

### Neu hinzugefügt

- Charakterbezogene Asset-Standortauflösung für SDE-Standorte, NPC-Stationen und Spielerstrukturen.
- Root-first-Containerpfade mit SDE-Typnamen und kontrollierter Erkennung zyklischer Beziehungen.
- Vollständige Standort-Snapshots mit Referenz auf den zugrunde liegenden Asset-Snapshot und zusammengefassten Statuswerten.
- Synthetische Golden-Fälle für Station, verschachtelte Container, Struktur-403, fehlenden Scope, Zyklen und Folgefehler.
- Echte zweisprachige Asset-Oberfläche mit Suche, Besitzer- und Standortstatusfilter, Mengen, Datenalter und root-first Standortpfaden.
- Serverseitig begrenzte 100-Zeilen-Seiten sowie ein synthetischer 100.000-Positionen-Regressionstest.
- Gefilterter, atomarer UTF-8-CSV-Export nach `data\exports` mit Formelneutralisierung.
- Atomare, charaktergetrennte Asset-Deltas mit Baseline, deterministischem Ereignis-Fingerabdruck und vollständigem Snapshot-/Run-Nachweis.
- Zweisprachiger Änderungsverlauf für hinzugekommene, entfernte, mengenveränderte und verschobene Assets mit Suche, Besitzer- und Änderungsartfilter.
- Korrelationsbelege aus Charakter, Typ, Richtung, Mengendifferenz und Beobachtungsfenster für die spätere Zuordnung von Industrie-Jobs.
- Synthetischer Regressionstest mit 10.000 Delta-Ereignissen und begrenztem 50-Ereignis-Antwortfenster.

### Geändert

- Eine nicht lesbare Spielerstruktur ist jetzt ein stabiler eingeschränkter Fachzustand und kein Fehler des gesamten Standortlaufs.
- Wiederholte Stationen oder Strukturen werden innerhalb eines Auflösungslaufs nur einmal abgefragt.
- Die Asset-Oberfläche verwendet nur den letzten vollständigen Snapshot je Charakter und lädt höchstens 100 Zeilen pro sichtbarer Seite.
- Der lokale Antwortschutz erlaubt bounded Asset-Seiten, während große CSV-Inhalte als Datei geschrieben und nicht durch die Desktop-Brücke übertragen werden.
- Die Asset-Synchronisierung veröffentlicht Bestand und Delta gemeinsam oder rollt beide zurück; die Historie überträgt höchstens 50 Ereignisse pro sichtbarer Seite.

### Behobene Fehler

- Fehlende Container und zyklische Containerbeziehungen können die Auflösung nicht mehr unkontrolliert abbrechen oder endlos rekursiv laufen.
- Ein technischer Fehler während der Standortauflösung veröffentlicht keinen Teilstand und überschreibt keinen letzten vollständigen Snapshot.
- Standortpfade eines älteren Snapshots können nach einem neueren Asset-Sync nicht versehentlich mit den neuen Positionen verbunden werden; bis zur passenden Auflösung erscheint `pending`.
- Beschädigte vollständige Asset- oder Standort-Snapshots sowie unsichere CSV-Zielpfade werden geschlossen abgewiesen.
- Fehlgeschlagene oder widersprüchliche Asset-Folgeläufe können keine falschen Änderungen erzeugen; manipulierte Delta-Fingerabdrücke werden beim Lesen abgewiesen.

### Bekannte Einschränkungen

- Schutzregeln für `main` sind noch nicht aktiviert.
- Spielerstrukturen ohne erteilten Scope oder ohne Zugriffsrecht bleiben absichtlich ohne Namen und werden als eingeschränkt markiert.
- Asset-Deltas sind für die spätere Industrie-Jobkorrelation vorbereitet, werden aber bis zum Jobs-Sync bewusst als `unmatched` angezeigt.

### Update und Datenbankmigration

- Keine Anwendungsmigration; SQLite-Schema 6 bleibt unverändert. Standort- und Delta-Daten bleiben ableitbare Snapshots, CSV-Dateien liegen unter `data\exports`.

## 0.0.5-preview.2 – 10. September 2026

### Neu hinzugefügt

- Minimaler SDE-Bestand für Typen, Gruppen und Orte mit atomarem Austausch und eindeutiger SDE-Buildnummer.
- Multi-Character-Asset-Synchronisierung über den zentralen ESI-Client mit `esi-assets.read_assets.v1`.
- Vollständige Asset-Pagination über `X-Pages` sowie charaktergetrennte Sync-Runs und Snapshots.
- Tests für atomaren SDE-Import, Pagination, vollständige Asset-Snapshots und abgebrochene Läufe.

### Geändert

- Abgeleitete SDE-Tabellen bleiben bewusst außerhalb der versionierten Anwendungsmigration und können vollständig neu aufgebaut werden.
- Asset-Daten werden erst veröffentlicht, wenn alle Seiten eines Charakterlaufs vollständig validiert wurden.
- Die sichtbare Versionsnummer lautet `v0.0.5-preview.2`.
- Der Masterplan markiert Pakete 17 und 18 als abgeschlossen; Paket 19 Standortauflösung ist der nächste Fachschritt.

### Behobene Fehler

- Ein fehlerhafter SDE-Import kann den letzten gültigen SDE-Bestand nicht mehr teilweise überschreiben.
- Ein Netzwerkfehler oder Abbruch mitten in der Asset-Pagination erzeugt keinen unvollständigen gültigen Snapshot.
- Doppelte Asset-`item_id` über mehrere Seiten werden als inkonsistenter Lauf verworfen.
- Der letzte vollständig abgeschlossene Asset-Cache bleibt bei einem Folgfehler für Cache-First/Offline-Nutzung erhalten.

### Bekannte Einschränkungen

- Die Asset-Synchronisierung stellt in Paket 18 den Backend-Kern bereit; Standortauflösung und die vollständige Asset-Oberfläche folgen in Paketen 19 und 20.
- SDE- und Asset-Daten werden noch nicht als vollständig produktive Fachansicht in der React-Oberfläche dargestellt; vorhandene Fachkennzahlen bleiben dort teilweise synthetisch.
- Der sichere Refresh-Token-Speicher ist in dieser Windows-first Preview nur unter Windows verfügbar.
- Codesignierung, das manuelle Windows-Laufzeitgate und der Schutz von `main` bleiben offen.

### Update und Datenbankmigration

- Keine neue Anwendungsmigration; SQLite-Schema 6 bleibt unverändert.
- SDE-Tabellen sind abgeleitete Daten und werden beim Import atomar angelegt beziehungsweise ersetzt.
- Vorhandene Charaktere, Gruppen, Einstellungen, Refresh Tokens und bereits vollständige Cache-Snapshots bleiben erhalten.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen.

## 0.0.5-preview.1 – 10. September 2026

### Neu hinzugefügt

- Zentraler `EsiClient` als einzige HTTP-Vertrauensgrenze für alle künftigen EVE-ESI-Aufrufe.
- Charaktergetrennte In-Memory-Caches mit `Cache-Control`, `Expires`, `ETag`, `Last-Modified` und bedingter 304-Revalidierung.
- Begrenzte Wiederholungen für Netzwerkfehler und ausgewählte transiente HTTP-Status einschließlich `Retry-After`.
- Gemeinsames ESI-Fehlerbudget und Circuit Breaker mit sichtbarem, geheimnisfreiem Sidecar-Status.
- Deterministische Tests für Header, Auth-Isolation, Cache, Retry, Budget, Circuit, Zielbegrenzung, JSON-Grenzen und Token-Redigierung.

### Geändert

- Charaktergebundene ESI-Aufrufe beziehen Access Tokens ausschließlich über den bestehenden `CharacterTokenService`.
- Jede ESI-Anfrage setzt `X-Compatibility-Date: 2026-09-09` und einen beschreibenden User-Agent mit Produkt, Repository und Kontakt.
- ESI-Ziele sind auf relative Pfade unter `https://esi.evetech.net` begrenzt; Redirects werden abgewiesen.
- Masterplan 2.4 markiert Arbeitspaket 16 als abgeschlossen und den minimalen SDE-Import als nächsten Schritt.
- Die sichtbare Versionsnummer wurde auf `v0.0.5-preview.1` aktualisiert.

### Behobene Fehler

- Fachmodule können Cache-, Retry- oder Rate-Limit-Regeln nicht mehr unbemerkt voneinander abweichend implementieren.
- Abgelaufene Cacheeinträge werden mit Servervalidatoren geprüft, statt bekannte Antworten unnötig neu zu laden oder still zu leeren.
- Ein erschöpftes ESI-Fehlerbudget und wiederholte transiente Fehler stoppen weitere Aufrufe kontrolliert.
- Transportfehler geben keine Access Tokens, Antwortinhalte oder frei steuerbaren Ziel-URLs aus.

### Bekannte Einschränkungen

- Paket 16 liefert die zentrale Transport- und Resilienzschicht; SDE-Import, Endpoint-Pagination und fachliche Synchronisierung folgen ab Paket 17.
- Fachkennzahlen der Oberfläche bleiben bis zur jeweiligen Synchronisierungsanbindung synthetisch.
- Der sichere Refresh-Token-Speicher ist in dieser Windows-first Preview nur unter Windows verfügbar.
- Öffentliche Updateverteilung, Codesignierung, das manuelle Windows-Laufzeitgate und der Schutz von `main` bleiben offen.

### Update und Datenbankmigration

- Keine Datenbankmigration; Schema-Version 6 und alle vorhandenen Charakter-, Gruppen- und Einstellungsdaten bleiben erhalten.
- Bestehende Refresh Tokens verbleiben im Windows-Anmeldespeicher. ESI-Antwortcaches aus Paket 16 sind absichtlich prozesslokal und beginnen nach jedem Start leer.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen.

## 0.0.4-preview.6 – 10. September 2026

### Neu hinzugefügt

- Vollständiger Charaktereditor für lokalen Alias, Aktivstatus und optionale Kontogruppe.
- Editor für lokale Kontogruppen mit Anlegen, Umbenennen und Löschen ohne Verlust zugeordneter Charaktere.
- Verständliche Credential- und Scopepaket-Status pro Charakter einschließlich bestätigter und erforderlicher Scope-Anzahl.
- Zweistufig bestätigter vollständiger Löschablauf für Charakter, Scopes, Sync-Historie, Cache-Snapshots, Prozess-Token und Refresh Token.
- Automatisierte Backend-, IPC-, Migrations- und Oberflächentests für alle Verwaltungs- und Fehlerpfade.

### Geändert

- Das SQLite-Schema wurde auf Version 6 angehoben und speichert optionale lokale Charakteraliase.
- Die echte Charakterliste verwendet den Alias als primären Anzeigenamen, hält den verifizierten EVE-Namen aber sichtbar.
- Mehrfachvalidierung in React, Tauri und Sidecar begrenzt IDs, Alias, Gruppen und abgeleitete Statuswerte.
- Masterplan 2.3 markiert Arbeitspaket 15 als abgeschlossen und den zentralen ESI-Client als nächsten Schritt.
- Die sichtbare Versionsnummer wurde auf `v0.0.4-preview.6` aktualisiert; `Savoxmedia` bleibt ausschließlich als Ersteller der App neben der Version genannt.

### Behobene Fehler

- Verbundene Charaktere können jetzt deaktiviert oder lokal organisiert werden, ohne erneut autorisiert werden zu müssen.
- Beim Löschen eines Charakters bleiben keine abhängigen SQLite-Datensätze oder prozesslokalen Token-Leases zurück.
- Ein Fehler beim Löschen des Windows-Credentials entfernt den zugehörigen SQLite-Charakter nicht mehr teilweise.
- Das Löschen einer Kontogruppe lässt zugeordnete Charaktere korrekt als nicht gruppiert bestehen.

### Bekannte Einschränkungen

- Der zentrale ESI-Client und damit die echte Synchronisierung folgen in Arbeitspaket 16; Fachkennzahlen bleiben bis dahin synthetisch.
- Auf Linux und macOS ist absichtlich keine Ersatzablage aktiv; die Windows-first Preview meldet den Credential-Backend dort als nicht verfügbar.
- Öffentliche Updateverteilung und Codesignierung bleiben deaktiviert; das manuelle Windows-Laufzeitgate und der Schutz von `main` sind offen.

### Update und Datenbankmigration

- Beim ersten Start migriert die App Schema 5 auf Schema 6 und ergänzt `characters.alias`; vorher wird automatisch eine geprüfte Sicherung unter `data\backups` angelegt.
- Vorhandene Charaktere, Gruppen, Scopes, Einstellungen und Refresh Tokens bleiben erhalten; Aliasse beginnen leer.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen. Refresh Tokens verbleiben getrennt im Windows-Anmeldespeicher des aktuellen Nutzers.

## 0.0.4-preview.5 – 9. September 2026

### Neu hinzugefügt

- Charaktergebundene Refresh-Token-Ablage im Windows-Anmeldespeicher ohne Datei- oder SQLite-Rückfall.
- Verifizierter Zwei-Slot-Austausch für Erstablage und Rotation einschließlich Wiederaufnahme nach unterbrochenem Schreiben.
- Prozesslokaler Access-Token-Cache mit rechtzeitiger, charaktergebundener Erneuerung und Konfliktschutz für parallele Rotationen.
- Automatisierte Sicherheits- und Integrationsprüfungen für Ablage, Rotation, Redigierung, Identität und Fehlerpfade.

### Geändert

- Ein erfolgreicher SSO-Rückruf gilt erst nach geprüfter Identität, erfolgreicher SQLite-Speicherung und bestätigter Aktivierung des Refresh Tokens als verbunden.
- Access Tokens verbleiben ausschließlich im Sidecar-Speicher; Refresh Tokens werden ausschließlich über den Windows-Anmeldespeicher gelesen und ersetzt.
- Der Sidecar meldet den verfügbaren Credential-Backend-Status, ohne Eintragsnamen oder Geheimnisse preiszugeben.
- Masterplan 2.2 markiert Arbeitspaket 14 als abgeschlossen und die vollständige Charakterverwaltung als nächsten Schritt.
- Die sichtbare Versionsnummer wurde auf `v0.0.4-preview.5` aktualisiert; `Savoxmedia` bleibt ausschließlich als Ersteller der App neben der Version genannt.

### Behobene Fehler

- Nach einer erfolgreichen Autorisierung wird der Refresh Token nicht mehr verworfen; der verbundene Charakter kann künftig ohne erneute Browseranmeldung ein Access Token erhalten.
- Ein fehlgeschlagener Austausch überschreibt den letzten aktiven Refresh Token nicht.
- Eine veraltete parallele Rotation kann einen bereits erneuerten Refresh Token nicht zurücksetzen.
- Tokenwerte erscheinen auch vollqualifiziert verpackt weder in Objekt-Repräsentationen noch in öffentlichen Fehlertexten.

### Bekannte Einschränkungen

- Die Verwaltungsoberfläche für Alias, Aktivstatus, Gruppen, Scope-Status und vollständiges Löschen folgt in Arbeitspaket 15.
- Der zentrale ESI-Client und damit die echte Synchronisierung folgen in Arbeitspaket 16; Fachkennzahlen bleiben bis dahin synthetisch.
- Auf Linux und macOS ist absichtlich keine Ersatzablage aktiv; die aktuelle Windows-first Preview meldet den Credential-Backend dort als nicht verfügbar.
- Öffentliche Updateverteilung und Codesignierung bleiben deaktiviert; das manuelle Windows-Laufzeitgate und der Schutz von `main` sind offen.

### Update und Datenbankmigration

- Keine Datenbankmigration; Schema-Version 5 und alle Daten unter `data` bleiben erhalten.
- Bereits in `v0.0.4-preview.4` verbundene Charaktere besitzen noch keinen Refresh Token und müssen einmal erneut verbunden werden.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen. Refresh Tokens verbleiben getrennt im Windows-Anmeldespeicher des aktuellen Nutzers.

## 0.0.4-preview.4 – 9. September 2026

### Neu hinzugefügt

- Echter PKCE-Codeaustausch ohne Client Secret und strikte JWT-Prüfung über EVE-Metadaten und JWKS.
- Prüfung von `RS256`-Signatur, Schlüssel-ID, Issuer, beiden Audience-Werten, Ablauf, Charakter-ID, Name und bestätigten Scopes.
- Sichtbare, dauerhaft aus SQLite geladene Liste aller erfolgreich verbundenen EVE-Charaktere.
- Globale Schriftgröße in fünf Stufen für alle derzeit sichtbaren Oberflächentexte.
- Automatisierte Positiv- und Negativtests für Token-, Identitäts-, Persistenz- und Darstellungskette.

### Geändert

- Ein Callback wechselt zunächst in den sichtbaren Prüfzustand; nur eine vollständig validierte EVE-Identität erreicht den Zustand `connected`.
- Erneute Autorisierung aktualisiert denselben Charakter idempotent und erhält eine bestehende lokale Kontogruppenzuordnung.
- Die Schriftgrößenstufe wird ohne neue Datenbankmigration in `app_settings` im Programmordner gespeichert.
- Masterplan 2.1 markiert Arbeitspaket 13 als abgeschlossen und Schlüsselbund/Rotation als nächsten Schritt.
- Die sichtbare Versionsnummer wurde auf `v0.0.4-preview.4` aktualisiert; `Savoxmedia` bleibt ausschließlich als Ersteller der App neben der Version genannt.

### Behobene Fehler

- Ein im Browser erfolgreich autorisierter Charakter bleibt nach einem erneuten Login nicht mehr unsichtbar, sondern erscheint sofort und nach Neustarts in der echten Charakterliste.
- Ungeprüfte, manipulierte, abgelaufene oder für einen anderen Client ausgestellte Tokens können keinen Charakterdatensatz erzeugen.
- Alle sichtbaren Textbereiche reagieren gemeinsam auf eine Schriftgrößenänderung.

### Bekannte Einschränkungen

- Eine Autorisierung aus `v0.0.4-preview.3` muss wiederholt werden, weil Paket 12 den einmaligen Code bewusst verworfen hat.
- Access und Refresh Token werden nach der Identitätsprüfung noch verworfen; Schlüsselbundspeicherung und Rotation folgen in Paket 14.
- Fachkennzahlen bleiben synthetisch; ESI, SDE, echte Synchronisierung und Berechnungen sind noch nicht angeschlossen.
- Öffentliche Updateverteilung und Codesignierung bleiben deaktiviert; das manuelle Windows-Laufzeitgate und der Schutz von `main` sind offen.

### Update und Datenbankmigration

- Keine Datenbankmigration; Schema-Version 5 und alle Daten unter `data` bleiben erhalten.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen.

## 0.0.4-preview.3 – 9. September 2026

### Neu hinzugefügt

- Echter EVE-SSO-Autorisierungsstart im Systembrowser für jeweils einen Charakter.
- Kurzlebiger Callback-Listener an `http://127.0.0.1:17891/oauth/callback` mit kryptografischem `state`, neuem PKCE-Verifier und `S256`-Challenge je Versuch.
- Auswahl minimaler Funktions-Scopes pro Charakter sowie sichtbare Zustände für Warten, Erfolg, EVE-Ablehnung, Timeout und Abbruch.
- Durchgängige Backend-, Sidecar-, native IPC- und Oberflächentests einschließlich Frozen-Smoke-Prüfung.

### Geändert

- Tauri öffnet nur vollständig geprüfte EVE-Autorisierungs-URLs und gibt keine PKCE-Geheimnisse an die Weboberfläche weiter.
- Mehrere Charaktere werden weiterhin einzeln autorisiert; gemeinsame und getrennte Übersichten bleiben unverändert vorbereitet.
- Masterplan 2.0 führt Arbeitspaket 12 als abgeschlossen und JWT-Validierung als nächsten Schritt.
- Die sichtbare Versionsnummer wurde auf `v0.0.4-preview.3` aktualisiert; `Savoxmedia` bleibt ausschließlich als Ersteller der App neben der Version genannt.

### Behobene Fehler

- Falsche, fehlende oder doppelte `state`- und Code-Parameter können keinen erfolgreichen lokalen Rückruf mehr erzeugen.
- Timeout, Abbruch, Fehler und App-Ende lassen keinen aktiven Callback-Listener und keine temporären PKCE-Werte zurück.
- Der Frozen-Smoke-Test erhält mehr Zeit für einen sauberen Prozess-Shutdown unter paralleler Windows-CI-Last.

### Bekannte Einschränkungen

- Paket 12 endet nach dem verifizierten Browser-Rückruf. Codeaustausch, JWT-Validierung und dauerhafte Charakterzuordnung folgen in Paket 13; der Autorisierungscode wird in dieser Preview bewusst verworfen.
- Die Mehrcharakter-Oberfläche verwendet weiterhin synthetische Fachwerte und liest ihre Inhalte noch nicht aus SQLite.
- ESI, SDE, echte Synchronisierung und Fachberechnungen sind noch nicht angeschlossen.
- Öffentliche Updateverteilung und Codesignierung bleiben deaktiviert; das manuelle Windows-Laufzeitgate und der Schutz von `main` sind offen.

### Update und Datenbankmigration

- Keine Datenbankmigration; Schema-Version 5 und alle Daten unter `data` bleiben unverändert.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen.

## 0.0.4-preview.2 – 9. September 2026

### Neu hinzugefügt

- Verbindliches öffentliches EVE-SSO-App-Profil mit fester Loopback-Callback-URI, öffentlicher Client-ID und Entwicklerkontakt.
- Minimale Scopepakete für Industrie, private Strukturen, Markt, Projekte und Planetary Industry.
- Strikte Profil-, Sidecar- und Frozen-Pakettests gegen Callback-, Scope- und Client-ID-Drift.
- ADR-012 und dokumentierte Portalwerte für reproduzierbare spätere Abgleiche.

### Geändert

- Sidecar und Selbsttest melden das gebündelte SSO-Profil als registriert.
- Der feste Browser-Callback-Port ist ausdrücklich vom dynamischen internen Sidecar-Port getrennt.
- Arbeitspaket 11 ist abgeschlossen; als Nächstes folgt der eigentliche PKCE-Login.
- Die sichtbare Versionsnummer wurde auf `v0.0.4-preview.2` aktualisiert.

### Behobene Fehler

- Callback-URI, öffentliche Client-ID und Scope-Menge können nicht mehr unbemerkt zwischen Portalvorlage, Code, Paket und Tests auseinanderlaufen.
- Ein fehlender oder ungültiger Client-ID-Wert wird nicht als abgeschlossene Registrierung gemeldet.

### Bekannte Einschränkungen

- Die Registrierung ist vollständig, aber eine echte EVE-Anmeldung folgt erst mit PKCE-, Callback- und JWT-Implementierung in den nächsten Arbeitspaketen.
- Die Mehrcharakter-Oberfläche arbeitet weiterhin mit synthetischen Daten.
- ESI, SDE, echte Synchronisierung und Fachberechnungen fehlen noch.
- Öffentliche Updateverteilung und Codesignierung bleiben deaktiviert; das manuelle Windows-Laufzeitgate und der Schutz von `main` sind offen.

### Update und Datenbankmigration

- Keine Datenbankmigration; Schema-Version 5 und alle Daten unter `data` bleiben unverändert.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen.

## 0.0.4-preview.1 – 9. September 2026

### Neu hinzugefügt

- Wählbare, lokal gespeicherte Updatekanäle „Offiziell“, „Beta“ und „Vorschau / Test“.
- Schema-Version 5 mit `app_settings` und sicherem Standardkanal `stable`.
- Gebündeltes Ed25519-signiertes, nicht auslieferndes Testmanifest samt strenger Struktur- und Zielprüfung.
- Backend-, Sidecar-, IPC-, UI- und Frozen-Pakettests für Kanalwahl und Vertrauensgrenze.

### Geändert

- Kanaländerungen laufen ausschließlich über den authentifizierten Sidecar und bleiben nach einem Neustart in der Datenbank im Programmordner erhalten.
- Laufzeitstatus und Oberfläche unterscheiden Manifestprüfung und öffentliche Verteilung ausdrücklich.
- Der Sidecar-Build bündelt Testmanifest, Signatur und die fest versionierte Kryptografie-Abhängigkeit.
- Die sichtbare Versionsnummer wurde auf `v0.0.4-preview.1` aktualisiert.

### Behobene Fehler

- Nicht vertrauenswürdige, mehrdeutige oder auf einen öffentlichen Host verweisende Testmetadaten werden vor Verwendung abgewiesen.
- Die Browser-Vorschau kann keinen erfolgreichen nativen Kanalwechsel vortäuschen.

### Bekannte Einschränkungen

- Es gibt noch keinen öffentlichen Updater, Netzwerkabruf, Download oder automatische Installation; die Auswahl speichert derzeit nur die spätere Kanalpräferenz.
- Die Mehrcharakter-Oberfläche verwendet weiterhin synthetische Werte und liest ihre Fachinhalte noch nicht aus SQLite.
- EVE SSO, ESI, SDE, echte Synchronisierung und Fachberechnungen fehlen noch.
- Installer und portable EXE sind noch nicht code-signiert.
- Das manuelle Windows-Laufzeitgate und die Schutzregeln für `main` sind noch offen.

### Update und Datenbankmigration

- Schema 4 wird nach automatischer Sicherung auf Schema 5 migriert und um lokale Anwendungseinstellungen ergänzt.
- Bestehende Charakter- und Cache-Daten bleiben erhalten; die Updatekanal-Präferenz startet einmalig mit `stable`.
- Eine frische Installation legt direkt Schema-Version 5 an.

## 0.0.3-preview.3 – 9. September 2026

### Neu hinzugefügt

- Cache-first-Startzustände für Laden, Aktualisieren, leer, aktuell, veraltet, offline und fehlerhaft.
- Zweisprachiges Statusband mit echtem lokalen Datenalter und verständlicher Zustandsbeschreibung.
- Schema-Version 4 mit optionalem Ablaufzeitpunkt je Cache-Snapshot.
- Tests für Cache-Ablauf, Offlinebetrieb, Folgfehler, laufende Aktualisierung und ungültige Metadaten.

### Geändert

- Sidecar und Tauri-Schale übertragen und prüfen den aus SQLite abgeleiteten Cachezustand.
- Die native App simuliert keine erfolgreiche Aktualisierung mehr, solange ESI noch nicht angeschlossen ist.
- Programmordner-, Datenbank- und Sidecarfehler werden verständlich und ohne absolute lokale Pfade erklärt.
- Die sichtbare Versionsnummer wurde auf `v0.0.3-preview.3` aktualisiert.

### Behobene Fehler

- Ein fehlgeschlagener Folgelauf lässt einen vorhandenen vollständigen Cache nicht mehr leer erscheinen.
- Interne Synchronisierungsfehler werden vor der UI-Ausgabe auf stabile Codes reduziert.

### Bekannte Einschränkungen

- Die Mehrcharakter-Oberfläche verwendet weiterhin synthetische Werte und liest ihre Fachinhalte noch nicht aus SQLite.
- EVE SSO, ESI, SDE, echte Synchronisierung und Fachberechnungen fehlen noch.
- Installer und portable EXE sind noch nicht code-signiert.
- Das manuelle Windows-Laufzeitgate und die Schutzregeln für `main` sind noch offen.

### Update und Datenbankmigration

- Schema 3 wird nach automatischer Sicherung auf Schema 4 migriert und um `expires_at` für Cache-Snapshots ergänzt.
- Bestehende Snapshots ohne bestätigten Ablaufzeitpunkt bleiben erhalten und gelten vorsichtshalber als veraltet.
- Eine frische Installation legt direkt Schema-Version 4 an.

## 0.0.3-preview.2 – 9. September 2026

### Neu hinzugefügt

- Konsistente SQLite-Sicherung vor jeder ausstehenden Migration unter `data\backups`.
- Prüfung von Integrität, Fremdschlüsseln, Schema-Version und SHA-256 vor Beginn einer Migration.
- Automatische Wiederherstellung des geprüften Ausgangsstands bei fehlgeschlagener Migration oder Abschlussprüfung.
- Schema-Version 3 mit lokaler Sicherungshistorie und Aufbewahrung der fünf neuesten Migrationssnapshots.
- Automatisierte Fehler- und Wiederherstellungstests einschließlich beschädigter Sicherungen.

### Geändert

- Der native Bereitschaftsstatus kennzeichnet die aktive Migrationssicherung.
- Sidecar-, Backend-, Portable- und Release-Dokumentation beschreiben den vollständigen Sicherungsablauf.
- Der Release-Workflow verwendet bereits vor der SHA-256-Erzeugung den endgültigen öffentlichen Installer-Dateinamen.
- Die sichtbare Versionsnummer wurde auf `v0.0.3-preview.2` aktualisiert.

### Behobene Fehler

- Eine Migration kann nicht mehr ohne vorherige erfolgreiche Sicherung beginnen.
- Nach einem Migrationsfehler bleibt kein teilweise aktualisiertes Schema als einsatzbereit zurück.
- Eine beschädigte Sicherung kann die aktuelle Datenbank nicht ersetzen.
- Der Dateiname innerhalb der Installer-Prüfsumme stimmt nun mit dem GitHub-Assetnamen überein.

### Bekannte Einschränkungen

- Die Oberfläche verwendet weiterhin synthetische Mehrcharakterdaten und liest noch nicht aus SQLite.
- EVE SSO, ESI, SDE, Synchronisierung und fachliche Berechnungen fehlen noch.
- Eine manuelle Auswahl älterer Sicherungen in der Oberfläche ist noch nicht vorhanden.
- Installer und portable EXE sind noch nicht code-signiert.
- Die portable ZIP benötigt eine vorhandene Microsoft Edge WebView2 Runtime und einen beschreibbaren Zielordner.
- Schutzregeln für `main` sind noch nicht aktiviert.

### Update und Datenbankmigration

- Eine vorhandene Schema-Version-2-Datenbank aus `v0.0.3-preview.1` wird nach automatischer Sicherung auf Schema-Version 3 aktualisiert. Es ist keine manuelle Aktion erforderlich.
- Eine frische Installation legt direkt Schema-Version 3 an und erzeugt deshalb keinen unnötigen Migrationssnapshot.
- Installer-Updates und Deinstallation lassen `data` einschließlich `data\backups` stehen. Bei einer portablen Aktualisierung die App schließen und den vollständigen Ordner `data` übernehmen.

## 0.0.3-preview.1 – 8. September 2026

### Neu hinzugefügt

- Gebündelter FastAPI-Sidecar mit dynamischem Loopback-Port, versioniertem Startprotokoll und neuem 256-Bit-Sitzungstoken je App-Start.
- Produktive SQLite-Anlage unter `data\foundry.sqlite3` sowie vorbereiteter Backup-Ordner `data\backups`, jeweils direkt im Programmordner.
- Single-Instance-Fokus, Kindprozessüberwachung und kontrollierter Sidecar-Shutdown.
- Native Start-, Bereit- und Fehlerzustände in der Oberfläche.
- Frozen-Smoke-Test und Paketprüfung für den mitgelieferten Windows-Sidecar.
- ADR-010 für die sichtbare Datenhaltung im Programmordner.

### Geändert

- `Savoxmedia` erscheint ausschließlich als Ersteller der App neben der Versionsnummer.
- Installer und portable ZIP enthalten Hauptprogramm und Sidecar; die portable ZIP enthält zusätzlich deutsch-englische Nutzungshinweise.
- Python-Laufzeit- und Build-Abhängigkeiten sind getrennt und exakt versioniert.
- Die sichtbare Versionsnummer wurde auf `v0.0.3-preview.1` aktualisiert.

### Behobene Fehler

- Der lokale Kern verwendet bei einem nicht beschreibbaren Programmordner keinen versteckten Ersatzpfad.
- Fehlende oder falsche Sitzungstokens werden auch am Health-Endpunkt abgewiesen und nicht ausgegeben.
- Die missverständliche Darstellung von `Savoxmedia` als lokales Benutzerprofil wurde entfernt.

### Bekannte Einschränkungen

- Die Oberfläche verwendet weiterhin synthetische Mehrcharakterdaten und liest noch nicht aus SQLite.
- EVE SSO, ESI, SDE, Synchronisierung, automatische Migrations-Backups und fachliche Berechnungen fehlen noch.
- Installer und portable EXE sind noch nicht code-signiert.
- Die portable ZIP benötigt eine vorhandene Microsoft Edge WebView2 Runtime und einen beschreibbaren Zielordner.
- Schutzregeln für `main` sind noch nicht aktiviert.

### Update und Datenbankmigration

- Frühere Previews erzeugten keine produktive Datenbank. Der erste Start legt Schema-Version 2 unter `<Programmordner>\data\foundry.sqlite3` neu an.
- Installer-Updates und Deinstallation lassen den nicht gebündelten Ordner `data` stehen. Bei einer portablen Aktualisierung die geschlossene App samt vollständigem Ordner `data` kopieren.

## 0.0.2-preview.2 – 8. September 2026

### Neu hinzugefügt

- Schema-Version 2 mit lokalen Kontogruppen, eindeutig identifizierten Charakteren und getrennt gespeicherten SSO-Scopes je Charakter.
- Atomare Charakteraktualisierung, damit eine erneute Autorisierung denselben Charakter aktualisiert und keine Dublette erzeugt.
- Auswahl zwischen einer gemeinsamen Übersicht aller Charaktere und einer eigenen Übersicht für jeden Charakter.
- Synthetische Mehrcharakter-Vorschau mit zwei lokalen Kontogruppen, drei Charakteren und jeweils eigenen Kennzahlen, Jobs, Hinweisen und Aktivitäten.
- ADR-009 als verbindliche Grundlage für charaktergebundene EVE-Zugänge und lokale Accountorganisation.

### Geändert

- Synchronisierungsläufe können jetzt eindeutig einem Charakter zugeordnet werden.
- Der Datenstand der Gesamtübersicht richtet sich nach dem ältesten enthaltenen Charakterstand und bleibt sichtbar.
- `Savoxmedia` wurde als Projektbezeichnung von synthetischen EVE-Charakteren getrennt; die eindeutige Kennzeichnung als App-Ersteller folgt in `v0.0.3-preview.1`.
- Die sichtbare Versionsnummer wurde auf `v0.0.2-preview.2` aktualisiert.

### Behobene Fehler

- Charakterbezogene Jobs, Hinweise und Aktivitäten behalten in der Gesamtansicht ihre sichtbare Besitzerzuordnung.
- Das Löschen einer lokalen Kontogruppe entfernt nicht versehentlich die darin einsortierten Charakterdatensätze.
- Das Löschen eines Charakters entfernt dessen lokale Scopes, Synchronisierungsläufe und Cache-Snapshots vollständig.

### Bekannte Einschränkungen

- Kontogruppen und Charakterübersichten verwenden in dieser Preview noch synthetische Daten und sind noch nicht mit der Oberfläche der SQLite-Datenbank verbunden.
- Jeder echte Charakter muss später separat über EVE SSO autorisiert werden; EVE stellt der Anwendung keine bestätigte Accountgruppierung bereit.
- FastAPI-Sidecar, Single Instance, lokaler Port-/Token-Handshake, EVE SSO, ESI und SDE fehlen noch.
- Installer und portable EXE sind noch nicht code-signiert.
- Die portable ZIP benötigt eine vorhandene Microsoft Edge WebView2 Runtime.
- Schutzregeln für `main` sind noch nicht aktiviert.

### Update und Datenbankmigration

- Beim normalen App-Start existiert weiterhin keine produktive Nutzerdatenbank; daher ist für Preview-Nutzer keine Migration erforderlich.
- Entwicklungsdatenbanken mit Schema-Version 1 werden ohne Verlust bestehender Metadaten auf Schema-Version 2 aktualisiert.
- Automatische Migrations-Backups und Wiederherstellung folgen mit Arbeitspaket 08 und sind noch nicht Teil dieser Preview.

## 0.0.2-preview.1 – 8. September 2026

### Neu hinzugefügt

- Erste versionierte SQLite-Basismigration für Metadaten, Synchronisierungsläufe und synthetische Cache-Snapshots.
- Automatische Aktivierung und Prüfung von Foreign Keys, WAL-Modus und `busy_timeout` auf jeder Backend-Verbindung.
- Lokaler Backend-Selbsttest für Schema-Version und Datenbankintegrität ohne Netzwerkdienst.
- Tauri-IPC-Befehl, über den die Oberfläche den echten Status und die Version der nativen Desktop-Schale erkennt.
- Automatisierte Tests für Migration, Integrität, Fremdschlüssel, paralleles Lesen im WAL-Modus und die Browser-/Desktop-Statusanzeige.

### Geändert

- Die Qualitäts- und Release-Prüfungen testen nun Frontend und Python-Backend gemeinsam.
- Die Statusanzeige unterscheidet zwischen Browser-Vorschau, verbundener Tauri-Schale, laufender Prüfung und fehlgeschlagener nativer Statusabfrage.
- Die sichtbare Versionsnummer wurde auf `v0.0.2-preview.1` aktualisiert.

### Behobene Fehler

- Die Browser-Vorschau behauptet nicht länger, mit einem nativen Desktop-Kern verbunden zu sein.

### Bekannte Einschränkungen

- Das Python-Backend ist noch kein gebündelter Sidecar und wird von der Desktop-Anwendung noch nicht gestartet.
- Die SQLite-Grundlage wird noch nicht für Nutzerdaten verwendet; die Oberfläche zeigt weiterhin ausschließlich synthetische Vorschauwerte.
- Single Instance, lokaler Port-/Token-Handshake, EVE SSO, ESI, SDE, Synchronisierung und fachliche Berechnungen fehlen noch.
- Installer und portable EXE sind noch nicht code-signiert.
- Die portable ZIP benötigt eine vorhandene Microsoft Edge WebView2 Runtime.
- Schutzregeln für `main` sind noch nicht aktiviert.

### Update und Datenbankmigration

- Keine Nutzerdatenmigration erforderlich. Diese Vorschau legt beim normalen App-Start weiterhin keine Nutzerdatenbank an.
- Eine installierte ältere Preview kann bestehen bleiben; die portable ZIP vollständig in einen eigenen Ordner entpacken.

## 0.0.1-preview.2 – 8. September 2026

### Neu hinzugefügt

- Portable Windows-ZIP mit ausführbarer Anwendung und deutsch-englischen Nutzungshinweisen.
- Separate SHA-256-Prüfsummen für Installer und portable ZIP.
- Paketprüfung, die den Installer, das ZIP und dessen erwartete Inhalte vor dem Merge validiert.

### Geändert

- Der Release-Workflow leitet Version, Tag, Notes und Kanal nun aus den versionierten Projektdateien ab und funktioniert damit für künftige Releases ohne fest verdrahtete Versionsnummer.
- Jedes Windows-Release veröffentlicht ab jetzt Installer und portable ZIP direkt am GitHub Release; Actions-Artefakte bleiben weiterhin ausgeschlossen.
- Die sichtbare Versionsnummer der Design Preview wurde auf `v0.0.1-preview.2` aktualisiert.

### Behobene Fehler

- Keine.

### Bekannte Einschränkungen

- Keine EVE-Anbindung und keine produktive Fachlogik.
- Installer und portable EXE sind noch nicht code-signiert.
- Die portable ZIP benötigt eine vorhandene Microsoft Edge WebView2 Runtime.
- Die damalige Planung eines vom Programmordner getrennten Datenorts wurde später durch ADR-010 ersetzt; ab `v0.0.3-preview.1` liegt die Fachdatenbank unter `data` im Programmordner.
- Schutzregeln für `main` sind noch nicht aktiviert.

### Update und Datenbankmigration

- Keine Datenbankmigration erforderlich; diese Design Preview legt weiterhin keine Nutzerdatenbank an.
- `v0.0.1-preview.1` kann installiert bleiben. Die portable Fassung wird unabhängig davon in einen eigenen Ordner entpackt.

## 0.0.1-preview.1 – 8. September 2026

### Neu hinzugefügt

- Erste installierbare Windows-Designvorschau mit Tauri 2, React und TypeScript.
- Synthetische Foundry-Übersicht, vollständige Modulnavigation, Suche sowie DE/EN-Umschaltung.
- UI-Tests, Frontend-Buildprüfung und direkte Veröffentlichung des NSIS-Installers an ein GitHub Prerelease.
- Lebender Masterplan, ADR-Grundlage und Repository-Richtlinien für Phase 0.

### Geändert

- Das zentrale öffentliche Repository `Savox76/eve-test-indu` übernimmt Quellcode, Dokumentation, Issues, Actions und Releases.
- Die öffentliche Sichtbarkeit ermöglicht Branchschutz auf GitHub Free; Quellcode und Release-Seiten sind dadurch öffentlich zugänglich.
- Der Projektstatus unterscheidet nun ausdrücklich zwischen Design Preview und funktionaler Alpha.

### Behobene Fehler

- Der Release-Gate-Ausdruck ist als gültiger YAML-Skalar quotiert und wird vor künftigen Veröffentlichungen durch die Repository-Prüfung abgesichert.

### Bekannte Einschränkungen

- Keine EVE-Anbindung und keine produktive Fachlogik.
- Noch nicht code-signierter Windows-Installer.
- Schutzregeln für `main` sind noch nicht aktiviert.

### Update und Datenbankmigration

- Keine Migration erforderlich; es gibt keine Vorgängerversion und noch keine Nutzerdatenbank.
