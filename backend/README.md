# Python-Backend

Dieses Verzeichnis enthält den lokalen fachlichen Kern von New Eden Foundry. Die aktuelle Ausbaustufe umfasst den gebündelten FastAPI-Sidecar, die versionierte SQLite-Grundlage mit automatischer Migrationssicherung und Wiederherstellung, cache-first Startzustände, lokale Kontogruppen, getrennte Charakterdatensätze und deren jeweilige SSO-Scopes. Hinzu kommt das Updater-Skelett mit lokaler Kanalpräferenz und einem gebündelten Ed25519-signierten Testmanifest. Tauri startet den Dienst als Kindprozess auf einem dynamischen Loopback-Port und übergibt das kurzlebige Sitzungstoken ausschließlich über die Standardeingabe.

Paket 16 bündelt sämtliche künftigen ESI-Aufrufe in `EsiClient`. Der Client erzwingt den festen Host, `X-Compatibility-Date`, eine beschreibende Produktkennung, charaktergetrennte Cache-Schlüssel, `ETag`/`If-None-Match`, `Last-Modified`/`If-Modified-Since`, `Expires`/`Cache-Control`, begrenzte Wiederholungen, `Retry-After`, das ESI-Fehlerbudget und einen Circuit Breaker. Antworten sind größenbegrenzt und werden als striktes UTF-8-JSON gelesen; Fehlertexte enthalten weder Token noch Nutzdaten.

Paket 17 ergänzt einen atomaren, über eine Buildnummer identifizierten Minimal-SDE-Bestand für Typen, Gruppen und Orte. Paket 18 verwendet den zentralen `EsiClient` für charaktergetrennte Asset-Läufe mit vollständiger `X-Pages`-Pagination. Erst ein vollständig validierter Lauf erzeugt einen neuen `cached_snapshots`-Datensatz; Fehlerläufe bleiben getrennt in `sync_runs` und lassen den letzten gültigen Cache unverändert.

Die Fachpakete 23–25 wenden dieselbe vollständige Snapshot-Regel auf Blueprints, persönliche Industrieaufträge und Charakter-Skills an. Paket 26 ergänzt einen globalen `industry_facilities`-Snapshot aus dem öffentlichen NPC-Anlagenkatalog, Systemkostenindizes und begrenzt aufgelösten Universumsnamen. Spielerstrukturen werden nur aus den letzten vollständigen persönlichen Job-Snapshots entdeckt und mit dem Scope `esi-universe.read_structures.v1` charakterbezogen aufgelöst; fehlender Scope, ACL-403 und unbekannte Anlagen bleiben eigene Zustände. Die internen Routen `/industry-facilities/query` und `/industry-facilities/sync` liefern ausschließlich streng geprüfte, begrenzte Antworten an die Tauri-Brücke.

Der Sidecar bündelt außerdem das vollständige öffentliche EVE-SSO-Registrierungsprofil und meldet dessen Zustand als `registered`. Das Profil enthält die öffentliche Client-ID und ausdrücklich kein Client Secret. Für jeden Anmeldeversuch erzeugt er unabhängige 256-Bit-Werte für `state` und PKCE-Verifier, bindet kurzzeitig den festen Callback `127.0.0.1:17891`, prüft den Rückruf exakt und unterstützt Status, Drei-Minuten-Timeout und Abbruch über die authentifizierte interne API. Der Codeaustausch verwendet PKCE, bezieht Token- und JWKS-Endpunkte aus streng geprüften EVE-Metadaten und validiert `RS256`-Signatur, Schlüssel-ID, Issuer, beide Audience-Werte, Ablauf, Charakter-ID, Name und Scopes, bevor Identität oder Token übernommen werden.

EVE autorisiert jeden Charakter einzeln. Eine lokale Kontogruppe dient nur der vom Nutzer vergebenen Organisation mehrerer Charaktere; sie speichert weder EVE-Accountnamen noch Zugangsdaten. Paket 15 ergänzt Alias, Aktivstatus, Gruppeneditor sowie abgeleitete Credential- und Scopepaket-Status. Das vollständige Löschen entfernt innerhalb eines geschützten Ablaufs Charakterzeile und abhängige SQLite-Daten, den Windows-Credential-Eintrag und einen möglichen Access-Token-Lease; ein Fehler beim Credential-Löschen rollt die Datenbankänderung zurück. Paket 14 speichert und rotiert Refresh Tokens weiterhin ausschließlich im Windows-Anmeldespeicher. Access Tokens bleiben ausschließlich im Prozessspeicher. Tokenwerte werden niemals in SQLite, API-Antworten oder Logs geschrieben; ein fehlender Anmeldespeicher führt zu einem geschlossenen Fehler statt zu einer Klartext-Ausweichablage. Die globale Schriftgrößenstufe wird als nicht geheime Einstellung in der Tabelle `app_settings` gespeichert.

Der Selbsttest lässt sich aus diesem Verzeichnis ausführen:

```powershell
python -m new_eden_foundry_backend --database .\foundry-development.sqlite3
```

Die erzeugte Entwicklungsdatenbank ist durch die Repository-Regeln vom Commit ausgeschlossen. Beim normalen App-Start liegt die produktive Datenbank ausschließlich unter `data\foundry.sqlite3` neben der Hauptanwendung; ein nicht beschreibbarer Programmordner führt zu einem sichtbaren Startfehler und nie zu einem versteckten Ersatzpfad. Vor jeder anstehenden Migration wird über die SQLite-Backup-API ein eigenständiger Snapshot unter `data\backups` erstellt, geprüft und mit SHA-256 in der Datenbankhistorie vermerkt. Ein Migrationsfehler löst die verifizierte Wiederherstellung aus; die fünf neuesten Snapshots werden aufbewahrt.

Der Startstatus wird ausschließlich aus lokalen Metadaten abgeleitet. Nur Snapshots eines vollständig abgeschlossenen Synchronisierungslaufs gelten als verwendbar. `expires_at` entscheidet zwischen aktuell und veraltet; Netzwerkfehler markieren Offlinebetrieb, ohne den letzten vollständigen Snapshot zu löschen. Beliebige interne Fehlertexte werden vor der Ausgabe auf stabile Fehlercodes reduziert.

Die Updatekanäle `stable`, `beta` und `preview` werden als nicht geheime Einstellung in derselben Datenbank gespeichert. Das mitgelieferte Testmanifest wird offline streng geparst und mit einem eingebetteten öffentlichen Ed25519-Schlüssel geprüft. Seine URL liegt absichtlich unter `updates.invalid`; `publicDistribution` bleibt `false`. Es gibt noch keinen Netzwerkabruf, Download oder Installationsaufruf, und kein privater Signaturschlüssel gehört in Repository oder Build.

Alle Tests laufen ohne Netzwerkzugriff und verwenden temporäre, vollständig synthetische Datenbanken:

```powershell
python -m unittest discover -s tests -v
```

Für Laufzeit- und Build-Abhängigkeiten gelten die getrennten, fest versionierten Dateien `requirements-runtime.txt` und `requirements-build.txt`. Der eingefrorene Sidecar wird über `scripts/build_sidecar.py` erzeugt und mit `scripts/smoke_sidecar.py` gegen Startprotokoll, Authentifizierung, PKCE-Start/Abbruch, Datenbankpfad, Migration, Testmanifest, Kanalpersistenz und Shutdown geprüft.
