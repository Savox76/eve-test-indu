NEW EDEN FOUNDRY - PORTABLE WINDOWS VERSION
============================================

DEUTSCH
-------

1. Das ZIP-Archiv vollständig an einen beliebigen beschreibbaren Ort entpacken,
   zum Beispiel auf den Desktop, einen USB-Stick oder in einen eigenen Ordner.
2. "New Eden Foundry.exe" aus dem entpackten Ordner starten.
3. Die Anwendung benötigt keine Installation und keine Administratorrechte.

"Portable" bedeutet einen vollständig entpackten, verschiebbaren Programmordner.
Es bedeutet nicht, dass die App innerhalb des ZIP-Archivs oder als einzelne EXE
ohne die mitgelieferten Dateien ausgeführt wird.

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
- Der gewählte Update-Kanal wird lokal in der Datenbank gespeichert. Die App
  prüft beim Start und auf Knopfdruck, ob ein vollständiges neueres GitHub
  Release vorliegt, und öffnet auf Wunsch dessen exakte Release-Seite.
- Download und automatische Installation bleiben deaktiviert, bis produktiv
  signierte Pakete, Rollback und das Windows-Update-Gate bereitstehen.
- Zum Umziehen oder Sichern die Anwendung zuerst schließen und anschließend den
  vollständigen Programmordner einschließlich "data" kopieren.
- Portables Update: App vollständig schließen und den Ordner "data" zusätzlich
  sichern. Die neue ZIP entweder am bisherigen Ort entpacken und nur die
  ausgelieferten Programmdateien ersetzen, oder in einen neuen beliebigen
  Ordner entpacken und den bisherigen Ordner "data" dorthin kopieren. Ein
  Installationsordner wird dafür niemals benötigt. Danach die EXE starten und
  die neue Versionsnummer sowie vorhandene Charaktere und Pläne prüfen.
- Beim einmaligen Wechsel von einer älteren, versionsabhängigen Ausgabe den
  bisherigen "data"-Ordner nach "New Eden Foundry Portable" kopieren.
- Spätere EVE-Zugangsdaten bleiben im Windows-Anmeldespeicher und werden beim
  Kopieren des Programmordners nicht mitgeführt.

Integrität prüfen (PowerShell):
  Get-FileHash -Algorithm SHA256 .\New.Eden.Foundry_<VERSION>_x64-portable.zip

Den erwarteten Hash enthält die gleichnamige Datei mit der Endung ".sha256"
auf der GitHub-Release-Seite.


ENGLISH
-------

1. Fully extract the ZIP archive to any writable location, for example the
   desktop, a USB drive, or another folder of your choice.
2. Run "New Eden Foundry.exe" from the extracted folder.
3. The application requires no installation and no administrator privileges.

"Portable" means a fully extracted, movable application folder. It does not
mean running the app inside the ZIP archive or as one EXE without its bundled
files.

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
- The selected update channel is stored locally in the database. On startup and
  on demand, the app checks for a complete newer GitHub Release and can open
  its exact release page.
- Download and automatic installation remain disabled until production-signed
  packages, rollback, and the Windows update gate are available.
- To move or back up the app, close it first and then copy the complete program
  folder including "data".
- Portable update: close the app completely and make an additional backup of
  the "data" folder. Either extract the new ZIP at the existing location and
  replace only the bundled application files, or extract it to any new folder
  and copy the previous "data" folder there. An installer directory is never
  required. Start the EXE and verify the new version plus existing characters
  and plans.
- When moving once from an older version-specific package, copy its existing
  "data" directory into "New Eden Foundry Portable".
- Future EVE credentials remain in Windows Credential Manager and do not travel
  with a copied program folder.

Verify integrity (PowerShell):
  Get-FileHash -Algorithm SHA256 .\New.Eden.Foundry_<VERSION>_x64-portable.zip

The expected hash is published in the file with the matching name and the
".sha256" suffix on the GitHub Release page.
