# Python-Backend

Dieses Verzeichnis enthält den lokalen fachlichen Kern von New Eden Foundry. Die aktuelle Ausbaustufe umfasst den gebündelten FastAPI-Sidecar, die versionierte SQLite-Grundlage mit automatischer Migrationssicherung und Wiederherstellung, lokale Kontogruppen, getrennte Charakterdatensätze und deren jeweilige SSO-Scopes. Tauri startet den Dienst als Kindprozess auf einem dynamischen Loopback-Port und übergibt das kurzlebige Sitzungstoken ausschließlich über die Standardeingabe.

EVE autorisiert jeden Charakter einzeln. Eine lokale Kontogruppe dient nur der vom Nutzer vergebenen Organisation mehrerer Charaktere; sie speichert weder EVE-Accountnamen noch Zugangsdaten. Token werden in einer späteren Ausbaustufe pro Charakter im Windows-Anmeldespeicher abgelegt und gehören nicht in SQLite.

Der Selbsttest lässt sich aus diesem Verzeichnis ausführen:

```powershell
python -m new_eden_foundry_backend --database .\foundry-development.sqlite3
```

Die erzeugte Entwicklungsdatenbank ist durch die Repository-Regeln vom Commit ausgeschlossen. Beim normalen App-Start liegt die produktive Datenbank ausschließlich unter `data\foundry.sqlite3` neben der Hauptanwendung; ein nicht beschreibbarer Programmordner führt zu einem sichtbaren Startfehler und nie zu einem versteckten Ersatzpfad. Vor jeder anstehenden Migration wird über die SQLite-Backup-API ein eigenständiger Snapshot unter `data\backups` erstellt, geprüft und mit SHA-256 in der Datenbankhistorie vermerkt. Ein Migrationsfehler löst die verifizierte Wiederherstellung aus; die fünf neuesten Snapshots werden aufbewahrt.

Alle Tests laufen ohne Netzwerkzugriff und verwenden temporäre, vollständig synthetische Datenbanken:

```powershell
python -m unittest discover -s tests -v
```

Für Laufzeit- und Build-Abhängigkeiten gelten die getrennten, fest versionierten Dateien `requirements-runtime.txt` und `requirements-build.txt`. Der eingefrorene Sidecar wird über `scripts/build_sidecar.py` erzeugt und mit `scripts/smoke_sidecar.py` gegen Startprotokoll, Authentifizierung, Datenbankpfad und Shutdown geprüft.
