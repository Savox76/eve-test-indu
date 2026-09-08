import {
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  Bell,
  Boxes,
  Check,
  ChevronRight,
  CircleCheck,
  Clock3,
  Command,
  Database,
  Factory,
  FlaskConical,
  FolderKanban,
  Languages,
  LayoutDashboard,
  LineChart,
  type LucideIcon,
  MoreHorizontal,
  Orbit,
  PackageSearch,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  activity,
  attentionItems,
  demoMetadata,
  materialCoverage,
  metrics,
  modulePreview,
  productionStages,
} from "./demo";

type Locale = "de" | "en";
type ModuleId = "overview" | keyof typeof modulePreview;

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
    syncFresh: "Datenstand: vor 6 Min.",
    syncNow: "Jetzt aktuell",
    refresh: "Datenstand simuliert aktualisieren",
    notices: "Hinweise anzeigen",
    settings: "Einstellungen",
    connected: "Lokaler Arbeitsbereich",
    connectedDetail: "Bereit · nur dieses Gerät",
    syntheticPilot: "Mara Venn",
    syntheticCorp: "Kestrel Foundry · Demo",
    preview: "Design Preview",
    synthetic: "Ausschließlich synthetische Daten – noch keine EVE-Verbindung",
    dateLine: "OPERATIONS-BRIEF · YC 128.09.08",
    greeting: "Guten Morgen, Pilot.",
    heroText:
      "Deine Fertigung läuft stabil. Zwei Entscheidungen brauchen heute deine Aufmerksamkeit, bevor der nächste Produktionszyklus beginnt.",
    planAction: "Produktionsplan öffnen",
    inspectAction: "Datenlage prüfen",
    readiness: "Produktionsbereitschaft",
    readinessDetail: "für Projekt Aurora",
    readinessDelta: "+6 Punkte seit gestern",
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
    footerVersion: "v0.0.1-preview.2",
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
    syncFresh: "Data age: 6 min",
    syncNow: "Up to date",
    refresh: "Simulate data refresh",
    notices: "Show notices",
    settings: "Settings",
    connected: "Local workspace",
    connectedDetail: "Ready · this device only",
    syntheticPilot: "Mara Venn",
    syntheticCorp: "Kestrel Foundry · Demo",
    preview: "Design Preview",
    synthetic: "Synthetic data only – no EVE connection yet",
    dateLine: "OPERATIONS BRIEF · YC 128.09.08",
    greeting: "Good morning, pilot.",
    heroText:
      "Your production is running steadily. Two decisions need your attention today before the next manufacturing cycle begins.",
    planAction: "Open production plan",
    inspectAction: "Inspect data health",
    readiness: "Production readiness",
    readinessDetail: "for Project Aurora",
    readinessDelta: "+6 points since yesterday",
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
    footerVersion: "v0.0.1-preview.2",
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

export function App() {
  const [locale, setLocale] = useState<Locale>("de");
  const [activeModule, setActiveModule] = useState<ModuleId>("overview");
  const [query, setQuery] = useState("");
  const [searchFocused, setSearchFocused] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const t = copy[locale];

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

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

  const simulateRefresh = () => {
    setSyncing(true);
    window.setTimeout(() => setSyncing(false), 900);
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

        <div className="local-status">
          <div className="local-status__icon">
            <ShieldCheck size={17} />
          </div>
          <div>
            <strong>{t.connected}</strong>
            <span>{t.connectedDetail}</span>
          </div>
        </div>

        <button className="profile" type="button" aria-label={t.settings}>
          <span className="avatar">MV</span>
          <span className="profile-copy">
            <strong>{t.syntheticPilot}</strong>
            <small>{t.syntheticCorp}</small>
          </span>
          <Settings size={17} />
        </button>

        <div className="sidebar-footer">
          <span>{t.footerVersion}</span>
          <span className="preview-word">PREVIEW</span>
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

          <button className="sync-status" type="button" onClick={simulateRefresh} aria-label={t.refresh}>
            <RefreshCw className={syncing ? "spin" : ""} size={15} />
            <span>{syncing ? t.syncNow : t.syncFresh}</span>
          </button>

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

        <div className="preview-strip" role="status">
          <FlaskConical size={15} />
          <strong>{t.preview}</strong>
          <span>{t.synthetic}</span>
          <span className="preview-strip__meta">synthetic: {String(demoMetadata.synthetic)}</span>
        </div>

        {activeModule === "overview" ? (
          <Overview
            locale={locale}
            t={t}
            onOpenProduction={() => selectModule("production")}
            onInspect={scrollToAttention}
          />
        ) : (
          <ModulePreview activeModule={activeModule} t={t} />
        )}
      </main>
    </div>
  );
}

type Translation = (typeof copy)[Locale];

function Overview({
  locale,
  t,
  onOpenProduction,
  onInspect,
}: {
  locale: Locale;
  t: Translation;
  onOpenProduction: () => void;
  onInspect: () => void;
}) {
  return (
    <div className="workspace overview-workspace">
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
          <div className="readiness-ring" aria-label={`${t.readiness}: 84%`}>
            <div>
              <strong>84</strong><span>%</span>
            </div>
          </div>
          <div className="readiness-copy">
            <strong>{t.readiness}</strong>
            <span>{t.readinessDetail}</span>
            <small><TrendingUp size={13} /> {t.readinessDelta}</small>
          </div>
        </div>
      </section>

      <section className="metric-grid" aria-label={locale === "de" ? "Kennzahlen" : "Metrics"}>
        {metrics.map((metric) => (
          <article className={`metric-card metric-card--${metric.trend}`} key={metric.id}>
            <div className="metric-topline">
              <span>{t.metricLabels[metric.id]}</span>
              <button type="button" aria-label="Details"><MoreHorizontal size={17} /></button>
            </div>
            <div className="metric-body">
              <div>
                <strong className="metric-value">{metric.value}</strong>
                <span className="metric-unit">{metric.unit}</span>
              </div>
              <TrendLine id={metric.id} points={metric.points} warning={metric.trend === "warn"} />
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
            {productionStages.map((stage, index) => (
              <div className="production-row" key={stage.name}>
                <div className="job-name">
                  <span className={`job-glyph job-glyph--${index + 1}`}><Factory size={15} /></span>
                  <div><strong>{stage.name}</strong><small>{locale === "de" ? ["42 von 60 Einheiten", "Material reserviert", "Blueprint-Forschung"][index] : stage.detail}</small></div>
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
            {attentionItems.map((item, index) => (
              <div className="attention-item" key={item.title}>
                <StatusDot tone={item.severity === "critical" ? "critical" : item.severity === "warning" ? "warn" : "good"} />
                <div><strong>{item.title}</strong><span>{t.attentionDetails[index]}</span></div>
                <button type="button">{t.attentionActions[index]}<ChevronRight size={14} /></button>
              </div>
            ))}
          </div>
        </section>

        <section className="panel activity-panel">
          <PanelHeader icon={Database} title={t.activityTitle} subtitle={t.activitySubtitle} />
          <div className="activity-list">
            {activity.map((item, index) => (
              <div className="activity-item" key={item.title}>
                <span className={`activity-icon activity-icon--${item.kind}`}>
                  {item.kind === "complete" ? <Check size={15} /> : item.kind === "market" ? <LineChart size={15} /> : <RefreshCw size={15} />}
                </span>
                <div><strong>{t.activityTitles[index]}</strong><span>{t.activityDetails[index]}</span></div>
                <time>{t.activityTimes[index]}</time>
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
