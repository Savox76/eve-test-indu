NEW EDEN FOUNDRY - PORTABLE WINDOWS VERSION
============================================

DEUTSCH
-------

1. Das ZIP-Archiv vollständig in einen eigenen Ordner entpacken.
2. "New Eden Foundry.exe" aus dem entpackten Ordner starten.
3. Die Anwendung benötigt keine Installation und keine Administratorrechte.

Wichtig:
- Die EXE nicht direkt aus der ZIP-Vorschau des Explorers starten.
- Microsoft Edge WebView2 Runtime wird benötigt. Sie ist in unterstützten,
  aktuellen Windows-10- und Windows-11-Systemen normalerweise bereits enthalten.
- Diese Preview ist noch nicht code-signiert. Windows kann deshalb vor einem
  unbekannten Herausgeber warnen.
- Beim ersten Start entsteht im Programmordner "data\foundry.sqlite3". Der
  entpackte Ordner muss deshalb beschreibbar sein. Es wird kein versteckter
  Ersatzpfad verwendet.
- Vor einer notwendigen Datenbankmigration legt die App automatisch eine
  geprüfte Sicherung unter "data\backups" an. Bei einem Migrationsfehler wird
  der vorherige Stand automatisch wiederhergestellt. Die fünf neuesten
  Migrationssicherungen bleiben erhalten.
- Offline oder veraltete lokale Daten bleiben sichtbar und werden mit ihrem
  Datenalter gekennzeichnet; ein fehlgeschlagener Folgelauf leert den Cache nicht.
- Der gewählte Update-Kanal wird lokal in der Datenbank gespeichert. In dieser
  Preview sind Downloads und automatische Installation noch deaktiviert; neue
  Versionen werden weiterhin manuell von GitHub Releases geladen.
- Zum Umziehen oder Sichern die Anwendung zuerst schließen und anschließend den
  vollständigen Programmordner einschließlich "data" kopieren.
- Spätere EVE-Zugangsdaten bleiben im Windows-Anmeldespeicher und werden beim
  Kopieren des Programmordners nicht mitgeführt.

Integrität prüfen (PowerShell):
  Get-FileHash -Algorithm SHA256 .\New.Eden.Foundry_<VERSION>_x64-portable.zip

Den erwarteten Hash enthält die gleichnamige Datei mit der Endung ".sha256"
auf der GitHub-Release-Seite.


ENGLISH
-------

1. Extract the complete ZIP archive into its own folder.
2. Run "New Eden Foundry.exe" from the extracted folder.
3. The application requires no installation and no administrator privileges.

Important:
- Do not run the executable directly from File Explorer's ZIP preview.
- Microsoft Edge WebView2 Runtime is required. It is normally already included
  with supported, up-to-date Windows 10 and Windows 11 systems.
- This preview is not code-signed yet. Windows may therefore warn about an
  unknown publisher.
- The first start creates "data\foundry.sqlite3" inside the program folder. The
  extracted folder must therefore be writable. No hidden fallback path is used.
- Before a required database migration, the app automatically creates a
  verified backup under "data\backups". A failed migration automatically
  restores the previous state. The five newest migration backups are retained.
- Offline or stale local data remains visible and is labelled with its age; a
  failed follow-up run does not empty the cache.
- The selected update channel is stored locally in the database. Downloads and
  automatic installation remain disabled in this preview; new versions are
  still downloaded manually from GitHub Releases.
- To move or back up the app, close it first and then copy the complete program
  folder including "data".
- Future EVE credentials remain in Windows Credential Manager and do not travel
  with a copied program folder.

Verify integrity (PowerShell):
  Get-FileHash -Algorithm SHA256 .\New.Eden.Foundry_<VERSION>_x64-portable.zip

The expected hash is published in the file with the matching name and the
".sha256" suffix on the GitHub Release page.
