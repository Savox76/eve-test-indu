# Python-Backend

Dieses Verzeichnis enthält den lokalen fachlichen Kern von New Eden Foundry. Die aktuelle Ausbaustufe umfasst die versionierte SQLite-Grundlage, lokale Kontogruppen, getrennte Charakterdatensätze und deren jeweilige SSO-Scopes. Ein Netzwerkdienst wird noch nicht gestartet.

EVE autorisiert jeden Charakter einzeln. Eine lokale Kontogruppe dient nur der vom Nutzer vergebenen Organisation mehrerer Charaktere; sie speichert weder EVE-Accountnamen noch Zugangsdaten. Token werden in einer späteren Ausbaustufe pro Charakter im Windows-Anmeldespeicher abgelegt und gehören nicht in SQLite.

Der Selbsttest lässt sich aus diesem Verzeichnis ausführen:

```powershell
python -m new_eden_foundry_backend --database .\foundry-development.sqlite3
```

Die erzeugte Entwicklungsdatenbank ist durch die Repository-Regeln vom Commit ausgeschlossen. Produktive Daten werden später ausschließlich im Windows-Anwendungsdatenverzeichnis angelegt.

Alle Tests laufen ohne Netzwerkzugriff und verwenden temporäre, vollständig synthetische Datenbanken:

```powershell
python -m unittest discover -s tests -v
```
