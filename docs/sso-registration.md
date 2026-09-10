# EVE-SSO-App-Registrierung

**Stand:** 9. September 2026  
**Status:** Im EVE Developers Portal registriert

Dieses Dokument ist die verbindliche Vorlage für die öffentliche EVE-SSO-App von New Eden Foundry. Die identischen Werte stehen maschinenlesbar in `backend/new_eden_foundry_backend/resources/eve-sso-registration.json` und werden automatisiert geprüft.

## Portalwerte

| Feld | Verbindlicher Wert |
|---|---|
| Anwendungsname | `New Eden Foundry` |
| Anwendungstyp | Native öffentliche Desktop-App, Authorization Code mit PKCE (`S256`) |
| Beschreibung | Lokale Windows-Desktop-App zur nachvollziehbaren EVE-Online-Industrieplanung für mehrere separat autorisierte Charaktere. |
| Callback-URI | `http://127.0.0.1:17891/oauth/callback` |
| Öffentliche Client-ID | `a8409de72d5b4cab9b0424819d0abdec` |
| Entwicklerkontakt | `Savox76` über [private GitHub-Sicherheitsmeldung](https://github.com/Savox76/eve-test-indu/security/advisories/new) |
| Quellcode | `https://github.com/Savox76/eve-test-indu` |

Der Callback-Port `17891` ist ausschließlich für den kurzlebigen Browser-Rückruf reserviert. Die interne Tauri-/Sidecar-API verwendet weiterhin einen vom Betriebssystem gewählten dynamischen Port. Es wird kein Client Secret in Quellcode, Konfiguration, Paket oder Log übernommen; ein vom Portal angezeigtes Secret wird für den PKCE-Desktopfluss nicht verwendet.

## Im Portal einzutragende Scopes

Die Portalregistrierung erhält alle unten aufgeführten Scopes. Beim Verbinden oder erneuten Autorisieren eines Charakters fordert New Eden Foundry den vollständigen aktuell benötigten Satz automatisch an. Fehlen einem bereits gespeicherten Charakter nach einem Update neue Scopes, bleibt er erhalten und die Oberfläche fordert sichtbar zur erneuten Anmeldung desselben Charakters auf.

| Paket | Scopes | Verwendungszweck |
|---|---|---|
| `industry-core` | `esi-assets.read_assets.v1`<br>`esi-characters.read_blueprints.v1`<br>`esi-industry.read_character_jobs.v1`<br>`esi-skills.read_skills.v1` | Bestand, Blueprints, persönliche Industrieaufträge und relevante Charakterfähigkeiten |
| `private-structures` | `esi-universe.read_structures.v1` | Namen und Daten zugänglicher Spielerstrukturen auflösen |
| `market` | `esi-markets.read_character_orders.v1`<br>`esi-wallet.read_character_wallet.v1` | Persönliche Marktaufträge und Walletdaten |
| `projects` | `esi-fittings.read_fittings.v1` | Eigene Fittings als Projekt- oder Doktrinquelle |
| `planetary-industry` | `esi-planets.manage_planets.v1` | Eigene Kolonien und Planetary-Industry-Daten lesen |

Der technisch schreibend klingende PI-Scope wird nur für die ESI-Lesewege zu eigenen Kolonien vorgesehen. New Eden Foundry plant keine schreibende PI-Aktion im Client. Corporation-Scopes, EVE Mail, Kontakte, Flotten-, Kalender- und UI-Schreibzugriffe sind nicht Bestandteil dieser Registrierung.

## Registrierung und Abgleich

1. Unter [EVE Developers – My Applications](https://developers.eveonline.com/applications) mit dem vorgesehenen Entwicklerkonto eine neue Anwendung anlegen.
2. Name, Beschreibung, Callback-URI und sämtliche oben gelisteten Scopes exakt übernehmen.
3. Die vom Portal ausgegebene öffentliche Client-ID `a8409de72d5b4cab9b0424819d0abdec` mit diesem Dokument und dem Feld `clientId` in `eve-sso-registration.json` abgleichen. Kein Client Secret übernehmen.
4. Repository- und Backendtests ausführen. Sie blockieren eine abweichende Callback-URI, unbekannte Scopepakete und ungültige Profilfelder.
5. Vor dem Merge die gespeicherte Portalansicht noch einmal Zeichen für Zeichen mit dieser Tabelle vergleichen.

Die echte Client-ID ist eingetragen und das Registrierungsprofil damit vollständig. Paket 12 hat Listener, Systembrowser, `state`, PKCE, Timeout und Abbruch umgesetzt. Der Ablauf und seine bewusste Grenze vor dem Tokenaustausch stehen in [sso-pkce-login.md](sso-pkce-login.md).

## Quellen

- [Offizielle EVE-SSO-Dokumentation](https://developers.eveonline.com/docs/services/sso/)
- [Offizieller ESI API Explorer](https://developers.eveonline.com/api-explorer)
- [OAuth-Server-Metadaten von EVE SSO](https://login.eveonline.com/.well-known/oauth-authorization-server)
