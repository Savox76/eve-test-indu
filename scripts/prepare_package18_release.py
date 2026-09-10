#!/usr/bin/env python3
"""Prepare v0.0.5-preview.2 release metadata for completed packages 17 and 18."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.0.5-preview.1"
NEW = "0.0.5-preview.2"
TAG = f"v{NEW}"
DATE = "10. September 2026"

VERSION_FILES = (
    "package.json",
    "package-lock.json",
    "src-tauri/Cargo.toml",
    "src-tauri/Cargo.lock",
    "frontend/src/App.tsx",
    "frontend/src/App.test.tsx",
    "frontend/src/runtime.test.ts",
)


def replace_required(path: str, old: str, new: str) -> None:
    file_path = ROOT / path
    text = file_path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Required marker missing in {path}: {old!r}")
    file_path.write_text(text.replace(old, new), encoding="utf-8")


for path in VERSION_FILES:
    replace_required(path, OLD, NEW)

release_notes = f"""# New Eden Foundry {TAG}

## Neu hinzugefügt

- Minimaler SDE-Bestand für Typen, Gruppen und Orte mit atomarem Austausch und eindeutiger SDE-Buildnummer.
- Multi-Character-Asset-Synchronisierung über den zentralen ESI-Client mit `esi-assets.read_assets.v1`.
- Vollständige Asset-Pagination über `X-Pages` sowie charaktergetrennte Sync-Runs und Snapshots.
- Tests für atomaren SDE-Import, Pagination, vollständige Asset-Snapshots und abgebrochene Läufe.

## Geändert

- Abgeleitete SDE-Tabellen bleiben bewusst außerhalb der versionierten Anwendungsmigration und können vollständig neu aufgebaut werden.
- Asset-Daten werden erst veröffentlicht, wenn alle Seiten eines Charakterlaufs vollständig validiert wurden.
- Die sichtbare Versionsnummer lautet `{TAG}`.
- Der Masterplan markiert Pakete 17 und 18 als abgeschlossen; Paket 19 Standortauflösung ist der nächste Fachschritt.

## Behobene Fehler

- Ein fehlerhafter SDE-Import kann den letzten gültigen SDE-Bestand nicht mehr teilweise überschreiben.
- Ein Netzwerkfehler oder Abbruch mitten in der Asset-Pagination erzeugt keinen unvollständigen gültigen Snapshot.
- Doppelte Asset-`item_id` über mehrere Seiten werden als inkonsistenter Lauf verworfen.
- Der letzte vollständig abgeschlossene Asset-Cache bleibt bei einem Folgfehler für Cache-First/Offline-Nutzung erhalten.

## Bekannte Einschränkungen

- Die Asset-Synchronisierung stellt in Paket 18 den Backend-Kern bereit; Standortauflösung und die vollständige Asset-Oberfläche folgen in Paketen 19 und 20.
- SDE- und Asset-Daten werden noch nicht als vollständig produktive Fachansicht in der React-Oberfläche dargestellt; vorhandene Fachkennzahlen bleiben dort teilweise synthetisch.
- Der sichere Refresh-Token-Speicher ist in dieser Windows-first Preview nur unter Windows verfügbar.
- Codesignierung, das manuelle Windows-Laufzeitgate und der Schutz von `main` bleiben offen.

## Update und Datenbankmigration

- Keine neue Anwendungsmigration; SQLite-Schema 6 bleibt unverändert.
- SDE-Tabellen sind abgeleitete Daten und werden beim Import atomar angelegt beziehungsweise ersetzt.
- Vorhandene Charaktere, Gruppen, Einstellungen, Refresh Tokens und bereits vollständige Cache-Snapshots bleiben erhalten.
- Für ein portables Update die Anwendung schließen und den bisherigen Ordner `data` vollständig in den neuen Programmordner übernehmen.
"""
(ROOT / "docs" / "releases" / f"{TAG}.md").write_text(release_notes, encoding="utf-8")

changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
marker = f"## {OLD} – {DATE}"
if marker not in changelog:
    raise RuntimeError("Previous release marker missing in CHANGELOG.md")
section = release_notes.replace(f"# New Eden Foundry {TAG}\n\n", "").replace("## ", "### ")
section = f"## {NEW} – {DATE}\n\n" + section
(ROOT / "CHANGELOG.md").write_text(changelog.replace(marker, section + "\n" + marker, 1), encoding="utf-8")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
old_status = "**Technische Preview – `v0.0.5-preview.1`.** Alle künftigen EVE-ESI-Zugriffe laufen jetzt durch einen zentralen, charaktergetrennten Client. Er setzt die feste Compatibility-Date und eine beschreibende Produktkennung, beachtet HTTP-Cache-Validatoren, begrenzt Antworten und Wiederholungen und schützt ESI mit Fehlerbudget sowie Circuit Breaker. Sein Zustand ist ohne Geheimnisse im authentifizierten Sidecar-Status sichtbar."
new_status = "**Technische Preview – `v0.0.5-preview.2`.** Der zentrale ESI-Client ist jetzt mit dem ersten echten Fachsync verbunden: Typen, Gruppen und Orte können als atomarer SDE-Bestand aufgebaut werden, und aktivierte Charaktere können ihre Assets vollständig paginiert und charaktergetrennt synchronisieren. Nur vollständig abgeschlossene Läufe werden als gültiger Snapshot veröffentlicht."
if old_status not in readme:
    raise RuntimeError("README project-status marker missing")
readme = readme.replace(old_status, new_status, 1)
old_detail = "Charakteridentitäten, Aliasse, Gruppen und Scope-Status stammen weiterhin aus SQLite; Refresh Tokens bleiben im Windows-Anmeldespeicher und Access Tokens ausschließlich im Sidecar-Prozess. Die Fachwerte der Mehrcharakter-Vorschau bleiben klar synthetisch: Der Client ist die sichere Transportgrundlage, SDE-Import und fachliche ESI-Synchronisierung folgen in den nächsten Paketen. Versionen werden weiterhin manuell über [GitHub Releases](https://github.com/Savox76/eve-test-indu/releases) bezogen; das vollständige Windows-Installationsgate bleibt Voraussetzung für die erste technische Alpha."
new_detail = "Charakteridentitäten, Aliasse, Gruppen und Scope-Status stammen weiterhin aus SQLite; Refresh Tokens bleiben im Windows-Anmeldespeicher und Access Tokens ausschließlich im Sidecar-Prozess. Paket 17 liefert den wiederaufbaubaren SDE-Minimalbestand, Paket 18 den vollständigen Asset-Sync mit `X-Pages`, Fehlerlauf-Protokoll und Cache-First-Snapshot-Semantik. Standortauflösung und Asset-UI folgen als nächste Schritte. Versionen werden weiterhin manuell über [GitHub Releases](https://github.com/Savox76/eve-test-indu/releases) bezogen; das vollständige Windows-Installationsgate bleibt Voraussetzung für die erste technische Alpha."
if old_detail not in readme:
    raise RuntimeError("README detail marker missing")
readme = readme.replace(old_detail, new_detail, 1)
readme = readme.replace("und der [zentrale ESI-Client](docs/esi-client.md).", "der [zentrale ESI-Client](docs/esi-client.md) und der [Asset-Sync](docs/asset-sync.md).", 1)
(ROOT / "README.md").write_text(readme, encoding="utf-8")

backend = (ROOT / "backend" / "README.md").read_text(encoding="utf-8")
anchor = "Paket 16 bündelt sämtliche künftigen ESI-Aufrufe in `EsiClient`. Der Client erzwingt den festen Host, `X-Compatibility-Date`, eine beschreibende Produktkennung, charaktergetrennte Cache-Schlüssel, `ETag`/`If-None-Match`, `Last-Modified`/`If-Modified-Since`, `Expires`/`Cache-Control`, begrenzte Wiederholungen, `Retry-After`, das ESI-Fehlerbudget und einen Circuit Breaker. Antworten sind größenbegrenzt und werden als striktes UTF-8-JSON gelesen; Fehlertexte enthalten weder Token noch Nutzdaten."
addition = anchor + "\n\nPaket 17 ergänzt einen atomaren, über eine Buildnummer identifizierten Minimal-SDE-Bestand für Typen, Gruppen und Orte. Paket 18 verwendet den zentralen `EsiClient` für charaktergetrennte Asset-Läufe mit vollständiger `X-Pages`-Pagination. Erst ein vollständig validierter Lauf erzeugt einen neuen `cached_snapshots`-Datensatz; Fehlerläufe bleiben getrennt in `sync_runs` und lassen den letzten gültigen Cache unverändert."
if anchor not in backend:
    raise RuntimeError("backend README ESI marker missing")
(ROOT / "backend" / "README.md").write_text(backend.replace(anchor, addition, 1), encoding="utf-8")

master = (ROOT / "docs" / "MASTERPLAN.md").read_text(encoding="utf-8")
master = master.replace("**Fassung:** 2.4 (lebendes Repository-Dokument)", "**Fassung:** 2.5 (lebendes Repository-Dokument)", 1)
master = master.replace("**Status:** In Umsetzung – Phase 2 mit zentraler ESI-Transportgrenze", "**Status:** In Umsetzung – Phase 3 mit SDE-Basis und Multi-Character-Asset-Sync", 1)
anchor16 = "- **Abgeschlossen:** 16 – `EsiClient` bildet die einzige HTTP-Vertrauensgrenze für ESI. Er erzwingt festen Host, Compatibility-Date, User-Agent und charaktergetrennte Autorisierung, verarbeitet Cacheheader und bedingte 304-Antworten, begrenzt JSON und Wiederholungen und kapselt Retry-After, ESI-Fehlerbudget sowie Circuit Breaker. Der authentifizierte Sidecar-Status macht diese Policy ohne Zugangsdaten sichtbar."
insert = anchor16 + "\n- **Abgeschlossen:** 17 – der minimale SDE-Bestand für Typen, Gruppen und Orte wird als abgeleitete Datenbasis atomar aufgebaut und über eine eindeutige Buildnummer identifiziert. Ein fehlerhafter Import lässt den vorherigen gültigen Stand unangetastet und verändert das Anwendungsschema nicht.\n- **Abgeschlossen:** 18 – aktivierte Charaktere können Assets über den zentralen ESI-Client vollständig paginiert synchronisieren. Jeder Charakter erhält einen eigenen Lauf und Snapshot; nur vollständige Läufe werden veröffentlicht, während Abbruch und Fehler den letzten gültigen Cache erhalten."
if anchor16 not in master:
    raise RuntimeError("Masterplan package 16 marker missing")
master = master.replace(anchor16, insert, 1)
old_next = "- **Als Nächstes:** Arbeitspaket 17 importiert den minimal benötigten SDE-Bestand für Typen, Gruppen und Orte atomar und kennzeichnet ihn eindeutig mit seiner Buildnummer. Parallel bleibt das A0-Windows-Gate für Installation, zweiten Start, Migration/Update und Entfernung auf einem freigegebenen Windows-Testgerät offen."
new_next = "- **Als Nächstes:** Arbeitspaket 19 löst Asset-Standorte und Containerpfade belastbar auf, einschließlich Stationen, Struktur-403 und zyklischer Containerbeziehungen in synthetischen Golden-Fällen. Parallel bleibt das A0-Windows-Gate für Installation, zweiten Start, Migration/Update und Entfernung auf einem freigegebenen Windows-Testgerät offen."
if old_next not in master:
    raise RuntimeError("Masterplan next-package marker missing")
master = master.replace(old_next, new_next, 1)
(ROOT / "docs" / "MASTERPLAN.md").write_text(master, encoding="utf-8")

# Remove the temporary preparer and its workflow from the release tree.
(ROOT / "scripts" / "prepare_package18_release.py").unlink(missing_ok=True)
(ROOT / ".github" / "workflows" / "package18-release-prep.yml").unlink(missing_ok=True)
