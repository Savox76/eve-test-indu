# ADR-012: Festes öffentliches EVE-SSO-Registrierungsprofil

- **Status:** Angenommen
- **Datum:** 9. September 2026
- **Entscheider:** Projektverantwortlicher

## Kontext

EVE SSO weist einer registrierten Anwendung eine öffentliche Client-ID zu und akzeptiert nur zuvor registrierte Redirect-URIs und Scopes. New Eden Foundry benötigt für den späteren PKCE-Login einen lokalen Browser-Callback, während die interne Sidecar-API aus Sicherheits- und Parallelitätsgründen weiterhin einen dynamischen Port verwendet. Ohne eine einzige geprüfte Quelle könnten Portal, Code, Tests und Dokumentation auseinanderlaufen.

## Entscheidung

Das Repository führt ein streng validiertes, maschinenlesbares SSO-Registrierungsprofil.

- Die einzige Callback-URI lautet `http://127.0.0.1:17891/oauth/callback`.
- Port `17891` ist ausschließlich für den vorübergehenden SSO-Callback reserviert und nicht der interne Sidecar-Port.
- New Eden Foundry ist ein öffentlicher nativer Client und verwendet Authorization Code mit PKCE `S256`, ohne ausgeliefertes Client Secret.
- `Savox76` ist als Entwicklerkontakt über die privaten GitHub Security Advisories des Repositories erreichbar.
- Scopes sind in die kleinsten funktionsbezogenen Pakete `industry-core`, `private-structures`, `market`, `projects` und `planetary-industry` getrennt.
- Das Portal erhält die gesamte für Version 1.0 vorgesehene Scope-Menge; ein einzelner Charakter-Login fordert nur die für aktivierte Funktionen erforderlichen Pakete an.
- Die öffentliche Client-ID bleibt ausdrücklich `null`, bis das EVE Developers Portal sie erzeugt hat. Ein erfundener oder scheinbar produktiver Platzhalter ist verboten.

## Folgen

Der spätere Login kann Callback und Scopes aus einer geprüften Quelle lesen. Eine belegte Änderung an Callback oder Scope-Menge erfordert eine bewusste Profil-, Test- und Dokumentationsänderung sowie einen Abgleich im Portal. Ein belegter Portkonflikt kann deshalb nicht still zur Laufzeit auf einen anderen Port ausweichen, sondern muss verständlich zum erneuten Versuch auffordern.

Arbeitspaket 11 bleibt bis zum Eintrag der echten Client-ID und dem erfolgreichen Speichern der URI im Portal offen. Diese externe Registrierung kann nicht durch Repository-Code ersetzt werden.

## Verifikation

Backendtests prüfen das gebündelte Profil, die feste Loopback-URI, exakt erlaubte Scopepakete, den Entwicklerkontakt, Client-ID-Format und Drift. Die Repository-Richtlinie verlangt Profil, Dokumentation, ADR und Tests; der Sidecar-Build nimmt das Profil ausdrücklich in die portable und installierte Anwendung auf.

## Referenzen

- [EVE Developer Documentation – SSO](https://developers.eveonline.com/docs/services/sso/)
- [EVE Developers – API Explorer](https://developers.eveonline.com/api-explorer)
- [ADR-004 – EVE SSO mit PKCE](0004-eve-sso-pkce.md)
- [ADR-009 – Mehrere Charaktere und Scope-Trennung](0009-multi-character-scopes-and-local-account-groups.md)
