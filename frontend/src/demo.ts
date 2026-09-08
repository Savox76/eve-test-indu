export const demoMetadata = {
  synthetic: true,
  scenario: "Three fictional characters in two locally named account groups.",
  generatedAt: "2026-09-08T07:42:00Z",
} as const;

export type CharacterId = "mara-venn" | "elias-torv" | "nera-sol";
export type OverviewScopeId = "all" | CharacterId;
export type CharacterRole = "manufacturing" | "research" | "planetary";

export interface DemoCharacter {
  id: CharacterId;
  name: string;
  role: CharacterRole;
  dataAgeMinutes: number;
  readinessDelta: number;
}

export const demoCharacters: readonly DemoCharacter[] = [
  { id: "mara-venn", name: "Mara Venn", role: "manufacturing", dataAgeMinutes: 4, readinessDelta: 8 },
  { id: "elias-torv", name: "Elias Torv", role: "research", dataAgeMinutes: 6, readinessDelta: 2 },
  { id: "nera-sol", name: "Nera Sol", role: "planetary", dataAgeMinutes: 9, readinessDelta: 5 },
];

export const accountGroups = [
  {
    id: "industry-core",
    label: "Industry Core",
    characterIds: ["mara-venn", "elias-torv"],
  },
  {
    id: "pi-network",
    label: "PI Network",
    characterIds: ["nera-sol"],
  },
] as const satisfies ReadonlyArray<{
  id: string;
  label: string;
  characterIds: readonly CharacterId[];
}>;

type MetricId = "assets" | "jobs" | "readiness" | "attention";
type MetricTrend = "up" | "steady" | "warn";

interface OverviewMetric {
  id: MetricId;
  value: string;
  unit: string;
  delta: string;
  trend: MetricTrend;
  points: readonly number[];
}

const points = {
  assets: [22, 27, 25, 31, 34, 38, 41, 47, 45, 53, 59, 63],
  jobs: [33, 38, 42, 38, 44, 48, 52, 55, 52, 57, 61, 59],
  readiness: [24, 26, 31, 34, 38, 39, 45, 47, 52, 57, 61, 67],
  attention: [58, 53, 59, 55, 48, 51, 44, 42, 46, 38, 35, 31],
} as const;

export const overviewMetrics: Record<OverviewScopeId, readonly OverviewMetric[]> = {
  all: [
    { id: "assets", value: "18.42 B", unit: "ISK", delta: "+2.8%", trend: "up", points: points.assets },
    { id: "jobs", value: "12", unit: "24 slots", delta: "3 end soon", trend: "steady", points: points.jobs },
    { id: "readiness", value: "84", unit: "%", delta: "+6 pts", trend: "up", points: points.readiness },
    { id: "attention", value: "4", unit: "signals", delta: "2 urgent", trend: "warn", points: points.attention },
  ],
  "mara-venn": [
    { id: "assets", value: "9.80 B", unit: "ISK", delta: "+3.1%", trend: "up", points: points.assets },
    { id: "jobs", value: "7", unit: "10 slots", delta: "1 ends soon", trend: "steady", points: points.jobs },
    { id: "readiness", value: "91", unit: "%", delta: "+8 pts", trend: "up", points: points.readiness },
    { id: "attention", value: "1", unit: "signal", delta: "1 urgent", trend: "warn", points: points.attention },
  ],
  "elias-torv": [
    { id: "assets", value: "5.37 B", unit: "ISK", delta: "+1.4%", trend: "up", points: points.assets },
    { id: "jobs", value: "3", unit: "8 slots", delta: "1 ends soon", trend: "steady", points: points.jobs },
    { id: "readiness", value: "76", unit: "%", delta: "+2 pts", trend: "up", points: points.readiness },
    { id: "attention", value: "2", unit: "signals", delta: "0 urgent", trend: "warn", points: points.attention },
  ],
  "nera-sol": [
    { id: "assets", value: "3.25 B", unit: "ISK", delta: "+4.2%", trend: "up", points: points.assets },
    { id: "jobs", value: "2", unit: "6 slots", delta: "1 ends soon", trend: "steady", points: points.jobs },
    { id: "readiness", value: "68", unit: "%", delta: "+5 pts", trend: "up", points: points.readiness },
    { id: "attention", value: "1", unit: "signal", delta: "1 urgent", trend: "warn", points: points.attention },
  ],
};

export const productionStages = [
  {
    ownerId: "mara-venn",
    name: "Asterion Relay",
    detail: "42 of 60 units",
    progress: 70,
    status: "active",
    eta: "5h 18m",
  },
  {
    ownerId: "elias-torv",
    name: "Vesper Field Array",
    detail: "Materials reserved",
    progress: 36,
    status: "active",
    eta: "1d 4h",
  },
  {
    ownerId: "nera-sol",
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
    ownerId: "mara-venn",
    kind: "complete",
    title: "Orion Frame batch completed",
    detail: "8 units moved to Borealis Hangar",
    time: "14 min",
  },
  {
    ownerId: "elias-torv",
    kind: "market",
    title: "Purchase window detected",
    detail: "Synthetic alloy basket is 6.4% below profile",
    time: "39 min",
  },
  {
    ownerId: "nera-sol",
    kind: "sync",
    title: "Asset snapshot refreshed",
    detail: "1,284 fictional positions reconciled",
    time: "1h",
  },
] as const;

export const attentionItems = [
  {
    ownerId: "nera-sol",
    severity: "critical",
    title: "Nereid extraction cycle",
    detail: "Ends in 2h 12m",
    action: "Review PI",
  },
  {
    ownerId: "mara-venn",
    severity: "warning",
    title: "Borealis structure access",
    detail: "Location details unavailable",
    action: "Inspect",
  },
  {
    ownerId: "elias-torv",
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
