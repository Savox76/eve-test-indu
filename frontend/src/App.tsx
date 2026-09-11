import {
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  Bell,
  Boxes,
  Check,
  ChevronDown,
  ChevronRight,
  CircleCheck,
  Clock3,
  Command,
  Database,
  Download,
  Factory,
  FlaskConical,
  FolderKanban,
  LogIn,
  Languages,
  LayoutDashboard,
  LineChart,
  type LucideIcon,
  MoreHorizontal,
  Minus,
  Orbit,
  PackageSearch,
  RefreshCw,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Type,
  UserRound,
  UsersRound,
  X,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  accountGroups,
  activity,
  attentionItems,
  demoCharacters,
  demoMetadata,
  materialCoverage,
  modulePreview,
  overviewMetrics,
  productionStages,
  type OverviewScopeId,
} from "./demo";
import {
  assetLocationStatuses,
  assetDeltaChangeTypes,
  assetDeltaPageSize,
  assetPageSize,
  cancelEveSso,
  createAccountGroup,
  deleteAccountGroup,
  deleteEveCharacter,
  fontScales,
  initialRuntimeStatus,
  exportAssetsCsv,
  loadAccountGroups,
  loadEveCharacters,
  loadEveSsoStatus,
  loadDesktopRuntimeStatus,
  loadAssets,
  loadAssetDeltas,
  loadBlueprints,
  loadCharacterSkills,
  loadIndustryJobs,
  syncAssets,
  syncBlueprints,
  syncCharacterSkills,
  syncIndustryJobs,
  renameAccountGroup,
  setDesktopUpdateChannel,
  setDesktopFontScale,
  startEveSso,
  updateEveCharacter,
  ssoScopePackages,
  type AccountGroup,
  type AssetCsvExport,
  type AssetDeltaChangeType,
  type AssetDeltaPage,
  type AssetDeltaQuery,
  type AssetLocationStatus,
  type AssetPage,
  type AssetSortField,
  type AssetSyncResult,
  type AssetQuery,
  type BlueprintKind,
  type BlueprintPage,
  type BlueprintQuery,
  type BlueprintSortField,
  type BlueprintSyncResult,
  type CharacterSkillActiveState,
  type CharacterSkillPage,
  type CharacterSkillQuery,
  type CharacterSkillSortField,
  type CharacterSkillSyncResult,
  type IndustryActivityId,
  type IndustryCorrelationState,
  type IndustryJobPage,
  type IndustryJobQuery,
  type IndustryJobSortField,
  type IndustryJobStatus,
  type IndustryJobSyncResult,
  type CharacterUpdate,
  type DesktopRuntimeStatus,
  type EveCharacter,
  type FontScale,
  type LocalDataState,
  type SsoLoginStatus,
  type SsoScopePackage,
  type SortDirection,
  type UpdateChannel,
  type UpdaterStatus,
  type AppearanceStatus,
  blueprintPageSize,
  characterSkillPageSize,
  industryJobPageSize,
} from "./runtime";

type Locale = "de" | "en";
type ModuleId = "overview" | keyof typeof modulePreview;

const initialSsoStatus: SsoLoginStatus = {
  state: "idle",
  attemptId: null,
  scopePackages: [],
  expiresAt: null,
  errorCode: null,
  character: null,
};

const navigation: ReadonlyArray<{ id: ModuleId; icon: LucideIcon }> = [
  { id: "overview", icon: LayoutDashboard },
  { id: "assets", icon: PackageSearch },
  { id: "blueprints", icon: Boxes },
  { id: "production", icon: Factory },
  { id: "invention", icon: FlaskConical },
  { id: "market", icon: LineChart },
  { id: "projects", icon: FolderKanban },
  { id: "pi", icon: Orbit },
];

const copy = {
  de: {
    nav: {
      overview: "Übersicht",
      assets: "Assets",
      blueprints: "Blueprints & Jobs",
      production: "Produktion",
      invention: "T2-Invention",
      market: "Markt",
      projects: "Projekte",
      pi: "Planetary Industry",
    },
    navSection: "Arbeitsbereiche",
    search: "Foundry durchsuchen …",
    searchHint: "Module direkt öffnen",
    noResults: "Kein Modul gefunden",
    syncFresh: "Vorschau: vor 6 Min.",
    syncNow: "Jetzt aktuell",
    refresh: "Datenstand simuliert aktualisieren",
    notices: "Hinweise anzeigen",
    runtimeStatus: {
      checking: {
        title: "Desktop-Kern",
        detail: "Status wird geprüft …",
      },
      starting: {
        title: "Lokaler Kern startet",
        detail: "Datenbank im Programmordner wird geprüft",
      },
      ready: {
        title: "Lokaler Kern aktiv",
        detail: "data\\foundry.sqlite3 · Migrationssicherung aktiv",
      },
      error: {
        title: "Lokaler Kern gestört",
        detail: "Sidecar oder Programmordner nicht verfügbar",
      },
      preview: {
        title: "Designvorschau",
        detail: "Desktop-Kern nur in der App",
      },
      unavailable: {
        title: "Desktop-Kern gestört",
        detail: "Statusabfrage nicht möglich",
      },
    },
    runtimeErrors: {
      storage: "Programmordner ist nicht beschreibbar",
      database: "Datenbank konnte nicht sicher geöffnet werden",
      sidecar: "Lokaler Dienst wurde unerwartet beendet",
      fallback: "Sidecar oder Programmordner nicht verfügbar",
    },
    dataStatus: {
      loading: {
        title: "Lokaler Datenstand wird geladen",
        detail: "Die Datenbank wird geprüft, bevor Inhalte angezeigt werden.",
        noDataDetail: "Die Datenbank wird geprüft, bevor Inhalte angezeigt werden.",
      },
      refreshing: {
        title: "Cache sichtbar · Aktualisierung läuft",
        detail: "Der letzte geprüfte Stand bleibt während der Aktualisierung nutzbar.",
        noDataDetail: "Die erste Aktualisierung läuft.",
      },
      empty: {
        title: "Noch keine lokalen Daten",
        detail: "Nach der EVE-Anmeldung erscheint hier der erste geprüfte Datenstand.",
        noDataDetail: "Nach der EVE-Anmeldung erscheint hier der erste geprüfte Datenstand.",
      },
      fresh: {
        title: "Lokaler Datenstand aktuell",
        detail: "Die Oberfläche verwendet den letzten vollständig geprüften Cache.",
        noDataDetail: "Noch kein vollständiger Cache vorhanden.",
      },
      stale: {
        title: "Veralteter Cache sichtbar",
        detail: "Die bekannten Daten bleiben verfügbar und sind eindeutig als veraltet markiert.",
        noDataDetail: "Es ist noch kein verwendbarer Cache vorhanden.",
      },
      offline: {
        title: "Offline · Cache bleibt verfügbar",
        detail: "Die Verbindung fehlt; der letzte geprüfte Stand wird nicht gelöscht.",
        noDataDetail: "Die Verbindung fehlt und es ist noch kein lokaler Stand vorhanden.",
      },
      error: {
        title: "Synchronisierung gestört",
        detail: "Der letzte geprüfte Cache bleibt sichtbar; der Fehlerstatus wird getrennt geführt.",
        noDataDetail: "Die Synchronisierung ist fehlgeschlagen und es gibt noch keinen Cache.",
      },
    },
    dataAge: "Datenalter",
    noDataAge: "noch kein Datenstand",
    updates: {
      label: "Update-Kanal",
      select: "Update-Kanal auswählen",
      channels: {
        stable: "Offiziell",
        beta: "Beta",
        preview: "Vorschau / Test",
      },
      verified: "Signiertes Testmanifest geprüft",
      invalid: "Testmanifest ungültig · Updates gesperrt",
      checking: "Testmanifest wird geprüft",
      unavailable: "Updater derzeit nicht verfügbar",
      disabled: "Downloads noch deaktiviert",
      saving: "Kanal wird gespeichert …",
      saveError: "Kanal konnte nicht gespeichert werden",
      desktopOnly: "In der Desktop-App wählbar",
    },
    sso: {
      eyebrow: "EVE SSO · PKCE",
      states: {
        idle: {
          title: "EVE-Charakter verbinden",
          detail: "Jede Anmeldung autorisiert genau einen Charakter. Weitere Charaktere können danach einzeln ergänzt werden.",
        },
        waiting: {
          title: "Browser-Anmeldung läuft",
          detail: "EVE SSO ist im Systembrowser geöffnet. Die App wartet bis zu drei Minuten auf den sicheren Rückruf.",
        },
        exchanging: {
          title: "EVE-Identität wird geprüft",
          detail: "Der Rückruf ist gültig. Signatur, Aussteller, Zielgruppe, Ablauf, Scopes und Charakter-ID werden geprüft.",
        },
        connected: {
          title: "EVE-Charakter verbunden",
          detail: "Die geprüfte Charakteridentität wurde sicher in der lokalen Datenbank gespeichert.",
        },
        cancelled: {
          title: "Anmeldung abgebrochen",
          detail: "Der lokale Listener wurde beendet und alle temporären PKCE-Werte wurden verworfen.",
        },
        "timed-out": {
          title: "Zeitfenster abgelaufen",
          detail: "Der Anmeldeversuch wurde nach drei Minuten beendet. Du kannst sofort neu starten.",
        },
        failed: {
          title: "Anmeldung nicht abgeschlossen",
          detail: "EVE SSO hat den Rückruf abgelehnt oder die Freigabe wurde nicht erteilt.",
        },
      },
      start: "Charakter verbinden",
      startAnother: "Weiteren Charakter verbinden",
      cancel: "Abbrechen",
      retry: "Erneut versuchen",
      desktopOnly: "Die echte Anmeldung ist in der Windows-App verfügbar.",
      commandError: "Die Anmeldung konnte nicht gestartet oder abgefragt werden.",
      scopeTitle: "Automatische Berechtigungen",
      scopeAutomatic: "Alle aktuell benötigten SSO-Pakete werden automatisch angefordert.",
      security: "Systembrowser · S256 · zufälliger state · 3-Minuten-Zeitfenster",
      connectedName: "Verbunden: {name}",
      packageLabels: {
        "industry-core": "Industrie-Basis",
        market: "Markt",
        "planetary-industry": "Planetary Industry",
        projects: "Projekte & Fittings",
        "private-structures": "Private Strukturen",
      },
    },
    characters: {
      title: "Verbundene EVE-Charaktere",
      empty: "Noch kein geprüfter Charakter verbunden",
      unavailable: "Charakterverwaltung konnte nicht geladen werden",
      count: "{count} lokal verbunden",
      scopes: "Bestätigte Scopes: {count}",
      ungrouped: "Nicht gruppiert",
      manage: "Verwalten",
      close: "Editor schließen",
      alias: "Lokaler Alias",
      aliasPlaceholder: "Optionaler Anzeigename",
      group: "Kontogruppe",
      active: "Charakter aktiv verwenden",
      save: "Änderungen speichern",
      saving: "Wird gespeichert …",
      delete: "Charakter vollständig löschen",
      confirmDelete: "Löschen endgültig bestätigen",
      cancelDelete: "Löschen abbrechen",
      deleteDetail: "Entfernt Identität, Scopes, Cache, Historie und Refresh Token dauerhaft.",
      error: "Änderung konnte nicht sicher abgeschlossen werden.",
      credential: "Anmeldedaten",
      credentialStates: {
        stored: "sicher gespeichert",
        missing: "erneut verbinden",
        unavailable: "Speicher nicht verfügbar",
      },
      scopeStates: {
        granted: "vollständig",
        partial: "teilweise",
        missing: "fehlt",
      },
      inactive: "Inaktiv",
      groupsTitle: "Lokale Kontogruppen",
      newGroup: "Neue Gruppe",
      createGroup: "Gruppe anlegen",
      renameGroup: "Gruppe umbenennen",
      deleteGroup: "Gruppe löschen",
      noGroups: "Noch keine Kontogruppe angelegt",
      members: "{count} Charaktere",
      reauthorizationShort: "Anmeldung nötig",
      reauthorizationTitle: "Berechtigungen müssen erneuert werden",
      reauthorizationDetail: "Für diesen Charakter fehlen aktuelle Berechtigungen. Melde denselben Charakter erneut über EVE SSO an.",
      reauthorize: "Jetzt neu anmelden",
    },
    fontSize: {
      label: "Schriftgröße",
      smaller: "Schrift kleiner",
      larger: "Schrift größer",
      levels: {
        "very-small": "Sehr klein",
        small: "Klein",
        normal: "Normal",
        large: "Groß",
        "very-large": "Sehr groß",
      },
    },
    scope: {
      label: "Übersichtsbereich",
      select: "Ansicht wählen",
      combined: "Alle Charaktere",
      combinedBadge: "GESAMT",
      characterBadge: "CHARAKTER",
      accountGroups: "lokale Kontogruppen",
      characters: "Charaktere",
      dataAge: "Datenstand",
      roles: {
        manufacturing: "Produktion & Assets",
        research: "Forschung & Blueprints",
        planetary: "Planetary Industry",
      },
    },
    creatorLabel: "Erstellt von",
    preview: "Design Preview",
    synthetic: "Fachansichten verwenden synthetische Daten – sichere EVE-Autorisierung jetzt verfügbar",
    dateLine: "OPERATIONS-BRIEF · YC 128.09.08",
    greeting: "Guten Morgen, Pilot.",
    heroText:
      "Deine Fertigung läuft stabil. Zwei Entscheidungen brauchen heute deine Aufmerksamkeit, bevor der nächste Produktionszyklus beginnt.",
    planAction: "Produktionsplan öffnen",
    inspectAction: "Datenlage prüfen",
    readiness: "Produktionsbereitschaft",
    readinessDetail: "für Projekt Aurora",
    metricLabels: {
      assets: "Asset-Wert",
      jobs: "Aktive Jobs",
      readiness: "Materialdeckung",
      attention: "Aufmerksamkeit",
    },
    metricContext: {
      assets: "synthetische Bewertung",
      jobs: "50 % ausgelastet",
      readiness: "über alle Projekte",
      attention: "in deiner Foundry",
    },
    operations: "Produktionslage",
    operationsSubtitle: "Aktive Vorhaben und nächste Fertigstellungen",
    viewProduction: "Produktion ansehen",
    jobProgress: "Fortschritt",
    due: "Fertig in",
    materialTitle: "Materialdeckung",
    materialSubtitle: "Projekt Aurora · vollständige Stückliste",
    materialTotal: "Gesamtbedarf",
    materialValue: "1.84 B ISK",
    coverageLegend: ["Vorhanden", "Einkaufen", "Herstellen"],
    buildBuy: "Build-vs-Buy-Empfehlung",
    buildBuyValue: "11 Komponenten selbst fertigen",
    buildBuySaving: "geschätzte Ersparnis 126 M ISK",
    attentionTitle: "Braucht Aufmerksamkeit",
    attentionSubtitle: "Nach Dringlichkeit sortiert",
    attentionActions: ["PI prüfen", "Ansehen", "Aktualisieren"],
    attentionDetails: [
      "Endet in 2 Std. 12 Min.",
      "Standortdetails nicht verfügbar",
      "Letzter Preissatz: vor 3 Std.",
    ],
    activityTitle: "Foundry Pulse",
    activitySubtitle: "Letzte nachvollziehbare Änderungen",
    activityTitles: [
      "Orion-Rahmen fertiggestellt",
      "Günstiges Einkaufsfenster erkannt",
      "Asset-Snapshot aktualisiert",
    ],
    activityDetails: [
      "8 Einheiten ins Borealis-Hangar verschoben",
      "Synthetischer Legierungskorb 6,4 % unter Profil",
      "1.284 erfundene Positionen abgeglichen",
    ],
    activityTimes: ["vor 14 Min.", "vor 39 Min.", "vor 1 Std."],
    confidence: "Datenvertrauen",
    confidenceValue: "Hoch",
    cache: "Cache vollständig",
    localOnly: "Lokal verarbeitet",
    assets: {
      kicker: "LOKALER ASSET-BESTAND",
      subtitle: "Vollständige Snapshots durchsuchen, nach Besitzer und Standortstatus filtern und als CSV sichern.",
      search: "Typ, Standort, Besitzer oder ID suchen",
      owner: "Besitzer",
      allOwners: "Alle Besitzer",
      status: "Standortstatus",
      allStatuses: "Alle Status",
      statusLabels: {
        resolved: "Aufgelöst",
        restricted: "Eingeschränkt",
        unresolved: "Unaufgelöst",
        cycle: "Container-Zyklus",
        pending: "Auflösung ausstehend",
      },
      positions: "Positionen",
      units: "Einheiten",
      type: "Typ",
      location: "Standort",
      quantity: "Menge",
      age: "Datenalter",
      flag: "Hangar / Bereich",
      export: "Treffer als CSV",
      sync: "Assets aktualisieren",
      syncing: "Assets werden aktualisiert …",
      syncComplete: "{assets} Positionen von {characters} Charakter(en) aktualisiert.",
      syncPartial: "{completed} aktualisiert, {failed} fehlgeschlagen. Berechtigungen und Verbindung prüfen.",
      syncEmpty: "Kein aktivierter Charakter für den Asset-Sync vorhanden.",
      syncError: "Asset-Sync konnte nicht gestartet werden.",
      exporting: "CSV wird erstellt …",
      exported: "{rows} Zeilen gespeichert · {path}",
      exportError: "CSV konnte nicht sicher erstellt werden.",
      loading: "Asset-Bestand wird geladen …",
      unavailable: "Die echte Asset-Ansicht ist in der laufenden Desktop-App verfügbar.",
      noData: "Noch kein vollständiger Asset-Snapshot vorhanden.",
      noMatches: "Keine Assets entsprechen der Suche und den Filtern.",
      queryError: "Der lokale Asset-Bestand konnte nicht gelesen werden.",
      pendingLocation: "Standortauflösung ausstehend",
      resultRange: "{from}–{to} von {total}",
      previous: "Vorherige Seite",
      next: "Nächste Seite",
      liveNotice: "Echte lokale Asset-Snapshots · keine synthetischen Fachwerte",
      deltas: {
        kicker: "ASSET-ÄNDERUNGEN",
        title: "Nachvollziehbare Änderungen",
        subtitle: "Vergleich vollständiger Snapshots mit belegbarer Zuordnung zu abgeschlossenen Industrieaufträgen.",
        filter: "Änderungsart",
        all: "Alle Änderungen",
        labels: {
          added: "Hinzugekommen",
          removed: "Entfernt",
          quantity: "Menge geändert",
          location: "Verschoben",
        },
        changes: "Änderungen",
        beforeAfter: "Vorher → Nachher",
        interval: "Vergleichsfenster",
        source: "Quellnachweis",
        loading: "Änderungsverlauf wird geladen …",
        noBaseline: "Noch kein vollständiger Ausgangssnapshot vorhanden.",
        unavailable: "Der echte Änderungsverlauf ist in der laufenden Desktop-App verfügbar.",
        noChanges: "Für diese Auswahl wurden keine Änderungen erkannt.",
        error: "Der lokale Änderungsverlauf konnte nicht gelesen werden.",
        correlationLabels: {
          linked: "Job belegt", ambiguous: "Mehrere Jobkandidaten",
          unmatched: "Kein passender Job", unavailable: "Kein Job-Snapshot",
          "not-applicable": "Keine Ausgabeänderung",
        },
      },
    },
    blueprints: {
      kicker: "LOKALER BLUEPRINT-BESTAND",
      subtitle: "BPOs und BPCs aller aktiven Charaktere mit ME, TE und verbleibenden Läufen.",
      search: "Blueprint, Besitzer, Ort oder ID suchen",
      owner: "Besitzer",
      allOwners: "Alle Besitzer",
      kind: "Art",
      allKinds: "BPO & BPC",
      original: "Original (BPO)",
      copy: "Kopie (BPC)",
      type: "Blueprint",
      me: "ME",
      te: "TE",
      runs: "Läufe",
      location: "Bereich",
      age: "Datenalter",
      count: "Blueprints",
      unlimited: "unbegrenzt",
      sync: "Blueprints aktualisieren",
      syncing: "Blueprints werden aktualisiert …",
      syncComplete: "{blueprints} Blueprints von {characters} Charakter(en) aktualisiert.",
      syncPartial: "{completed} aktualisiert, {failed} fehlgeschlagen. Anmeldung oder Verbindung prüfen.",
      syncEmpty: "Kein aktivierter Charakter für den Blueprint-Sync vorhanden.",
      syncError: "Blueprint-Sync konnte nicht gestartet werden.",
      loading: "Blueprint-Bestand wird geladen …",
      unavailable: "Die echte Blueprint-Ansicht ist in der Windows-App verfügbar.",
      noData: "Noch kein vollständiger Blueprint-Snapshot vorhanden.",
      noMatches: "Keine Blueprints entsprechen der Auswahl.",
      queryError: "Der lokale Blueprint-Bestand konnte nicht gelesen werden.",
      resultRange: "{from}–{to} von {total}",
      previous: "Vorherige Seite",
      next: "Nächste Seite",
      liveNotice: "Echte lokale Blueprint-Snapshots · automatisch beim Programmstart",
      jobs: {
        kicker: "PERSÖNLICHE INDUSTRIEAUFTRÄGE",
        title: "Industrieaufträge",
        subtitle: "Aktive und abgeschlossene ESI-Aufträge mit belegbarer Blueprint- und Asset-Zuordnung.",
        search: "Job, Blueprint, Produkt, Besitzer oder ID suchen",
        status: "Status",
        allStatuses: "Alle Status",
        statusLabels: {
          active: "Aktiv", cancelled: "Abgebrochen", delivered: "Ausgeliefert",
          paused: "Pausiert", ready: "Fertig", reverted: "Zurückgesetzt",
        },
        activity: "Aktivität",
        allActivities: "Alle Aktivitäten",
        activityLabels: {
          manufacturing: "Produktion", "research-time": "Zeitforschung",
          "research-material": "Materialforschung", copying: "Kopieren",
          "reverse-engineering": "Reverse Engineering", invention: "Erfindung",
          reactions: "Reaktion",
        },
        correlation: "Zuordnung",
        allCorrelations: "Alle Zuordnungen",
        correlationLabels: {
          linked: "Belegt", partial: "Teilweise belegt", ambiguous: "Mehrere Kandidaten",
          unmatched: "Ohne Treffer", pending: "Noch laufend",
        },
        blueprint: "Blueprint / Job",
        product: "Produkt",
        owner: "Besitzer / Aktivität",
        runs: "Läufe",
        timeline: "Zeitplan",
        location: "Anlage / Ausgabe",
        evidence: "Quellnachweis",
        currentBlueprint: "aktueller Blueprint",
        historicalBlueprint: "historischer Blueprint",
        noBlueprint: "Blueprint nicht im Bestand",
        noBlueprintData: "kein Blueprint-Snapshot",
        assetLinked: "Asset-Änderung belegt",
        assetAmbiguous: "mehrere Asset-Kandidaten",
        assetPending: "Asset-Ausgabe noch ausstehend",
        assetUnmatched: "keine passende Asset-Änderung",
        assetUnavailable: "kein Asset-Verlauf",
        assetNotApplicable: "keine Ausgabe erwartet",
        successful: "erfolgreich",
        activeCount: "aktive Jobs",
        count: "Jobs",
        age: "Datenalter",
        sync: "Jobs aktualisieren",
        syncing: "Jobs werden aktualisiert …",
        syncComplete: "{jobs} Jobs von {characters} Charakter(en) aktualisiert.",
        syncPartial: "{completed} aktualisiert, {failed} fehlgeschlagen. Anmeldung oder Verbindung prüfen.",
        syncEmpty: "Kein aktivierter Charakter für den Job-Sync vorhanden.",
        syncError: "Job-Sync konnte nicht gestartet werden.",
        loading: "Industrieaufträge werden geladen …",
        noData: "Noch kein vollständiger Job-Snapshot vorhanden.",
        noMatches: "Keine Industrieaufträge entsprechen der Auswahl.",
        queryError: "Die lokalen Industrieaufträge konnten nicht gelesen werden.",
      },
      skills: {
        kicker: "CHARAKTER-SKILLS",
        title: "Skills für Industrie und Planung",
        subtitle: "Vollständige ESI-Skillstände aller aktivierten Charaktere als Grundlage für spätere Machbarkeits- und Lückenprüfungen.",
        search: "Skill, Besitzer oder Type-ID suchen",
        level: "Trainiertes Level",
        allLevels: "Alle Level",
        activeState: "Aktiver Zustand",
        allActiveStates: "Alle Zustände",
        stateLabels: {
          normal: "Normal aktiv",
          limited: "Aktiv eingeschränkt",
          boosted: "Temporär verstärkt",
        },
        skill: "Skill",
        owner: "Besitzer",
        trained: "Trainiert",
        active: "Aktiv",
        skillpoints: "Skillpunkte",
        source: "Quelle",
        count: "Skills",
        totalSp: "verteilte SP",
        unallocatedSp: "freie SP",
        age: "Datenalter",
        sync: "Skills aktualisieren",
        syncing: "Skills werden aktualisiert …",
        syncComplete: "{skills} Skills von {characters} Charakter(en) aktualisiert.",
        syncPartial: "{completed} aktualisiert, {failed} fehlgeschlagen. Anmeldung oder Verbindung prüfen.",
        syncEmpty: "Kein aktivierter Charakter für den Skill-Sync vorhanden.",
        syncError: "Skill-Sync konnte nicht gestartet werden.",
        loading: "Charakter-Skills werden geladen …",
        noData: "Noch kein vollständiger Skill-Snapshot vorhanden.",
        noMatches: "Keine Skills entsprechen der Auswahl.",
        queryError: "Die lokalen Charakter-Skills konnten nicht gelesen werden.",
      },
    },
    moduleKicker: "MODULVORSCHAU",
    moduleText:
      "Dieser Bereich zeigt bereits die geplante Informationsarchitektur. Fachlogik und echte EVE-Daten werden in den kommenden Releases schrittweise angeschlossen.",
    moduleCards: {
      assets: ["Standortbaum", "Besitzerfilter", "Änderungsverlauf"],
      blueprints: ["BPO- & BPC-Bibliothek", "ME-/TE-Forschung", "Industrie-Slots"],
      production: ["Stückliste", "Build vs. Buy", "Fertigungsroute"],
      invention: ["Kopierläufe", "Decryptor-Szenarien", "Datacore-Bedarf"],
      market: ["Preisprofile", "Orderbuchtiefe", "Chancen-Scanner"],
      projects: ["Projektportfolio", "Reservierungen", "Einkaufslisten"],
      pi: ["Kolonie-Timer", "Routenbalance", "P0–P4-Planung"],
    },
    moduleSecondary: {
      assets: "18,42 B ISK",
      blueprints: "18 forschungsbereit",
      production: "Materialdeckung",
      invention: "modellierter Erfolg",
      market: "beobachtete Signale",
      projects: "aktive Projekte",
      pi: "synthetische Kolonien",
    },
    planned: "Geplant",
    previewOnly: "Noch ohne Live-Funktion",
    footerVersion: "v0.0.5-preview.8",
  },
  en: {
    nav: {
      overview: "Overview",
      assets: "Assets",
      blueprints: "Blueprints & Jobs",
      production: "Production",
      invention: "T2 Invention",
      market: "Market",
      projects: "Projects",
      pi: "Planetary Industry",
    },
    navSection: "Workspaces",
    search: "Search the Foundry …",
    searchHint: "Open modules directly",
    noResults: "No module found",
    syncFresh: "Preview: 6 min ago",
    syncNow: "Up to date",
    refresh: "Simulate data refresh",
    notices: "Show notices",
    runtimeStatus: {
      checking: {
        title: "Desktop core",
        detail: "Checking status …",
      },
      starting: {
        title: "Local core starting",
        detail: "Checking the database in the program folder",
      },
      ready: {
        title: "Local core active",
        detail: "data\\foundry.sqlite3 · migration backup active",
      },
      error: {
        title: "Local core unavailable",
        detail: "Sidecar or program folder is unavailable",
      },
      preview: {
        title: "Design preview",
        detail: "Desktop core available in the app",
      },
      unavailable: {
        title: "Desktop core unavailable",
        detail: "Status request failed",
      },
    },
    runtimeErrors: {
      storage: "Program folder is not writable",
      database: "Database could not be opened safely",
      sidecar: "Local service stopped unexpectedly",
      fallback: "Sidecar or program folder is unavailable",
    },
    dataStatus: {
      loading: {
        title: "Loading local data",
        detail: "The database is verified before any content is shown.",
        noDataDetail: "The database is verified before any content is shown.",
      },
      refreshing: {
        title: "Cache visible · refresh in progress",
        detail: "The last verified state remains usable while data is refreshed.",
        noDataDetail: "The first refresh is in progress.",
      },
      empty: {
        title: "No local data yet",
        detail: "The first verified data state will appear after EVE sign-in.",
        noDataDetail: "The first verified data state will appear after EVE sign-in.",
      },
      fresh: {
        title: "Local data is current",
        detail: "The interface uses the latest fully verified cache.",
        noDataDetail: "No complete cache is available yet.",
      },
      stale: {
        title: "Stale cache remains visible",
        detail: "Known data stays available and is clearly marked as stale.",
        noDataDetail: "No usable cache is available yet.",
      },
      offline: {
        title: "Offline · cache remains available",
        detail: "The connection is unavailable; the last verified state is not deleted.",
        noDataDetail: "The connection is unavailable and there is no local state yet.",
      },
      error: {
        title: "Sync unavailable",
        detail: "The last verified cache remains visible while the error is tracked separately.",
        noDataDetail: "Synchronization failed and no cache is available yet.",
      },
    },
    dataAge: "Data age",
    noDataAge: "no data yet",
    updates: {
      label: "Update channel",
      select: "Select update channel",
      channels: {
        stable: "Official",
        beta: "Beta",
        preview: "Preview / test",
      },
      verified: "Signed test manifest verified",
      invalid: "Test manifest invalid · updates blocked",
      checking: "Checking test manifest",
      unavailable: "Updater is currently unavailable",
      disabled: "Downloads remain disabled",
      saving: "Saving channel …",
      saveError: "Channel could not be saved",
      desktopOnly: "Selectable in the desktop app",
    },
    sso: {
      eyebrow: "EVE SSO · PKCE",
      states: {
        idle: {
          title: "Connect an EVE character",
          detail: "Each sign-in authorizes exactly one character. Additional characters can be added individually afterwards.",
        },
        waiting: {
          title: "Browser sign-in in progress",
          detail: "EVE SSO is open in your system browser. The app waits up to three minutes for the secure callback.",
        },
        exchanging: {
          title: "Verifying EVE identity",
          detail: "The callback is valid. Signature, issuer, audience, expiry, scopes and character ID are being verified.",
        },
        connected: {
          title: "EVE character connected",
          detail: "The verified character identity was safely stored in the local database.",
        },
        cancelled: {
          title: "Sign-in cancelled",
          detail: "The local listener was stopped and all temporary PKCE values were discarded.",
        },
        "timed-out": {
          title: "Sign-in window expired",
          detail: "The attempt ended after three minutes. You can start again immediately.",
        },
        failed: {
          title: "Sign-in not completed",
          detail: "EVE SSO rejected the callback or permission was not granted.",
        },
      },
      start: "Connect character",
      startAnother: "Connect another character",
      cancel: "Cancel",
      retry: "Try again",
      desktopOnly: "Real sign-in is available in the Windows app.",
      commandError: "The sign-in could not be started or checked.",
      scopeTitle: "Automatic permissions",
      scopeAutomatic: "All SSO packages currently required by the app are requested automatically.",
      security: "System browser · S256 · random state · 3-minute window",
      connectedName: "Connected: {name}",
      packageLabels: {
        "industry-core": "Industry core",
        market: "Market",
        "planetary-industry": "Planetary industry",
        projects: "Projects & fittings",
        "private-structures": "Private structures",
      },
    },
    characters: {
      title: "Connected EVE characters",
      empty: "No verified character connected yet",
      unavailable: "Character management could not be loaded",
      count: "{count} connected locally",
      scopes: "Confirmed scopes: {count}",
      ungrouped: "Ungrouped",
      manage: "Manage",
      close: "Close editor",
      alias: "Local alias",
      aliasPlaceholder: "Optional display name",
      group: "Account group",
      active: "Use character actively",
      save: "Save changes",
      saving: "Saving …",
      delete: "Delete character completely",
      confirmDelete: "Confirm permanent deletion",
      cancelDelete: "Cancel deletion",
      deleteDetail: "Permanently removes identity, scopes, cache, history, and refresh token.",
      error: "The change could not be completed safely.",
      credential: "Credentials",
      credentialStates: {
        stored: "stored securely",
        missing: "reconnect required",
        unavailable: "store unavailable",
      },
      scopeStates: {
        granted: "complete",
        partial: "partial",
        missing: "missing",
      },
      inactive: "Inactive",
      groupsTitle: "Local account groups",
      newGroup: "New group",
      createGroup: "Create group",
      renameGroup: "Rename group",
      deleteGroup: "Delete group",
      noGroups: "No account group created yet",
      members: "{count} characters",
      reauthorizationShort: "Sign-in required",
      reauthorizationTitle: "Permissions need to be renewed",
      reauthorizationDetail: "This character is missing current permissions. Sign in again with the same character through EVE SSO.",
      reauthorize: "Sign in again",
    },
    fontSize: {
      label: "Font size",
      smaller: "Decrease font size",
      larger: "Increase font size",
      levels: {
        "very-small": "Very small",
        small: "Small",
        normal: "Normal",
        large: "Large",
        "very-large": "Very large",
      },
    },
    scope: {
      label: "Overview scope",
      select: "Choose view",
      combined: "All characters",
      combinedBadge: "COMBINED",
      characterBadge: "CHARACTER",
      accountGroups: "local account groups",
      characters: "characters",
      dataAge: "Data age",
      roles: {
        manufacturing: "Manufacturing & assets",
        research: "Research & blueprints",
        planetary: "Planetary industry",
      },
    },
    creatorLabel: "Created by",
    preview: "Design Preview",
    synthetic: "Domain views use synthetic data – secure EVE authorization is now available",
    dateLine: "OPERATIONS BRIEF · YC 128.09.08",
    greeting: "Good morning, pilot.",
    heroText:
      "Your production is running steadily. Two decisions need your attention today before the next manufacturing cycle begins.",
    planAction: "Open production plan",
    inspectAction: "Inspect data health",
    readiness: "Production readiness",
    readinessDetail: "for Project Aurora",
    metricLabels: {
      assets: "Asset value",
      jobs: "Active jobs",
      readiness: "Material coverage",
      attention: "Attention",
    },
    metricContext: {
      assets: "synthetic valuation",
      jobs: "50% utilized",
      readiness: "across all projects",
      attention: "in your Foundry",
    },
    operations: "Production status",
    operationsSubtitle: "Active initiatives and next completions",
    viewProduction: "View production",
    jobProgress: "Progress",
    due: "Due in",
    materialTitle: "Material coverage",
    materialSubtitle: "Project Aurora · complete bill of materials",
    materialTotal: "Total requirement",
    materialValue: "1.84 B ISK",
    coverageLegend: ["Available", "Buy", "Build"],
    buildBuy: "Build-vs-buy recommendation",
    buildBuyValue: "Manufacture 11 components",
    buildBuySaving: "estimated saving 126 M ISK",
    attentionTitle: "Needs attention",
    attentionSubtitle: "Sorted by urgency",
    attentionActions: ["Review PI", "Inspect", "Refresh"],
    attentionDetails: [
      "Ends in 2h 12m",
      "Location details unavailable",
      "Last quote set: 3h ago",
    ],
    activityTitle: "Foundry Pulse",
    activitySubtitle: "Latest traceable changes",
    activityTitles: [
      "Orion frame batch completed",
      "Purchase window detected",
      "Asset snapshot refreshed",
    ],
    activityDetails: [
      "8 units moved to Borealis Hangar",
      "Synthetic alloy basket is 6.4% below profile",
      "1,284 fictional positions reconciled",
    ],
    activityTimes: ["14 min ago", "39 min ago", "1h ago"],
    confidence: "Data confidence",
    confidenceValue: "High",
    cache: "Cache complete",
    localOnly: "Processed locally",
    assets: {
      kicker: "LOCAL ASSET INVENTORY",
      subtitle: "Search complete snapshots, filter by owner and location status, and save the result as CSV.",
      search: "Search type, location, owner, or ID",
      owner: "Owner",
      allOwners: "All owners",
      status: "Location status",
      allStatuses: "All statuses",
      statusLabels: {
        resolved: "Resolved",
        restricted: "Restricted",
        unresolved: "Unresolved",
        cycle: "Container cycle",
        pending: "Resolution pending",
      },
      positions: "positions",
      units: "units",
      type: "Type",
      location: "Location",
      quantity: "Quantity",
      age: "Data age",
      flag: "Hangar / division",
      export: "Export results as CSV",
      sync: "Refresh assets",
      syncing: "Refreshing assets …",
      syncComplete: "Updated {assets} positions from {characters} character(s).",
      syncPartial: "{completed} updated, {failed} failed. Check permissions and connection.",
      syncEmpty: "No enabled character is available for asset sync.",
      syncError: "Asset sync could not be started.",
      exporting: "Creating CSV …",
      exported: "{rows} rows saved · {path}",
      exportError: "The CSV could not be created safely.",
      loading: "Loading asset inventory …",
      unavailable: "The live asset view is available in the running desktop app.",
      noData: "No complete asset snapshot is available yet.",
      noMatches: "No assets match the search and filters.",
      queryError: "The local asset inventory could not be read.",
      pendingLocation: "Location resolution pending",
      resultRange: "{from}–{to} of {total}",
      previous: "Previous page",
      next: "Next page",
      liveNotice: "Live local asset snapshots · no synthetic domain values",
      deltas: {
        kicker: "ASSET DELTAS",
        title: "Traceable changes",
        subtitle: "Complete snapshot comparisons with traceable links to completed industry jobs.",
        filter: "Change type",
        all: "All changes",
        labels: {
          added: "Added",
          removed: "Removed",
          quantity: "Quantity changed",
          location: "Moved",
        },
        changes: "changes",
        beforeAfter: "Before → after",
        interval: "Comparison window",
        source: "Source evidence",
        loading: "Loading change history …",
        noBaseline: "No complete baseline snapshot is available yet.",
        unavailable: "The live change history is available in the running desktop app.",
        noChanges: "No changes were detected for this selection.",
        error: "The local change history could not be read.",
        correlationLabels: {
          linked: "Job linked", ambiguous: "Multiple job candidates",
          unmatched: "No matching job", unavailable: "No job snapshot",
          "not-applicable": "Not an output delta",
        },
      },
    },
    blueprints: {
      kicker: "LOCAL BLUEPRINT INVENTORY",
      subtitle: "BPOs and BPCs for all active characters, including ME, TE, and remaining runs.",
      search: "Search blueprint, owner, location, or ID",
      owner: "Owner",
      allOwners: "All owners",
      kind: "Kind",
      allKinds: "BPO & BPC",
      original: "Original (BPO)",
      copy: "Copy (BPC)",
      type: "Blueprint",
      me: "ME",
      te: "TE",
      runs: "Runs",
      location: "Division",
      age: "Data age",
      count: "blueprints",
      unlimited: "unlimited",
      sync: "Refresh blueprints",
      syncing: "Refreshing blueprints …",
      syncComplete: "Updated {blueprints} blueprints from {characters} character(s).",
      syncPartial: "{completed} updated, {failed} failed. Check sign-in or connection.",
      syncEmpty: "No enabled character is available for blueprint sync.",
      syncError: "Blueprint sync could not be started.",
      loading: "Loading blueprint inventory …",
      unavailable: "The live blueprint view is available in the Windows app.",
      noData: "No complete blueprint snapshot is available yet.",
      noMatches: "No blueprints match the selection.",
      queryError: "The local blueprint inventory could not be read.",
      resultRange: "{from}–{to} of {total}",
      previous: "Previous page",
      next: "Next page",
      liveNotice: "Live local blueprint snapshots · automatic at application startup",
      jobs: {
        kicker: "PERSONAL INDUSTRY JOBS",
        title: "Industry jobs",
        subtitle: "Active and completed ESI jobs with traceable blueprint and asset correlation.",
        search: "Search job, blueprint, product, owner, or ID",
        status: "Status",
        allStatuses: "All statuses",
        statusLabels: {
          active: "Active", cancelled: "Cancelled", delivered: "Delivered",
          paused: "Paused", ready: "Ready", reverted: "Reverted",
        },
        activity: "Activity",
        allActivities: "All activities",
        activityLabels: {
          manufacturing: "Manufacturing", "research-time": "Time research",
          "research-material": "Material research", copying: "Copying",
          "reverse-engineering": "Reverse engineering", invention: "Invention",
          reactions: "Reaction",
        },
        correlation: "Correlation",
        allCorrelations: "All correlations",
        correlationLabels: {
          linked: "Linked", partial: "Partially linked", ambiguous: "Multiple candidates",
          unmatched: "No match", pending: "Still running",
        },
        blueprint: "Blueprint / job",
        product: "Product",
        owner: "Owner / activity",
        runs: "Runs",
        timeline: "Timeline",
        location: "Facility / output",
        evidence: "Source evidence",
        currentBlueprint: "current blueprint",
        historicalBlueprint: "historical blueprint",
        noBlueprint: "blueprint not in inventory",
        noBlueprintData: "no blueprint snapshot",
        assetLinked: "asset delta linked",
        assetAmbiguous: "multiple asset candidates",
        assetPending: "asset output pending",
        assetUnmatched: "no matching asset delta",
        assetUnavailable: "no asset history",
        assetNotApplicable: "no output expected",
        successful: "successful",
        activeCount: "active jobs",
        count: "jobs",
        age: "Data age",
        sync: "Refresh jobs",
        syncing: "Refreshing jobs …",
        syncComplete: "Updated {jobs} jobs from {characters} character(s).",
        syncPartial: "{completed} updated, {failed} failed. Check sign-in or connection.",
        syncEmpty: "No enabled character is available for job sync.",
        syncError: "Industry-job sync could not be started.",
        loading: "Loading industry jobs …",
        noData: "No complete industry-job snapshot is available yet.",
        noMatches: "No industry jobs match the selection.",
        queryError: "The local industry jobs could not be read.",
      },
      skills: {
        kicker: "CHARACTER SKILLS",
        title: "Skills for industry and planning",
        subtitle: "Complete ESI skill levels for every enabled character, ready for later feasibility and gap checks.",
        search: "Search skill, owner, or type ID",
        level: "Trained level",
        allLevels: "All levels",
        activeState: "Active state",
        allActiveStates: "All states",
        stateLabels: {
          normal: "Normally active",
          limited: "Active level limited",
          boosted: "Temporarily boosted",
        },
        skill: "Skill",
        owner: "Owner",
        trained: "Trained",
        active: "Active",
        skillpoints: "Skill points",
        source: "Source",
        count: "skills",
        totalSp: "allocated SP",
        unallocatedSp: "unallocated SP",
        age: "Data age",
        sync: "Refresh skills",
        syncing: "Refreshing skills …",
        syncComplete: "Updated {skills} skills from {characters} character(s).",
        syncPartial: "{completed} updated, {failed} failed. Check sign-in or connection.",
        syncEmpty: "No enabled character is available for skill sync.",
        syncError: "Character-skill sync could not be started.",
        loading: "Loading character skills …",
        noData: "No complete character-skill snapshot is available yet.",
        noMatches: "No skills match the selection.",
        queryError: "The local character skills could not be read.",
      },
    },
    moduleKicker: "MODULE PREVIEW",
    moduleText:
      "This area already shows the planned information architecture. Domain logic and real EVE data will be connected incrementally in upcoming releases.",
    moduleCards: {
      assets: ["Location tree", "Ownership filters", "Change history"],
      blueprints: ["BPO & BPC library", "ME / TE research", "Industry slots"],
      production: ["Bill of materials", "Build vs. buy", "Manufacturing route"],
      invention: ["Copying batches", "Decryptor scenarios", "Datacore demand"],
      market: ["Price profiles", "Order depth", "Opportunity scanner"],
      projects: ["Project portfolio", "Reservations", "Shopping lists"],
      pi: ["Colony timers", "Route balance", "P0–P4 planning"],
    },
    moduleSecondary: {
      assets: "18.42 B ISK",
      blueprints: "18 research-ready",
      production: "material coverage",
      invention: "modeled success",
      market: "tracked signals",
      projects: "active projects",
      pi: "synthetic colonies",
    },
    planned: "Planned",
    previewOnly: "No live function yet",
    footerVersion: "v0.0.5-preview.8",
  },
} as const;

function TrendLine({
  id,
  points,
  warning = false,
}: {
  id: string;
  points: readonly number[];
  warning?: boolean;
}) {
  const width = 132;
  const height = 48;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = Math.max(max - min, 1);
  const coordinates = points.map((point, index) => {
    const x = (index / (points.length - 1)) * width;
    const y = height - 6 - ((point - min) / range) * (height - 14);
    return [x, y] as const;
  });
  const line = coordinates.map(([x, y], index) => `${index === 0 ? "M" : "L"}${x},${y}`).join(" ");
  const area = `${line} L${width},${height} L0,${height} Z`;

  return (
    <svg className="trend-line" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <defs>
        <linearGradient id={`fade-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={warning ? "#de7867" : "#66c7bd"} stopOpacity="0.3" />
          <stop offset="1" stopColor={warning ? "#de7867" : "#66c7bd"} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#fade-${id})`} />
      <path d={line} fill="none" stroke={warning ? "#de7867" : "#66c7bd"} strokeWidth="2" />
    </svg>
  );
}

function StatusDot({ tone = "good" }: { tone?: "good" | "warn" | "critical" }) {
  return <span className={`status-dot status-dot--${tone}`} aria-hidden="true" />;
}

function formatDataAge(seconds: number, locale: Locale): string {
  if (seconds < 60) return locale === "de" ? "unter 1 Min." : "under 1 min";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return locale === "de" ? `${minutes} Min.` : `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return locale === "de" ? `${hours} Std.` : `${hours} hr`;
  const days = Math.floor(hours / 24);
  return locale === "de" ? `${days} Tage` : `${days} days`;
}

function DataStateNotice({
  state,
  hasCachedData,
  ageSeconds,
  locale,
  t,
}: {
  state: LocalDataState;
  hasCachedData: boolean;
  ageSeconds: number | null;
  locale: Locale;
  t: Translation;
}) {
  const statusCopy = t.dataStatus[state];
  const detail = hasCachedData ? statusCopy.detail : statusCopy.noDataDetail;
  const Icon = state === "fresh"
    ? CircleCheck
    : state === "stale"
      ? Clock3
      : state === "offline" || state === "error"
        ? AlertTriangle
        : state === "loading" || state === "refreshing"
          ? RefreshCw
          : Database;

  return (
    <section className={`data-state data-state--${state}`} role="status" aria-live="polite">
      <div className="data-state__icon" aria-hidden="true">
        <Icon className={state === "loading" || state === "refreshing" ? "spin" : ""} size={17} />
      </div>
      <div className="data-state__copy">
        <strong>{statusCopy.title}</strong>
        <span>{detail}</span>
      </div>
      <div className="data-state__age">
        <Clock3 size={13} aria-hidden="true" />
        <span>
          {ageSeconds === null ? t.noDataAge : `${t.dataAge}: ${formatDataAge(ageSeconds, locale)}`}
        </span>
      </div>
    </section>
  );
}

export function App({
  runtimeLoader = loadDesktopRuntimeStatus,
  updateChannelSetter = setDesktopUpdateChannel,
  ssoStarter = startEveSso,
  ssoStatusLoader = loadEveSsoStatus,
  ssoCanceller = cancelEveSso,
  charactersLoader = loadEveCharacters,
  accountGroupsLoader = loadAccountGroups,
  characterUpdater = updateEveCharacter,
  characterDeleter = deleteEveCharacter,
  accountGroupCreator = createAccountGroup,
  accountGroupRenamer = renameAccountGroup,
  accountGroupDeleter = deleteAccountGroup,
  assetsLoader = loadAssets,
  assetsCsvExporter = exportAssetsCsv,
  assetDeltasLoader = loadAssetDeltas,
  assetSyncer = syncAssets,
  blueprintsLoader = loadBlueprints,
  blueprintSyncer = syncBlueprints,
  industryJobsLoader = loadIndustryJobs,
  industryJobSyncer = syncIndustryJobs,
  characterSkillsLoader = loadCharacterSkills,
  characterSkillSyncer = syncCharacterSkills,
  fontScaleSetter = setDesktopFontScale,
}: {
  runtimeLoader?: () => Promise<DesktopRuntimeStatus>;
  updateChannelSetter?: (channel: UpdateChannel) => Promise<UpdaterStatus>;
  ssoStarter?: (scopePackages: SsoScopePackage[]) => Promise<SsoLoginStatus>;
  ssoStatusLoader?: () => Promise<SsoLoginStatus>;
  ssoCanceller?: () => Promise<SsoLoginStatus>;
  charactersLoader?: () => Promise<EveCharacter[]>;
  accountGroupsLoader?: () => Promise<AccountGroup[]>;
  characterUpdater?: (characterId: number, update: CharacterUpdate) => Promise<EveCharacter>;
  characterDeleter?: (characterId: number) => Promise<void>;
  accountGroupCreator?: (label: string) => Promise<AccountGroup>;
  accountGroupRenamer?: (groupId: number, label: string) => Promise<AccountGroup>;
  accountGroupDeleter?: (groupId: number) => Promise<void>;
  assetsLoader?: (query: AssetQuery) => Promise<AssetPage>;
  assetsCsvExporter?: (
    query: Omit<AssetQuery, "offset" | "limit">,
  ) => Promise<AssetCsvExport>;
  assetDeltasLoader?: (query: AssetDeltaQuery) => Promise<AssetDeltaPage>;
  assetSyncer?: () => Promise<AssetSyncResult>;
  blueprintsLoader?: (query: BlueprintQuery) => Promise<BlueprintPage>;
  blueprintSyncer?: () => Promise<BlueprintSyncResult>;
  industryJobsLoader?: (query: IndustryJobQuery) => Promise<IndustryJobPage>;
  industryJobSyncer?: () => Promise<IndustryJobSyncResult>;
  characterSkillsLoader?: (query: CharacterSkillQuery) => Promise<CharacterSkillPage>;
  characterSkillSyncer?: () => Promise<CharacterSkillSyncResult>;
  fontScaleSetter?: (fontScale: FontScale) => Promise<AppearanceStatus>;
}) {
  const [locale, setLocale] = useState<Locale>("de");
  const [activeModule, setActiveModule] = useState<ModuleId>("overview");
  const [query, setQuery] = useState("");
  const [searchFocused, setSearchFocused] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [assetRevision, setAssetRevision] = useState(0);
  const [blueprintRevision, setBlueprintRevision] = useState(0);
  const [industryJobRevision, setIndustryJobRevision] = useState(0);
  const [characterSkillRevision, setCharacterSkillRevision] = useState(0);
  const initialAssetSyncStarted = useRef(false);
  const [runtimeStatus, setRuntimeStatus] = useState(initialRuntimeStatus);
  const [overviewScope, setOverviewScope] = useState<OverviewScopeId>("all");
  const [savingUpdateChannel, setSavingUpdateChannel] = useState(false);
  const [updateChannelError, setUpdateChannelError] = useState(false);
  const [ssoStatus, setSsoStatus] = useState(initialSsoStatus);
  const [ssoBusy, setSsoBusy] = useState(false);
  const [ssoCommandError, setSsoCommandError] = useState(false);
  const [characters, setCharacters] = useState<EveCharacter[]>([]);
  const [managedGroups, setManagedGroups] = useState<AccountGroup[]>([]);
  const [charactersError, setCharactersError] = useState(false);
  const [fontScale, setFontScale] = useState<FontScale>("normal");
  const [fontScaleBusy, setFontScaleBusy] = useState(false);
  const t = copy[locale];

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  useEffect(() => {
    document.documentElement.dataset.fontScale = fontScale;
  }, [fontScale]);

  useEffect(() => {
    let active = true;
    let pollTimer: number | undefined;
    const refreshRuntimeStatus = async () => {
      const status = await runtimeLoader();
      if (!active) return;
      setRuntimeStatus(status);
      if (status.state === "ready") setFontScale(status.appearance.fontScale);
      if (status.state === "ready" && status.sidecar === "starting") {
        pollTimer = window.setTimeout(refreshRuntimeStatus, 250);
      }
    };
    void refreshRuntimeStatus();
    return () => {
      active = false;
      if (pollTimer !== undefined) window.clearTimeout(pollTimer);
    };
  }, [runtimeLoader]);

  const nativeCoreReady = runtimeStatus.state === "ready" && runtimeStatus.sidecar === "ready";

  const runAssetSync = useCallback(async () => {
    const result = await assetSyncer();
    setAssetRevision((revision) => revision + 1);
    return result;
  }, [assetSyncer]);

  const runBlueprintSync = useCallback(async () => {
    const result = await blueprintSyncer();
    setBlueprintRevision((revision) => revision + 1);
    return result;
  }, [blueprintSyncer]);

  const runIndustryJobSync = useCallback(async () => {
    const result = await industryJobSyncer();
    setIndustryJobRevision((revision) => revision + 1);
    return result;
  }, [industryJobSyncer]);

  const runCharacterSkillSync = useCallback(async () => {
    const result = await characterSkillSyncer();
    setCharacterSkillRevision((revision) => revision + 1);
    return result;
  }, [characterSkillSyncer]);

  const runAllSyncs = useCallback(async () => {
    setSyncing(true);
    try {
      const sources = await Promise.allSettled([
        runAssetSync(), runBlueprintSync(), runCharacterSkillSync(),
      ]);
      const jobs = await Promise.allSettled([runIndustryJobSync()]);
      const failed = [...sources, ...jobs].find((result) => result.status === "rejected");
      if (failed?.status === "rejected") throw failed.reason;
      const assetResult = sources[0];
      if (assetResult.status === "rejected") throw assetResult.reason;
      return assetResult.value;
    } finally {
      setSyncing(false);
    }
  }, [runAssetSync, runBlueprintSync, runCharacterSkillSync, runIndustryJobSync]);

  useEffect(() => {
    if (!nativeCoreReady) return;
    let active = true;
    void Promise.all([ssoStatusLoader(), charactersLoader(), accountGroupsLoader()])
      .then(([status, loadedCharacters, loadedGroups]) => {
        if (active) {
          setSsoStatus(status);
          setCharacters(loadedCharacters);
          setManagedGroups(loadedGroups);
          setCharactersError(false);
          if (
            loadedCharacters.some((character) => character.enabled) &&
            status.state !== "connected" &&
            !initialAssetSyncStarted.current
          ) {
            initialAssetSyncStarted.current = true;
            void runAllSyncs().catch(() => undefined);
          }
        }
      })
      .catch(() => {
        if (active) {
          setSsoCommandError(true);
          setCharactersError(true);
        }
      });
    return () => {
      active = false;
    };
  }, [accountGroupsLoader, charactersLoader, nativeCoreReady, runAllSyncs, ssoStatusLoader]);

  useEffect(() => {
    if (!nativeCoreReady || !["waiting", "exchanging"].includes(ssoStatus.state)) return;
    let active = true;
    let pollTimer: number | undefined;
    const poll = async () => {
      try {
        const status = await ssoStatusLoader();
        if (!active) return;
        setSsoStatus(status);
        setSsoCommandError(false);
        if (status.state === "waiting" || status.state === "exchanging") {
          pollTimer = window.setTimeout(poll, 750);
        }
      } catch {
        if (active) {
          setSsoCommandError(true);
          pollTimer = window.setTimeout(poll, 1_500);
        }
      }
    };
    pollTimer = window.setTimeout(poll, 750);
    return () => {
      active = false;
      if (pollTimer !== undefined) window.clearTimeout(pollTimer);
    };
  }, [nativeCoreReady, ssoStatus.state, ssoStatusLoader]);

  useEffect(() => {
    if (!nativeCoreReady || ssoStatus.state !== "connected") return;
    let active = true;
    void Promise.all([charactersLoader(), accountGroupsLoader()])
      .then(([loadedCharacters, loadedGroups]) => {
        if (active) {
          setCharacters(loadedCharacters);
          setManagedGroups(loadedGroups);
          setCharactersError(false);
          if (loadedCharacters.some((character) => character.enabled)) {
            initialAssetSyncStarted.current = true;
            void runAllSyncs().catch(() => undefined);
          }
        }
      })
      .catch(() => {
        if (active) setCharactersError(true);
      });
    return () => {
      active = false;
    };
  }, [accountGroupsLoader, charactersLoader, nativeCoreReady, runAllSyncs, ssoStatus.state]);

  const refreshCharacterManagement = async () => {
    try {
      const [loadedCharacters, loadedGroups] = await Promise.all([
        charactersLoader(),
        accountGroupsLoader(),
      ]);
      setCharacters(loadedCharacters);
      setManagedGroups(loadedGroups);
      setCharactersError(false);
    } catch {
      setCharactersError(true);
      throw new Error("character-management-refresh-failed");
    }
  };

  const runtimePresentationState =
    runtimeStatus.state === "ready" ? runtimeStatus.sidecar : runtimeStatus.state;
  const localData = runtimeStatus.state === "ready" ? runtimeStatus.data : null;
  const updater = runtimeStatus.state === "ready" ? runtimeStatus.updater : null;
  const nativeSyncLabel = localData?.ageSeconds === null
    ? t.noDataAge
    : localData
      ? `${t.dataAge}: ${formatDataAge(localData.ageSeconds, locale)}`
      : null;
  let runtimeDetail: string = t.runtimeStatus[runtimePresentationState].detail;
  if (runtimeStatus.state === "ready" && runtimeStatus.sidecar === "error") {
    switch (runtimeStatus.errorCode) {
      case "program-storage-unavailable":
        runtimeDetail = t.runtimeErrors.storage;
        break;
      case "database-startup-failed":
        runtimeDetail = t.runtimeErrors.database;
        break;
      case "sidecar-exited":
        runtimeDetail = t.runtimeErrors.sidecar;
        break;
      default:
        runtimeDetail = t.runtimeErrors.fallback;
    }
  }

  const searchResults = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase(locale);
    if (!normalized) return navigation;
    return navigation.filter(({ id }) => t.nav[id].toLocaleLowerCase(locale).includes(normalized));
  }, [locale, query, t]);

  const selectModule = (id: ModuleId) => {
    setActiveModule(id);
    setQuery("");
    setSearchFocused(false);
  };

  const chooseUpdateChannel = async (channel: UpdateChannel) => {
    if (runtimeStatus.state !== "ready" || runtimeStatus.sidecar !== "ready") return;
    setSavingUpdateChannel(true);
    setUpdateChannelError(false);
    try {
      const nextUpdater = await updateChannelSetter(channel);
      setRuntimeStatus((current) => current.state === "ready"
        ? { ...current, updater: nextUpdater }
        : current);
    } catch {
      setUpdateChannelError(true);
    } finally {
      setSavingUpdateChannel(false);
    }
  };

  const changeFontScale = async (direction: -1 | 1) => {
    if (fontScaleBusy) return;
    const currentIndex = fontScales.indexOf(fontScale);
    const nextIndex = Math.min(fontScales.length - 1, Math.max(0, currentIndex + direction));
    const nextScale = fontScales[nextIndex];
    if (nextScale === fontScale) return;
    const previousScale = fontScale;
    setFontScale(nextScale);
    setFontScaleBusy(true);
    try {
      const appearance = await fontScaleSetter(nextScale);
      setFontScale(appearance.fontScale);
      setRuntimeStatus((current) => current.state === "ready"
        ? { ...current, appearance }
        : current);
    } catch {
      setFontScale(previousScale);
    } finally {
      setFontScaleBusy(false);
    }
  };

  const beginSsoLogin = async () => {
    if (!nativeCoreReady || ssoStatus.state === "waiting" || ssoStatus.state === "exchanging") return;
    setSsoBusy(true);
    setSsoCommandError(false);
    try {
      setSsoStatus(await ssoStarter([...ssoScopePackages]));
    } catch {
      setSsoCommandError(true);
    } finally {
      setSsoBusy(false);
    }
  };

  const abortSsoLogin = async () => {
    if (!nativeCoreReady || !["waiting", "exchanging"].includes(ssoStatus.state)) return;
    setSsoBusy(true);
    setSsoCommandError(false);
    try {
      setSsoStatus(await ssoCanceller());
    } catch {
      setSsoCommandError(true);
    } finally {
      setSsoBusy(false);
    }
  };

  const scrollToAttention = () => {
    document.getElementById("attention-panel")?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <div>
            <div className="brand-name">NEW EDEN</div>
            <div className="brand-subtitle">FOUNDRY</div>
          </div>
        </div>

        <div className="nav-label">{t.navSection}</div>
        <nav className="navigation" aria-label={t.navSection}>
          {navigation.map(({ id, icon: Icon }) => (
            <button
              className={`nav-item ${activeModule === id ? "nav-item--active" : ""}`}
              key={id}
              type="button"
              onClick={() => selectModule(id)}
              aria-current={activeModule === id ? "page" : undefined}
            >
              <Icon size={18} strokeWidth={1.8} />
              <span>{t.nav[id]}</span>
              {id === "overview" && <span className="nav-signal" aria-hidden="true" />}
              {id === "pi" && <span className="nav-count">2</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-spacer" />

        <section className="update-channel" aria-label={t.updates.label}>
          <div className="update-channel__heading">
            <RefreshCw size={14} aria-hidden="true" />
            <span>{t.updates.label}</span>
          </div>
          <select
            value={updater?.channel ?? "stable"}
            onChange={(event) => void chooseUpdateChannel(event.target.value as UpdateChannel)}
            disabled={
              savingUpdateChannel ||
              runtimeStatus.state !== "ready" ||
              runtimeStatus.sidecar !== "ready" ||
              updater?.manifestState !== "verified"
            }
            aria-label={t.updates.select}
          >
            {(["stable", "beta", "preview"] as const).map((channel) => (
              <option value={channel} key={channel}>{t.updates.channels[channel]}</option>
            ))}
          </select>
          <small className={updateChannelError || updater?.manifestState === "invalid" ? "is-error" : ""}>
            {updateChannelError
              ? t.updates.saveError
              : savingUpdateChannel
                ? t.updates.saving
                : updater
                  ? `${t.updates[updater.manifestState]} · ${t.updates.disabled}`
                  : t.updates.desktopOnly}
          </small>
        </section>

        <div className={`local-status local-status--${runtimePresentationState}`} role="status">
          <div className="local-status__icon">
            <ShieldCheck size={17} />
          </div>
          <div>
            <strong>{t.runtimeStatus[runtimePresentationState].title}</strong>
            <span>{runtimeDetail}</span>
          </div>
        </div>

        <div className="sidebar-footer">
          <span>{t.footerVersion}</span>
          <span className="creator-credit">
            {t.creatorLabel} <strong>Savoxmedia</strong>
          </span>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="topbar-title">
            <span>{t.nav[activeModule]}</span>
            <small>New Eden Foundry</small>
          </div>

          <div className="search-wrap">
            <Search size={17} aria-hidden="true" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => window.setTimeout(() => setSearchFocused(false), 120)}
              placeholder={t.search}
              aria-label={t.search}
            />
            <kbd><Command size={11} /> K</kbd>
            {searchFocused && (
              <div className="search-results">
                <span className="search-results__hint">{t.searchHint}</span>
                {searchResults.length > 0 ? (
                  searchResults.slice(0, 5).map(({ id, icon: Icon }) => (
                    <button key={id} type="button" onMouseDown={() => selectModule(id)}>
                      <Icon size={16} />
                      <span>{t.nav[id]}</span>
                      <ArrowRight size={14} />
                    </button>
                  ))
                ) : (
                  <span className="search-results__empty">{t.noResults}</span>
                )}
              </div>
            )}
          </div>

          <button
            className={`sync-status ${localData ? `sync-status--${localData.state}` : ""}`}
            type="button"
            onClick={() => void runAllSyncs().catch(() => undefined)}
            aria-label={t.refresh}
            disabled={!nativeCoreReady || syncing}
          >
            <RefreshCw
              className={syncing || localData?.state === "loading" || localData?.state === "refreshing" ? "spin" : ""}
              size={15}
            />
            <span>{nativeSyncLabel ?? (syncing ? t.syncNow : t.syncFresh)}</span>
          </button>

          <div className="font-size-control" aria-label={t.fontSize.label}>
            <Type size={15} aria-hidden="true" />
            <button
              type="button"
              onClick={() => void changeFontScale(-1)}
              disabled={fontScaleBusy || fontScale === fontScales[0]}
              aria-label={t.fontSize.smaller}
              title={t.fontSize.smaller}
            >
              <Minus size={13} />
            </button>
            <span title={t.fontSize.levels[fontScale]}>{fontScales.indexOf(fontScale) + 1}/5</span>
            <button
              type="button"
              onClick={() => void changeFontScale(1)}
              disabled={fontScaleBusy || fontScale === fontScales[fontScales.length - 1]}
              aria-label={t.fontSize.larger}
              title={t.fontSize.larger}
            >
              <Plus size={13} />
            </button>
          </div>

          <div className="language-switch" aria-label="Language">
            <Languages size={15} />
            {(["de", "en"] as const).map((language) => (
              <button
                key={language}
                type="button"
                className={locale === language ? "is-active" : ""}
                onClick={() => setLocale(language)}
                aria-label={language.toUpperCase()}
              >
                {language.toUpperCase()}
              </button>
            ))}
          </div>

          <button className="icon-button" type="button" aria-label={t.notices} onClick={scrollToAttention}>
            <Bell size={18} />
            <span className="notification-dot" aria-hidden="true" />
          </button>
        </header>

        {(activeModule === "assets" || activeModule === "blueprints") && nativeCoreReady ? (
          <div className="preview-strip preview-strip--live" role="status">
            <Database size={15} />
            <strong>LOCAL</strong>
            <span>{activeModule === "blueprints" ? t.blueprints.liveNotice : t.assets.liveNotice}</span>
          </div>
        ) : (
          <div className="preview-strip" role="status">
            <FlaskConical size={15} />
            <strong>{t.preview}</strong>
            <span>{t.synthetic}</span>
            <span className="preview-strip__meta">synthetic: {String(demoMetadata.synthetic)}</span>
          </div>
        )}

        <section className={`sso-panel sso-panel--${ssoStatus.state}`} aria-labelledby="sso-title">
          <div className="sso-panel__icon" aria-hidden="true">
            {ssoStatus.state === "waiting" || ssoStatus.state === "exchanging"
              ? <RefreshCw className="spin" size={20} />
              : <LogIn size={20} />}
          </div>
          <div className="sso-panel__copy" aria-live="polite">
            <span>{t.sso.eyebrow}</span>
            <strong id="sso-title">{t.sso.states[ssoStatus.state].title}</strong>
            <p>
              {ssoCommandError
                ? t.sso.commandError
                : ssoStatus.state === "connected" && ssoStatus.character
                  ? t.sso.connectedName.replace("{name}", ssoStatus.character.name)
                  : t.sso.states[ssoStatus.state].detail}
            </p>
            <small>{nativeCoreReady ? t.sso.security : t.sso.desktopOnly}</small>
          </div>
          <div className="sso-scopes sso-scopes--automatic">
            <strong>{t.sso.scopeTitle}</strong>
            <span>{t.sso.scopeAutomatic}</span>
          </div>
          <div className="sso-panel__actions">
            {ssoStatus.state === "waiting" || ssoStatus.state === "exchanging" ? (
              <button type="button" className="sso-cancel" onClick={() => void abortSsoLogin()} disabled={ssoBusy}>
                <X size={15} />
                {t.sso.cancel}
              </button>
            ) : (
              <button type="button" className="sso-start" onClick={() => void beginSsoLogin()} disabled={!nativeCoreReady || ssoBusy}>
                <LogIn size={15} />
                {ssoStatus.state === "connected"
                  ? t.sso.startAnother
                  : ssoStatus.state === "idle"
                    ? t.sso.start
                    : t.sso.retry}
              </button>
            )}
          </div>
        </section>

        <CharacterManager
          characters={characters}
          groups={managedGroups}
          unavailable={charactersError}
          disabled={!nativeCoreReady}
          t={t}
          updateCharacter={characterUpdater}
          deleteCharacter={characterDeleter}
          createGroup={accountGroupCreator}
          renameGroup={accountGroupRenamer}
          deleteGroup={accountGroupDeleter}
          onRefresh={refreshCharacterManagement}
          onReauthorize={beginSsoLogin}
        />

        {localData && (
          <DataStateNotice
            state={localData.state}
            hasCachedData={localData.hasCachedData}
            ageSeconds={localData.ageSeconds}
            locale={locale}
            t={t}
          />
        )}

        {activeModule === "overview" ? (
          <Overview
            locale={locale}
            t={t}
            scope={overviewScope}
            onScopeChange={setOverviewScope}
            onOpenProduction={() => selectModule("production")}
            onInspect={scrollToAttention}
          />
        ) : activeModule === "assets" ? (
          <AssetWorkspace
            available={nativeCoreReady}
            locale={locale}
            t={t}
            loadAssets={assetsLoader}
            exportCsv={assetsCsvExporter}
            loadDeltas={assetDeltasLoader}
            syncAssets={runAssetSync}
            refreshRevision={assetRevision}
          />
        ) : activeModule === "blueprints" ? (
          <BlueprintWorkspace
            available={nativeCoreReady}
            locale={locale}
            t={t}
            loadBlueprints={blueprintsLoader}
            syncBlueprints={runBlueprintSync}
            refreshRevision={blueprintRevision}
            loadIndustryJobs={industryJobsLoader}
            syncIndustryJobs={runIndustryJobSync}
            industryJobRevision={industryJobRevision}
            loadCharacterSkills={characterSkillsLoader}
            syncCharacterSkills={runCharacterSkillSync}
            characterSkillRevision={characterSkillRevision}
          />
        ) : (
          <ModulePreview activeModule={activeModule} t={t} />
        )}
      </main>
    </div>
  );
}

type Translation = (typeof copy)[Locale];

function AssetWorkspace({
  available,
  locale,
  t,
  loadAssets: loadAssetPage,
  exportCsv,
  loadDeltas: loadDeltaPage,
  syncAssets: runAssetSync,
  refreshRevision,
}: {
  available: boolean;
  locale: Locale;
  t: Translation;
  loadAssets: (query: AssetQuery) => Promise<AssetPage>;
  exportCsv: (query: Omit<AssetQuery, "offset" | "limit">) => Promise<AssetCsvExport>;
  loadDeltas: (query: AssetDeltaQuery) => Promise<AssetDeltaPage>;
  syncAssets: () => Promise<AssetSyncResult>;
  refreshRevision: number;
}) {
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [ownerCharacterId, setOwnerCharacterId] = useState<number | null>(null);
  const [locationStatus, setLocationStatus] = useState<AssetLocationStatus | null>(null);
  const [sortBy, setSortBy] = useState<AssetSortField>("type");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<AssetPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exported, setExported] = useState<AssetCsvExport | null>(null);
  const [exportFailed, setExportFailed] = useState(false);
  const [deltaChangeType, setDeltaChangeType] = useState<AssetDeltaChangeType | null>(null);
  const [deltaOffset, setDeltaOffset] = useState(0);
  const [deltaPage, setDeltaPage] = useState<AssetDeltaPage | null>(null);
  const [deltasLoading, setDeltasLoading] = useState(false);
  const [deltasFailed, setDeltasFailed] = useState(false);
  const [syncResult, setSyncResult] = useState<AssetSyncResult | null>(null);
  const [syncFailed, setSyncFailed] = useState(false);
  const [assetsSyncing, setAssetsSyncing] = useState(false);
  const numberFormat = useMemo(
    () => new Intl.NumberFormat(locale === "de" ? "de-DE" : "en-US"),
    [locale],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setAppliedSearch(search.trim().replace(/\s+/g, " "));
      setOffset(0);
      setDeltaOffset(0);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (!available) return;
    let active = true;
    setLoading(true);
    setFailed(false);
    void loadAssetPage({
      search: appliedSearch,
      ownerCharacterId,
      locationStatus,
      offset,
      limit: assetPageSize,
      sortBy,
      sortDirection,
    })
      .then((loadedPage) => {
        if (!active) return;
        if (loadedPage.total > 0 && loadedPage.offset >= loadedPage.total) {
          setOffset(Math.floor((loadedPage.total - 1) / assetPageSize) * assetPageSize);
          return;
        }
        setPage(loadedPage);
        setFailed(false);
      })
      .catch(() => {
        if (active) setFailed(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [appliedSearch, available, loadAssetPage, locationStatus, offset, ownerCharacterId, refreshRevision, sortBy, sortDirection]);

  useEffect(() => {
    if (!available) return;
    let active = true;
    setDeltasLoading(true);
    setDeltasFailed(false);
    void loadDeltaPage({
      search: appliedSearch,
      ownerCharacterId,
      changeType: deltaChangeType,
      offset: deltaOffset,
      limit: assetDeltaPageSize,
    })
      .then((loadedPage) => {
        if (!active) return;
        if (loadedPage.total > 0 && loadedPage.offset >= loadedPage.total) {
          setDeltaOffset(Math.floor((loadedPage.total - 1) / assetDeltaPageSize) * assetDeltaPageSize);
          return;
        }
        setDeltaPage(loadedPage);
        setDeltasFailed(false);
      })
      .catch(() => {
        if (active) setDeltasFailed(true);
      })
      .finally(() => {
        if (active) setDeltasLoading(false);
      });
    return () => {
      active = false;
    };
  }, [appliedSearch, available, deltaChangeType, deltaOffset, loadDeltaPage, ownerCharacterId, refreshRevision]);

  const refreshAssets = async () => {
    if (!available || assetsSyncing) return;
    setAssetsSyncing(true);
    setSyncFailed(false);
    setSyncResult(null);
    try {
      const result = await runAssetSync();
      setSyncResult(result);
      setOffset(0);
      setDeltaOffset(0);
    } catch {
      setSyncFailed(true);
    } finally {
      setAssetsSyncing(false);
    }
  };

  const createExport = async () => {
    if (!available || exporting) return;
    setExporting(true);
    setExported(null);
    setExportFailed(false);
    try {
      setExported(await exportCsv({
        search: appliedSearch,
        ownerCharacterId,
        locationStatus,
        sortBy,
        sortDirection,
      }));
    } catch {
      setExportFailed(true);
    } finally {
      setExporting(false);
    }
  };

  const total = page?.total ?? 0;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + (page?.items.length ?? 0), total);
  const resultRange = t.assets.resultRange
    .replace("{from}", numberFormat.format(from))
    .replace("{to}", numberFormat.format(to))
    .replace("{total}", numberFormat.format(total));
  const statusTone = (status: AssetLocationStatus) =>
    status === "resolved"
      ? "good"
      : status === "restricted" || status === "pending"
        ? "warn"
        : "critical";
  const changeSort = (field: AssetSortField) => {
    if (sortBy === field) {
      setSortDirection((direction) => direction === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortDirection("asc");
    }
    setOffset(0);
  };
  const sortHeader = (field: AssetSortField, label: string) => (
    <button type="button" className="asset-sort" onClick={() => changeSort(field)}>
      {label}
      {sortBy === field && (
        <ChevronDown
          className={sortDirection === "asc" ? "asset-sort__asc" : ""}
          size={14}
          aria-hidden="true"
        />
      )}
    </button>
  );

  return (
    <div className="workspace asset-workspace">
      <section className="asset-hero">
        <div>
          <span className="eyebrow">{t.assets.kicker}</span>
          <h1>{t.nav.assets}</h1>
          <p>{t.assets.subtitle}</p>
        </div>
        <div className="asset-hero__metrics" aria-live="polite">
          <span>
            <strong>{numberFormat.format(total)}</strong>
            <small>{t.assets.positions}</small>
          </span>
          <span>
            <strong>{numberFormat.format(page?.quantityTotal ?? 0)}</strong>
            <small>{t.assets.units}</small>
          </span>
          <span>
            <strong>
              {page?.ageSeconds === null || page?.ageSeconds === undefined
                ? "—"
                : formatDataAge(page.ageSeconds, locale)}
            </strong>
            <small>{t.assets.age}</small>
          </span>
        </div>
      </section>

      <section className="asset-browser" aria-busy={loading}>
        <div className="asset-toolbar">
          <label className="asset-search">
            <span>{t.assets.search}</span>
            <div>
              <Search size={16} aria-hidden="true" />
              <input
                value={search}
                maxLength={120}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t.assets.search}
                disabled={!available}
              />
            </div>
          </label>
          <label>
            <span>{t.assets.owner}</span>
            <select
              aria-label={t.assets.owner}
              value={ownerCharacterId ?? ""}
              onChange={(event) => {
                setOwnerCharacterId(event.target.value ? Number(event.target.value) : null);
                setOffset(0);
                setDeltaOffset(0);
              }}
              disabled={!available}
            >
              <option value="">{t.assets.allOwners}</option>
              {(page?.owners ?? []).map((owner) => (
                <option value={owner.characterId} key={owner.characterId}>{owner.name}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{t.assets.status}</span>
            <select
              aria-label={t.assets.status}
              value={locationStatus ?? ""}
              onChange={(event) => {
                setLocationStatus((event.target.value || null) as AssetLocationStatus | null);
                setOffset(0);
              }}
              disabled={!available}
            >
              <option value="">{t.assets.allStatuses}</option>
              {assetLocationStatuses.map((status) => (
                <option value={status} key={status}>{t.assets.statusLabels[status]}</option>
              ))}
            </select>
          </label>
          <button
            className="secondary-button asset-export"
            type="button"
            onClick={() => void refreshAssets()}
            disabled={!available || assetsSyncing}
          >
            <RefreshCw className={assetsSyncing ? "spin" : ""} size={15} />
            {assetsSyncing ? t.assets.syncing : t.assets.sync}
          </button>
          <button
            className="secondary-button asset-export"
            type="button"
            onClick={() => void createExport()}
            disabled={!available || exporting || loading}
          >
            {exporting ? <RefreshCw className="spin" size={15} /> : <Download size={15} />}
            {exporting ? t.assets.exporting : t.assets.export}
          </button>
        </div>

        {(syncResult || syncFailed) && (
          <div className={`asset-export-status ${syncFailed || (syncResult?.failed ?? 0) > 0 ? "asset-export-status--error" : ""}`} role="status">
            {syncFailed
              ? t.assets.syncError
              : syncResult?.characters.length === 0
                ? t.assets.syncEmpty
                : (syncResult?.failed ?? 0) > 0
                  ? t.assets.syncPartial
                      .replace("{completed}", numberFormat.format(syncResult?.completed ?? 0))
                      .replace("{failed}", numberFormat.format(syncResult?.failed ?? 0))
                  : t.assets.syncComplete
                      .replace("{assets}", numberFormat.format(syncResult?.assets ?? 0))
                      .replace("{characters}", numberFormat.format(syncResult?.completed ?? 0))}
          </div>
        )}

        {(exported || exportFailed) && (
          <div className={`asset-export-status ${exportFailed ? "asset-export-status--error" : ""}`} role="status">
            {exportFailed
              ? t.assets.exportError
              : t.assets.exported
                  .replace("{rows}", numberFormat.format(exported?.rows ?? 0))
                  .replace("{path}", exported?.relativePath ?? "")}
          </div>
        )}

        {!available ? (
          <div className="asset-empty"><Database size={22} />{t.assets.deltas.unavailable}</div>
        ) : failed ? (
          <div className="asset-empty asset-empty--error" role="alert">
            <AlertTriangle size={22} />{t.assets.queryError}
          </div>
        ) : loading && page === null ? (
          <div className="asset-empty"><RefreshCw className="spin" size={22} />{t.assets.loading}</div>
        ) : page && page.items.length === 0 ? (
          <div className="asset-empty">
            <PackageSearch size={22} />
            {page.observedAt === null ? t.assets.noData : t.assets.noMatches}
          </div>
        ) : page ? (
          <div className="asset-table-wrap">
            <table className="asset-table">
              <thead>
                <tr>
                  <th aria-sort={sortBy === "type" ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}>{sortHeader("type", t.assets.type)}</th>
                  <th aria-sort={sortBy === "owner" ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}>{sortHeader("owner", t.assets.owner)}</th>
                  <th aria-sort={sortBy === "location" ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}>{sortHeader("location", t.assets.location)}</th>
                  <th aria-sort={sortBy === "flag" ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}>{sortHeader("flag", t.assets.flag)}</th>
                  <th className="asset-table__number" aria-sort={sortBy === "quantity" ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}>{sortHeader("quantity", t.assets.quantity)}</th>
                  <th aria-sort={sortBy === "age" ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}>{sortHeader("age", t.assets.age)}</th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((item) => (
                  <tr key={item.itemId}>
                    <td>
                      <strong>{item.typeName}</strong>
                      <small>Type {item.typeId} · Item {item.itemId}</small>
                    </td>
                    <td><strong>{item.ownerName}</strong><small>EVE ID {item.ownerCharacterId}</small></td>
                    <td>
                      <span className={`asset-status asset-status--${statusTone(item.locationStatus)}`}>
                        <StatusDot tone={statusTone(item.locationStatus)} />
                        {t.assets.statusLabels[item.locationStatus]}
                      </span>
                      <small title={item.locationPath}>
                        {item.locationPath || t.assets.pendingLocation}
                      </small>
                    </td>
                    <td>{item.locationFlag}</td>
                    <td className="asset-table__number"><strong>{numberFormat.format(item.quantity)}</strong></td>
                    <td>{formatDataAge(item.ageSeconds, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {available && page && (
          <footer className="asset-pagination">
            <span>{resultRange}</span>
            <div>
              <button
                type="button"
                onClick={() => setOffset(Math.max(0, offset - assetPageSize))}
                disabled={loading || offset === 0}
              >
                <ChevronRight className="asset-pagination__previous" size={15} />
                {t.assets.previous}
              </button>
              <button
                type="button"
                onClick={() => setOffset(offset + assetPageSize)}
                disabled={loading || offset + assetPageSize >= total}
              >
                {t.assets.next}
                <ChevronRight size={15} />
              </button>
            </div>
          </footer>
        )}
      </section>

      <section className="asset-browser asset-deltas" aria-busy={deltasLoading}>
        <header className="asset-deltas__header">
          <div>
            <span className="eyebrow">{t.assets.deltas.kicker}</span>
            <h2>{t.assets.deltas.title}</h2>
            <p>{t.assets.deltas.subtitle}</p>
          </div>
          <label>
            <span>{t.assets.deltas.filter}</span>
            <select
              aria-label={t.assets.deltas.filter}
              value={deltaChangeType ?? ""}
              disabled={!available}
              onChange={(event) => {
                setDeltaChangeType(event.target.value === "" ? null : event.target.value as AssetDeltaChangeType);
                setDeltaOffset(0);
              }}
            >
              <option value="">{t.assets.deltas.all}</option>
              {assetDeltaChangeTypes.map((changeType) => (
                <option key={changeType} value={changeType}>{t.assets.deltas.labels[changeType]}</option>
              ))}
            </select>
          </label>
        </header>

        {deltaPage && (
          <div className="asset-deltas__summary" aria-live="polite">
            {assetDeltaChangeTypes.map((changeType) => (
              <span key={changeType}>
                <strong>{numberFormat.format(deltaPage.summary[changeType])}</strong>
                <small>{t.assets.deltas.labels[changeType]}</small>
              </span>
            ))}
          </div>
        )}

        {!available ? (
          <div className="asset-empty"><Database size={22} />{t.assets.unavailable}</div>
        ) : deltasFailed ? (
          <div className="asset-empty asset-empty--error" role="alert">
            <AlertTriangle size={22} />{t.assets.deltas.error}
          </div>
        ) : deltasLoading && deltaPage === null ? (
          <div className="asset-empty"><RefreshCw className="spin" size={22} />{t.assets.deltas.loading}</div>
        ) : deltaPage && deltaPage.items.length === 0 ? (
          <div className="asset-empty">
            <Clock3 size={22} />
            {deltaPage.hasBaseline ? t.assets.deltas.noChanges : t.assets.deltas.noBaseline}
          </div>
        ) : deltaPage ? (
          <div className="asset-table-wrap">
            <table className="asset-table asset-delta-table">
              <thead>
                <tr>
                  <th>{t.assets.type}</th>
                  <th>{t.assets.deltas.changes}</th>
                  <th>{t.assets.deltas.beforeAfter}</th>
                  <th>{t.assets.location}</th>
                  <th>{t.assets.deltas.interval}</th>
                  <th>{t.assets.deltas.source}</th>
                </tr>
              </thead>
              <tbody>
                {deltaPage.items.map((event) => (
                  <tr key={event.eventId}>
                    <td>
                      <strong>{event.typeName}</strong>
                      <small>{event.ownerName} · Item {event.itemId}</small>
                    </td>
                    <td>
                      <div className="asset-delta-table__badges">
                        {event.changeTypes.map((changeType) => (
                          <span key={changeType} className={`asset-delta-badge asset-delta-badge--${changeType}`}>
                            {t.assets.deltas.labels[changeType]}
                          </span>
                        ))}
                      </div>
                      <small className={event.quantityDelta > 0 ? "delta-positive" : event.quantityDelta < 0 ? "delta-negative" : ""}>
                        {event.quantityDelta > 0 ? "+" : ""}{numberFormat.format(event.quantityDelta)}
                      </small>
                    </td>
                    <td>
                      <strong>{event.quantityBefore === null ? "—" : numberFormat.format(event.quantityBefore)} → {event.quantityAfter === null ? "—" : numberFormat.format(event.quantityAfter)}</strong>
                    </td>
                    <td>
                      <strong>{event.locationFlagBefore ?? "—"} → {event.locationFlagAfter ?? "—"}</strong>
                      <small>{event.locationIdBefore ?? "—"} → {event.locationIdAfter ?? "—"}</small>
                    </td>
                    <td>
                      <strong>{formatDataAge(event.ageSeconds, locale)}</strong>
                      <small>{event.jobCorrelation.windowStart} → {event.jobCorrelation.windowEnd}</small>
                    </td>
                    <td>
                      <strong>{t.assets.deltas.correlationLabels[event.jobCorrelation.state]}</strong>
                      <small>{event.jobCorrelation.jobIds.length > 0 ? `Job ${event.jobCorrelation.jobIds.join(", ")} · ` : ""}Run {event.currentAssetSyncRunId}</small>
                      <small>{event.eventId.slice(0, 10)}</small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {available && deltaPage && (
          <footer className="asset-pagination">
            <span>{t.assets.resultRange
              .replace("{from}", numberFormat.format(deltaPage.total === 0 ? 0 : deltaOffset + 1))
              .replace("{to}", numberFormat.format(Math.min(deltaOffset + deltaPage.items.length, deltaPage.total)))
              .replace("{total}", numberFormat.format(deltaPage.total))}</span>
            <div>
              <button aria-label={`${t.assets.deltas.title}: ${t.assets.previous}`} type="button" onClick={() => setDeltaOffset(Math.max(0, deltaOffset - assetDeltaPageSize))} disabled={deltasLoading || deltaOffset === 0}>
                <ChevronRight className="asset-pagination__previous" size={15} />{t.assets.previous}
              </button>
              <button aria-label={`${t.assets.deltas.title}: ${t.assets.next}`} type="button" onClick={() => setDeltaOffset(deltaOffset + assetDeltaPageSize)} disabled={deltasLoading || deltaOffset + assetDeltaPageSize >= deltaPage.total}>
                {t.assets.next}<ChevronRight size={15} />
              </button>
            </div>
          </footer>
        )}
      </section>
    </div>
  );
}

function CharacterManager({
  characters,
  groups,
  unavailable,
  disabled,
  t,
  updateCharacter,
  deleteCharacter,
  createGroup,
  renameGroup,
  deleteGroup,
  onRefresh,
  onReauthorize,
}: {
  characters: EveCharacter[];
  groups: AccountGroup[];
  unavailable: boolean;
  disabled: boolean;
  t: Translation;
  updateCharacter: (characterId: number, update: CharacterUpdate) => Promise<EveCharacter>;
  deleteCharacter: (characterId: number) => Promise<void>;
  createGroup: (label: string) => Promise<AccountGroup>;
  renameGroup: (groupId: number, label: string) => Promise<AccountGroup>;
  deleteGroup: (groupId: number) => Promise<void>;
  onRefresh: () => Promise<void>;
  onReauthorize: () => Promise<void>;
}) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [alias, setAlias] = useState("");
  const [groupId, setGroupId] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [newGroup, setNewGroup] = useState("");
  const [groupLabels, setGroupLabels] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [deleteArmed, setDeleteArmed] = useState(false);
  const selected = characters.find((character) => character.characterId === selectedId) ?? null;

  const selectCharacter = (character: EveCharacter) => {
    setSelectedId(character.characterId);
    setAlias(character.alias ?? "");
    setGroupId(character.accountGroupId === null ? "" : String(character.accountGroupId));
    setEnabled(character.enabled);
    setDeleteArmed(false);
    setFailed(false);
  };

  const saveCharacter = async () => {
    if (!selected || busy) return;
    setBusy(true);
    setFailed(false);
    try {
      await updateCharacter(selected.characterId, {
        alias: alias.trim() || null,
        accountGroupId: groupId === "" ? null : Number(groupId),
        enabled,
      });
      await onRefresh();
      setDeleteArmed(false);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const removeCharacter = async () => {
    if (!selected || busy) return;
    if (!deleteArmed) {
      setDeleteArmed(true);
      return;
    }
    setBusy(true);
    setFailed(false);
    try {
      await deleteCharacter(selected.characterId);
      setSelectedId(null);
      setDeleteArmed(false);
      await onRefresh();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const addGroup = async () => {
    const label = newGroup.trim();
    if (!label || busy) return;
    setBusy(true);
    setFailed(false);
    try {
      await createGroup(label);
      setNewGroup("");
      await onRefresh();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const changeGroupLabel = async (group: AccountGroup) => {
    const label = (groupLabels[group.id] ?? group.label).trim();
    if (!label || label === group.label || busy) return;
    setBusy(true);
    setFailed(false);
    try {
      await renameGroup(group.id, label);
      setGroupLabels((current) => ({ ...current, [group.id]: label }));
      await onRefresh();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const removeGroup = async (group: AccountGroup) => {
    if (busy) return;
    setBusy(true);
    setFailed(false);
    try {
      await deleteGroup(group.id);
      if (groupId === String(group.id)) setGroupId("");
      await onRefresh();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="character-roster" aria-label={t.characters.title}>
      <div className="character-roster__heading">
        <div><UsersRound size={17} aria-hidden="true" /></div>
        <span>
          <strong>{t.characters.title}</strong>
          <small>{t.characters.count.replace("{count}", String(characters.length))}</small>
        </span>
      </div>
      <div className="character-roster__list" aria-live="polite">
        {unavailable ? (
          <span className="character-roster__empty character-roster__empty--error">
            {t.characters.unavailable}
          </span>
        ) : characters.length === 0 ? (
          <span className="character-roster__empty">{t.characters.empty}</span>
        ) : characters.map((character) => {
          const authorizationRequired = character.credentialState !== "stored" ||
            character.scopePackages.some((scopePackage) => scopePackage.status !== "granted");
          return (
          <article
            className={`character-chip ${character.enabled ? "" : "character-chip--inactive"} ${authorizationRequired ? "character-chip--authorization" : ""}`}
            key={character.characterId}
          >
            <span className="character-chip__avatar"><UserRound size={16} /></span>
            <span>
              <strong>{character.alias ?? character.name}</strong>
              <small>
                {character.alias ? `${character.name} · ` : ""}
                {character.accountGroupLabel ?? t.characters.ungrouped}
              </small>
            </span>
            <span className="character-chip__scopes">
              <ShieldCheck size={13} />
              {t.characters.scopes.replace("{count}", String(character.scopes.length))}
            </span>
            {!character.enabled && <small className="status-pill">{t.characters.inactive}</small>}
            {authorizationRequired && <small className="status-pill status-pill--warn">{t.characters.reauthorizationShort}</small>}
            <button
              type="button"
              className="character-chip__manage"
              onClick={() => selectCharacter(character)}
              disabled={disabled}
              aria-expanded={selectedId === character.characterId}
            >
              {t.characters.manage}
            </button>
          </article>
          );
        })}
      </div>

      {selected && (
        <div className="character-manager" data-testid="character-manager">
          <div className="character-manager__title">
            <span>
              <strong>{selected.alias ?? selected.name}</strong>
              <small>{selected.name} · EVE ID {selected.characterId}</small>
            </span>
            <button
              type="button"
              className="icon-button"
              onClick={() => setSelectedId(null)}
              aria-label={t.characters.close}
            >
              <X size={16} />
            </button>
          </div>

          <form
            className="character-manager__form"
            onSubmit={(event) => {
              event.preventDefault();
              void saveCharacter();
            }}
          >
            <label>
              <span>{t.characters.alias}</span>
              <input
                value={alias}
                maxLength={80}
                placeholder={t.characters.aliasPlaceholder}
                onChange={(event) => setAlias(event.target.value)}
                disabled={busy}
              />
            </label>
            <label>
              <span>{t.characters.group}</span>
              <select
                value={groupId}
                onChange={(event) => setGroupId(event.target.value)}
                disabled={busy}
              >
                <option value="">{t.characters.ungrouped}</option>
                {groups.map((group) => (
                  <option value={group.id} key={group.id}>{group.label}</option>
                ))}
              </select>
            </label>
            <label className="character-manager__toggle">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(event) => setEnabled(event.target.checked)}
                disabled={busy}
              />
              <span>{t.characters.active}</span>
            </label>
            <div className="character-manager__status">
              <span>
                {t.characters.credential}:{" "}
                <strong>{t.characters.credentialStates[selected.credentialState]}</strong>
              </span>
              <div>
                {selected.scopePackages.map((scopePackage) => (
                  <span
                    className={`scope-status scope-status--${scopePackage.status}`}
                    key={scopePackage.id}
                  >
                    {t.sso.packageLabels[scopePackage.id]} ·{" "}
                    {t.characters.scopeStates[scopePackage.status]}{" "}
                    {scopePackage.grantedCount}/{scopePackage.requiredCount}
                  </span>
                ))}
              </div>
            </div>
            {(selected.credentialState !== "stored" || selected.scopePackages.some((scopePackage) => scopePackage.status !== "granted")) && (
              <div className="character-manager__reauthorization" role="alert">
                <strong>{t.characters.reauthorizationTitle}</strong>
                <span>{t.characters.reauthorizationDetail}</span>
                <button type="button" className="sso-start" onClick={() => void onReauthorize()} disabled={busy || disabled}>
                  <LogIn size={15} />
                  {t.characters.reauthorize}
                </button>
              </div>
            )}
            {failed && <p className="character-manager__error" role="alert">{t.characters.error}</p>}
            <div className="character-manager__actions">
              <button type="submit" className="sso-start" disabled={busy}>
                <Check size={15} />
                {busy ? t.characters.saving : t.characters.save}
              </button>
              <button
                type="button"
                className={deleteArmed ? "danger-button danger-button--armed" : "danger-button"}
                onClick={() => void removeCharacter()}
                disabled={busy}
              >
                {deleteArmed ? t.characters.confirmDelete : t.characters.delete}
              </button>
              {deleteArmed && (
                <button
                  type="button"
                  className="sso-cancel"
                  onClick={() => setDeleteArmed(false)}
                  disabled={busy}
                >
                  {t.characters.cancelDelete}
                </button>
              )}
            </div>
            {deleteArmed && <small className="character-manager__delete-detail">{t.characters.deleteDetail}</small>}
          </form>

          <div className="account-groups">
            <strong>{t.characters.groupsTitle}</strong>
            <form
              className="account-groups__create"
              onSubmit={(event) => {
                event.preventDefault();
                void addGroup();
              }}
            >
              <input
                value={newGroup}
                maxLength={80}
                placeholder={t.characters.newGroup}
                aria-label={t.characters.newGroup}
                onChange={(event) => setNewGroup(event.target.value)}
                disabled={busy}
              />
              <button type="submit" className="sso-start" disabled={busy || !newGroup.trim()}>
                <Plus size={14} />
                {t.characters.createGroup}
              </button>
            </form>
            {groups.length === 0 ? (
              <small>{t.characters.noGroups}</small>
            ) : (
              <div className="account-groups__list">
                {groups.map((group) => (
                  <div className="account-group-row" key={group.id}>
                    <input
                      value={groupLabels[group.id] ?? group.label}
                      maxLength={80}
                      aria-label={`${t.characters.renameGroup}: ${group.label}`}
                      onChange={(event) => setGroupLabels((current) => ({
                        ...current,
                        [group.id]: event.target.value,
                      }))}
                      disabled={busy}
                    />
                    <small>{t.characters.members.replace("{count}", String(group.characterCount))}</small>
                    <button
                      type="button"
                      onClick={() => void changeGroupLabel(group)}
                      disabled={busy || (groupLabels[group.id] ?? group.label).trim() === group.label}
                    >
                      {t.characters.renameGroup}
                    </button>
                    <button
                      type="button"
                      className="danger-button"
                      onClick={() => void removeGroup(group)}
                      disabled={busy}
                    >
                      {t.characters.deleteGroup}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function Overview({
  locale,
  t,
  scope,
  onScopeChange,
  onOpenProduction,
  onInspect,
}: {
  locale: Locale;
  t: Translation;
  scope: OverviewScopeId;
  onScopeChange: (scope: OverviewScopeId) => void;
  onOpenProduction: () => void;
  onInspect: () => void;
}) {
  const selectedCharacter = scope === "all"
    ? undefined
    : demoCharacters.find((character) => character.id === scope);
  const selectedGroup = selectedCharacter
    ? accountGroups.find((group) =>
        (group.characterIds as readonly string[]).includes(selectedCharacter.id))
    : undefined;
  const selectedMetrics = overviewMetrics[scope];
  const readiness = Number(
    selectedMetrics.find((metric) => metric.id === "readiness")?.value ?? 0,
  );
  const dataAgeMinutes = selectedCharacter?.dataAgeMinutes
    ?? Math.max(...demoCharacters.map((character) => character.dataAgeMinutes));
  const readinessDelta = selectedCharacter?.readinessDelta ?? 6;
  const scopeDetail = selectedCharacter
    ? `${selectedGroup?.label ?? "—"} · ${t.scope.roles[selectedCharacter.role]}`
    : `${accountGroups.length} ${t.scope.accountGroups} · ${demoCharacters.length} ${t.scope.characters}`;
  const scopedProductionStages = productionStages
    .map((stage, sourceIndex) => ({ stage, sourceIndex }))
    .filter(({ stage }) => scope === "all" || stage.ownerId === scope);
  const scopedAttentionItems = attentionItems
    .map((item, sourceIndex) => ({ item, sourceIndex }))
    .filter(({ item }) => scope === "all" || item.ownerId === scope);
  const scopedActivity = activity
    .map((item, sourceIndex) => ({ item, sourceIndex }))
    .filter(({ item }) => scope === "all" || item.ownerId === scope);
  const characterName = (characterId: string) =>
    demoCharacters.find((character) => character.id === characterId)?.name ?? "—";

  return (
    <div className="workspace overview-workspace">
      <section className="scope-bar" aria-label={t.scope.label}>
        <div className="scope-bar__icon" aria-hidden="true">
          {scope === "all" ? <UsersRound size={19} /> : <UserRound size={19} />}
        </div>
        <div className="scope-bar__copy" aria-live="polite">
          <span>{t.scope.label}</span>
          <div>
            <strong>{selectedCharacter?.name ?? t.scope.combined}</strong>
            <small>{scope === "all" ? t.scope.combinedBadge : t.scope.characterBadge}</small>
          </div>
          <p>{scopeDetail}</p>
        </div>
        <div className="scope-bar__freshness">
          <StatusDot />
          <span>{t.scope.dataAge}: {dataAgeMinutes} Min.</span>
        </div>
        <label className="scope-picker">
          <span>{t.scope.select}</span>
          <div>
            <select
              value={scope}
              onChange={(event) => onScopeChange(event.target.value as OverviewScopeId)}
              aria-label={t.scope.label}
            >
              <option value="all">{t.scope.combined}</option>
              {accountGroups.map((group) => (
                <optgroup label={group.label} key={group.id}>
                  {group.characterIds.map((characterId) => {
                    const character = demoCharacters.find(({ id }) => id === characterId)!;
                    return <option value={character.id} key={character.id}>{character.name}</option>;
                  })}
                </optgroup>
              ))}
            </select>
            <ChevronDown size={15} aria-hidden="true" />
          </div>
        </label>
      </section>

      <section className="hero-panel">
        <div className="hero-grid" aria-hidden="true" />
        <div className="hero-copy">
          <div className="eyebrow"><Sparkles size={14} /> {t.dateLine}</div>
          <h1>{t.greeting}</h1>
          <p>{t.heroText}</p>
          <div className="hero-actions">
            <button className="primary-button" type="button" onClick={onOpenProduction}>
              {t.planAction}<ArrowUpRight size={17} />
            </button>
            <button className="secondary-button" type="button" onClick={onInspect}>
              {t.inspectAction}<ChevronRight size={16} />
            </button>
          </div>
        </div>
        <div className="readiness-block">
          <div
            className="readiness-ring"
            aria-label={`${t.readiness}: ${readiness}%`}
            style={{
              background: `conic-gradient(var(--teal) 0 ${readiness}%, #29332c ${readiness}% 100%)`,
            }}
          >
            <div>
              <strong>{readiness}</strong><span>%</span>
            </div>
          </div>
          <div className="readiness-copy">
            <strong>{t.readiness}</strong>
            <span>{t.readinessDetail}</span>
            <small>
              <TrendingUp size={13} /> +{readinessDelta} {locale === "de" ? "Punkte seit gestern" : "points since yesterday"}
            </small>
          </div>
        </div>
      </section>

      <section className="metric-grid" aria-label={locale === "de" ? "Kennzahlen" : "Metrics"}>
        {selectedMetrics.map((metric) => (
          <article className={`metric-card metric-card--${metric.trend}`} key={`${scope}-${metric.id}`}>
            <div className="metric-topline">
              <span>{t.metricLabels[metric.id]}</span>
              <button type="button" aria-label="Details"><MoreHorizontal size={17} /></button>
            </div>
            <div className="metric-body">
              <div>
                <strong className="metric-value">{metric.value}</strong>
                <span className="metric-unit">{metric.unit}</span>
              </div>
              <TrendLine id={`${scope}-${metric.id}`} points={metric.points} warning={metric.trend === "warn"} />
            </div>
            <div className="metric-footer">
              <span className="metric-delta">{metric.delta}</span>
              <span>{t.metricContext[metric.id]}</span>
            </div>
          </article>
        ))}
      </section>

      <div className="dashboard-grid">
        <section className="panel production-panel">
          <PanelHeader
            icon={Factory}
            title={t.operations}
            subtitle={t.operationsSubtitle}
            action={t.viewProduction}
            onAction={onOpenProduction}
          />
          <div className="production-table">
            <div className="production-table__head">
              <span>{locale === "de" ? "Vorhaben" : "Initiative"}</span>
              <span>{t.jobProgress}</span>
              <span>{t.due}</span>
            </div>
            {scopedProductionStages.map(({ stage, sourceIndex }) => (
              <div className="production-row" key={stage.name}>
                <div className="job-name">
                  <span className={`job-glyph job-glyph--${sourceIndex + 1}`}><Factory size={15} /></span>
                  <div>
                    <strong>{stage.name}</strong>
                    <small>
                      {locale === "de"
                        ? ["42 von 60 Einheiten", "Material reserviert", "Blueprint-Forschung"][sourceIndex]
                        : stage.detail}
                      {scope === "all" ? ` · ${characterName(stage.ownerId)}` : ""}
                    </small>
                  </div>
                </div>
                <div className="job-progress">
                  <div><span>{stage.progress}%</span><span>{stage.status === "research" ? (locale === "de" ? "Forschung" : "Research") : (locale === "de" ? "Aktiv" : "Active")}</span></div>
                  <div className="progress-track"><span style={{ width: `${stage.progress}%` }} /></div>
                </div>
                <span className="job-eta"><Clock3 size={14} /> {stage.eta}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="panel material-panel">
          <PanelHeader icon={Boxes} title={t.materialTitle} subtitle={t.materialSubtitle} />
          <div className="material-total">
            <span>{t.materialTotal}</span>
            <strong>{t.materialValue}</strong>
          </div>
          <div className="coverage-bar" aria-label={`${t.materialTitle}: 68%`}>
            {materialCoverage.map((part) => (
              <span key={part.name} className={`coverage-bar__${part.tone}`} style={{ width: `${part.value}%` }} />
            ))}
          </div>
          <div className="coverage-legend">
            {materialCoverage.map((part, index) => (
              <div key={part.name}>
                <span className={`legend-dot legend-dot--${part.tone}`} />
                <span>{t.coverageLegend[index]}</span>
                <strong>{part.value}%</strong>
              </div>
            ))}
          </div>
          <div className="recommendation-card">
            <div className="recommendation-icon"><Zap size={17} /></div>
            <div><small>{t.buildBuy}</small><strong>{t.buildBuyValue}</strong><span>{t.buildBuySaving}</span></div>
            <ChevronRight size={17} />
          </div>
        </section>

        <section className="panel attention-panel" id="attention-panel">
          <PanelHeader icon={AlertTriangle} title={t.attentionTitle} subtitle={t.attentionSubtitle} />
          <div className="attention-list">
            {scopedAttentionItems.map(({ item, sourceIndex }) => (
              <div className="attention-item" key={item.title}>
                <StatusDot tone={item.severity === "critical" ? "critical" : item.severity === "warning" ? "warn" : "good"} />
                <div>
                  <strong>{item.title}</strong>
                  <span>
                    {scope === "all" ? `${characterName(item.ownerId)} · ` : ""}
                    {t.attentionDetails[sourceIndex]}
                  </span>
                </div>
                <button type="button">{t.attentionActions[sourceIndex]}<ChevronRight size={14} /></button>
              </div>
            ))}
          </div>
        </section>

        <section className="panel activity-panel">
          <PanelHeader icon={Database} title={t.activityTitle} subtitle={t.activitySubtitle} />
          <div className="activity-list">
            {scopedActivity.map(({ item, sourceIndex }) => (
              <div className="activity-item" key={item.title}>
                <span className={`activity-icon activity-icon--${item.kind}`}>
                  {item.kind === "complete" ? <Check size={15} /> : item.kind === "market" ? <LineChart size={15} /> : <RefreshCw size={15} />}
                </span>
                <div>
                  <strong>{t.activityTitles[sourceIndex]}</strong>
                  <span>
                    {scope === "all" ? `${characterName(item.ownerId)} · ` : ""}
                    {t.activityDetails[sourceIndex]}
                  </span>
                </div>
                <time>{t.activityTimes[sourceIndex]}</time>
              </div>
            ))}
          </div>
          <div className="trust-row">
            <div><ShieldCheck size={16} /><span>{t.confidence}</span><strong>{t.confidenceValue}</strong></div>
            <div><CircleCheck size={16} /><span>{t.cache}</span></div>
            <div><Database size={16} /><span>{t.localOnly}</span></div>
          </div>
        </section>
      </div>
    </div>
  );
}

function PanelHeader({
  icon: Icon,
  title,
  subtitle,
  action,
  onAction,
}: {
  icon: LucideIcon;
  title: string;
  subtitle: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <header className="panel-header">
      <div className="panel-heading-icon"><Icon size={17} /></div>
      <div><h2>{title}</h2><p>{subtitle}</p></div>
      {action && <button type="button" onClick={onAction}>{action}<ArrowRight size={15} /></button>}
    </header>
  );
}

function BlueprintWorkspace({
  available, locale, t, loadBlueprints: loadPage, syncBlueprints: runSync, refreshRevision,
  loadIndustryJobs: loadJobs, syncIndustryJobs: runJobSync, industryJobRevision,
  loadCharacterSkills: loadSkills, syncCharacterSkills: runSkillSync, characterSkillRevision,
}: {
  available: boolean;
  locale: Locale;
  t: Translation;
  loadBlueprints: (query: BlueprintQuery) => Promise<BlueprintPage>;
  syncBlueprints: () => Promise<BlueprintSyncResult>;
  refreshRevision: number;
  loadIndustryJobs: (query: IndustryJobQuery) => Promise<IndustryJobPage>;
  syncIndustryJobs: () => Promise<IndustryJobSyncResult>;
  industryJobRevision: number;
  loadCharacterSkills: (query: CharacterSkillQuery) => Promise<CharacterSkillPage>;
  syncCharacterSkills: () => Promise<CharacterSkillSyncResult>;
  characterSkillRevision: number;
}) {
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [ownerCharacterId, setOwnerCharacterId] = useState<number | null>(null);
  const [kind, setKind] = useState<BlueprintKind | null>(null);
  const [sortBy, setSortBy] = useState<BlueprintSortField>("type");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<BlueprintPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [syncingBlueprints, setSyncingBlueprints] = useState(false);
  const [syncResult, setSyncResult] = useState<BlueprintSyncResult | null>(null);
  const [syncFailed, setSyncFailed] = useState(false);
  const numberFormat = useMemo(() => new Intl.NumberFormat(locale === "de" ? "de-DE" : "en-US"), [locale]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setAppliedSearch(search.trim().replace(/\s+/g, " "));
      setOffset(0);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (!available) return;
    let active = true;
    setLoading(true);
    setFailed(false);
    void loadPage({ search: appliedSearch, ownerCharacterId, kind, offset, limit: blueprintPageSize, sortBy, sortDirection })
      .then((result) => {
        if (!active) return;
        if (result.total > 0 && result.offset >= result.total) {
          setOffset(Math.floor((result.total - 1) / blueprintPageSize) * blueprintPageSize);
          return;
        }
        setPage(result);
      })
      .catch(() => { if (active) setFailed(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [appliedSearch, available, kind, loadPage, offset, ownerCharacterId, refreshRevision, sortBy, sortDirection]);

  const refresh = async () => {
    if (!available || syncingBlueprints) return;
    setSyncingBlueprints(true);
    setSyncFailed(false);
    setSyncResult(null);
    try {
      setSyncResult(await runSync());
      setOffset(0);
    } catch {
      setSyncFailed(true);
    } finally {
      setSyncingBlueprints(false);
    }
  };
  const changeSort = (field: BlueprintSortField) => {
    if (sortBy === field) setSortDirection((value) => value === "asc" ? "desc" : "asc");
    else { setSortBy(field); setSortDirection("asc"); }
    setOffset(0);
  };
  const header = (field: BlueprintSortField, label: string) => (
    <button type="button" className="asset-sort" onClick={() => changeSort(field)}>
      {label}{sortBy === field && <ChevronDown className={sortDirection === "asc" ? "asset-sort__asc" : ""} size={14} />}
    </button>
  );
  const total = page?.total ?? 0;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + (page?.items.length ?? 0), total);
  const range = t.blueprints.resultRange.replace("{from}", numberFormat.format(from))
    .replace("{to}", numberFormat.format(to)).replace("{total}", numberFormat.format(total));

  return (
    <div className="workspace asset-workspace blueprint-workspace">
      <section className="asset-hero">
        <div><span className="eyebrow">{t.blueprints.kicker}</span><h1>{t.nav.blueprints}</h1><p>{t.blueprints.subtitle}</p></div>
        <div className="asset-hero__metrics"><span><strong>{numberFormat.format(total)}</strong><small>{t.blueprints.count}</small></span><span><strong>{page?.ageSeconds == null ? "—" : formatDataAge(page.ageSeconds, locale)}</strong><small>{t.blueprints.age}</small></span></div>
      </section>
      <section className="asset-browser" aria-busy={loading}>
        <div className="asset-toolbar">
          <label className="asset-search"><span>{t.blueprints.search}</span><div><Search size={16} /><input value={search} maxLength={120} onChange={(event) => setSearch(event.target.value)} placeholder={t.blueprints.search} disabled={!available} /></div></label>
          <label><span>{t.blueprints.owner}</span><select value={ownerCharacterId ?? ""} onChange={(event) => { setOwnerCharacterId(event.target.value ? Number(event.target.value) : null); setOffset(0); }}><option value="">{t.blueprints.allOwners}</option>{(page?.owners ?? []).map((owner) => <option key={owner.characterId} value={owner.characterId}>{owner.name}</option>)}</select></label>
          <label><span>{t.blueprints.kind}</span><select value={kind ?? ""} onChange={(event) => { setKind((event.target.value || null) as BlueprintKind | null); setOffset(0); }}><option value="">{t.blueprints.allKinds}</option><option value="original">{t.blueprints.original}</option><option value="copy">{t.blueprints.copy}</option></select></label>
          <button className="secondary-button asset-export" type="button" onClick={() => void refresh()} disabled={!available || syncingBlueprints}><RefreshCw className={syncingBlueprints ? "spin" : ""} size={15} />{syncingBlueprints ? t.blueprints.syncing : t.blueprints.sync}</button>
        </div>
        {(syncResult || syncFailed) && <div className={`asset-export-status ${syncFailed || (syncResult?.failed ?? 0) > 0 ? "asset-export-status--error" : ""}`} role="status">{syncFailed ? t.blueprints.syncError : syncResult?.characters.length === 0 ? t.blueprints.syncEmpty : (syncResult?.failed ?? 0) > 0 ? t.blueprints.syncPartial.replace("{completed}", String(syncResult?.completed ?? 0)).replace("{failed}", String(syncResult?.failed ?? 0)) : t.blueprints.syncComplete.replace("{blueprints}", numberFormat.format(syncResult?.blueprints ?? 0)).replace("{characters}", String(syncResult?.completed ?? 0))}</div>}
        {!available ? <div className="asset-empty"><Database size={22} />{t.blueprints.unavailable}</div>
          : failed ? <div className="asset-empty asset-empty--error"><AlertTriangle size={22} />{t.blueprints.queryError}</div>
          : loading && page === null ? <div className="asset-empty"><RefreshCw className="spin" size={22} />{t.blueprints.loading}</div>
          : page && page.items.length === 0 ? <div className="asset-empty"><Boxes size={22} />{page.observedAt === null ? t.blueprints.noData : t.blueprints.noMatches}</div>
          : page ? <div className="asset-table-wrap"><table className="asset-table blueprint-table"><thead><tr>
              <th>{header("type", t.blueprints.type)}</th><th>{header("owner", t.blueprints.owner)}</th><th>{header("kind", t.blueprints.kind)}</th><th>{header("me", t.blueprints.me)}</th><th>{header("te", t.blueprints.te)}</th><th>{header("runs", t.blueprints.runs)}</th><th>{t.blueprints.location}</th><th>{header("age", t.blueprints.age)}</th>
            </tr></thead><tbody>{page.items.map((item) => <tr key={item.itemId}>
              <td><strong>{item.typeName}</strong><small>Type #{item.typeId}</small></td><td>{item.ownerName}</td><td><span className={`status-pill status-pill--${item.kind === "original" ? "good" : "info"}`}>{item.kind === "original" ? "BPO" : "BPC"}</span></td><td className="asset-table__number">{item.materialEfficiency}</td><td className="asset-table__number">{item.timeEfficiency}</td><td className="asset-table__number">{item.runs === -1 ? t.blueprints.unlimited : numberFormat.format(item.runs)}</td><td><strong>{item.locationFlag}</strong><small>#{item.locationId}</small></td><td>{formatDataAge(item.ageSeconds, locale)}</td>
            </tr>)}</tbody></table></div> : null}
        {page && total > 0 && <div className="asset-pagination"><span>{range}</span><div><button type="button" onClick={() => setOffset(Math.max(0, offset - blueprintPageSize))} disabled={offset === 0}>{t.blueprints.previous}</button><button type="button" onClick={() => setOffset(offset + blueprintPageSize)} disabled={offset + blueprintPageSize >= total}>{t.blueprints.next}</button></div></div>}
      </section>
      <IndustryJobsPanel
        available={available}
        locale={locale}
        t={t}
        loadJobs={loadJobs}
        syncJobs={runJobSync}
        refreshRevision={industryJobRevision}
      />
      <CharacterSkillsPanel
        available={available}
        locale={locale}
        t={t}
        loadSkills={loadSkills}
        syncSkills={runSkillSync}
        refreshRevision={characterSkillRevision}
      />
    </div>
  );
}

function IndustryJobsPanel({
  available, locale, t, loadJobs, syncJobs, refreshRevision,
}: {
  available: boolean;
  locale: Locale;
  t: Translation;
  loadJobs: (query: IndustryJobQuery) => Promise<IndustryJobPage>;
  syncJobs: () => Promise<IndustryJobSyncResult>;
  refreshRevision: number;
}) {
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [ownerCharacterId, setOwnerCharacterId] = useState<number | null>(null);
  const [status, setStatus] = useState<IndustryJobStatus | null>(null);
  const [activityId, setActivityId] = useState<IndustryActivityId | null>(null);
  const [correlation, setCorrelation] = useState<IndustryCorrelationState | null>(null);
  const [sortBy, setSortBy] = useState<IndustryJobSortField>("end");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<IndustryJobPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [syncingJobs, setSyncingJobs] = useState(false);
  const [syncResult, setSyncResult] = useState<IndustryJobSyncResult | null>(null);
  const [syncFailed, setSyncFailed] = useState(false);
  const numberFormat = useMemo(
    () => new Intl.NumberFormat(locale === "de" ? "de-DE" : "en-US"),
    [locale],
  );
  const iskFormat = useMemo(
    () => new Intl.NumberFormat(locale === "de" ? "de-DE" : "en-US", { maximumFractionDigits: 2 }),
    [locale],
  );
  const dateFormat = useMemo(
    () => new Intl.DateTimeFormat(locale === "de" ? "de-DE" : "en-US", {
      dateStyle: "short", timeStyle: "short",
    }),
    [locale],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setAppliedSearch(search.trim().replace(/\s+/g, " "));
      setOffset(0);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (!available) return;
    let active = true;
    setLoading(true);
    setFailed(false);
    void loadJobs({
      search: appliedSearch, ownerCharacterId, status, activityId, correlation,
      offset, limit: industryJobPageSize, sortBy, sortDirection,
    }).then((result) => {
      if (!active) return;
      if (result.total > 0 && result.offset >= result.total) {
        setOffset(Math.floor((result.total - 1) / industryJobPageSize) * industryJobPageSize);
        return;
      }
      setPage(result);
    }).catch(() => {
      if (active) setFailed(true);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [activityId, appliedSearch, available, correlation, loadJobs, offset, ownerCharacterId, refreshRevision, sortBy, sortDirection, status]);

  const refresh = async () => {
    if (!available || syncingJobs) return;
    setSyncingJobs(true);
    setSyncFailed(false);
    setSyncResult(null);
    try {
      setSyncResult(await syncJobs());
      setOffset(0);
    } catch {
      setSyncFailed(true);
    } finally {
      setSyncingJobs(false);
    }
  };
  const changeSort = (field: IndustryJobSortField) => {
    if (sortBy === field) setSortDirection((value) => value === "asc" ? "desc" : "asc");
    else { setSortBy(field); setSortDirection("asc"); }
    setOffset(0);
  };
  const header = (field: IndustryJobSortField, label: string) => (
    <button type="button" className="asset-sort" onClick={() => changeSort(field)}>
      {label}{sortBy === field && <ChevronDown className={sortDirection === "asc" ? "asset-sort__asc" : ""} size={14} />}
    </button>
  );
  const blueprintEvidence = (state: IndustryJobPage["items"][number]["blueprintCorrelation"]["state"]) => ({
    current: t.blueprints.jobs.currentBlueprint,
    historical: t.blueprints.jobs.historicalBlueprint,
    unmatched: t.blueprints.jobs.noBlueprint,
    unavailable: t.blueprints.jobs.noBlueprintData,
  })[state];
  const assetEvidence = (state: IndustryJobPage["items"][number]["assetCorrelation"]["state"]) => ({
    linked: t.blueprints.jobs.assetLinked,
    ambiguous: t.blueprints.jobs.assetAmbiguous,
    pending: t.blueprints.jobs.assetPending,
    unmatched: t.blueprints.jobs.assetUnmatched,
    unavailable: t.blueprints.jobs.assetUnavailable,
    "not-applicable": t.blueprints.jobs.assetNotApplicable,
  })[state];
  const total = page?.total ?? 0;
  const active = page?.activeTotal ?? 0;
  const range = t.blueprints.resultRange
    .replace("{from}", numberFormat.format(total === 0 ? 0 : offset + 1))
    .replace("{to}", numberFormat.format(Math.min(offset + (page?.items.length ?? 0), total)))
    .replace("{total}", numberFormat.format(total));

  return (
    <section className="asset-browser industry-jobs" aria-busy={loading}>
      <header className="asset-deltas__header industry-jobs__header">
        <div>
          <span className="eyebrow">{t.blueprints.jobs.kicker}</span>
          <h2>{t.blueprints.jobs.title}</h2>
          <p>{t.blueprints.jobs.subtitle}</p>
        </div>
        <div className="asset-hero__metrics">
          <span><strong>{numberFormat.format(total)}</strong><small>{t.blueprints.jobs.count}</small></span>
          <span><strong>{numberFormat.format(active)}</strong><small>{t.blueprints.jobs.activeCount}</small></span>
          <span><strong>{page?.ageSeconds == null ? "—" : formatDataAge(page.ageSeconds, locale)}</strong><small>{t.blueprints.jobs.age}</small></span>
        </div>
      </header>
      <div className="asset-toolbar industry-jobs__toolbar">
        <label className="asset-search"><span>{t.blueprints.jobs.search}</span><div><Search size={16} /><input value={search} maxLength={120} onChange={(event) => setSearch(event.target.value)} placeholder={t.blueprints.jobs.search} disabled={!available} /></div></label>
        <label><span>{t.blueprints.owner}</span><select value={ownerCharacterId ?? ""} onChange={(event) => { setOwnerCharacterId(event.target.value ? Number(event.target.value) : null); setOffset(0); }}><option value="">{t.blueprints.allOwners}</option>{(page?.owners ?? []).map((owner) => <option key={owner.characterId} value={owner.characterId}>{owner.name}</option>)}</select></label>
        <label><span>{t.blueprints.jobs.status}</span><select value={status ?? ""} onChange={(event) => { setStatus((event.target.value || null) as IndustryJobStatus | null); setOffset(0); }}><option value="">{t.blueprints.jobs.allStatuses}</option>{(page?.statuses ?? []).map((value) => <option key={value} value={value}>{t.blueprints.jobs.statusLabels[value]}</option>)}</select></label>
        <label><span>{t.blueprints.jobs.activity}</span><select value={activityId ?? ""} onChange={(event) => { setActivityId(event.target.value ? Number(event.target.value) as IndustryActivityId : null); setOffset(0); }}><option value="">{t.blueprints.jobs.allActivities}</option>{(page?.activities ?? []).map((value) => { const key = ({ 1: "manufacturing", 3: "research-time", 4: "research-material", 5: "copying", 7: "reverse-engineering", 8: "invention", 9: "reactions", 11: "reactions" } as const)[value]; return <option key={value} value={value}>{t.blueprints.jobs.activityLabels[key]}</option>; })}</select></label>
        <label><span>{t.blueprints.jobs.correlation}</span><select value={correlation ?? ""} onChange={(event) => { setCorrelation((event.target.value || null) as IndustryCorrelationState | null); setOffset(0); }}><option value="">{t.blueprints.jobs.allCorrelations}</option>{(page?.correlations ?? []).map((value) => <option key={value} value={value}>{t.blueprints.jobs.correlationLabels[value]}</option>)}</select></label>
        <button className="secondary-button asset-export" type="button" onClick={() => void refresh()} disabled={!available || syncingJobs}><RefreshCw className={syncingJobs ? "spin" : ""} size={15} />{syncingJobs ? t.blueprints.jobs.syncing : t.blueprints.jobs.sync}</button>
      </div>
      {(syncResult || syncFailed) && <div className={`asset-export-status ${syncFailed || (syncResult?.failed ?? 0) > 0 ? "asset-export-status--error" : ""}`} role="status">{syncFailed ? t.blueprints.jobs.syncError : syncResult?.characters.length === 0 ? t.blueprints.jobs.syncEmpty : (syncResult?.failed ?? 0) > 0 ? t.blueprints.jobs.syncPartial.replace("{completed}", String(syncResult?.completed ?? 0)).replace("{failed}", String(syncResult?.failed ?? 0)) : t.blueprints.jobs.syncComplete.replace("{jobs}", numberFormat.format(syncResult?.jobs ?? 0)).replace("{characters}", String(syncResult?.completed ?? 0))}</div>}
      {!available ? <div className="asset-empty"><Database size={22} />{t.blueprints.unavailable}</div>
        : failed ? <div className="asset-empty asset-empty--error"><AlertTriangle size={22} />{t.blueprints.jobs.queryError}</div>
        : loading && page === null ? <div className="asset-empty"><RefreshCw className="spin" size={22} />{t.blueprints.jobs.loading}</div>
        : page && page.items.length === 0 ? <div className="asset-empty"><Factory size={22} />{page.observedAt === null ? t.blueprints.jobs.noData : t.blueprints.jobs.noMatches}</div>
        : page ? <div className="asset-table-wrap"><table className="asset-table industry-job-table"><thead><tr>
            <th>{header("type", t.blueprints.jobs.blueprint)}</th><th>{t.blueprints.jobs.product}</th><th>{header("owner", t.blueprints.jobs.owner)}</th><th>{header("status", t.blueprints.jobs.status)}</th><th>{header("runs", t.blueprints.jobs.runs)}</th><th>{header("end", t.blueprints.jobs.timeline)}</th><th>{t.blueprints.jobs.location}</th><th>{header("correlation", t.blueprints.jobs.evidence)}</th>
          </tr></thead><tbody>{page.items.map((item) => <tr key={item.jobId}>
            <td><strong>{item.blueprintName}</strong><small>Job #{item.jobId} · Item #{item.blueprintItemId}</small></td>
            <td><strong>{item.productName ?? "—"}</strong>{item.productTypeId && <small>Type #{item.productTypeId}</small>}</td>
            <td><strong>{item.ownerName}</strong><small>{t.blueprints.jobs.activityLabels[item.activityKey]}</small></td>
            <td><span className={`status-pill status-pill--${item.status === "delivered" ? "good" : item.status === "cancelled" || item.status === "reverted" ? "warn" : "info"}`}>{t.blueprints.jobs.statusLabels[item.status]}</span></td>
            <td className="asset-table__number"><strong>{numberFormat.format(item.runs)}</strong><small>{item.successfulRuns == null ? "" : `${numberFormat.format(item.successfulRuns)} ${t.blueprints.jobs.successful}`}{item.cost == null ? "" : ` · ${iskFormat.format(item.cost)} ISK`}</small></td>
            <td><strong>{dateFormat.format(new Date(item.endDate))}</strong><small>{dateFormat.format(new Date(item.startDate))} → {item.completedDate ? dateFormat.format(new Date(item.completedDate)) : "—"}</small></td>
            <td><strong>#{item.facilityId}</strong><small>Output #{item.outputLocationId}</small></td>
            <td><span className={`status-pill status-pill--${item.correlationState === "linked" ? "good" : item.correlationState === "ambiguous" || item.correlationState === "partial" ? "warn" : "info"}`}>{t.blueprints.jobs.correlationLabels[item.correlationState]}</span><small>{blueprintEvidence(item.blueprintCorrelation.state)} · {assetEvidence(item.assetCorrelation.state)}</small><small>Run {item.jobSyncRunId}{item.assetCorrelation.eventIds[0] ? ` · ${item.assetCorrelation.eventIds[0].slice(0, 10)}` : ""}</small></td>
          </tr>)}</tbody></table></div> : null}
      {page && total > 0 && <div className="asset-pagination"><span>{range}</span><div><button type="button" onClick={() => setOffset(Math.max(0, offset - industryJobPageSize))} disabled={offset === 0}>{t.blueprints.previous}</button><button type="button" onClick={() => setOffset(offset + industryJobPageSize)} disabled={offset + industryJobPageSize >= total}>{t.blueprints.next}</button></div></div>}
    </section>
  );
}

function CharacterSkillsPanel({
  available, locale, t, loadSkills, syncSkills, refreshRevision,
}: {
  available: boolean;
  locale: Locale;
  t: Translation;
  loadSkills: (query: CharacterSkillQuery) => Promise<CharacterSkillPage>;
  syncSkills: () => Promise<CharacterSkillSyncResult>;
  refreshRevision: number;
}) {
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [ownerCharacterId, setOwnerCharacterId] = useState<number | null>(null);
  const [trainedLevel, setTrainedLevel] = useState<number | null>(null);
  const [activeState, setActiveState] = useState<CharacterSkillActiveState | null>(null);
  const [sortBy, setSortBy] = useState<CharacterSkillSortField>("skill");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<CharacterSkillPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [syncingSkills, setSyncingSkills] = useState(false);
  const [syncResult, setSyncResult] = useState<CharacterSkillSyncResult | null>(null);
  const [syncFailed, setSyncFailed] = useState(false);
  const numberFormat = useMemo(
    () => new Intl.NumberFormat(locale === "de" ? "de-DE" : "en-US"),
    [locale],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setAppliedSearch(search.trim().replace(/\s+/g, " "));
      setOffset(0);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (!available) return;
    let active = true;
    setLoading(true);
    setFailed(false);
    void loadSkills({
      search: appliedSearch,
      ownerCharacterId,
      trainedLevel,
      activeState,
      offset,
      limit: characterSkillPageSize,
      sortBy,
      sortDirection,
    }).then((result) => {
      if (!active) return;
      if (result.total > 0 && result.offset >= result.total) {
        setOffset(Math.floor((result.total - 1) / characterSkillPageSize) * characterSkillPageSize);
        return;
      }
      setPage(result);
    }).catch(() => {
      if (active) setFailed(true);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [activeState, appliedSearch, available, loadSkills, offset, ownerCharacterId, refreshRevision, sortBy, sortDirection, trainedLevel]);

  const refresh = async () => {
    if (!available || syncingSkills) return;
    setSyncingSkills(true);
    setSyncFailed(false);
    setSyncResult(null);
    try {
      setSyncResult(await syncSkills());
      setOffset(0);
    } catch {
      setSyncFailed(true);
    } finally {
      setSyncingSkills(false);
    }
  };
  const changeSort = (field: CharacterSkillSortField) => {
    if (sortBy === field) setSortDirection((value) => value === "asc" ? "desc" : "asc");
    else { setSortBy(field); setSortDirection("asc"); }
    setOffset(0);
  };
  const header = (field: CharacterSkillSortField, label: string) => (
    <button type="button" className="asset-sort" onClick={() => changeSort(field)}>
      {label}{sortBy === field && <ChevronDown className={sortDirection === "asc" ? "asset-sort__asc" : ""} size={14} />}
    </button>
  );
  const total = page?.total ?? 0;
  const range = t.blueprints.resultRange
    .replace("{from}", numberFormat.format(total === 0 ? 0 : offset + 1))
    .replace("{to}", numberFormat.format(Math.min(offset + (page?.items.length ?? 0), total)))
    .replace("{total}", numberFormat.format(total));

  return (
    <section className="asset-browser character-skills" aria-busy={loading}>
      <header className="asset-deltas__header industry-jobs__header">
        <div>
          <span className="eyebrow">{t.blueprints.skills.kicker}</span>
          <h2>{t.blueprints.skills.title}</h2>
          <p>{t.blueprints.skills.subtitle}</p>
        </div>
        <div className="asset-hero__metrics">
          <span><strong>{numberFormat.format(total)}</strong><small>{t.blueprints.skills.count}</small></span>
          <span><strong>{numberFormat.format(page?.totalSp ?? 0)}</strong><small>{t.blueprints.skills.totalSp}</small></span>
          <span><strong>{numberFormat.format(page?.unallocatedSp ?? 0)}</strong><small>{t.blueprints.skills.unallocatedSp}</small></span>
          <span><strong>{page?.ageSeconds == null ? "—" : formatDataAge(page.ageSeconds, locale)}</strong><small>{t.blueprints.skills.age}</small></span>
        </div>
      </header>
      <div className="asset-toolbar industry-jobs__toolbar">
        <label className="asset-search"><span>{t.blueprints.skills.search}</span><div><Search size={16} /><input value={search} maxLength={120} onChange={(event) => setSearch(event.target.value)} placeholder={t.blueprints.skills.search} disabled={!available} /></div></label>
        <label><span>{t.blueprints.owner}</span><select value={ownerCharacterId ?? ""} onChange={(event) => { setOwnerCharacterId(event.target.value ? Number(event.target.value) : null); setOffset(0); }}><option value="">{t.blueprints.allOwners}</option>{(page?.owners ?? []).map((owner) => <option key={owner.characterId} value={owner.characterId}>{owner.name}</option>)}</select></label>
        <label><span>{t.blueprints.skills.level}</span><select value={trainedLevel ?? ""} onChange={(event) => { setTrainedLevel(event.target.value ? Number(event.target.value) : null); setOffset(0); }}><option value="">{t.blueprints.skills.allLevels}</option>{(page?.levels ?? []).map((level) => <option key={level} value={level}>{level}</option>)}</select></label>
        <label><span>{t.blueprints.skills.activeState}</span><select value={activeState ?? ""} onChange={(event) => { setActiveState((event.target.value || null) as CharacterSkillActiveState | null); setOffset(0); }}><option value="">{t.blueprints.skills.allActiveStates}</option>{(page?.activeStates ?? []).map((state) => <option key={state} value={state}>{t.blueprints.skills.stateLabels[state]}</option>)}</select></label>
        <button className="secondary-button asset-export" type="button" onClick={() => void refresh()} disabled={!available || syncingSkills}><RefreshCw className={syncingSkills ? "spin" : ""} size={15} />{syncingSkills ? t.blueprints.skills.syncing : t.blueprints.skills.sync}</button>
      </div>
      {(syncResult || syncFailed) && <div className={`asset-export-status ${syncFailed || (syncResult?.failed ?? 0) > 0 ? "asset-export-status--error" : ""}`} role="status">{syncFailed ? t.blueprints.skills.syncError : syncResult?.characters.length === 0 ? t.blueprints.skills.syncEmpty : (syncResult?.failed ?? 0) > 0 ? t.blueprints.skills.syncPartial.replace("{completed}", String(syncResult?.completed ?? 0)).replace("{failed}", String(syncResult?.failed ?? 0)) : t.blueprints.skills.syncComplete.replace("{skills}", numberFormat.format(syncResult?.skills ?? 0)).replace("{characters}", String(syncResult?.completed ?? 0))}</div>}
      {!available ? <div className="asset-empty"><Database size={22} />{t.blueprints.unavailable}</div>
        : failed ? <div className="asset-empty asset-empty--error"><AlertTriangle size={22} />{t.blueprints.skills.queryError}</div>
        : loading && page === null ? <div className="asset-empty"><RefreshCw className="spin" size={22} />{t.blueprints.skills.loading}</div>
        : page && page.items.length === 0 ? <div className="asset-empty"><Sparkles size={22} />{page.observedAt === null ? t.blueprints.skills.noData : t.blueprints.skills.noMatches}</div>
        : page ? <div className="asset-table-wrap"><table className="asset-table character-skill-table"><thead><tr>
            <th>{header("skill", t.blueprints.skills.skill)}</th><th>{header("owner", t.blueprints.skills.owner)}</th><th>{header("trained", t.blueprints.skills.trained)}</th><th>{header("active", t.blueprints.skills.active)}</th><th>{header("skillpoints", t.blueprints.skills.skillpoints)}</th><th>{t.blueprints.skills.source}</th><th>{header("age", t.blueprints.skills.age)}</th>
          </tr></thead><tbody>{page.items.map((item) => <tr key={`${item.ownerCharacterId}:${item.skillId}`}>
            <td><strong>{item.skillName}</strong><small>Type #{item.skillId}</small></td>
            <td>{item.ownerName}</td>
            <td className="asset-table__number"><strong>{item.trainedLevel}</strong></td>
            <td><span className={`status-pill status-pill--${item.activeState === "normal" ? "good" : item.activeState === "limited" ? "warn" : "info"}`}>{item.activeLevel}</span><small>{t.blueprints.skills.stateLabels[item.activeState]}</small></td>
            <td className="asset-table__number">{numberFormat.format(item.skillpoints)}</td>
            <td><strong>Snapshot #{item.snapshotId}</strong><small>Run #{item.syncRunId}</small></td>
            <td>{formatDataAge(item.ageSeconds, locale)}</td>
          </tr>)}</tbody></table></div> : null}
      {page && total > 0 && <div className="asset-pagination"><span>{range}</span><div><button type="button" onClick={() => setOffset(Math.max(0, offset - characterSkillPageSize))} disabled={offset === 0}>{t.blueprints.previous}</button><button type="button" onClick={() => setOffset(offset + characterSkillPageSize)} disabled={offset + characterSkillPageSize >= total}>{t.blueprints.next}</button></div></div>}
    </section>
  );
}

function ModulePreview({ activeModule, t }: { activeModule: Exclude<ModuleId, "overview">; t: Translation }) {
  const module = modulePreview[activeModule];
  const { icon: Icon } = navigation.find(({ id }) => id === activeModule)!;

  return (
    <div className="workspace module-workspace">
      <section className="module-hero">
        <div className="module-hero__icon"><Icon size={28} /></div>
        <div>
          <span className="eyebrow">{t.moduleKicker}</span>
          <h1>{t.nav[activeModule]}</h1>
          <p>{t.moduleText}</p>
        </div>
        <div className="module-hero__metric">
          <strong>{module.metric}</strong>
          <span>{t.moduleSecondary[activeModule]}</span>
        </div>
      </section>

      <section className="module-preview-grid">
        {t.moduleCards[activeModule].map((card, index) => (
          <article className="module-card" key={card}>
            <div className="module-card__top"><span>0{index + 1}</span><span className="planned-badge">{t.planned}</span></div>
            <div className={`module-card__visual module-card__visual--${index + 1}`}>
              <span /><span /><span /><span />
            </div>
            <h2>{card}</h2>
            <p>{t.previewOnly}</p>
          </article>
        ))}
      </section>

      <div className="module-note"><FlaskConical size={16} /> {t.synthetic}</div>
    </div>
  );
}
