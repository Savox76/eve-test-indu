export const demoMetadata = {
  synthetic: true,
  scenario: "A fictional solo industrialist with mixed manufacturing and research jobs.",
  generatedAt: "2026-09-08T07:42:00Z",
} as const;

export const metrics = [
  {
    id: "assets",
    value: "18.42 B",
    unit: "ISK",
    delta: "+2.8%",
    trend: "up",
    points: [22, 27, 25, 31, 34, 38, 41, 47, 45, 53, 59, 63],
  },
  {
    id: "jobs",
    value: "12",
    unit: "24 slots",
    delta: "3 end soon",
    trend: "steady",
    points: [33, 38, 42, 38, 44, 48, 52, 55, 52, 57, 61, 59],
  },
  {
    id: "readiness",
    value: "84",
    unit: "%",
    delta: "+6 pts",
    trend: "up",
    points: [24, 26, 31, 34, 38, 39, 45, 47, 52, 57, 61, 67],
  },
  {
    id: "attention",
    value: "4",
    unit: "signals",
    delta: "2 urgent",
    trend: "warn",
    points: [58, 53, 59, 55, 48, 51, 44, 42, 46, 38, 35, 31],
  },
] as const;

export const productionStages = [
  {
    name: "Asterion Relay",
    detail: "42 of 60 units",
    progress: 70,
    status: "active",
    eta: "5h 18m",
  },
  {
    name: "Vesper Field Array",
    detail: "Materials reserved",
    progress: 36,
    status: "active",
    eta: "1d 4h",
  },
  {
    name: "Helix Power Cell",
    detail: "Blueprint research",
    progress: 88,
    status: "research",
    eta: "47m",
  },
] as const;

export const materialCoverage = [
  { name: "Available", value: 68, tone: "teal" },
  { name: "Buy", value: 21, tone: "gold" },
  { name: "Build", value: 11, tone: "slate" },
] as const;

export const activity = [
  {
    kind: "complete",
    title: "Orion Frame batch completed",
    detail: "8 units moved to Borealis Hangar",
    time: "14 min",
  },
  {
    kind: "market",
    title: "Purchase window detected",
    detail: "Synthetic alloy basket is 6.4% below profile",
    time: "39 min",
  },
  {
    kind: "sync",
    title: "Asset snapshot refreshed",
    detail: "1,284 fictional positions reconciled",
    time: "1h",
  },
] as const;

export const attentionItems = [
  {
    severity: "critical",
    title: "Nereid extraction cycle",
    detail: "Ends in 2h 12m",
    action: "Review PI",
  },
  {
    severity: "warning",
    title: "Borealis structure access",
    detail: "Location details unavailable",
    action: "Inspect",
  },
  {
    severity: "info",
    title: "Market profile age",
    detail: "Last quote set: 3h ago",
    action: "Refresh",
  },
] as const;

export const modulePreview = {
  assets: {
    metric: "1,284",
    secondary: "18.42 B ISK",
    cards: ["Location tree", "Ownership filters", "Change history"],
  },
  blueprints: {
    metric: "326",
    secondary: "18 research-ready",
    cards: ["BPO & BPC library", "ME / TE research", "Industry slots"],
  },
  production: {
    metric: "84%",
    secondary: "material coverage",
    cards: ["Bill of materials", "Build vs. buy", "Manufacturing route"],
  },
  invention: {
    metric: "41.8%",
    secondary: "modeled success",
    cards: ["Copying batches", "Decryptor scenarios", "Datacore demand"],
  },
  market: {
    metric: "92",
    secondary: "tracked signals",
    cards: ["Price profiles", "Order depth", "Opportunity scanner"],
  },
  projects: {
    metric: "7",
    secondary: "active projects",
    cards: ["Project portfolio", "Reservations", "Shopping lists"],
  },
  pi: {
    metric: "14",
    secondary: "synthetic colonies",
    cards: ["Colony timers", "Route balance", "P0–P4 planning"],
  },
} as const;
