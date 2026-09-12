Warning: truncated output (original token count: 63139)
Total output lines: 5125

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
  checkForUpdates,
  createAccountGroup,
  deleteAccountGroup,
  deleteEveCharacter,
  deleteResearchPlan,
  deleteProductionPlan,
  fontScales,
  industryFacilityPageSize,
  initialRuntimeStatus,
  exportAssetsCsv,
  loadAccountGroups,
  loadEveCharacters,
  loadEveSsoStatus,
  loadDesktopRuntimeStatus,
  loadAssets,
  loadAssetSummary,
  loadAssetDeltas,
  loadBlueprints,
  loadCharacterSkills,
  loadIndustryFacilities,
  loadIndustryJobs,
  loadIndustrySlots,
  loadProductionCatalog,
  loadProductionPlans,
  loadResearchPlans,
  syncAssets,
  syncBlueprints,
  syncCharacterSkills,
  syncIndustryFacilities,
  syncIndustryJobs,
  renameAccountGroup,
  openReleaseDownloads,
  saveProductionPlan,
  saveResearchPlan,
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
  type AssetSummaryPage,
  type AssetSummaryQuery,
  type AssetSummarySortField,
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
  type IndustryCostActivity,
  type IndustryFacilityAccess,
  type IndustryFacilityKind,
  type IndustryFacilityPage,
  type IndustryFacilityQuery,
  type IndustryFacilitySortField,
  type IndustryFacilitySyncResult,
  type IndustrySecurityClass,
  type IndustryJobPage,
  type IndustryJobQuery,
  type IndustryJobSortField,
  type IndustryJobStatus,
  type IndustryJobSyncResult,
  type IndustrySlotActivityKey,
  type IndustrySlotPage,
  type IndustrySlotQuery,
  type ResearchPlanInput,
  type ResearchPlanPage,
  type ResearchPlanQuery,
  type ResearchPlanSortField,
  type ResearchPlanState,
  type ProductionActivity,
  type ProductionCatalogItem,
  type ProductionCatalogPage,
  type ProductionCatalogQuery,
  type ProductionPlanInput,
  type ProductionPlanPage,
  type ProductionPlanQuery,
  type ProductionPlanSortField,
  type ProductionPlanState,
  type PublicReleaseNotice,
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
  industrySlotPageSize,
  productionCatalogPageSize,
  productionPlanPageSize,
  researchPlanPageSize,
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
      migration: "Datenübernahme aus der vorherigen Version konnte nicht abgeschlossen werden",
      database: "Datenbank konnte nicht sicher geöffnet werden",
      sidecar: "Lokaler Dienst wurde unerwartet beendet",
      sidecarMissing: "Lokaler Dienst fehlt im Programmordner",
      sidecarBlocked: "Windows konnte den lokalen Dienst nicht starten",
      loopback: "Lokale Verbindung zu 127.0.0.1 konnte nicht geöffnet werden",
      fallback: "Sidecar oder Programmordner nicht verfügbar",
    },
    runtimeErrorCodeLabel: "Fehlercode",
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
      checkingRelease: "GitHub-Releases werden geprüft …",
      releaseAvailable: "Version {version} ist verfügbar",
      releaseCurrent: "Diese Version ist aktuell",
      releaseUnavailable: "Für diesen Kanal wurde kein vollständiges Release gefunden",
      releaseError: "Release-Prüfung derzeit nicht möglich",
      checkNow: "Jetzt prüfen",
      openRelease: "Release öffnen",
      portableHint: "Portable: Die ZIP vollständig an einen beliebigen beschreibbaren Ort entpacken – Desktop, USB-Stick oder eigener Ordner. Keine Installation und kein Installationsordner nötig. Für Updates den vorhandenen Ordner data sichern und übernehmen.",
      installedHint: "Installer: App schließen und die neue Setup-Datei starten. Den Haken zum Löschen der Anwendungsdaten nicht setzen. Datenbank und Sicherungen liegen sichtbar im Unterordner data des Installationsordners.",
      signedBoundary: "Automatische Installation bleibt bis zur produktiv signierten Updatekette gesperrt.",
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
      subtitle: "Bestände nach Gegenstand zusammenfassen oder bis zur einzelnen Position und ihrem Standort auflösen.",
      view: "Darstellung",
      summaryView: "Bestandsübersicht",
      positionsView: "Einzelpositionen",
      itemTypes: "Gegenstände",
      ownersCount: "Besitzer",
      locationsCount: "Standorte",
      showPositions: "Einzelpositionen anzeigen",
      distribution: "Verteilung",
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
      syncPartial: "{completed} vollständig, {partial} mit Teilfehler, {failed} fehlgeschlagen.",
      syncDetail: "{character}: {reason}",
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
      subtitle: "Persönliche BPOs und BPCs aller aktiven Charaktere mit ME, TE und verbleibenden Läufen. Corporation-Blueprints sind nicht enthalten.",
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
      syncDetail: "{character}: {reason}",
      syncEmpty: "Kein aktivierter Charakter für den Blueprint-Sync vorhanden.",
      syncError: "Blueprint-Sync konnte nicht gestartet werden.",
      loading: "Blueprint-Bestand wird geladen …",
      unavailable: "Die echte Blueprint-Ansicht ist in der Windows-App verfügbar.",
      noData: "Noch kein persönlicher Blueprint-Snapshot vorhanden. Jetzt aktualisieren; bei einem Berechtigungsfehler den Charakter neu anmelden.",
      noMatches: "Keine Blueprints entsprechen der Auswahl.",
      queryError: "Der lokale Blueprint-Bestand konnte nicht gelesen werden.",
      resultRange: "{from}–{to} von {total}",
      previous: "Vorherige Seite",
      next: "Nächste Seite",
      liveNotice: "Echte lokale Blueprint-Snapshots · automatisch beim Programmstart",
      snapshotTitle: "Snapshot-Status",
      snapshotAvailable: "{count} Blueprints · {age}",
      snapshotMissing: "Kein Snapshot – jetzt aktualisieren; bei Berechtigungsfehler neu anmelden",
      jobs: {
        kicker: "PERSÖNLICHE INDUSTRIEAUFTRÄGE",
        title: "Industrieaufträge",
        subtitle: "Aktive und abgeschlossene ESI-Aufträge mit belegbarer Blueprint- und Asset-Zuordnung.",
        search: "Job, Blueprint, Produkt, Besitzer oder ID suchen",
        status: "Status",
        allStatuses: "Alle Status",
        statusLabels: {
          active: "Läuft", cancelled: "Abgebrochen", delivered: "Abgeholt",
          paused: "Pausiert", ready: "Abholbereit", reverted: "Zurückgesetzt",
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
        activeCount: "offene Jobs",
        count: "Jobs",
        age: "Datenalter",
        sync: "Jobs aktualisieren",
        syncing: "Jobs werden aktualisiert …",
        syncComplete: "{jobs} Jobs von {characters} Charakter(en) aktualisiert.",
        syncPartial: "{completed} aktualisiert, {failed} fehlgeschlagen. Anmeldung oder Verbindung prüfen.",
        syncDetail: "{character}: {reason}",
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
      facilities: {
        kicker: "ANLAGEN & SYSTEMKOSTEN",
        title: "Industrieanlagen",
        subtitle: "Offizieller ESI-Anlagenkatalog mit Systemkostenindizes und den aus persönlichen Jobs beobachteten Spielerstrukturen.",
        boundary: "ESI liefert keine Struktur- oder Rigboni; unbekannte Werte werden nicht geschätzt.",
        search: "Anlage, System, Region, Besitzer, Typ oder ID suchen",
        kind: "Anlagenart",
        allKinds: "Alle Anlagenarten",
        kindLabels: { station: "NPC-Station", structure: "Spielerstruktur", unknown: "Unbekannt" },
        access: "Zugriff",
        allAccess: "Alle Zugriffszustände",
        accessLabels: {
          public: "Öffentlich", available: "Verfügbar", restricted: "ACL eingeschränkt",
          "scope-missing": "Neuanmeldung nötig", unknown: "Unbekannt",
        },
        security: "Sicherheitsraum",
        allSecurity: "Alle Sicherheitsräume",
        securityLabels: {
          highsec: "Highsec", lowsec: "Lowsec", nullsec: "Nullsec", unknown: "Unbekannt",
        },
        activity: "Kostenaktivität",
        activityLabels: {
          manufacturing: "Produktion", reaction: "Reaktion", copying: "Kopieren",
          invention: "Erfindung", researching_material_efficiency: "Materialforschung",
          researching_time_efficiency: "Zeitforschung",
        },
        usedOnly: "Nur in Jobs verwendet",
        facility: "Anlage / Typ",
        system: "System / Region",
        owner: "Besitzer",
        cost: "Systemkostenindex",
        jobs: "Beobachtete Jobs",
        source: "Quellnachweis",
        count: "Anlagen",
        systems: "Systeme",
        restricted: "eingeschränkt",
        active: "aktiv",
        noJobs: "noch nicht in Jobs beobachtet",
        taxUnknown: "Anlagensteuer unbekannt",
        age: "Datenalter",
        sync: "Anlagen aktualisieren",
        syncing: "Anlagen werden aktualisiert …",
        syncComplete: "{facilities} Anlagen und {systems} Systemkostenstände aktualisiert.",
        syncError: "Anlagen-Sync konnte nicht abgeschlossen werden.",
        loading: "Industrieanlagen werden geladen …",
        noData: "Noch kein vollständiger Anlagen-Snapshot vorhanden.",
        noMatches: "Keine Anlagen entsprechen der Auswahl.",
        queryError: "Der lokale Anlagenkatalog konnte nicht gelesen werden.",
      },
      slots: {
        kicker: "INDUSTRIE-SLOTS",
        title: "Kapazität und Arbeitsvorrat",
        subtitle: "Fertigung, Reaktionen und Wissenschaft je Charakter mit echter Skill-Kapazität und aktueller Jobbelegung.",
        boundary: "Fehlt ein vollständiger Skill- oder Job-Snapshot, bleibt der betroffene Wert unbekannt. Produktionsziele liefern jetzt den belegbaren Fertigungs- und Reaktionsvorrat.",
        owner: "Charakter",
        allOwners: "Alle Charaktere",
        characters: "Charaktere",
        occupied: "belegte Slots",
        ready: "fertige Jobs",
        researchQueue: "Forschungspläne offen",
        activityLabels: {
          manufacturing: "Fertigung", reactions: "Reaktionen", science: "Wissenschaft",
        },
        stateLabels: {
          unknown: "Daten fehlen", available: "Slots frei", full: "Voll belegt",
          overbooked: "Über Kapazität",
        },
        slotValue: "{available} frei · {occupied}/{capacity} belegt",
        slotUnknown: "Kapazität oder Belegung unbekannt",
        jobs: "{active} aktiv · {ready} fertig · {paused} pausiert",
        noJobSnapshot: "Job-Snapshot fehlt",
        skillValue: "{primary} {primaryLevel} · {advanced} {advancedLevel}",
        noSkillSnapshot: "Skill-Snapshot fehlt",
        skillLabels: {
          massProduction: "Mass Production",
          advancedMassProduction: "Advanced Mass Production",
          massReactions: "Mass Reactions",
          advancedMassReactions: "Advanced Mass Reactions",
          laboratoryOperation: "Laboratory Operation",
          advancedLaboratoryOperation: "Advanced Laboratory Operation",
        },
        nextEnd: "Nächstes Ende {date}",
        noActiveJob: "Kein aktiver Job",
        plans: "{queued} geplant · {running} laufend · {blocked} blockiert · {complete} fertig",
        planningPending: "Noch kein Fertigungs-Arbeitsvorrat",
        source: "Skills #{skills} / Lauf #{skillRun} · Jobs #{jobs} / Lauf #{jobRun}",
        sourceMissing: "Quellen noch unvollständig",
        age: "Datenalter",
        loading: "Industrie-Slots werden geladen …",
        noData: "Noch keine verbundenen Charaktere vorhanden.",
        noMatches: "Kein Charakter entspricht der Auswahl.",
        queryError: "Die lokale Industrie-Slotübersicht konnte nicht gelesen werden.",
        resultRange: "{from}–{to} von {total}",
      },
      research: {
        kicker: "FORSCHUNGSPLANUNG",
        title: "ME-/TE-Forschungsplan",
        subtitle: "Updatefeste Ziele für eigene BPOs mit echten Skill-Slots, laufenden Jobs und beobachteten Anlagen.",
        boundary: "Der Plan ist ausschließlich eine lokale Arbeitsliste und sendet oder startet nichts in EVE. Zeiten und Gesamtkosten werden vor dem Einbau nicht geschätzt; laufende EVE-Jobs werden nur abgeglichen.",
        search: "Blueprint, Besitzer, Notiz, Anlage oder ID suchen",
        state: "Planstatus",
        allStates: "Alle Status",
        stateLabels: {
          unplanned: "Nicht geplant", ready: "Bereit", queued: "Wartet auf Slot",
          running: "Läuft", complete: "Ziel erreicht", unverified: "Skills fehlen",
          missing: "BPO nicht im Bestand",
        },
        plannedOnly: "Nur gespeicherte Pläne",
        blueprint: "Blueprint / Besitzer",
        status: "Status / Bestand",
        plan: "Nächster Schritt / Ziele",
        activityLabels: { material: "Materialforschung", time: "Zeitforschung" },
        targetMe: "Ziel-ME",
        targetTe: "Ziel-TE",
        priority: "Priorität",
        note: "Notiz",
        notePlaceholder: "Optionaler Planungshinweis",
        slots: "Forschungsslots / Skills",
        slotsUnknown: "Skill-Snapshot fehlt",
        slotsValue: "{available} frei · {used}/{capacity} belegt",
        skillValue: "Research {research} · Metallurgy {metallurgy}",
        evidence: "Job / Anlage",
        noActiveJob: "Kein laufender Forschungsjob",
        activeJob: "Job #{job} · {activity}",
        ends: "Ende {date}",
        lastFacility: "zuletzt dort genutzt",
        currentFacility: "laufender Job",
        noFacility: "Noch keine Anlage belegt",
        systemCost: "Systemkostenindex {value}",
        source: "Quellen",
        save: "Plan speichern",
        update: "Aktualisieren",
        remove: "Entfernen",
        saving: "Wird gespeichert …",
        saved: "Forschungsplan gespeichert.",
        deleted: "Forschungsplan entfernt.",
        mutationError: "Der Forschungsplan konnte nicht geändert werden.",
        plans: "gespeicherte Pläne",
        ready: "bereit",
        running: "laufend",
        freeSlots: "freie Slots",
        age: "Datenalter",
        loading: "Forschungsplanung wird geladen …",
        noData: "Noch kein persönlicher Blueprint-Snapshot vorhanden. Aktualisiere oben zuerst die Blueprints; nur eigene BPOs können als Forschungsziel erscheinen.",
        noMatches: "Keine Forschungszeilen entsprechen der Auswahl.",
        queryError: "Die lokale Forschungsplanung konnte nicht gelesen werden.",
        resultRange: "{from}–{to} von {total}",
      },
    },
    productionPlanning: {
      kicker: "PRODUKTIONSPLANUNG",
      title: "Fertigungs- und Reaktionsziele",
      subtitle: "Persistente Ziele werden aus der aktiven Blueprintbasis reproduzierbar in Schritte und Bruttomaterial aufgelöst.",
      boundary: "Bruttobedarf ohne Bestandsabzug, Reservierungen, Blueprint-ME, Skills, Anlagen-/Rigboni, Steuern oder Preise. Angezeigt werden unveränderte SDE-Basiswerte.",
      build: "SDE-Build {build}",
      searchRecipe: "Produkt oder Blueprint suchen",
      activity: "Aktivität",
      allActivities: "Fertigung & Reaktion",
      activityLabels: { manufacturing: "Fertigung", reaction: "Reaktion" },
      catalog: "Produkt auswählen",
      allOwners: "Alle Charaktere",
      output: "{quantity} je Lauf · {materials} Materialarten",
      select: "Auswählen",
      selected: "Ausgewählt",
      owner: "Ausführender Charakter",
      target: "Zielmenge",
      priority: "Priorität",
      note: "Notiz",
      notePlaceholder: "Optionaler Planungshinweis",
      create: "Ziel speichern",
      save: "Änderungen speichern",
      remove: "Ziel entfernen",
      saving: "Wird gespeichert …",
      saved: "Produktionsziel gespeichert.",
      deleted: "Produktionsziel entfernt.",
      mutationError: "Das Produktionsziel konnte nicht geändert werden.",
      plans: "Produktionsziele",
      searchPlans: "Produkt, Blueprint, Besitzer oder Notiz suchen",
      state: "Planstatus",
      allStates: "Alle Status",
      stateLabels: {
        ready: "Bereit", "sde-unavailable": "SDE fehlt", "recipe-missing": "Rezept fehlt",
        cycle: "Zyklus erkannt", "complexity-limit": "Kette zu groß",
      },
      sort: "Sortierung",
      sortLabels: {
        priority: "Priorität", product: "Produkt", owner: "Charakter",
        activity: "Aktivität", state: "Status", updated: "Zuletzt geändert",
      },
      quantity: "Zielmenge",
      goalQuantity: "Ziel: {quantity}",
      steps: "Herstellungsreihenfolge",
      sequenceHint: "Vorprodukte werden zuerst hergestellt; das gewählte Zielprodukt steht bewusst am Ende.",
      step: "Schritt {sequence}",
      intermediateStep: "Vorprodukt",
      goalStep: "Zielprodukt",
      runs: "{runs} Läufe · {produced} produziert · {surplus} Überschuss",
      baseTime: "SDE-Basiszeit {time}",
      gross: "Bruttomaterialbedarf",
      noGross: "Kein äußerer Materialbedarf",
      alternatives: "Für {type} existieren {count} Rezepte; deterministisch wurde Blueprint #{blueprint} gewählt.",
      loading: "Produktionsplanung wird geladen …",
      catalogLoading: "Produktkatalog wird geladen …",
      noSde: "Noch keine vollständige Blueprint-Aktivitätsbasis importiert. Bis dahin können keine neuen Ziele angelegt werden.",
      noOwners: "Verbinde und aktiviere zuerst mindestens einen Charakter.",
      noRecipes: "Keine Produkte entsprechen der Suche.",
      noPlans: "Noch kein Produktionsziel gespeichert.",
      noMatches: "Keine Produktionsziele entsprechen der Auswahl.",
      queryError: "Die lokale Produktionsplanung konnte nicht gelesen werden.",
      resultRange: "{from}–{to} von {total}",
      previous: "Vorherige Seite",
      next: "Nächste Seite",
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
    footerVersion: "v0.0.5-preview.21",
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
      migration: "Data migration from the previous version could not be completed",
      database: "Database could not be opened safely",
      sidecar: "Local service stopped unexpectedly",
      sidecarMissing: "Local service is missing from the program folder",
      sidecarBlocked: "Windows could not start the local service",
      loopback: "The local 127.0.0.1 connection could not be opened",
      fallback: "Sidecar or program folder is unavailable",
    },
    runtimeErrorCodeLabel: "Error code",
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
      checkingRelease: "Checking GitHub releases …",
      releaseAvailable: "Version {version} is available",
      releaseCurrent: "This version is current",
      releaseUnavailable: "No complete release was found for this channel",
      releaseError: "Release check is currently unavailable",
      checkNow: "Check now",
      openRelease: "Open release",
      portableHint: "Portable: fully extract the ZIP to any writable location – desktop, USB drive, or another folder. No installation or installer directory is required. For updates, back up and retain the existing data folder.",
      installedHint: "Installer: close the app and run the new setup. Do not select the checkbox that deletes application data. The database and backups are visible in the data subfolder of the installation directory.",
      signedBoundary: "Automatic installation remains blocked until the production-signed update chain is available.",
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
      subtitle: "Group stock by item or drill down to each individual position and its location.",
      view: "View",
      summaryView: "Stock overview",
      positionsView: "Individual positions",
      itemTypes: "items",
      ownersCount: "Owners",
      locationsCount: "Locations",
      showPositions: "Show individual positions",
      distribution: "Distribution",
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
      syncPartial: "{completed} complete, {partial} partial, {failed} failed.",
      syncDetail: "{character}: {reason}",
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
      subtitle: "Personal BPOs and BPCs for all active characters, including ME, TE, and remaining runs. Corporation blueprints are not included.",
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
      syncDetail: "{character}: {reason}",
      syncEmpty: "No enabled character is available for blueprint sync.",
      syncError: "Blueprint sync could not be started.",
      loading: "Loading blueprint inventory …",
      unavailable: "The live blueprint view is available in the Windows app.",
      noData: "No personal blueprint snapshot is available yet. Refresh now; sign in the character again if permission fails.",
      noMatches: "No blueprints match the selection.",
      queryError: "The local blueprint inventory could not be read.",
      resultRange: "{from}–{to} of {total}",
      previous: "Previous page",
      next: "Next page",
      liveNotice: "Live local blueprint snapshots · automatic at application startup",
      snapshotTitle: "Snapshot status",
      snapshotAvailable: "{count} blueprints · {age}",
      snapshotMissing: "No snapshot – refresh now; sign in again if permission fails",
      jobs: {
        kicker: "PERSONAL INDUSTRY JOBS",
        title: "Industry jobs",
        subtitle: "Active and completed ESI jobs with traceable blueprint and asset correlation.",
        search: "Search job, blueprint, product, owner, or ID",
        status: "Status",
        allStatuses: "All statuses",
        statusLabels: {
          active: "Running", cancelled: "Cancelled", delivered: "Delivered",
          paused: "Paused", ready: "Ready for delivery", reverted: "Reverted",
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
        activeCount: "open jobs",
        count: "jobs",
        age: "Data age",
        sync: "Refresh jobs",
        syncing: "Refreshing jobs …",
        syncComplete: "Updated {jobs} jobs from {characters} character(s).",
        syncPartial: "{completed} updated, {failed} failed. Check sign-in or connection.",
        syncDetail: "{character}: {reason}",
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
      facilities: {
        kicker: "FACILITIES & SYSTEM COSTS",
        title: "Industry facilities",
        subtitle: "Official ESI facility catalog with system cost indices and player structure…33139 tokens truncated…ationState === "ambiguous" || item.correlationState === "partial" ? "warn" : "info"}`}>{t.blueprints.jobs.correlationLabels[item.correlationState]}</span><small>{blueprintEvidence(item.blueprintCorrelation.state)} · {assetEvidence(item.assetCorrelation.state)}</small><small>Run {item.jobSyncRunId}{item.assetCorrelation.eventIds[0] ? ` · ${item.assetCorrelation.eventIds[0].slice(0, 10)}` : ""}</small></td>
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

function IndustryFacilitiesPanel({
  available, locale, t, loadFacilities, syncFacilities, refreshRevision,
}: {
  available: boolean;
  locale: Locale;
  t: Translation;
  loadFacilities: (query: IndustryFacilityQuery) => Promise<IndustryFacilityPage>;
  syncFacilities: () => Promise<IndustryFacilitySyncResult>;
  refreshRevision: number;
}) {
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [kind, setKind] = useState<IndustryFacilityKind | null>(null);
  const [access, setAccess] = useState<IndustryFacilityAccess | null>(null);
  const [securityClass, setSecurityClass] = useState<IndustrySecurityClass | null>(null);
  const [activity, setActivity] = useState<IndustryCostActivity>("manufacturing");
  const [usedOnly, setUsedOnly] = useState(false);
  const [sortBy, setSortBy] = useState<IndustryFacilitySortField>("facility");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<IndustryFacilityPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [syncingFacilities, setSyncingFacilities] = useState(false);
  const [syncResult, setSyncResult] = useState<IndustryFacilitySyncResult | null>(null);
  const [syncFailed, setSyncFailed] = useState(false);
  const numberFormat = useMemo(
    () => new Intl.NumberFormat(locale === "de" ? "de-DE" : "en-US"),
    [locale],
  );
  const percentFormat = useMemo(
    () => new Intl.NumberFormat(locale === "de" ? "de-DE" : "en-US", {
      style: "percent", maximumFractionDigits: 4,
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
    let activeRequest = true;
    setLoading(true);
    setFailed(false);
    void loadFacilities({
      search: appliedSearch, kind, access, securityClass, activity, usedOnly,
      offset, limit: industryFacilityPageSize, sortBy, sortDirection,
    }).then((result) => {
      if (!activeRequest) return;
      if (result.total > 0 && result.offset >= result.total) {
        setOffset(Math.floor((result.total - 1) / industryFacilityPageSize) * industryFacilityPageSize);
        return;
      }
      setPage(result);
    }).catch(() => {
      if (activeRequest) setFailed(true);
    }).finally(() => {
      if (activeRequest) setLoading(false);
    });
    return () => { activeRequest = false; };
  }, [access, activity, appliedSearch, available, kind, loadFacilities, offset, refreshRevision, securityClass, sortBy, sortDirection, usedOnly]);

  const refresh = async () => {
    if (!available || syncingFacilities) return;
    setSyncingFacilities(true);
    setSyncFailed(false);
    setSyncResult(null);
    try {
      setSyncResult(await syncFacilities());
      setOffset(0);
    } catch {
      setSyncFailed(true);
    } finally {
      setSyncingFacilities(false);
    }
  };
  const changeSort = (field: IndustryFacilitySortField) => {
    if (sortBy === field) setSortDirection((value) => value === "asc" ? "desc" : "asc");
    else { setSortBy(field); setSortDirection("asc"); }
    setOffset(0);
  };
  const header = (field: IndustryFacilitySortField, label: string) => (
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
    <section className="asset-browser industry-facilities" aria-busy={loading}>
      <header className="asset-deltas__header industry-jobs__header">
        <div>
          <span className="eyebrow">{t.blueprints.facilities.kicker}</span>
          <h2>{t.blueprints.facilities.title}</h2>
          <p>{t.blueprints.facilities.subtitle}</p>
        </div>
        <div className="asset-hero__metrics">
          <span><strong>{numberFormat.format(total)}</strong><small>{t.blueprints.facilities.count}</small></span>
          <span><strong>{numberFormat.format(page?.systems ?? 0)}</strong><small>{t.blueprints.facilities.systems}</small></span>
          <span><strong>{numberFormat.format(page?.restrictedStructures ?? 0)}</strong><small>{t.blueprints.facilities.restricted}</small></span>
          <span><strong>{page?.ageSeconds == null ? "—" : formatDataAge(page.ageSeconds, locale)}</strong><small>{t.blueprints.facilities.age}</small></span>
        </div>
      </header>
      <div className="asset-toolbar industry-facility-toolbar">
        <label className="asset-search"><span>{t.blueprints.facilities.search}</span><div><Search size={16} /><input value={search} maxLength={120} onChange={(event) => setSearch(event.target.value)} placeholder={t.blueprints.facilities.search} disabled={!available} /></div></label>
        <label><span>{t.blueprints.facilities.kind}</span><select value={kind ?? ""} onChange={(event) => { setKind((event.target.value || null) as IndustryFacilityKind | null); setOffset(0); }}><option value="">{t.blueprints.facilities.allKinds}</option>{(page?.kinds ?? []).map((value) => <option key={value} value={value}>{t.blueprints.facilities.kindLabels[value]}</option>)}</select></label>
        <label><span>{t.blueprints.facilities.access}</span><select value={access ?? ""} onChange={(event) => { setAccess((event.target.value || null) as IndustryFacilityAccess | null); setOffset(0); }}><option value="">{t.blueprints.facilities.allAccess}</option>{(page?.accessStates ?? []).map((value) => <option key={value} value={value}>{t.blueprints.facilities.accessLabels[value]}</option>)}</select></label>
        <label><span>{t.blueprints.facilities.security}</span><select value={securityClass ?? ""} onChange={(event) => { setSecurityClass((event.target.value || null) as IndustrySecurityClass | null); setOffset(0); }}><option value="">{t.blueprints.facilities.allSecurity}</option>{(page?.securityClasses ?? []).map((value) => <option key={value} value={value}>{t.blueprints.facilities.securityLabels[value]}</option>)}</select></label>
        <label><span>{t.blueprints.facilities.activity}</span><select value={activity} onChange={(event) => { setActivity(event.target.value as IndustryCostActivity); setOffset(0); }}>{(page?.activities ?? []).map((value) => <option key={value} value={value}>{t.blueprints.facilities.activityLabels[value]}</option>)}</select></label>
        <button className={`secondary-button facility-used-toggle ${usedOnly ? "is-active" : ""}`} type="button" aria-pressed={usedOnly} onClick={() => { setUsedOnly((value) => !value); setOffset(0); }}>{t.blueprints.facilities.usedOnly}</button>
        <button className="secondary-button asset-export" type="button" onClick={() => void refresh()} disabled={!available || syncingFacilities}><RefreshCw className={syncingFacilities ? "spin" : ""} size={15} />{syncingFacilities ? t.blueprints.facilities.syncing : t.blueprints.facilities.sync}</button>
      </div>
      <div className="asset-export-status facility-boundary">{t.blueprints.facilities.boundary}</div>
      {(syncResult || syncFailed) && <div className={`asset-export-status ${syncFailed ? "asset-export-status--error" : ""}`} role="status">{syncFailed ? t.blueprints.facilities.syncError : t.blueprints.facilities.syncComplete.replace("{facilities}", numberFormat.format(syncResult?.facilities ?? 0)).replace("{systems}", numberFormat.format(syncResult?.systems ?? 0))}</div>}
      {!available ? <div className="asset-empty"><Database size={22} />{t.blueprints.unavailable}</div>
        : failed ? <div className="asset-empty asset-empty--error"><AlertTriangle size={22} />{t.blueprints.facilities.queryError}</div>
        : loading && page === null ? <div className="asset-empty"><RefreshCw className="spin" size={22} />{t.blueprints.facilities.loading}</div>
        : page && page.items.length === 0 ? <div className="asset-empty"><Factory size={22} />{page.observedAt === null ? t.blueprints.facilities.noData : t.blueprints.facilities.noMatches}</div>
        : page ? <div className="asset-table-wrap"><table className="asset-table industry-facility-table"><thead><tr>
            <th>{header("facility", t.blueprints.facilities.facility)}</th><th>{header("system", t.blueprints.facilities.system)}</th><th>{t.blueprints.facilities.owner}</th><th>{header("cost", t.blueprints.facilities.cost)}</th><th>{header("jobs", t.blueprints.facilities.jobs)}</th><th>{header("access", t.blueprints.facilities.access)}</th><th>{header("age", t.blueprints.facilities.source)}</th>
          </tr></thead><tbody>{page.items.map((item) => <tr key={item.facilityId}>
            <td><strong>{item.facilityName ?? `#${item.facilityId}`}</strong><small>{item.typeName ?? t.blueprints.facilities.kindLabels[item.kind]}{item.typeId == null ? "" : ` · Type #${item.typeId}`}</small></td>
            <td><strong>{item.solarSystemName ?? "—"}</strong><small>{item.regionName ?? (item.solarSystemId == null ? "—" : `#${item.solarSystemId}`)} · {t.blueprints.facilities.securityLabels[item.securityClass]}{item.securityStatus == null ? "" : ` ${item.securityStatus.toLocaleString(locale === "de" ? "de-DE" : "en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`}</small></td>
            <td><strong>{item.ownerName ?? "—"}</strong><small>{item.ownerId == null ? "—" : `#${item.ownerId}`}</small></td>
            <td className="asset-table__number"><strong>{item.activityCostIndex == null ? "—" : percentFormat.format(item.activityCostIndex)}</strong><small>{item.tax == null ? t.blueprints.facilities.taxUnknown : percentFormat.format(item.tax)}</small></td>
            <td className="asset-table__number"><strong>{numberFormat.format(item.jobCount)}</strong><small>{item.jobCount === 0 ? t.blueprints.facilities.noJobs : `${numberFormat.format(item.activeJobs)} ${t.blueprints.facilities.active}`}</small></td>
            <td><span className={`status-pill status-pill--${item.access === "public" || item.access === "available" ? "good" : item.access === "unknown" ? "info" : "warn"}`}>{t.blueprints.facilities.accessLabels[item.access]}</span><small>{t.blueprints.facilities.kindLabels[item.kind]}</small></td>
            <td><strong>Snapshot #{item.snapshotId}</strong><small>Run #{item.syncRunId} · {formatDataAge(item.ageSeconds, locale)}</small></td>
          </tr>)}</tbody></table></div> : null}
      {page && total > 0 && <div className="asset-pagination"><span>{range}</span><div><button type="button" onClick={() => setOffset(Math.max(0, offset - industryFacilityPageSize))} disabled={offset === 0}>{t.blueprints.previous}</button><button type="button" onClick={() => setOffset(offset + industryFacilityPageSize)} disabled={offset + industryFacilityPageSize >= total}>{t.blueprints.next}</button></div></div>}
    </section>
  );
}

function ResearchPlanningPanel({
  available, locale, t, loadPlans, savePlan, deletePlan, refreshRevision,
}: {
  available: boolean;
  locale: Locale;
  t: Translation;
  loadPlans: (query: ResearchPlanQuery) => Promise<ResearchPlanPage>;
  savePlan: (input: ResearchPlanInput) => Promise<unknown>;
  deletePlan: (ownerCharacterId: number, blueprintItemId: number) => Promise<void>;
  refreshRevision: number;
}) {
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [ownerCharacterId, setOwnerCharacterId] = useState<number | null>(null);
  const [planState, setPlanState] = useState<ResearchPlanState | null>(null);
  const [plannedOnly, setPlannedOnly] = useState(false);
  const [sortBy, setSortBy] = useState<ResearchPlanSortField>("priority");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<ResearchPlanPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [localRevision, setLocalRevision] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, ResearchPlanInput>>({});
  const [mutationKey, setMutationKey] = useState<string | null>(null);
  const [mutationStatus, setMutationStatus] = useState<"saved" | "deleted" | "error" | null>(null);
  const numberFormat = useMemo(
    () => new Intl.NumberFormat(locale === "de" ? "de-DE" : "en-US", { maximumFractionDigits: 2 }),
    [locale],
  );
  const percentFormat = useMemo(
    () => new Intl.NumberFormat(locale === "de" ? "de-DE" : "en-US", {
      style: "percent", maximumFractionDigits: 4,
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
    let activeRequest = true;
    setLoading(true);
    setFailed(false);
    void loadPlans({
      search: appliedSearch, ownerCharacterId, state: planState, plannedOnly,
      offset, limit: researchPlanPageSize, sortBy, sortDirection,
    }).then((result) => {
      if (!activeRequest) return;
      if (result.total > 0 && result.offset >= result.total) {
        setOffset(Math.floor((result.total - 1) / researchPlanPageSize) * researchPlanPageSize);
        return;
      }
      const nextDrafts: Record<string, ResearchPlanInput> = {};
      result.items.forEach((item) => {
        const key = `${item.ownerCharacterId}:${item.blueprintItemId}`;
        nextDrafts[key] = {
          ownerCharacterId: item.ownerCharacterId,
          blueprintItemId: item.blueprintItemId,
          nextActivity: item.planned
            ? item.nextActivity
            : (item.currentMaterialEfficiency ?? 0) < 10 ? "material" : "time",
          targetMaterialEfficiency: item.planned
            ? item.targetMaterialEfficiency
            : Math.max(item.currentMaterialEfficiency ?? 0, 10),
          targetTimeEfficiency: item.planned
            ? item.targetTimeEfficiency
            : Math.max(item.currentTimeEfficiency ?? 0, 20),
          priority: item.planned ? item.priority : 50,
          note: item.note,
        };
      });
      setDrafts(nextDrafts);
      setPage(result);
    }).catch(() => {
      if (activeRequest) setFailed(true);
    }).finally(() => {
      if (activeRequest) setLoading(false);
    });
    return () => { activeRequest = false; };
  }, [appliedSearch, available, loadPlans, localRevision, offset, ownerCharacterId, planState, plannedOnly, refreshRevision, sortBy, sortDirection]);

  const changeSort = (field: ResearchPlanSortField) => {
    if (sortBy === field) setSortDirection((value) => value === "asc" ? "desc" : "asc");
    else { setSortBy(field); setSortDirection(field === "priority" ? "desc" : "asc"); }
    setOffset(0);
  };
  const header = (field: ResearchPlanSortField, label: string) => (
    <button type="button" className="asset-sort" onClick={() => changeSort(field)}>
      {label}{sortBy === field && <ChevronDown className={sortDirection === "asc" ? "asset-sort__asc" : ""} size={14} />}
    </button>
  );
  const updateDraft = (key: string, update: Partial<ResearchPlanInput>) => {
    setDrafts((current) => ({ ...current, [key]: { ...current[key], ...update } }));
    setMutationStatus(null);
  };
  const save = async (key: string) => {
    const draft = drafts[key];
    if (!draft || mutationKey) return;
    setMutationKey(key);
    setMutationStatus(null);
    try {
      await savePlan(draft);
      setMutationStatus("saved");
      setLocalRevision((value) => value + 1);
    } catch {
      setMutationStatus("error");
    } finally {
      setMutationKey(null);
    }
  };
  const remove = async (key: string, ownerId: number, itemId: number) => {
    if (mutationKey) return;
    setMutationKey(key);
    setMutationStatus(null);
    try {
      await deletePlan(ownerId, itemId);
      setMutationStatus("deleted");
      setLocalRevision((value) => value + 1);
    } catch {
      setMutationStatus("error");
    } finally {
      setMutationKey(null);
    }
  };
  const stateTone = (state: ResearchPlanState) => state === "ready" || state === "complete"
    ? "good" : state === "queued" || state === "unverified" || state === "missing" ? "warn"
      : state === "running" ? "info" : "neutral";
  const total = page?.total ?? 0;
  const plannedCount = page == null
    ? 0
    : Object.entries(page.summary).reduce((sum, [state, count]) => sum + (state === "unplanned" ? 0 : count), 0);
  const freeSlots = page?.owners.reduce((sum, owner) => sum + (owner.slotsAvailable ?? 0), 0) ?? 0;
  const range = t.blueprints.research.resultRange
    .replace("{from}", numberFormat.format(total === 0 ? 0 : offset + 1))
    .replace("{to}", numberFormat.format(Math.min(offset + (page?.items.length ?? 0), total)))
    .replace("{total}", numberFormat.format(total));

  return (
    <section className="asset-browser research-planning" aria-busy={loading}>
      <header className="asset-deltas__header industry-jobs__header">
        <div>
          <span className="eyebrow">{t.blueprints.research.kicker}</span>
          <h2>{t.blueprints.research.title}</h2>
          <p>{t.blueprints.research.subtitle}</p>
        </div>
        <div className="asset-hero__metrics">
          <span><strong>{numberFormat.format(plannedCount)}</strong><small>{t.blueprints.research.plans}</small></span>
          <span><strong>{numberFormat.format(page?.summary.ready ?? 0)}</strong><small>{t.blueprints.research.ready}</small></span>
          <span><strong>{numberFormat.format(page?.summary.running ?? 0)}</strong><small>{t.blueprints.research.running}</small></span>
          <span><strong>{numberFormat.format(freeSlots)}</strong><small>{t.blueprints.research.freeSlots}</small></span>
        </div>
      </header>
      <div className="asset-toolbar research-toolbar">
        <label className="asset-search"><span>{t.blueprints.research.search}</span><div><Search size={16} /><input value={search} maxLength={120} onChange={(event) => setSearch(event.target.value)} placeholder={t.blueprints.research.search} disabled={!available} /></div></label>
        <label><span>{t.blueprints.owner}</span><select value={ownerCharacterId ?? ""} onChange={(event) => { setOwnerCharacterId(event.target.value ? Number(event.target.value) : null); setOffset(0); }}><option value="">{t.blueprints.allOwners}</option>{(page?.owners ?? []).map((owner) => <option key={owner.characterId} value={owner.characterId}>{owner.name}</option>)}</select></label>
        <label><span>{t.blueprints.research.state}</span><select value={planState ?? ""} onChange={(event) => { setPlanState((event.target.value || null) as ResearchPlanState | null); setOffset(0); }}><option value="">{t.blueprints.research.allStates}</option>{(page?.states ?? []).map((state) => <option key={state} value={state}>{t.blueprints.research.stateLabels[state]}</option>)}</select></label>
        <button className={`secondary-button facility-used-toggle ${plannedOnly ? "is-active" : ""}`} type="button" aria-pressed={plannedOnly} onClick={() => { setPlannedOnly((value) => !value); setOffset(0); }}>{t.blueprints.research.plannedOnly}</button>
      </div>
      <div className="asset-export-status facility-boundary">{t.blueprints.research.boundary}</div>
      {mutationStatus && <div className={`asset-export-status ${mutationStatus === "error" ? "asset-export-status--error" : ""}`} role="status">{mutationStatus === "saved" ? t.blueprints.research.saved : mutationStatus === "deleted" ? t.blueprints.research.deleted : t.blueprints.research.mutationError}</div>}
      {!available ? <div className="asset-empty"><Database size={22} />{t.blueprints.unavailable}</div>
        : failed ? <div className="asset-empty asset-empty--error"><AlertTriangle size={22} />{t.blueprints.research.queryError}</div>
        : loading && page === null ? <div className="asset-empty"><RefreshCw className="spin" size={22} />{t.blueprints.research.loading}</div>
        : page && page.items.length === 0 ? <div className="asset-empty"><FlaskConical size={22} />{page.observedAt === null ? t.blueprints.research.noData : t.blueprints.research.noMatches}</div>
        : page ? <div className="asset-table-wrap"><table className="asset-table research-table"><thead><tr>
            <th>{header("blueprint", t.blueprints.research.blueprint)}</th><th>{header("state", t.blueprints.research.status)}</th><th>{header("priority", t.blueprints.research.plan)}</th><th>{t.blueprints.research.slots}</th><th>{t.blueprints.research.evidence}</th><th>{t.blueprints.research.source}</th>
          </tr></thead><tbody>{page.items.map((item) => {
            const key = `${item.ownerCharacterId}:${item.blueprintItemId}`;
            const draft = drafts[key];
            return <tr key={key}>
              <td><strong>{item.blueprintName}</strong><small>{item.ownerName} · BPO #{item.blueprintItemId}</small><small>{item.locationFlag == null ? t.blueprints.research.stateLabels.missing : `${item.locationFlag} · #${item.locationId}`}</small></td>
              <td><span className={`status-pill status-pill--${stateTone(item.state)}`}>{t.blueprints.research.stateLabels[item.state]}</span><small>ME {item.currentMaterialEfficiency ?? "—"} → {draft?.targetMaterialEfficiency ?? item.targetMaterialEfficiency} · TE {item.currentTimeEfficiency ?? "—"} → {draft?.targetTimeEfficiency ?? item.targetTimeEfficiency}</small></td>
              <td>{draft && <div className="research-plan-editor">
                <select aria-label={t.blueprints.research.plan} value={draft.nextActivity} onChange={(event) => updateDraft(key, { nextActivity: event.target.value as "material" | "time" })}><option value="material">{t.blueprints.research.activityLabels.material}</option><option value="time">{t.blueprints.research.activityLabels.time}</option></select>
                <div className="research-targets"><label><span>{t.blueprints.research.targetMe}</span><select value={draft.targetMaterialEfficiency} onChange={(event) => updateDraft(key, { targetMaterialEfficiency: Number(event.target.value) })}>{Array.from({ length: 11 }, (_, value) => value).filter((value) => value >= (item.currentMaterialEfficiency ?? 0)).map((value) => <option key={value} value={value}>{value}</option>)}</select></label><label><span>{t.blueprints.research.targetTe}</span><select value={draft.targetTimeEfficiency} onChange={(event) => updateDraft(key, { targetTimeEfficiency: Number(event.target.value) })}>{Array.from({ length: 21 }, (_, value) => value).filter((value) => value >= (item.currentTimeEfficiency ?? 0)).map((value) => <option key={value} value={value}>{value}</option>)}</select></label><label><span>{t.blueprints.research.priority}</span><input type="number" min={0} max={999} value={draft.priority} onChange={(event) => updateDraft(key, { priority: Math.max(0, Math.min(999, Number(event.target.value))) })} /></label></div>
                <input className="research-note" aria-label={t.blueprints.research.note} maxLength={240} value={draft.note ?? ""} placeholder={t.blueprints.research.notePlaceholder} onChange={(event) => updateDraft(key, { note: event.target.value || null })} />
                <div className="research-actions"><button type="button" onClick={() => void save(key)} disabled={mutationKey !== null || !item.blueprintPresent && !item.planned}><Check size={14} />{mutationKey === key ? t.blueprints.research.saving : item.planned ? t.blueprints.research.update : t.blueprints.research.save}</button>{item.planned && <button className="research-remove" type="button" onClick={() => void remove(key, item.ownerCharacterId, item.blueprintItemId)} disabled={mutationKey !== null}><X size={14} />{t.blueprints.research.remove}</button>}</div>
              </div>}</td>
              <td>{item.slotCapacity == null ? <><strong>—</strong><small>{t.blueprints.research.slotsUnknown}</small></> : <><strong>{t.blueprints.research.slotsValue.replace("{available}", String(item.slotsAvailable)).replace("{used}", String(item.slotsUsed)).replace("{capacity}", String(item.slotCapacity))}</strong><small>{t.blueprints.research.skillValue.replace("{research}", String(item.researchLevel)).replace("{metallurgy}", String(item.metallurgyLevel))}</small></>}</td>
              <td>{item.activeJobId == null ? <><strong>{t.blueprints.research.noActiveJob}</strong></> : <><strong>{t.blueprints.research.activeJob.replace("{job}", String(item.activeJobId)).replace("{activity}", t.blueprints.research.activityLabels[item.activeJobActivity!])}</strong><small>{t.blueprints.research.ends.replace("{date}", new Date(item.activeJobEndDate!).toLocaleString(locale === "de" ? "de-DE" : "en-US"))}{item.activeJobCost == null ? "" : ` · ${numberFormat.format(item.activeJobCost)} ISK`}</small></>}<small>{item.facilityId == null ? t.blueprints.research.noFacility : `${item.facilityName ?? `#${item.facilityId}`} · ${item.facilityEvidence === "active-job" ? t.blueprints.research.currentFacility : t.blueprints.research.lastFacility}`}</small>{item.solarSystemName && <small>{item.solarSystemName}{item.systemCostIndex == null ? "" : ` · ${t.blueprints.research.systemCost.replace("{value}", percentFormat.format(item.systemCostIndex))}`}</small>}</td>
              <td><strong>{item.blueprintSnapshotId == null ? "BP —" : `BP #${item.blueprintSnapshotId}`}</strong><small>{item.skillSnapshotId == null ? "Skills —" : `Skills #${item.skillSnapshotId}`} · {item.jobSnapshotId == null ? "Jobs —" : `Jobs #${item.jobSnapshotId}`}</small><small>{item.ageSeconds == null ? "—" : formatDataAge(item.ageSeconds, locale)}</small></td>
            </tr>;
          })}</tbody></table></div> : null}
      {page && total > 0 && <div className="asset-pagination"><span>{range}</span><div><button type="button" onClick={() => setOffset(Math.max(0, offset - researchPlanPageSize))} disabled={offset === 0}>{t.blueprints.previous}</button><button type="button" onClick={() => setOffset(offset + researchPlanPageSize)} disabled={offset + researchPlanPageSize >= total}>{t.blueprints.next}</button></div></div>}
    </section>
  );
}

function ProductionWorkspace({
  available, locale, t, loadCatalog, loadPlans, savePlan, deletePlan,
}: {
  available: boolean;
  locale: Locale;
  t: Translation;
  loadCatalog: (query: ProductionCatalogQuery) => Promise<ProductionCatalogPage>;
  loadPlans: (query: ProductionPlanQuery) => Promise<ProductionPlanPage>;
  savePlan: (input: ProductionPlanInput) => Promise<unknown>;
  deletePlan: (planId: number) => Promise<void>;
}) {
  const [catalogSearch, setCatalogSearch] = useState("");
  const [appliedCatalogSearch, setAppliedCatalogSearch] = useState("");
  const [catalogActivity, setCatalogActivity] = useState<ProductionActivity | null>(null);
  const [catalogOffset, setCatalogOffset] = useState(0);
  const [catalog, setCatalog] = useState<ProductionCatalogPage | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogFailed, setCatalogFailed] = useState(false);
  const [selected, setSelected] = useState<ProductionCatalogItem | null>(null);
  const [newOwner, setNewOwner] = useState<number | null>(null);
  const [newQuantity, setNewQuantity] = useState(1);
  const [newPriority, setNewPriority] = useState(0);
  const [newNote, setNewNote] = useState("");
  const [planSearch, setPlanSearch] = useState("");
  const [appliedPlanSearch, setAppliedPlanSearch] = useState("");
  const [planOwner, setPlanOwner] = useState<number | null>(null);
  const [planActivity, setPlanActivity] = useState<ProductionActivity | null>(null);
  const [planState, setPlanState] = useState<ProductionPlanState | null>(null);
  const [sortBy, setSortBy] = useState<ProductionPlanSortField>("priority");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [planOffset, setPlanOffset] = useState(0);
  const [plans, setPlans] = useState<ProductionPlanPage | null>(null);
  const [plansLoading, setPlansLoading] = useState(false);
  const [plansFailed, setPlansFailed] = useState(false);
  const [revision, setRevision] = useState(0);
  const [busyId, setBusyId] = useState<number | "new" | null>(null);
  const [mutationState, setMutationState] = useState<"saved" | "deleted" | "error" | null>(null);
  const [drafts, setDrafts] = useState<Record<number, { owner: number; quantity: number; priority: number; note: string }>>({});
  const numberFormat = useMemo(() => new Intl.NumberFormat(locale === "de" ? "de-DE" : "en-US"), [locale]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setAppliedCatalogSearch(catalogSearch.trim().replace(/\s+/g, " "));
      setCatalogOffset(0);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [catalogSearch]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setAppliedPlanSearch(planSearch.trim().replace(/\s+/g, " "));
      setPlanOffset(0);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [planSearch]);

  useEffect(() => {
    if (!available) return;
    let active = true;
    setCatalogLoading(true);
    setCatalogFailed(false);
    void loadCatalog({ search: appliedCatalogSearch, activity: catalogActivity,
      offset: catalogOffset, limit: productionCatalogPageSize })
      .then((page) => {
        if (!active) return;
        if (page.total > 0 && page.offset >= page.total) {
          setCatalogOffset(Math.floor((page.total - 1) / productionCatalogPageSize) * productionCatalogPageSize);
          return;
        }
        setCatalog(page);
      })
      .catch(() => { if (active) setCatalogFailed(true); })
      .finally(() => { if (active) setCatalogLoading(false); });
    return () => { active = false; };
  }, [appliedCatalogSearch, available, catalogActivity, catalogOffset, loadCatalog, revision]);

  useEffect(() => {
    if (!available) return;
    let active = true;
    setPlansLoading(true);
    setPlansFailed(false);
    void loadPlans({ search: appliedPlanSearch, ownerCharacterId: planOwner, activity: planActivity,
      state: planState, offset: planOffset, limit: productionPlanPageSize, sortBy, sortDirection })
      .then((page) => {
        if (!active) return;
        if (page.total > 0 && page.offset >= page.total) {
          setPlanOffset(Math.floor((page.total - 1) / productionPlanPageSize) * productionPlanPageSize);
          return;
        }
        setPlans(page);
        setDrafts(Object.fromEntries(page.items.map((item) => [item.planId, {
          owner: item.ownerCharacterId, quantity: item.targetQuantity,
          priority: item.priority, note: item.note ?? "",
        }])));
        setNewOwner((current) => current ?? page.owners[0]?.characterId ?? null);
      })
      .catch(() => { if (active) setPlansFailed(true); })
      .finally(() => { if (active) setPlansLoading(false); });
    return () => { active = false; };
  }, [appliedPlanSearch, available, loadPlans, planActivity, planOffset, planOwner,
    planState, revision, sortBy, sortDirection]);

  const createGoal = async () => {
    if (!selected || newOwner === null || busyId !== null) return;
    setBusyId("new");
    setMutationState(null);
    try {
      await savePlan({ planId: null, ownerCharacterId: newOwner,
        blueprintTypeId: selected.blueprintTypeId, activity: selected.activity,
        productTypeId: selected.productTypeId, targetQuantity: newQuantity,
        priority: newPriority, note: newNote || null });
      setMutationState("saved");
      setSelected(null);
      setNewQuantity(1);
      setNewPriority(0);
      setNewNote("");
      setRevision((value) => value + 1);
    } catch {
      setMutationState("error");
    } finally {
      setBusyId(null);
    }
  };
  const updateGoal = async (item: ProductionPlanPage["items"][number]) => {
    const draft = drafts[item.planId];
    if (!draft || busyId !== null) return;
    setBusyId(item.planId);
    setMutationState(null);
    try {
      await savePlan({ planId: item.planId, ownerCharacterId: draft.owner,
        blueprintTypeId: item.blueprintTypeId, activity: item.activity,
        productTypeId: item.productTypeId, targetQuantity: draft.quantity,
        priority: draft.priority, note: draft.note || null });
      setMutationState("saved");
      setRevision((value) => value + 1);
    } catch {
      setMutationState("error");
    } finally {
      setBusyId(null);
    }
  };
  const removeGoal = async (planId: number) => {
    if (busyId !== null) return;
    setBusyId(planId);
    setMutationState(null);
    try {
      await deletePlan(planId);
      setMutationState("deleted");
      setRevision((value) => value + 1);
    } catch {
      setMutationState("error");
    } finally {
      setBusyId(null);
    }
  };
  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return hours > 0 ? `${hours} h ${minutes} min` : `${minutes} min`;
  };
  const planTotal = plans?.total ?? 0;
  const planFrom = planTotal === 0 ? 0 : planOffset + 1;
  const planTo = Math.min(planOffset + (plans?.items.length ?? 0), planTotal);

  return (
    <div className="workspace production-workspace">
      <section className="asset-hero">
        <div><span className="eyebrow">{t.productionPlanning.kicker}</span><h1>{t.productionPlanning.title}</h1><p>{t.productionPlanning.subtitle}</p></div>
        <div className="asset-hero__metrics"><span><strong>{numberFormat.format(planTotal)}</strong><small>{t.productionPlanning.plans}</small></span><span><strong>{plans?.buildNumber ?? "—"}</strong><small>SDE</small></span></div>
      </section>
      <section className="production-boundary"><ShieldCheck size={18} /><span>{t.productionPlanning.boundary}</span></section>

      <section className="production-builder">
        <PanelHeader icon={Factory} title={t.productionPlanning.catalog} subtitle={catalog?.buildNumber ? t.productionPlanning.build.replace("{build}", catalog.buildNumber) : t.productionPlanning.noSde} />
        <div className="asset-toolbar production-toolbar">
          <label className="asset-search"><span>{t.productionPlanning.searchRecipe}</span><div><Search size={16} /><input value={catalogSearch} maxLength={120} onChange={(event) => setCatalogSearch(event.target.value)} disabled={!available || catalog?.buildNumber === null} /></div></label>
          <label><span>{t.productionPlanning.activity}</span><select value={catalogActivity ?? ""} onChange={(event) => { setCatalogActivity((event.target.value || null) as ProductionActivity | null); setCatalogOffset(0); }}><option value="">{t.productionPlanning.allActivities}</option><option value="manufacturing">{t.productionPlanning.activityLabels.manufacturing}</option><option value="reaction">{t.productionPlanning.activityLabels.reaction}</option></select></label>
        </div>
        {!available ? <div className="asset-empty"><Database size={22} />{t.productionPlanning.queryError}</div>
          : catalogFailed ? <div className="asset-empty asset-empty--error"><AlertTriangle size={22} />{t.productionPlanning.queryError}</div>
          : catalogLoading && catalog === null ? <div className="asset-empty"><RefreshCw className="spin" size={22} />{t.productionPlanning.catalogLoading}</div>
          : catalog?.buildNumber === null ? <div className="asset-empty"><Database size={22} />{t.productionPlanning.noSde}</div>
          : catalog && catalog.items.length === 0 ? <div className="asset-empty"><Search size={22} />{t.productionPlanning.noRecipes}</div>
          : catalog ? <div className="production-catalog">{catalog.items.map((item) => {
              const active = selected?.blueprintTypeId === item.blueprintTypeId && selected.productTypeId === item.productTypeId && selected.activity === item.activity;
              return <button type="button" className={`production-catalog__item ${active ? "is-selected" : ""}`} key={`${item.blueprintTypeId}:${item.activity}:${item.productTypeId}`} onClick={() => { setSelected(item); setNewQuantity(item.outputQuantity); }}>
                <span><strong>{item.productName}</strong><small>{item.blueprintName} · #{item.blueprintTypeId}</small></span>
                <span><em>{t.productionPlanning.activityLabels[item.activity]}</em><small>{t.productionPlanning.output.replace("{quantity}", numberFormat.format(item.outputQuantity)).replace("{materials}", numberFormat.format(item.materialCount))}</small></span>
                <b>{active ? t.productionPlanning.selected : t.productionPlanning.select}</b>
              </button>;
            })}</div> : null}
        {catalog && catalog.total > productionCatalogPageSize && <div className="asset-pagination"><span>{catalog.offset + 1}–{Math.min(catalog.offset + catalog.items.length, catalog.total)} / {catalog.total}</span><div><button type="button" onClick={() => setCatalogOffset(Math.max(0, catalogOffset - productionCatalogPageSize))} disabled={catalogOffset === 0}>{t.productionPlanning.previous}</button><button type="button" onClick={() => setCatalogOffset(catalogOffset + productionCatalogPageSize)} disabled={catalogOffset + productionCatalogPageSize >= catalog.total}>{t.productionPlanning.next}</button></div></div>}
        <div className="production-create">
          <div className="production-create__selection"><Factory size={18} /><span><strong>{selected?.productName ?? t.productionPlanning.catalog}</strong><small>{selected ? `${selected.blueprintName} · ${t.productionPlanning.activityLabels[selected.activity]}` : t.productionPlanning.searchRecipe}</small></span></div>
          <label><span>{t.productionPlanning.owner}</span><select value={newOwner ?? ""} onChange={(event) => setNewOwner(event.target.value ? Number(event.target.value) : null)}><option value="">—</option>{(plans?.owners ?? []).map((owner) => <option key={owner.characterId} value={owner.characterId}>{owner.name}</option>)}</select></label>
          <label><span>{t.productionPlanning.target}</span><input type="number" min={1} max={Number.MAX_SAFE_INTEGER} value={newQuantity} onChange={(event) => setNewQuantity(Math.max(1, Number(event.target.value) || 1))} /></label>
          <label><span>{t.productionPlanning.priority}</span><input type="number" min={0} max={999} value={newPriority} onChange={(event) => setNewPriority(Math.min(999, Math.max(0, Number(event.target.value) || 0)))} /></label>
          <label className="production-create__note"><span>{t.productionPlanning.note}</span><input value={newNote} maxLength={240} placeholder={t.productionPlanning.notePlaceholder} onChange={(event) => setNewNote(event.target.value)} /></label>
          <button type="button" className="primary-button" onClick={() => void createGoal()} disabled={!selected || newOwner === null || busyId !== null}>{busyId === "new" ? <RefreshCw className="spin" size={15} /> : <Plus size={15} />}{busyId === "new" ? t.productionPlanning.saving : t.productionPlanning.create}</button>
        </div>
        {plans && plans.owners.length === 0 && <div className="asset-export-status asset-export-status--error">{t.productionPlanning.noOwners}</div>}
        {mutationState && <div className={`asset-export-status ${mutationState === "error" ? "asset-export-status--error" : ""}`} role="status">{mutationState === "saved" ? t.productionPlanning.saved : mutationState === "deleted" ? t.productionPlanning.deleted : t.productionPlanning.mutationError}</div>}
      </section>

      <section className="production-plans" aria-busy={plansLoading}>
        <PanelHeader icon={Boxes} title={t.productionPlanning.plans} subtitle={t.productionPlanning.subtitle} />
        <div className="asset-toolbar production-toolbar">
          <label className="asset-search"><span>{t.productionPlanning.searchPlans}</span><div><Search size={16} /><input value={planSearch} maxLength={120} onChange={(event) => setPlanSearch(event.target.value)} /></div></label>
          <label><span>{t.productionPlanning.owner}</span><select value={planOwner ?? ""} onChange={(event) => { setPlanOwner(event.target.value ? Number(event.target.value) : null); setPlanOffset(0); }}><option value="">{t.productionPlanning.allOwners}</option>{(plans?.owners ?? []).map((owner) => <option key={owner.characterId} value={owner.characterId}>{owner.name}</option>)}</select></label>
          <label><span>{t.productionPlanning.activity}</span><select value={planActivity ?? ""} onChange={(event) => { setPlanActivity((event.target.value || null) as ProductionActivity | null); setPlanOffset(0); }}><option value="">{t.productionPlanning.allActivities}</option><option value="manufacturing">{t.productionPlanning.activityLabels.manufacturing}</option><option value="reaction">{t.productionPlanning.activityLabels.reaction}</option></select></label>
          <label><span>{t.productionPlanning.state}</span><select value={planState ?? ""} onChange={(event) => { setPlanState((event.target.value || null) as ProductionPlanState | null); setPlanOffset(0); }}><option value="">{t.productionPlanning.allStates}</option>{(plans?.states ?? []).map((state) => <option key={state} value={state}>{t.productionPlanning.stateLabels[state]}</option>)}</select></label>
          <label><span>{t.productionPlanning.sort}</span><select value={sortBy} onChange={(event) => { setSortBy(event.target.value as ProductionPlanSortField); setPlanOffset(0); }}>{(["priority", "product", "owner", "activity", "state", "updated"] as const).map((field) => <option key={field} value={field}>{t.productionPlanning.sortLabels[field]}</option>)}</select></label>
          <button type="button" className="secondary-button" onClick={() => setSortDirection((value) => value === "asc" ? "desc" : "asc")}><ChevronDown className={sortDirection === "asc" ? "asset-sort__asc" : ""} size={15} />{sortDirection.toUpperCase()}</button>
        </div>
        {!available ? <div className="asset-empty"><Database size={22} />{t.productionPlanning.queryError}</div>
          : plansFailed ? <div className="asset-empty asset-empty--error"><AlertTriangle size={22} />{t.productionPlanning.queryError}</div>
          : plansLoading && plans === null ? <div className="asset-empty"><RefreshCw className="spin" size={22} />{t.productionPlanning.loading}</div>
          : plans && plans.items.length === 0 ? <div className="asset-empty"><Factory size={22} />{planSearch || planOwner || planActivity || planState ? t.productionPlanning.noMatches : t.productionPlanning.noPlans}</div>
          : plans ? <div className="production-plan-list">{plans.items.map((item) => {
              const draft = drafts[item.planId] ?? { owner: item.ownerCharacterId, quantity: item.targetQuantity, priority: item.priority, note: item.note ?? "" };
              return <article className="production-plan-card" key={item.planId}>
                <header><div><span className={`status-pill status-pill--${item.state === "ready" ? "good" : "warn"}`}>{t.productionPlanning.stateLabels[item.state]}</span><h2>{item.productName}</h2><p>{item.blueprintName} · {t.productionPlanning.activityLabels[item.activity]} · #{item.blueprintTypeId}</p></div><strong>{t.productionPlanning.goalQuantity.replace("{quantity}", numberFormat.format(item.targetQuantity))}</strong></header>
                <div className="production-plan-editor">
                  <label><span>{t.productionPlanning.owner}</span><select value={draft.owner} onChange={(event) => setDrafts((current) => ({ ...current, [item.planId]: { ...draft, owner: Number(event.target.value) } }))}>{!plans.owners.some((owner) => owner.characterId === draft.owner) && <option value={draft.owner}>{item.ownerName}</option>}{plans.owners.map((owner) => <option key={owner.characterId} value={owner.characterId}>{owner.name}</option>)}</select></label>
                  <label><span>{t.productionPlanning.quantity}</span><input type="number" min={1} value={draft.quantity} onChange={(event) => setDrafts((current) => ({ ...current, [item.planId]: { ...draft, quantity: Math.max(1, Number(event.target.value) || 1) } }))} /></label>
                  <label><span>{t.productionPlanning.priority}</span><input type="number" min={0} max={999} value={draft.priority} onChange={(event) => setDrafts((current) => ({ ...current, [item.planId]: { ...draft, priority: Math.min(999, Math.max(0, Number(event.target.value) || 0)) } }))} /></label>
                  <label><span>{t.productionPlanning.note}</span><input maxLength={240} value={draft.note} onChange={(event) => setDrafts((current) => ({ ...current, [item.planId]: { ...draft, note: event.target.value } }))} /></label>
                  <button type="button" onClick={() => void updateGoal(item)} disabled={busyId !== null}>{busyId === item.planId ? <RefreshCw className="spin" size={14} /> : <Check size={14} />}{t.productionPlanning.save}</button>
                  <button type="button" className="danger-button" onClick={() => void removeGoal(item.planId)} disabled={busyId !== null}><X size={14} />{t.productionPlanning.remove}</button>
                </div>
                {item.warnings.map((warning) => <div className="production-warning" key={`${warning.typeId}:${warning.selectedBlueprintTypeId}`}><AlertTriangle size={14} />{t.productionPlanning.alternatives.replace("{type}", warning.typeName).replace("{count}", String(warning.candidateCount)).replace("{blueprint}", String(warning.selectedBlueprintTypeId))}</div>)}
                {item.state === "ready" && <div className="production-resolution">
                  <details open><summary>{t.productionPlanning.steps} · {item.steps.length}</summary><p className="production-sequence-hint">{t.productionPlanning.sequenceHint}</p><ol>{item.steps.map((step, index) => { const isGoal = index === item.steps.length - 1; return <li className={isGoal ? "production-step--goal" : ""} key={`${step.sequence}:${step.productTypeId}`}><div><strong>{t.productionPlanning.step.replace("{sequence}", String(step.sequence))} · {isGoal ? t.productionPlanning.goalStep : t.productionPlanning.intermediateStep}: {step.productName}</strong><span>{step.blueprintName} · {t.productionPlanning.activityLabels[step.activity]}</span></div><div><strong>{t.productionPlanning.runs.replace("{runs}", numberFormat.format(step.runs)).replace("{produced}", numberFormat.format(step.producedQuantity)).replace("{surplus}", numberFormat.format(step.surplusQuantity))}</strong><span>{t.productionPlanning.baseTime.replace("{time}", formatDuration(step.totalBaseTimeSeconds))}</span></div></li>; })}</ol></details>
                  <details open><summary>{t.productionPlanning.gross} · {item.grossMaterials.length}</summary>{item.grossMaterials.length === 0 ? <p>{t.productionPlanning.noGross}</p> : <ul>{item.grossMaterials.map((material) => <li key={material.typeId}><span>{material.typeName}<small>Type #{material.typeId}</small></span><strong>{numberFormat.format(material.quantity)}</strong></li>)}</ul>}</details>
                </div>}
              </article>;
            })}</div> : null}
        {plans && planTotal > 0 && <div className="asset-pagination"><span>{t.productionPlanning.resultRange.replace("{from}", numberFormat.format(planFrom)).replace("{to}", numberFormat.format(planTo)).replace("{total}", numberFormat.format(planTotal))}</span><div><button type="button" onClick={() => setPlanOffset(Math.max(0, planOffset - productionPlanPageSize))} disabled={planOffset === 0}>{t.productionPlanning.previous}</button><button type="button" onClick={() => setPlanOffset(planOffset + productionPlanPageSize)} disabled={planOffset + productionPlanPageSize >= planTotal}>{t.productionPlanning.next}</button></div></div>}
      </section>
    </div>
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
