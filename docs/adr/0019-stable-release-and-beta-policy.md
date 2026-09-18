# ADR-019 – Normale Releases und eindeutig getrennte Betas

**Status:** Angenommen

**Datum:** 18. September 2026

**Ersetzt teilweise:** ADR-011 und ADR-017

## Kontext

Die historisch wählbaren Kanäle `stable`, `beta` und `preview` vermischen technische Teststufen mit der Frage, welche Version normalen Nutzern als Update angeboten wird. Frühere `preview`- und `alpha`-Versionen waren auf GitHub zwar als Pre-Releases markiert, die Anwendung konnte sie über einen gewählten Kanal dennoch als neue Version melden.

Künftig sollen abgeschlossene Arbeitspakete normale Releases sein. Betas bleiben möglich, dienen aber ausschließlich einer bewussten manuellen Vorabprüfung und dürfen niemals in den normalen Updatepfad gelangen. Ihre Einordnung muss sowohl im Repository als auch auf der GitHub-Release-Seite eindeutig erkennbar sein.

## Entscheidung

- Ein normales Release verwendet ausschließlich `vX.Y.Z`. `package.json`, Cargo-Metadaten, Tag, Release-Titel und Paketnamen tragen dieselbe suffixlose Version. GitHub veröffentlicht es nicht als Pre-Release und markiert es als `Latest`.
- Eine Beta verwendet ausschließlich `vX.Y.Z-beta.N` mit positiver fortlaufender Nummer. Versionsdateien, Tag und Paketnamen tragen diesen Zusatz; der Release-Titel enthält zusätzlich `BETA`, und GitHub markiert die Version als Pre-Release.
- Neue `alpha`-, `preview`-, `rc`- oder andere Vorabkennzeichen sind nicht zulässig. Historische Tags und Releases bleiben unverändert.
- Der öffentliche Update-Manager besitzt nur den stabilen Pfad. Er akzeptiert ein Release ausschließlich, wenn dessen Version keinen Vorabzusatz trägt, GitHub `prerelease: false` meldet und alle vier erwarteten Windows-Dateien vollständig hochgeladen sind.
- Die doppelte Prüfung von Version und GitHub-Merkmal ist absichtlich redundant: Eine falsch markierte Beta bleibt wegen ihres Suffix ausgeschlossen; ein suffixloses Release mit Pre-Release-Merkmal bleibt ebenfalls ausgeschlossen.
- Die Kanalwahl wird aus der Oberfläche entfernt. Schema 15 setzt gespeicherte historische Werte `beta` oder `preview` auf `stable`. Sidecar, Tauri-Brücke und Frontend akzeptieren im öffentlichen Status nur noch `stable`.
- Das signierte Offline-Testmanifest aus ADR-011 bleibt ein nicht verteilender Kryptografie-Test unter `updates.invalid`. Sein historischer interner `preview`-Wert ist kein öffentlicher Updatekanal.
- Nach einer erfolgreichen Beta-Abnahme wird die Zielversion ohne `-beta.N` als normales Release veröffentlicht. Notwendige Korrekturen aus der Abnahme dürfen zuvor einfließen.

## Folgen

Normale Nutzer erhalten nur fertige normale Releases als Updatehinweis. Tester können Betas weiterhin direkt auf der GitHub-Release-Seite erkennen und manuell beziehen. Alte Installationen verlieren keine Fachdaten; lediglich ihre nicht mehr unterstützte Kanalpräferenz wird auf den stabilen Pfad zurückgesetzt.

Der Release-Workflow stoppt ungültige Versionsnamen vor dem Windows-Build. Eine Beta kann nicht versehentlich als `Latest` veröffentlicht werden, und ein normales Release kann nicht versehentlich als Beta-Titel erscheinen.

## Verifikation

- Backendtests prüfen, dass Beta-Tags auch bei einem fälschlich fehlenden GitHub-Pre-Release-Merkmal ignoriert werden.
- Backendtests prüfen, dass suffixlose Versionen mit gesetztem Pre-Release-Merkmal ebenfalls ignoriert werden.
- Ein Migrationstest startet mit einem gespeicherten Beta-Kanal in Schema 14 und erwartet nach Schema 15 `stable`.
- Frontend- und Tauri-Verträge akzeptieren ausschließlich den Kanal `stable`; die Oberfläche zeigt keine Kanalwahl mehr.
- Repository- und Release-Preflight erlauben nur `X.Y.Z` oder `X.Y.Z-beta.N` und erzeugen entsprechend normale Releases oder klar bezeichnete GitHub-Pre-Releases.

## Referenzen

- [ADR-011: Signiertes Updatekanal-Skelett](0011-signed-update-channel-skeleton.md)
- [ADR-017: Öffentlicher Release-Hinweis](0017-public-release-advisory-and-portable-updates.md)
- [Release-Regeln](../RELEASING.md)
