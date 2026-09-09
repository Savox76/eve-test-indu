# ADR-004: EVE SSO mit PKCE, Systembrowser und Betriebssystem-Schlüsselbund

- **Status:** Angenommen
- **Datum:** 7. September 2026
- **Entscheider:** Projektverantwortlicher

## Kontext

Eine ausgelieferte Desktop-Anwendung kann ein Client Secret nicht vertraulich halten. Gleichzeitig benötigen einzelne Funktionen autorisierten ESI-Zugriff pro Charakter. Anmeldung und Tokenablage sind deshalb eine zentrale Sicherheitsgrenze.

## Entscheidung

New Eden Foundry nutzt EVE SSO mit Authorization Code und PKCE (`S256`) als öffentlicher Client.

- Die Anwendung liefert kein Client Secret aus.
- Anmeldung erfolgt im Systembrowser direkt bei EVE.
- Pro Anmeldeversuch werden ein kryptografischer `state`-Wert und ein neuer PKCE-Verifier erzeugt und nach einmaliger Nutzung verworfen.
- Es gibt genau eine fest registrierte Loopback-Callback-URI. Sie ist vom dynamischen Port der internen Sidecar-API getrennt.
- Die exakte URI `http://127.0.0.1:17891/oauth/callback` ist in [ADR-012](0012-fixed-eve-sso-registration-profile.md) und dem maschinenlesbaren Registrierungsprofil festgelegt. Vor Login-Implementierung wird sie mit der tatsächlich akzeptierten Portalregistrierung abgeglichen.
- Callback mit falschem `state`, verspäteter Callback, Abbruch und bereits verwendeter Code werden abgewiesen.
- Endpunkte werden aus der offiziellen OAuth-Metadatenadresse bezogen und angemessen gecacht.
- Access Tokens werden anhand von Signatur/JWKS, Issuer, erwarteter Audience, Ablauf und Charakterbindung validiert.
- Refresh Tokens liegen pro Charakter im Betriebssystem-Schlüsselbund. Rotation wird atomar gespeichert; erst danach wird der alte Wert verworfen.
- Scopes werden als kleinste funktionsbezogene Pakete und erst bei Aktivierung angefordert.
- Tokens und Authorization Codes erscheinen nie in Logs, Diagnosepaketen oder Repository-Daten.

## Folgen

Eine nutzbare Client-ID und exakte Callback-URI müssen im EVE Developers Portal registriert werden. Schlüsselbundzugriff benötigt plattformspezifische Tests. Ein Charakter kann verbunden bleiben, obwohl einzelne optionale Scopepakete fehlen; die UI muss diesen Zustand erklären.

## Verifikation

Tests decken PKCE-Vektor, `state`, Callback-Bindung, Timeout, JWT-Fehler, Scope-Differenz und atomare Refresh-Token-Rotation ab. Ein Golden-Pfad funktioniert ohne Client Secret in Paket oder Prozessumgebung.

### Umsetzungsstand Pakete 12 bis 14

Systembrowser, fester IPv4-Loopback-Listener, unabhängiger 256-Bit-`state`, neuer 256-Bit-Verifier mit `S256`-Challenge, funktionsbezogene Scopeauswahl, Drei-Minuten-Timeout und manueller Abbruch sind implementiert. Der native Shell-Prozess öffnet nur eine vollständig geprüfte URL unter dem festen EVE-Autorisierungsendpunkt. Die Sidecar-API gibt weder `state` noch Verifier oder Autorisierungscode an die Weboberfläche zurück.

Paket 13 tauscht den Code über den aus den offiziellen Metadaten bezogenen Token-Endpunkt aus. Metadaten-, Token- und JWKS-Ziele sind auf HTTPS bei `login.eveonline.com` begrenzt; HTTP-Weiterleitungen werden nicht verfolgt. Das Access Token muss `RS256`, eine eindeutige veröffentlichte Schlüssel-ID, gültige Signatur, akzeptierten Issuer, die Audiences `EVE Online` und öffentliche Client-ID, gültigen Ablauf, ein Charakter-Subject, Name sowie mindestens alle angeforderten Scopes enthalten. Erst danach werden ID, Name und Scopes gespeichert.

Paket 14 hält Access Tokens ausschließlich im Prozessspeicher und speichert geprüfte Refresh Tokens pro Charakter als generische Zugangsdaten des aktuellen Windows-Nutzers. Ein neuer Wert wird zuerst in einem getrennten Zwischen-Slot geschrieben und zurückgelesen, dann als aktiv ersetzt und erneut geprüft; erst danach verschwindet der Zwischen-Slot. Bei einer Unterbrechung bleibt der bisherige aktive Token erhalten und ein vollständig geschriebener Kandidat wird beim nächsten Zugriff abgeschlossen. Eine Vergleichsprüfung verhindert, dass konkurrierende Rotationen einen neueren Token überschreiben. Andere Plattformen oder ein nicht verfügbarer Anmeldespeicher schlagen geschlossen fehl.

## Referenzen

- [EVE Developer Documentation – SSO](https://developers.eveonline.com/docs/services/sso/)
- [OAuth 2.0 Authorization Server Metadata](https://login.eveonline.com/.well-known/oauth-authorization-server)
- [RFC 8252 – OAuth 2.0 for Native Apps](https://www.rfc-editor.org/rfc/rfc8252)
