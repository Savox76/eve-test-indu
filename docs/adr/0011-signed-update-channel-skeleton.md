# ADR-011 – Signiertes Updatekanal-Skelett ohne öffentliche Verteilung

**Status:** Angenommen

**Datum:** 9. September 2026

## Kontext

New Eden Foundry benötigt vor einer späteren automatischen Aktualisierung eine belastbare Grenze zwischen lokal gewähltem Kanal, vertrauenswürdigen Metadaten und tatsächlich ausgelieferten Binärdateien. Arbeitspaket 10 verlangt deshalb eine wählbare Kanalpräferenz und die Prüfung eines signierten Testmanifests, ausdrücklich noch ohne öffentliche Updateverteilung.

Ein vorzeitig aktivierter Netzwerk-Endpunkt oder ein im Repository abgelegter privater Schlüssel würde aus dem Test bereits einen unsicheren Vertriebsweg machen. Gleichzeitig muss die portable Variante ihre nicht geheime Kanalwahl zusammen mit der Datenbank im Programmordner behalten.

## Entscheidung

- Die erlaubten Kanäle heißen `stable`, `beta` und `preview`. Die Oberfläche zeigt sie als „Offiziell“, „Beta“ und „Vorschau / Test“ an.
- Die Auswahl wird als `update_channel` in der Tabelle `app_settings` von `data\foundry.sqlite3` gespeichert. Neue und migrierte Installationen starten sicher mit `stable`.
- Der Sidecar enthält ein kleines, unveränderliches Testmanifest für `preview` und dessen getrennte Ed25519-Signatur. Vor einer Freigabe des lokalen Updater-Status werden Signatur, Schema, Kanal, Version, Zeitpunkt, Plattform, URL und SHA-256 streng geprüft. Doppelte und unbekannte JSON-Felder werden abgewiesen.
- Nur der öffentliche Testschlüssel ist Bestandteil des Quellcodes. Der zur einmaligen Erstellung der Testsignatur verwendete private Schlüssel wurde weder gespeichert noch in Repository, Build oder Release übernommen.
- Die Manifest-URL verwendet die reservierte Domain `updates.invalid`. Zusätzlich melden Sidecar, Tauri-Schale und UI stets `publicDistribution: false`. Es gibt in diesem Arbeitspaket keinen Netzwerkabruf, Download, Installer-Aufruf oder aktiviertes Tauri-Updater-Plugin.
- Die Browser-Oberfläche darf die Kanalwahl nicht vortäuschen. Schreiben ist nur in der laufenden Desktop-App über den authentifizierten Loopback-Sidecar möglich; Sitzungstoken werden der WebView nicht offengelegt.
- Eine spätere produktive Updateverteilung benötigt eine neue Entscheidung für getrennte Produktionsschlüssel, Offline-Signierung, HTTPS-Endpunkte, Artefakt- und Rollbackprüfung sowie das vollständige Windows-Update-Gate. Der private Produktionsschlüssel darf niemals in Repository oder Anwendung liegen.

## Folgen

- Kanalwahl, Persistenz und Vertrauensprüfung können jetzt unabhängig von einem öffentlichen Update-Dienst getestet werden.
- Ein manipuliertes, falsch strukturiertes oder auf einen realen Downloadhost umgebogenes Testmanifest sperrt den Updater-Status.
- Der öffentliche Schlüssel ist kein Geheimnis; seine Aufgabe ist ausschließlich die Signaturprüfung. Ohne den privaten Schlüssel kann die Anwendung keine neuen gültigen Manifeste erzeugen.
- Die Kanalwahl verändert in dieser Ausbaustufe weder die GitHub-Releases noch das Installationsverhalten. Nutzer sehen ausdrücklich, dass Downloads deaktiviert sind.
- Das Testformat ist keine stillschweigende Zusage für das endgültige Produktionsmanifest. Die spätere Tauri-Integration muss deren verpflichtende Update-Signaturen und Plattformformat zusätzlich erfüllen.

## Verifikation

- Backend-Tests prüfen Standardwert, persistente Kanalwechsel und die Ablehnung unbekannter Kanäle.
- Signaturtests prüfen das gebündelte Manifest sowie Manipulation, falschen Kanal, falschen Host und fehlerhafte Base64-Signaturen.
- Sidecar- und Frozen-Smoke-Tests prüfen die authentifizierte Kanaländerung, Schema 5, das mitgelieferte Manifest und die dauerhaft deaktivierte öffentliche Verteilung.
- Frontend-Tests prüfen Desktop-IPC, die sichtbare Kanalwahl und die Ablehnung eines Status, der öffentliche Verteilung behauptet.
- Die Repository-Prüfung verlangt Updater-Quellen, Testmanifest, Signatur, fest versionierte Kryptografie-Abhängigkeit und das Fehlen eines privaten Schlüssels im Updater-Modul.

## Referenzen

- [Tauri 2 Updater Plugin](https://v2.tauri.app/plugin/updater/)
- [Cryptography – Ed25519 signing and verification](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)
