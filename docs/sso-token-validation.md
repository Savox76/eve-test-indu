# EVE-SSO-Token- und Charakterprüfung

**Stand:** 9. September 2026  
**Umsetzung:** Arbeitspaket 13

## Vertrauenskette

1. Der lokale Callback akzeptiert genau einen Code mit dem zum Versuch gehörenden `state`.
2. Der Sidecar tauscht Code, öffentliche Client-ID und den nur dort gehaltenen PKCE-Verifier am von EVE veröffentlichten Token-Endpunkt aus. Ein Client Secret wird nicht verwendet.
3. Die OAuth-Metadatenadresse muss Issuer, Autorisierungs-, Token- und JWKS-Endpunkt unter HTTPS auf `login.eveonline.com` liefern. Weiterleitungen werden abgewiesen.
4. Das Access Token wird ausschließlich als JWT mit `RS256` und genau passendem `kid` aus dem JWKS akzeptiert.
5. Signatur, EVE-Issuer, die Audiences `EVE Online` und die öffentliche Client-ID, Ablauf, optionaler Gültigkeitsbeginn, `CHARACTER:EVE:<id>`, Name und bestätigte Scopes werden gemeinsam geprüft.
6. Erst danach werden Charakter-ID, Name und Scopes atomar in `data\foundry.sqlite3` eingefügt oder aktualisiert und über die geschützte lokale Charakterliste an die Oberfläche gegeben.

Kein Access Token, Refresh Token, Autorisierungscode, `state` oder PKCE-Verifier wird an React/Tauri übergeben, geloggt oder in SQLite gespeichert. Bis Arbeitspaket 14 werden die erhaltenen Tokens unmittelbar nach der Identitätsprüfung verworfen.

## Sichtbares Verhalten

- `waiting`: EVE-Anmeldung oder Charakterauswahl im Systembrowser läuft.
- `exchanging`: Callback ist gebunden; Token, Signatur und Claims werden geprüft.
- `connected`: geprüfter Charakter wurde gespeichert und erscheint in der Liste „Verbundene EVE-Charaktere“.
- `failed`: keine Identität wird gespeichert; die Oberfläche zeigt nur einen bereinigten Fehlerzustand.

Eine Autorisierung aus Paket 12 kann nicht nachträglich übernommen werden, weil der einmalige Code dort absichtlich verworfen wurde. Der Charakter wird deshalb mit Paket 13 genau einmal neu verbunden.

## Automatisierte Verifikation

- erfolgreicher PKCE-Codeaustausch ohne Client Secret
- Metadaten- und JWKS-Ziele ausschließlich bei EVE SSO
- Ablehnung von Weiterleitungen, übergroßen oder strukturell falschen Antworten
- `RS256`-Signatur und eindeutige Schlüssel-ID
- gültiger Issuer sowie beide erforderlichen Audience-Werte
- Ablauf, `nbf`, `iat`, Charakter-Subject, Name und Scope-Vollständigkeit
- keine Speicherung bei irgendeinem Token-, JWT- oder Datenbankfehler
- idempotentes Wiederverbinden und sichtbares Laden mehrerer Charaktere aus SQLite

## Offizielle Quelle

- [EVE Developer Documentation – Single Sign-On](https://developers.eveonline.com/docs/services/sso/)
- [EVE OAuth Authorization Server Metadata](https://login.eveonline.com/.well-known/oauth-authorization-server)
