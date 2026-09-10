# ADR-015: Automatische vollständige SSO-Berechtigungssätze

## Kontext

Funktionsweise wählbare Scopepakete führten dazu, dass ein später aktiviertes Modul eine erneute Anmeldung erforderte, ohne dass dies ausreichend sichtbar war. Für eine lokale Einzelplatzanwendung ist ein konsistenter, nachvollziehbarer Berechtigungsstand wichtiger als eine Auswahl, die bei jedem Charakter unterschiedlich ausfallen kann.

## Entscheidung

Bei jeder neuen oder erneuten Charakteranmeldung fordert New Eden Foundry automatisch alle Scopes des aktuell registrierten Profils an. Oberfläche, Tauri-Brücke und Sidecar akzeptieren nur den vollständigen Paketvektor in der registrierten Reihenfolge.

Gespeicherte Charaktere werden bei einem Update nicht gelöscht. Weicht ihr bestätigter Scope-Satz vom aktuellen Registrierungsprofil ab oder fehlt ihr Credential, zeigt die Charakterliste einen Warnstatus. Die Verwaltung bietet dann eine geführte erneute EVE-SSO-Anmeldung für denselben Charakter. Die idempotente Speicherung ersetzt dessen Autorisierung, ohne Alias, Gruppe oder lokale Fachdaten zu verlieren.

## Folgen

- Neue Charaktere besitzen unmittelbar alle derzeit benötigten Leseberechtigungen.
- Ein später ergänzter Scope erzwingt keine stille Fehlfunktion, sondern einen sichtbaren Hinweis zur erneuten Anmeldung.
- EVE zeigt den vollständigen Berechtigungsumfang vor Zustimmung an; der Nutzer kann weiterhin abbrechen.
- Die frühere optionale Paketauswahl aus ADR-009 und ADR-012 wird für den Anmeldevorgang durch diese Entscheidung ersetzt.

## Verifikation

- Client, Rust und Sidecar weisen unvollständige oder anders sortierte Paketlisten ab.
- UI-Tests prüfen den automatischen vollständigen Satz und den sichtbaren Neuanmeldeweg.
- Identitätstests sichern die idempotente Aktualisierung ohne Charakterduplikat.

## Referenzen

- [ADR-004: EVE SSO mit PKCE](0004-eve-sso-pkce.md)
- [ADR-009: Charaktergebundene Zugänge](0009-multi-character-scopes-and-local-account-groups.md)
- [SSO-App-Registrierung](../sso-registration.md)

