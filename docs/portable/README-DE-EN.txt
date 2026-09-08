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
- "Portable" bezeichnet die Anwendungsauslieferung ohne Installation. Diese
  Preview legt noch keine Fachdatenbank an. Künftige Versionen speichern lokale
  Daten weiterhin sicher im Windows-Benutzerprofil und Zugangsdaten im
  Windows-Anmeldespeicher. Die ZIP ist daher kein spurenloser USB-Modus.

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
- "Portable" describes distribution without installation. This preview does not
  create a production database yet. Future versions will still keep local data
  safely in the Windows user profile and credentials in Windows Credential
  Manager. The ZIP is therefore not a traceless USB mode.

Verify integrity (PowerShell):
  Get-FileHash -Algorithm SHA256 .\New.Eden.Foundry_<VERSION>_x64-portable.zip

The expected hash is published in the file with the matching name and the
".sha256" suffix on the GitHub Release page.
