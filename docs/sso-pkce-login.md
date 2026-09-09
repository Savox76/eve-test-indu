# EVE-SSO-PKCE-Login

**Stand:** 9. September 2026  
**Umsetzung:** Arbeitspaket 12

## Nutzerablauf

1. In der Desktop-App werden die Berechtigungspakete für genau einen Charakter ausgewählt. `industry-core` bleibt das notwendige Basispaket; Markt, PI, Projekte und private Strukturen sind optional.
2. „Charakter verbinden“ erzeugt einen neuen Anmeldeversuch und öffnet die EVE-Anmeldung im Systembrowser. Zugangsdaten werden ausschließlich bei EVE eingegeben.
3. Der lokale Sidecar wartet höchstens drei Minuten am registrierten Callback `http://127.0.0.1:17891/oauth/callback`.
4. Ein korrekter Rückruf bestätigt die Autorisierung in App und Browser. Abbruch, EVE-Ablehnung, ungültiger Rückruf und Timeout werden als getrennte Zustände angezeigt.
5. Weitere Charaktere können anschließend einzeln mit eigenen Berechtigungspaketen autorisiert werden. Die gemeinsame Übersicht und jede Einzelansicht bleiben das Zielmodell.

## Sicherheitsgrenzen

- Jeder Versuch erhält einen unabhängigen, kryptografisch zufälligen 256-Bit-`state` und einen neuen 256-Bit-PKCE-Verifier.
- Die Challenge ist `BASE64URL(SHA256(verifier))` ohne Padding; EVE erhält ausschließlich die Challenge und `S256`.
- Der Callback lauscht ausschließlich auf IPv4-Loopback und nur am festen Port `17891`. Der `Host`-Header, Pfad, einzelne `state`-Wert und einzelne Autorisierungscode werden streng geprüft.
- Die interne Status-, Start- und Abbruch-API bleibt durch das kurzlebige Sidecar-Sitzungstoken geschützt. Der Browser-Callback ist der einzige absichtlich öffentliche lokale Endpunkt.
- Die Tauri-Schale akzeptiert zum Öffnen nur `https://login.eveonline.com/v2/oauth/authorize` mit vollständigem erwarteten PKCE-Parametersatz. Andere Hosts, Pfade, Protokolle, Fragmente oder doppelte Parameter werden verworfen.
- Autorisierungscode, `state` und Verifier erscheinen weder in UI-Antworten noch Logs. Nach Erfolg, Fehler, Timeout, Abbruch oder App-Ende werden die temporären Werte gelöscht und der Listener geschlossen.
- Das Programm enthält und verwendet kein Client Secret.

## Zustände

| Zustand | Bedeutung | Nächste Aktion |
|---|---|---|
| `idle` | Kein Versuch aktiv | Charakteranmeldung starten |
| `waiting` | Systembrowser geöffnet, Callback ausstehend | Abschließen oder abbrechen |
| `authorization-received` | `state` und einmaliger Code wurden gültig empfangen | Weiteren Charakter autorisieren oder auf Paket 13 warten |
| `cancelled` | Nutzer hat lokal abgebrochen | Erneut starten |
| `timed-out` | Drei-Minuten-Fenster ist abgelaufen | Erneut starten |
| `failed` | EVE-Ablehnung oder ungültiger Callback | Scopes prüfen und erneut starten |

## Bewusste Paketgrenze

Paket 12 beweist den nativen Authorization-Code-mit-PKCE-Weg bis einschließlich des sicher gebundenen Browser-Rückrufs. Der einmalige Code wird noch nicht gegen Tokens getauscht, weil Paket 13 zuerst JWKS, Signatur, Issuer, Audience, Ablauf und Charakterbindung vollständig validiert. Dadurch gelangt kein ungeprüftes Token in die Charakterdatenbank. Paket 14 übernimmt danach Schlüsselbundspeicherung und atomare Refresh-Token-Rotation.

## Automatisierte Verifikation

- PKCE-Länge, Zeichensatz und Frische von Verifier und Challenge
- exakter Autorisierungsendpunkt und vollständige Parameter einschließlich ausgewählter Scopepakete
- falscher und korrekter `state`, einmalige Callback-Nutzung sowie bereinigte EVE-Ablehnung
- Drei-Minuten-Timeout, manueller Abbruch und Löschen aller temporären Geheimnisse
- authentifizierte Sidecar-Endpunkte in Quell- und Frozen-Smoke-Tests
- native URL-Zielprüfung sowie Start-, Status- und Abbruchvertrag bis zur React-Oberfläche

## Offizielle Quellen

- [EVE Developer Documentation – Single Sign-On](https://developers.eveonline.com/docs/services/sso/)
- [EVE OAuth Authorization Server Metadata](https://login.eveonline.com/.well-known/oauth-authorization-server)
- [RFC 7636 – Proof Key for Code Exchange](https://www.rfc-editor.org/rfc/rfc7636)
- [RFC 8252 – OAuth 2.0 for Native Apps](https://www.rfc-editor.org/rfc/rfc8252)
