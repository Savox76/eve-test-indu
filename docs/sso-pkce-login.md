# EVE-SSO-PKCE-Login

**Stand:** 9. September 2026  
**Umsetzung:** Arbeitspakete 12 und 13

## Nutzerablauf

1. In der Desktop-App werden die Berechtigungspakete für genau einen Charakter ausgewählt. `industry-core` bleibt das notwendige Basispaket; Markt, PI, Projekte und private Strukturen sind optional.
2. „Charakter verbinden“ erzeugt einen neuen Anmeldeversuch und öffnet die EVE-Anmeldung im Systembrowser. Zugangsdaten werden ausschließlich bei EVE eingegeben.
3. Der lokale Sidecar wartet höchstens drei Minuten am registrierten Callback `http://127.0.0.1:17891/oauth/callback`.
4. Ein korrekter Rückruf startet den PKCE-Codeaustausch. Die App zeigt während der Signatur- und Claim-Prüfung einen eigenen Zustand.
5. Erst eine vollständig geprüfte Identität wird in SQLite gespeichert und in „Verbundene EVE-Charaktere“ angezeigt. Abbruch, EVE-Ablehnung, Token-/JWT-Fehler und Timeout bleiben getrennte Zustände.
6. Weitere Charaktere können anschließend einzeln mit eigenen Berechtigungspaketen autorisiert werden.

## Sicherheitsgrenzen

- Jeder Versuch erhält einen unabhängigen, kryptografisch zufälligen 256-Bit-`state` und einen neuen 256-Bit-PKCE-Verifier.
- Die Challenge ist `BASE64URL(SHA256(verifier))` ohne Padding; EVE erhält ausschließlich die Challenge und `S256`.
- Der Callback lauscht ausschließlich auf IPv4-Loopback und nur am festen Port `17891`. Der `Host`-Header, Pfad, einzelne `state`-Wert und einzelne Autorisierungscode werden streng geprüft.
- Die interne Status-, Start- und Abbruch-API bleibt durch das kurzlebige Sidecar-Sitzungstoken geschützt. Der Browser-Callback ist der einzige absichtlich öffentliche lokale Endpunkt.
- Die Tauri-Schale akzeptiert zum Öffnen nur `https://login.eveonline.com/v2/oauth/authorize` mit vollständigem erwarteten PKCE-Parametersatz. Andere Hosts, Pfade, Protokolle, Fragmente oder doppelte Parameter werden verworfen.
- Autorisierungscode, Tokens, `state` und Verifier erscheinen weder in UI-Antworten noch Logs. Nach Verwendung, Fehler, Timeout, Abbruch oder App-Ende werden temporäre Werte gelöscht und der Listener geschlossen.
- Das Programm enthält und verwendet kein Client Secret.

## Zustände

| Zustand | Bedeutung | Nächste Aktion |
|---|---|---|
| `idle` | Kein Versuch aktiv | Charakteranmeldung starten |
| `waiting` | Systembrowser geöffnet, Callback ausstehend | Abschließen oder abbrechen |
| `exchanging` | Rückruf gültig; Codeaustausch, Signatur und Claims werden geprüft | Prüfung abwarten oder abbrechen |
| `connected` | Geprüfte Charakteridentität wurde lokal gespeichert | Charakter sehen oder weiteren verbinden |
| `cancelled` | Nutzer hat lokal abgebrochen | Erneut starten |
| `timed-out` | Drei-Minuten-Fenster ist abgelaufen | Erneut starten |
| `failed` | EVE-Ablehnung oder ungültiger Callback | Scopes prüfen und erneut starten |

## Bewusste Paketgrenze

Paket 13 führt Codeaustausch und vollständige JWT-Prüfung aus und speichert ausschließlich die geprüfte Identität mit Scopes. Paket 14 übernimmt danach Schlüsselbundspeicherung und atomare Refresh-Token-Rotation. Bis dahin werden Access und Refresh Token nach der Identitätsprüfung verworfen; dadurch ist die Identität sichtbar, aber ESI-Synchronisierung noch nicht möglich.

## Automatisierte Verifikation

- PKCE-Länge, Zeichensatz und Frische von Verifier und Challenge
- exakter Autorisierungsendpunkt und vollständige Parameter einschließlich ausgewählter Scopepakete
- falscher und korrekter `state`, einmalige Callback-Nutzung sowie bereinigte EVE-Ablehnung
- Drei-Minuten-Timeout, manueller Abbruch und Löschen aller temporären Geheimnisse
- authentifizierte Sidecar-Endpunkte in Quell- und Frozen-Smoke-Tests
- native URL-Zielprüfung sowie Start-, Status- und Abbruchvertrag bis zur React-Oberfläche
- Metadaten-/JWKS-Begrenzung, `RS256`-Signatur, Issuer, beide Audience-Werte, Ablauf, Charakter-ID und Scopes
- idempotente Speicherung und sichtbares erneutes Laden des verbundenen Charakters

## Offizielle Quellen

- [EVE Developer Documentation – Single Sign-On](https://developers.eveonline.com/docs/services/sso/)
- [EVE OAuth Authorization Server Metadata](https://login.eveonline.com/.well-known/oauth-authorization-server)
- [RFC 7636 – Proof Key for Code Exchange](https://www.rfc-editor.org/rfc/rfc7636)
- [RFC 8252 – OAuth 2.0 for Native Apps](https://www.rfc-editor.org/rfc/rfc8252)
