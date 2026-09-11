# Charakter-Skills

Paket 25 synchronisiert für jeden aktivierten Charakter den ESI-Endpunkt `/characters/{character_id}/skills/`. Der dafür notwendige Scope `esi-skills.read_skills.v1` gehört bereits zum automatisch angeforderten Paket `industry-core`.

Jeder Charakter erhält einen eigenen `character_skills`-Lauf. Erst eine vollständig geladene und streng geprüfte Antwort veröffentlicht den Snapshot `character_skills:<character_id>`. Fehlende Pflichtfelder, unbekannte Zusatzfelder, ungültige Level, doppelte Skill-IDs oder eine Abweichung zwischen der Summe der einzelnen Skillpunkte und `total_sp` markieren den Lauf als fehlgeschlagen. Der letzte vollständige Snapshot bleibt dabei unverändert und cache-first lesbar.

## Sichtbare Skilldaten

Die zweisprachige Ansicht unter **Blueprints & Jobs** zeigt:

- den über den bestehenden lokalen Typnamenscache aufgelösten Skillnamen und die Type-ID,
- den Besitzer sowie trainiertes und aktuell wirksames Level,
- Skillpunkte je Skill sowie verteilte und freie Skillpunkte in der Zusammenfassung,
- den Zustand `normal`, `limited` oder `boosted`,
- Datenalter und stabile Snapshot-/Sync-Run-IDs als Quellnachweis.

Suche, Besitzer-, Level- und Aktivzustandsfilter sowie die Sortierung werden vor der Seitenteilung im lokalen Sidecar angewendet. Pro Anfrage werden höchstens 200 und in der Oberfläche standardmäßig 100 Skills übertragen. Der Programmstart und eine erfolgreiche Charakteranmeldung aktualisieren Skills zusammen mit Assets und Blueprints vor den persönlichen Industrieaufträgen; ein manueller Folgelauf bleibt möglich.

## Bedeutung des aktiven Levels

`trained_skill_level` beschreibt den dauerhaft trainierten Stand. `active_skill_level` ist der aktuell wirksame Stand und kann davon abweichen:

- `normal`: aktives und trainiertes Level sind gleich,
- `limited`: das aktive Level liegt unter dem trainierten Level,
- `boosted`: das aktive Level liegt über dem trainierten Level.

Damit bleibt die Datenbasis für spätere Machbarkeits- und Skill-Lückenprüfungen ehrlich: Ein dauerhaft trainierter Wert wird nicht automatisch als aktuell wirksam angenommen.

## Bekannte ESI-Grenze

Die ESI-Endpunktbeschreibung weist darauf hin, dass die Antwort nach abgeschlossenen Einträgen in der Skill-Warteschlange veraltet sein kann, solange der Charakter danach nicht im Spiel angemeldet war. Paket 25 speichert deshalb den beobachteten Zeitpunkt und behauptet keine Echtzeitgenauigkeit. Eine spätere Warteschlangenüberlagerung muss den eigenen Scope, die Ablaufzeiten und dieselben vollständigen Snapshot-Regeln verwenden.
