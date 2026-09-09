# EVE-Tokenablage und Rotation

**Stand:** 9. September 2026  
**Umsetzung:** Arbeitspaket 14

## Speichergrenze

- Refresh Tokens werden erst nach vollständiger JWT- und Charakterprüfung übernommen.
- Jeder Charakter besitzt einen eigenen generischen Eintrag im Windows-Anmeldespeicher unter `NewEdenFoundry/EVE/<character-id>/refresh`.
- SQLite enthält weiterhin nur Charakter-ID, Namen, lokale Zuordnung und bestätigte Scopes. Access und Refresh Tokens werden dort nie gespeichert.
- Access Tokens bleiben ausschließlich im Speicher des Sidecars und werden spätestens mit dessen Prozessende verworfen.
- Auf nicht unterstützten Plattformen oder bei nicht verfügbarem Anmeldespeicher schlägt die Tokenablage geschlossen mit einem stabilen Fehlercode fehl. Es gibt keinen Rückfall auf Dateien, SQLite oder Klartext.

## Atomarer Austausch

Eine neue Autorisierung oder Refresh-Token-Rotation nutzt zwei getrennte Einträge pro Charakter:

1. Der neue Refresh Token wird zunächst in `refresh.pending` geschrieben und aus dem Anmeldespeicher zurückgelesen.
2. Erst nach erfolgreicher Prüfung wird der aktive Eintrag `refresh` ersetzt und ebenfalls zurückgelesen.
3. Erst danach wird `refresh.pending` entfernt.
4. Scheitert das Schreiben des aktiven Eintrags, bleibt der bisherige aktive Token erhalten. Der geprüfte Kandidat kann beim nächsten Zugriff abgeschlossen werden.
5. Eine Rotation vergleicht zusätzlich den erwarteten bisherigen Token, damit ein später konkurrierender Refresh keinen neueren Wert überschreibt.

Beim erstmaligen Verbinden wird der Refresh Token vor der SQLite-Identität vorgemerkt. Scheitert die Identitätsspeicherung, wird nur dieser Kandidat entfernt. Erst wenn beide Schritte erfolgreich waren, wird er aktiv geschaltet.

## Protokollierungsgrenze

- Öffentliche Fehler enthalten ausschließlich begrenzte Codes wie `credential-write-failed` oder `credential-rotation-conflict`.
- Tokenhaltige Objekte redigieren beide Token in ihrer Textdarstellung.
- Sidecar-Antworten, Bereitschaftsprotokoll, UI, Tauri und Diagnosepfade erhalten weder Tokenwerte noch Anmeldespeicherinhalte.
- Tests prüfen ausdrücklich, dass Geheimnisse weder in Repräsentationen noch Fehlertexten erscheinen.

## Lebenszyklus

- Ein gültiges Access Token wird für seine verbleibende Laufzeit im Sidecar-Speicher wiederverwendet.
- Vor Ablauf fordert der Sidecar über den gespeicherten Refresh Token ein neues Tokenpaar an, validiert erneut JWT, Charakterbindung und erwartete Scopes und rotiert erst dann den Refresh Token.
- Ein Token für eine andere Charakter-ID wird verworfen und kann den gespeicherten Wert nicht ersetzen.
- Das vollständige Entfernen eines Charakters wird in Arbeitspaket 15 mit der Löschung beider Anmeldespeicher-Slots verbunden.

## Automatisierte Verifikation

- Schreiben, Rücklesen und endgültige Aktivierung eines neuen Refresh Tokens
- Erhalt des alten Tokens bei fehlgeschlagenem Austausch
- Wiederaufnahme eines unterbrochenen, bereits dauerhaft vorgemerkten Austauschs
- Schutz vor konkurrierender Rotation mit veraltetem Ausgangswert
- erneute SSO-Prüfung von Charakter-ID und Scopes vor jeder Rotation
- ausschließliche Prozessspeicherung von Access Tokens
- rückstandsfreies Entfernen beider Slots im Test-Schlüsselbund
- redigierte Objekt- und Fehlerdarstellungen

## Offizielle Quellen

- [EVE Developer Documentation – Single Sign-On](https://developers.eveonline.com/docs/services/sso/)
- [Microsoft Learn – CredWriteW](https://learn.microsoft.com/windows/win32/api/wincred/nf-wincred-credwritew)
- [Microsoft Learn – Credential Manager](https://learn.microsoft.com/windows/win32/secauthn/credential-management)
