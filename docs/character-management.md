# Charakterverwaltung

## Zweck und Grenzen

Jede EVE-Anmeldung autorisiert genau einen Charakter. New Eden Foundry führt deshalb keine EVE-Accounts oder Passwörter, sondern ausschließlich einzeln geprüfte Charakteridentitäten. Frei benannte Kontogruppen sind lokale Organisationshilfen und keine von EVE bestätigte Accountzugehörigkeit.

## Verwaltungsfunktionen

Die Desktop-Oberfläche lädt Charaktere und Kontogruppen ausschließlich über die authentifizierte Sidecar-Verbindung. Pro Charakter können folgende Werte geändert werden:

- **Alias:** optionaler lokaler Anzeigename mit maximal 80 Zeichen; der verifizierte EVE-Name bleibt unverändert sichtbar.
- **Aktivstatus:** inaktive Charaktere bleiben gespeichert, werden aber von späteren regulären Synchronisierungen und Gesamtberechnungen ausgeschlossen.
- **Kontogruppe:** optionale lokale Zuordnung. Gruppen können angelegt, umbenannt und gelöscht werden. Das Löschen einer Gruppe löscht keine Charaktere, sondern setzt ihre Zuordnung auf „Nicht gruppiert“.
- **Credential-Status:** zeigt nur `stored`, `missing` oder `unavailable`; Credential-Namen und Tokenwerte verlassen den Sidecar nie.
- **Scopepaket-Status:** zeigt je registriertem Paket `granted`, `partial` oder `missing` sowie bestätigte und erforderliche Scope-Anzahl.

Die Paketauswahl erfolgt nicht manuell: jede Anmeldung fordert automatisch alle aktuell benötigten Pakete an. Fehlt nach einem Update ein Scope oder ein Credential, erhält der Charakter den sichtbaren Status **Anmeldung nötig**. Die Schaltfläche **Jetzt neu anmelden** öffnet EVE SSO; wird dort derselbe Charakter gewählt, werden Autorisierung und Scope-Status idempotent erneuert. Alias, lokale Kontogruppe und vorhandene vollständige Snapshots bleiben erhalten.

Alle Eingaben werden im React-Client, in der Tauri-Brücke und im Python-Sidecar erneut begrenzt und validiert. API-Antworten enthalten keine Access oder Refresh Tokens.

## Vollständiges Löschen

Das Löschen benötigt zwei bewusste Klicks. Danach führt der Sidecar folgenden geschützten Ablauf aus:

1. SQLite startet eine unmittelbare Transaktion und prüft die Charakter-ID.
2. Die Charakterzeile wird gelöscht; Foreign Keys entfernen Scopes, Synchronisierungsläufe und abhängige Cache-Snapshots.
3. Der charaktergebundene Refresh Token wird im Windows-Anmeldespeicher gelöscht.
4. Erst nach erfolgreicher Credential-Löschung wird die SQLite-Transaktion bestätigt.
5. Ein möglicher prozesslokaler Access-Token-Lease wird verworfen.

Schlägt Schritt 3 fehl, rollt der Sidecar die SQLite-Änderung zurück und meldet einen redigierten Fehler. Schlägt das Bestätigen der Datenbank nach erfolgreicher Credential-Löschung fehl, bleibt der Token aus Datenschutzgründen gelöscht; der weiterhin sichtbare Charakter kann sicher erneut gelöscht oder neu verbunden werden.

## Datenbankmigration

Paket 15 hebt das SQLite-Schema von 5 auf 6 an und ergänzt `characters.alias` als nullable Spalte. Vor der Migration wird nach den bestehenden Regeln eine SHA-256-geprüfte Sicherung erstellt. Vorhandene Charaktere, Gruppen, Scopes, Einstellungen und Token im Windows-Anmeldespeicher bleiben erhalten.

## Verifikation

Automatisierte Tests decken Alias und Aktivstatus, Gruppen-CRUD, Scope-/Credential-Ableitung, Migration von Schema 5, referenzielle Löschung, Credential-Rollback, Tauri-Antwortvalidierung und den zweistufigen UI-Löschdialog ab. Alle Testdaten und Tokenwerte sind synthetisch.
