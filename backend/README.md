# Python-Backend

Dieses Verzeichnis enthält den lokalen fachlichen Kern von New Eden Foundry. In der ersten Ausbaustufe stehen die versionierte SQLite-Grundlage und ein lokaler Selbsttest bereit. Ein Netzwerkdienst wird noch nicht gestartet.

Der Selbsttest lässt sich aus diesem Verzeichnis ausführen:

```powershell
python -m new_eden_foundry_backend --database .\foundry-development.sqlite3
```

Die erzeugte Entwicklungsdatenbank ist durch die Repository-Regeln vom Commit ausgeschlossen. Produktive Daten werden später ausschließlich im Windows-Anwendungsdatenverzeichnis angelegt.

Alle Tests laufen ohne Netzwerkzugriff und verwenden temporäre, vollständig synthetische Datenbanken:

```powershell
python -m unittest discover -s tests -v
```
