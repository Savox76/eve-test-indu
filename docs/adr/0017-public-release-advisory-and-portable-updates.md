# ADR-017: Öffentlicher Release-Hinweis und Portable-Updates

- **Status:** Angenommen
- **Datum:** 11. September 2026
- **Ergänzt:** ADR-011 und ADR-013

## Kontext

Installer und portable ZIP werden bereits gemeinsam mit ihren SHA-256-Dateien an einem öffentlichen GitHub Release veröffentlicht. Nutzer der portablen Ausgabe benötigen einen verlässlichen Hinweis auf neue Versionen und einen updatefesten Ablauf. Eine automatische Ersetzung ausführbarer Dateien wäre ohne produktive Paketsignatur, getrennt verwalteten privaten Schlüssel, Rollback und bestandenem Windows-Gate jedoch keine ausreichende Vertrauenskette.

## Entscheidung

- Die Desktop-App fragt nach dem Start und auf Nutzerwunsch ausschließlich die öffentliche Release-Liste des festen Repositorys `Savox76/eve-test-indu` ab.
- Der gespeicherte Kanal `stable`, `beta` oder `preview` filtert die berücksichtigten Versionen.
- Ein Release gilt erst als vollständig, wenn Installer, portable ZIP und beide exakt benannten SHA-256-Dateien veröffentlicht sind.
- Die Antwort ist nur ein Hinweis. Sie enthält stets `automaticInstall: false`; es wird nichts heruntergeladen, entpackt oder ausgeführt.
- Der Öffnen-Befehl akzeptiert nur eine semantische Version und erzeugt daraus selbst die exakte HTTPS-URL der GitHub-Release-Seite. Eine vom Netzwerk gelieferte beliebige URL wird nicht ausgeführt.
- Die Laufzeit erkennt anhand des portablen Markers, ob die installierte oder portable Anleitung angezeigt wird.
- Für ein portables Update wird die App vollständig geschlossen und die neue ZIP in denselben übergeordneten Ordner entpackt. Der konstante Archivordner `New Eden Foundry Portable` wird aktualisiert; der nicht ausgelieferte Unterordner `data` bleibt erhalten. Vorher ist eine Kopie von `data` die empfohlene zusätzliche Sicherung.

Eine automatische Download-/Installationsfunktion wird erst in einem eigenen Arbeitspaket freigegeben, wenn reale Pakete mit dem Tauri-Updater-Format produktiv signiert sind, der öffentliche Schlüssel fest in der App verankert ist und Sicherung, Prozessende, Installation, Neustart, Migrationsprüfung und Rollback das Windows-Gate bestanden haben.

## Folgen

Die App informiert installierte und portable Nutzer automatisch über vollständig veröffentlichte Versionen, ohne den bisherigen Sicherheitsvertrag des nicht verteilenden Updater-Skeletts zu umgehen. Portable Daten bleiben bei dem dokumentierten In-place-Entpacken erhalten. Der Nutzer muss Paket und Prüfsumme bis zur produktiv signierten Updatekette weiterhin selbst beziehen und die Anwendung vor dem Ersetzen schließen.

Ein GitHub- oder Netzwerkfehler blockiert den App-Start nicht. Er erscheint als erneuter Prüfhinweis; lokale Fachdaten bleiben unverändert.

## Verifikation

- Backendtests prüfen Kanalfilter, Versionsordnung, exakte Release-URL, vollständige vierteilige Release-Dateien und fehlerhafte Antworten.
- Tauri und Frontend weisen unbekannte Zustände, fremde URLs und inkonsistente Felder ab.
- Der Release-Workflow prüft weiterhin Installer, portable ZIP und beide SHA-256-Dateien vor Veröffentlichung.
- Die manuelle Windows-Abnahme prüft Hinweis, Linkziel, In-place-Entpacken, Datenfortbestand und Start der neuen Version.

## Referenzen

- [GitHub REST API: Releases](https://docs.github.com/en/rest/releases/releases)
- [Tauri Updater](https://v2.tauri.app/plugin/updater/)
- [ADR-011: Signiertes Updatekanal-Skelett](0011-signed-update-channel-skeleton.md)
- [ADR-013: Updatefeste Anwendungsdaten](0013-update-stable-application-data.md)
