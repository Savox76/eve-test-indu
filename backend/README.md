# Python-Backend

Dieses Verzeichnis enthält den lokalen fachlichen Kern von New Eden Foundry. Die aktuelle Ausbaustufe umfasst den gebündelten FastAPI-Sidecar, die versionierte SQLite-Grundlage mit automatischer Migrationssicherung und Wiederherstellung, cache-first Startzustände, lokale Kontogruppen, getrennte Charakterdatensätze und deren jeweilige SSO-Scopes. Hinzu kommt das Updater-Skelett mit lokaler Kanalpräferenz und einem gebündelten Ed25519-signierten Testmanifest. Tauri startet den Dienst als Kindprozess auf einem dynamischen Loopback-Port und übergibt das kurzlebige Sitzungstoken ausschließlich über die Standardeingabe.

Der Sidecar bündelt außerdem das öffentliche, noch nicht aktivierte EVE-SSO-Registrierungsprofil. Der Selbsttest meldet dessen Zustand als `pending-client-id`, bis die echte Client-ID aus dem EVE Developers Portal eingetragen ist. Das Profil enthält ausdrücklich kein Client Secret.

EVE autorisiert jeden Charakter einzeln. Eine lokale Kontogruppe dient nur der vom Nutzer vergebenen Organisation mehrerer Charaktere; sie speichert weder EVE-Accountnamen noch Zugangsdaten. Token werden in einer späteren Ausbaustufe pro Charakter im Windows-Anmeldespeicher abgelegt und gehören nicht in SQLite.

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

Für Laufzeit- und Build-Abhängigkeiten gelten die getrennten, fest versionierten Dateien `requirements-runtime.txt` und `requirements-build.txt`. Der eingefrorene Sidecar wird über `scripts/build_sidecar.py` erzeugt und mit `scripts/smoke_sidecar.py` gegen Startprotokoll, Authentifizierung, Datenbankpfad, Migration, Testmanifest, Kanalpersistenz und Shutdown geprüft.
