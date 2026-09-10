# Zentraler ESI-Client

## Verbindliche Grenze

Sämtliche ESI-Zugriffe von New Eden Foundry laufen durch `EsiClient`. Fachmodule dürfen weder eigene HTTP-Clients noch eigene Retry-, Cache- oder Rate-Limit-Regeln einführen. Der Client akzeptiert ausschließlich relative Pfade und baut daraus Ziele unter `https://esi.evetech.net`; Redirects werden abgewiesen.

Die aktuelle Kompatibilitätsbasis ist bewusst auf `2026-09-09` festgelegt. Jede Anfrage enthält:

- `X-Compatibility-Date: 2026-09-09`
- einen beschreibenden `User-Agent` mit Produktversion, öffentlichem Repository und Kontakt
- `Accept: application/json`
- bei charaktergebundenen Aufrufen einen nur im Prozess bezogenen Bearer Access Token

Eine neue Compatibility-Date ist eine geprüfte Produktänderung und darf nicht automatisch mit dem Kalendertag wandern.

## Authentifizierung und Isolation

Öffentliche Aufrufe benötigen weder Charakter-ID noch Scopes. Charaktergebundene Aufrufe benötigen eine positive ID und mindestens einen konkret erwarteten ESI-Scope. Der angebundene `CharacterTokenService` liefert dafür einen gültigen Access-Token-Lease und rotiert bei Bedarf den separat gespeicherten Refresh Token.

Der Cache-Schlüssel enthält URL und Charakter-ID. Dadurch können Antworten verschiedener Charaktere auch bei identischen Pfaden nicht vermischt werden. Tokenwerte, URLs mit nutzerdefinierten Hosts und Antwortinhalte gelangen nicht in öffentliche Fehlermeldungen.

## HTTP-Cache

Der Client verarbeitet `Cache-Control: max-age` und `Expires`. Solange eine Antwort frisch ist, wird sie ohne Netzaufruf zurückgegeben. Nach Ablauf sendet der Client vorhandene Validatoren als `If-None-Match` und `If-Modified-Since`. Eine gültige `304 Not Modified`-Antwort reaktiviert ausschließlich einen vorhandenen, charaktergebundenen Cacheeintrag. `Cache-Control: no-store` verhindert die Ablage.

Alle JSON-Antworten sind größenbegrenzt, müssen UTF-8 sein und dürfen keine doppelten Objektschlüssel enthalten.

## Wiederholungen, Fehlerbudget und Circuit Breaker

Nur Netzwerkfehler sowie HTTP `408`, `420`, `425`, `429`, `500`, `502`, `503` und `504` sind wiederholbar. Standardmäßig gibt es höchstens drei Versuche. `Retry-After` wird bis zur festen Obergrenze beachtet; andernfalls verwendet der Client begrenzten exponentiellen Backoff mit Jitter.

`X-ESI-Error-Limit-Remain` und `X-ESI-Error-Limit-Reset` aktualisieren ein gemeinsames Fehlerbudget. Unterhalb der Reserve werden weitere Aufrufe bis zum gemeldeten Reset gestoppt. Wiederholte transiente Fehler öffnen den Circuit Breaker; nach der Cooldown-Zeit ist ein neuer Versuch möglich. Ein Erfolg setzt die Fehlerserie zurück.

Der Sidecar meldet Zustand, Compatibility-Date, verbleibendes Fehlerbudget, Reset-Zeit und Anzahl der Cacheeinträge über seinen authentifizierten Health-Status. Diese Metadaten enthalten keine Zugangsdaten.

## Verifikation

Deterministische Tests verwenden ausschließlich synthetische Transportantworten. Sie prüfen Header und Zielbegrenzung, charaktergetrennte Autorisierung, frischen Cache, bedingte 304-Revalidierung, `no-store`, Retry-After, Fehlerbudget, Circuit Breaker, Recovery, Größenlimit, striktes JSON und redigierte Fehler. Der Frozen-Sidecar-Smoke-Test bestätigt, dass dieselbe ESI-Policy im Windows-Paket aktiv ist.

## Referenzen

- [EVE Developer Documentation – ESI overview](https://developers.eveonline.com/docs/services/esi/overview/)
- [EVE Developer Documentation – ESI best practices](https://developers.eveonline.com/docs/services/esi/best-practices/)
- [ADR-006 – Cache-first-Synchronisierung](adr/0006-cache-first-sync.md)
