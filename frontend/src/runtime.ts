import { invoke, isTauri } from "@tauri-apps/api/core";

export type LocalDataState =
  | "loading"
  | "refreshing"
  | "empty"
  | "fresh"
  | "stale"
  | "offline"
  | "error";

export type LastSyncStatus = "never" | "running" | "completed" | "failed" | "cancelled";
export type UpdateChannel = "stable" | "beta" | "preview";
export type FontScale = "very-small" | "small" | "normal" | "large" | "very-large";
export type ManifestState = "checking" | "verified" | "invalid" | "unavailable";
export type SsoLoginState =
  | "idle"
  | "waiting"
  | "exchanging"
  | "connected"
  | "cancelled"
  | "timed-out"
  | "failed";
export type SsoScopePackage =
  | "industry-core"
  | "market"
  | "planetary-industry"
  | "projects"
  | "private-structures";

export interface LocalDataStatus {
  state: LocalDataState;
  hasCachedData: boolean;
  observedAt: string | null;
  expiresAt: string | null;
  ageSeconds: number | null;
  lastSyncStatus: LastSyncStatus;
  errorCode: string | null;
}

export interface UpdaterStatus {
  channel: UpdateChannel;
  manifestState: ManifestState;
  publicDistribution: false;
}

export interface AppearanceStatus {
  fontScale: FontScale;
}

export interface EveCharacterIdentity {
  characterId: number;
  name: string;
  scopes: string[];
}

export type CredentialState = "stored" | "missing" | "unavailable";
export type ScopePackageState = "granted" | "partial" | "missing";

export interface ScopePackageStatus {
  id: SsoScopePackage;
  status: ScopePackageState;
  grantedCount: number;
  requiredCount: number;
}

export interface EveCharacter extends EveCharacterIdentity {
  alias: string | null;
  accountGroupId: number | null;
  accountGroupLabel: string | null;
  enabled: boolean;
  credentialState: CredentialState;
  scopePackages: ScopePackageStatus[];
}

export interface AccountGroup {
  id: number;
  label: string;
  sortOrder: number;
  characterCount: number;
}

export interface CharacterUpdate {
  alias: string | null;
  accountGroupId: number | null;
  enabled: boolean;
}

export type AssetLocationStatus =
  | "resolved"
  | "restricted"
  | "unresolved"
  | "cycle"
  | "pending";

export interface AssetLocationNode {
  locationId: number;
  kind: string;
  name: string | null;
  access: string;
  typeId: number | null;
}

export interface AssetRecord {
  itemId: number;
  typeId: number;
  typeName: string;
  quantity: number;
  ownerCharacterId: number;
  ownerName: string;
  locationFlag: string;
  locationStatus: AssetLocationStatus;
  locationPath: string;
  locationNodes: AssetLocationNode[];
  observedAt: string;
  ageSeconds: number;
}

export interface AssetOwner {
  characterId: number;
  name: string;
}

export interface AssetQuery {
  search: string;
  ownerCharacterId: number | null;
  locationStatus: AssetLocationStatus | null;
  offset: number;
  limit: number;
  sortBy: AssetSortField;
  sortDirection: SortDirection;
}

export type AssetSortField = "type" | "owner" | "location" | "flag" | "quantity" | "age";
export type SortDirection = "asc" | "desc";
export const assetSortFields: AssetSortField[] = ["type", "owner", "location", "flag", "quantity", "age"];

export interface AssetPage {
  items: AssetRecord[];
  total: number;
  quantityTotal: number;
  offset: number;
  limit: number;
  owners: AssetOwner[];
  locationStatuses: AssetLocationStatus[];
  observedAt: string | null;
  ageSeconds: number | null;
}

export interface AssetCsvExport {
  filename: string;
  relativePath: string;
  rows: number;
}

export interface AssetSyncResult {
  characters: Array<{
    characterId: number;
    status: "completed" | "failed";
    pages: number;
    assets: number;
    resolved: number;
    restricted: number;
    unresolved: number;
    cycles: number;
    errorCode: string | null;
  }>;
  completed: number;
  failed: number;
  assets: number;
}

export type BlueprintKind = "original" | "copy";
export type BlueprintSortField = "type" | "owner" | "kind" | "me" | "te" | "runs" | "age";
export const blueprintSortFields: BlueprintSortField[] = ["type", "owner", "kind", "me", "te", "runs", "age"];
export const blueprintPageSize = 100;

export interface BlueprintRecord {
  itemId: number;
  typeId: number;
  typeName: string;
  ownerCharacterId: number;
  ownerName: string;
  kind: BlueprintKind;
  materialEfficiency: number;
  timeEfficiency: number;
  runs: number;
  locationId: number;
  locationFlag: string;
  observedAt: string;
  ageSeconds: number;
}

export interface BlueprintQuery {
  search: string;
  ownerCharacterId: number | null;
  kind: BlueprintKind | null;
  offset: number;
  limit: number;
  sortBy: BlueprintSortField;
  sortDirection: SortDirection;
}

export interface BlueprintPage {
  items: BlueprintRecord[];
  total: number;
  offset: number;
  limit: number;
  owners: AssetOwner[];
  observedAt: string | null;
  ageSeconds: number | null;
}

export interface BlueprintSyncResult {
  characters: Array<{
    characterId: number;
    status: "completed" | "failed";
    pages: number;
    blueprints: number;
    errorCode: string | null;
  }>;
  completed: number;
  failed: number;
  blueprints: number;
}

export type AssetDeltaChangeType = "added" | "removed" | "quantity" | "location";
export type AssetDeltaDirection = "inbound" | "outbound" | "neutral";

export interface AssetDeltaCorrelation {
  state: "linked" | "ambiguous" | "unmatched" | "unavailable" | "not-applicable";
  key: string;
  direction: AssetDeltaDirection;
  windowStart: string;
  windowEnd: string;
  jobIds: number[];
  candidateCount: number;
  locationMatched: boolean;
}

export interface AssetDeltaRecord {
  eventId: string;
  itemId: number;
  typeId: number;
  typeName: string;
  ownerCharacterId: number;
  ownerName: string;
  changeTypes: AssetDeltaChangeType[];
  quantityBefore: number | null;
  quantityAfter: number | null;
  quantityDelta: number;
  locationIdBefore: number | null;
  locationIdAfter: number | null;
  locationTypeBefore: string | null;
  locationTypeAfter: string | null;
  locationFlagBefore: string | null;
  locationFlagAfter: string | null;
  previousAssetSnapshotId: number;
  currentAssetSnapshotId: number;
  currentAssetSyncRunId: number;
  observedAt: string;
  ageSeconds: number;
  jobCorrelation: AssetDeltaCorrelation;
}

export interface AssetDeltaQuery {
  search: string;
  ownerCharacterId: number | null;
  changeType: AssetDeltaChangeType | null;
  offset: number;
  limit: number;
}

export interface AssetDeltaPage {
  items: AssetDeltaRecord[];
  total: number;
  offset: number;
  limit: number;
  owners: AssetOwner[];
  changeTypes: AssetDeltaChangeType[];
  summary: Record<AssetDeltaChangeType, number>;
  hasBaseline: boolean;
  observedAt: string | null;
  ageSeconds: number | null;
}

export type IndustryJobStatus = "active" | "cancelled" | "delivered" | "paused" | "ready" | "reverted";
export type IndustryActivityId = 1 | 3 | 4 | 5 | 7 | 8 | 9 | 11;
export type IndustryActivityKey = "manufacturing" | "research-time" | "research-material" | "copying" | "reverse-engineering" | "invention" | "reactions";
export type IndustryCorrelationState = "linked" | "partial" | "ambiguous" | "unmatched" | "pending";
export type IndustryJobSortField = "start" | "end" | "type" | "owner" | "activity" | "status" | "runs" | "cost" | "correlation" | "age";
export const industryJobStatuses: readonly IndustryJobStatus[] = ["active", "cancelled", "delivered", "paused", "ready", "reverted"];
export const industryActivityIds: readonly IndustryActivityId[] = [1, 3, 4, 5, 7, 8, 9, 11];
export const industryCorrelationStates: readonly IndustryCorrelationState[] = ["linked", "partial", "ambiguous", "unmatched", "pending"];
export const industryJobSortFields: readonly IndustryJobSortField[] = ["start", "end", "type", "owner", "activity", "status", "runs", "cost", "correlation", "age"];
export const industryJobPageSize = 100;

export interface IndustryJobRecord {
  jobId: number;
  ownerCharacterId: number;
  ownerName: string;
  activityId: IndustryActivityId;
  activityKey: IndustryActivityKey;
  status: IndustryJobStatus;
  blueprintItemId: number;
  blueprintTypeId: number;
  blueprintName: string;
  productTypeId: number | null;
  productName: string | null;
  runs: number;
  successfulRuns: number | null;
  licensedRuns: number | null;
  probability: number | null;
  cost: number | null;
  durationSeconds: number;
  facilityId: number;
  stationId: number;
  blueprintLocationId: number;
  outputLocationId: number;
  startDate: string;
  endDate: string;
  completedDate: string | null;
  pauseDate: string | null;
  blueprintCorrelation: {
    state: "current" | "historical" | "unmatched" | "unavailable";
    snapshotId: number | null;
    syncRunId: number | null;
    observedAt: string | null;
  };
  assetCorrelation: {
    state: "linked" | "ambiguous" | "unmatched" | "unavailable" | "pending" | "not-applicable";
    eventIds: string[];
    candidateCount: number;
    locationMatched: boolean;
  };
  correlationState: IndustryCorrelationState;
  jobSnapshotId: number;
  jobSyncRunId: number;
  observedAt: string;
  ageSeconds: number;
}

export interface IndustryJobQuery {
  search: string;
  ownerCharacterId: number | null;
  status: IndustryJobStatus | null;
  activityId: IndustryActivityId | null;
  correlation: IndustryCorrelationState | null;
  offset: number;
  limit: number;
  sortBy: IndustryJobSortField;
  sortDirection: SortDirection;
}

export interface IndustryJobPage {
  items: IndustryJobRecord[];
  total: number;
  activeTotal: number;
  offset: number;
  limit: number;
  owners: AssetOwner[];
  statuses: IndustryJobStatus[];
  activities: IndustryActivityId[];
  correlations: IndustryCorrelationState[];
  observedAt: string | null;
  ageSeconds: number | null;
}

export interface IndustryJobSyncResult {
  characters: Array<{
    characterId: number;
    status: "completed" | "failed";
    jobs: number;
    active: number;
    completedJobs: number;
    errorCode: string | null;
  }>;
  completed: number;
  failed: number;
  jobs: number;
  active: number;
  completedJobs: number;
}

export type CharacterSkillActiveState = "normal" | "limited" | "boosted";
export type CharacterSkillSortField = "skill" | "owner" | "trained" | "active" | "skillpoints" | "age";
export const characterSkillLevels = [0, 1, 2, 3, 4, 5] as const;
export const characterSkillActiveStates: readonly CharacterSkillActiveState[] = ["normal", "limited", "boosted"];
export const characterSkillSortFields: readonly CharacterSkillSortField[] = ["skill", "owner", "trained", "active", "skillpoints", "age"];
export const characterSkillPageSize = 100;

export interface CharacterSkillRecord {
  skillId: number;
  skillName: string;
  ownerCharacterId: number;
  ownerName: string;
  trainedLevel: number;
  activeLevel: number;
  skillpoints: number;
  activeState: CharacterSkillActiveState;
  snapshotId: number;
  syncRunId: number;
  observedAt: string;
  ageSeconds: number;
}

export interface CharacterSkillQuery {
  search: string;
  ownerCharacterId: number | null;
  trainedLevel: number | null;
  activeState: CharacterSkillActiveState | null;
  offset: number;
  limit: number;
  sortBy: CharacterSkillSortField;
  sortDirection: SortDirection;
}

export interface CharacterSkillPage {
  items: CharacterSkillRecord[];
  total: number;
  totalSp: number;
  unallocatedSp: number;
  offset: number;
  limit: number;
  owners: AssetOwner[];
  levels: number[];
  activeStates: CharacterSkillActiveState[];
  observedAt: string | null;
  ageSeconds: number | null;
}

export interface CharacterSkillSyncResult {
  characters: Array<{
    characterId: number;
    status: "completed" | "failed";
    skills: number;
    totalSp: number;
    unallocatedSp: number;
    errorCode: string | null;
  }>;
  completed: number;
  failed: number;
  skills: number;
  totalSp: number;
  unallocatedSp: number;
}

export interface SsoLoginStatus {
  state: SsoLoginState;
  attemptId: string | null;
  scopePackages: SsoScopePackage[];
  expiresAt: string | null;
  errorCode: string | null;
  character: EveCharacterIdentity | null;
}

export type DesktopRuntimeStatus =
  | { state: "checking" }
  | { state: "preview" }
  | { state: "unavailable" }
  | {
      state: "ready";
      version: string;
      desktopShell: true;
      singleInstance: true;
      sidecar: "starting" | "ready" | "error";
      database: "starting" | "ready" | "error";
      databaseLocation: "data/foundry.sqlite3";
      schemaVersion: number | null;
      errorCode: string | null;
      data: LocalDataStatus;
      updater: UpdaterStatus;
      appearance: AppearanceStatus;
    };

export interface RuntimeAdapter {
  isAvailable: () => boolean;
  invoke: (command: string, arguments_?: Record<string, unknown>) => Promise<string>;
}

const tauriAdapter: RuntimeAdapter = {
  isAvailable: isTauri,
  invoke: (command, arguments_) => invoke<string>(command, arguments_),
};

const localDataStates: readonly LocalDataState[] = [
  "loading",
  "refreshing",
  "empty",
  "fresh",
  "stale",
  "offline",
  "error",
];
const lastSyncStatuses: readonly LastSyncStatus[] = [
  "never",
  "running",
  "completed",
  "failed",
  "cancelled",
];
const updateChannels: readonly UpdateChannel[] = ["stable", "beta", "preview"];
export const fontScales: readonly FontScale[] = [
  "very-small",
  "small",
  "normal",
  "large",
  "very-large",
];
const manifestStates: readonly ManifestState[] = [
  "checking",
  "verified",
  "invalid",
  "unavailable",
];
const ssoLoginStates: readonly SsoLoginState[] = [
  "idle",
  "waiting",
  "exchanging",
  "connected",
  "cancelled",
  "timed-out",
  "failed",
];
export const ssoScopePackages: readonly SsoScopePackage[] = [
  "industry-core",
  "market",
  "planetary-industry",
  "projects",
  "private-structures",
];

const scopePackageRequirements: Readonly<Record<SsoScopePackage, number>> = {
  "industry-core": 4,
  market: 2,
  "planetary-industry": 1,
  projects: 1,
  "private-structures": 1,
};
const credentialStates: readonly CredentialState[] = ["stored", "missing", "unavailable"];
const scopePackageStates: readonly ScopePackageState[] = ["granted", "partial", "missing"];
export const assetLocationStatuses: readonly AssetLocationStatus[] = [
  "resolved",
  "restricted",
  "unresolved",
  "cycle",
  "pending",
];
export const assetPageSize = 100;
export const assetDeltaChangeTypes: readonly AssetDeltaChangeType[] = [
  "added",
  "removed",
  "quantity",
  "location",
];
export const assetDeltaPageSize = 50;

export const initialRuntimeStatus: DesktopRuntimeStatus = { state: "checking" };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isNullableText(value: unknown): value is string | null {
  return value === null || (typeof value === "string" && value.trim().length > 0);
}

function parseLocalDataStatus(candidate: unknown): LocalDataStatus {
  if (
    !isRecord(candidate) ||
    typeof candidate.state !== "string" ||
    !localDataStates.includes(candidate.state as LocalDataState) ||
    typeof candidate.hasCachedData !== "boolean" ||
    !isNullableText(candidate.observedAt) ||
    !isNullableText(candidate.expiresAt) ||
    (candidate.ageSeconds !== null &&
      (!Number.isInteger(candidate.ageSeconds) || Number(candidate.ageSeconds) < 0)) ||
    typeof candidate.lastSyncStatus !== "string" ||
    !lastSyncStatuses.includes(candidate.lastSyncStatus as LastSyncStatus) ||
    !isNullableText(candidate.errorCode)
  ) {
    throw new Error("The native runtime returned invalid local-data metadata.");
  }

  const data = candidate as unknown as LocalDataStatus;
  const cacheFieldsAreValid = data.hasCachedData
    ? data.observedAt !== null
    : data.observedAt === null && data.expiresAt === null && data.ageSeconds === null;
  const stateCombinationIsValid = (() => {
    switch (data.state) {
      case "loading":
      case "empty":
        return !data.hasCachedData && data.errorCode === null;
      case "refreshing":
      case "stale":
        return data.hasCachedData && data.ageSeconds !== null && data.errorCode === null;
      case "fresh":
        return (
          data.hasCachedData &&
          data.ageSeconds !== null &&
          data.expiresAt !== null &&
          data.errorCode === null
        );
      case "offline":
      case "error":
        return data.errorCode !== null;
    }
  })();
  if (!cacheFieldsAreValid || !stateCombinationIsValid) {
    throw new Error("The native runtime returned inconsistent local-data metadata.");
  }
  return data;
}

function parseUpdaterStatus(candidate: unknown): UpdaterStatus {
  if (
    !isRecord(candidate) ||
    typeof candidate.channel !== "string" ||
    !updateChannels.includes(candidate.channel as UpdateChannel) ||
    typeof candidate.manifestState !== "string" ||
    !manifestStates.includes(candidate.manifestState as ManifestState) ||
    candidate.publicDistribution !== false
  ) {
    throw new Error("The native runtime returned invalid updater metadata.");
  }
  return candidate as unknown as UpdaterStatus;
}

function parseAppearanceStatus(candidate: unknown): AppearanceStatus {
  if (
    !isRecord(candidate) ||
    typeof candidate.fontScale !== "string" ||
    !fontScales.includes(candidate.fontScale as FontScale)
  ) {
    throw new Error("The native runtime returned invalid appearance metadata.");
  }
  return candidate as unknown as AppearanceStatus;
}

function parseEveCharacterIdentity(candidate: unknown): EveCharacterIdentity {
  if (
    !isRecord(candidate) ||
    !Number.isSafeInteger(candidate.characterId) ||
    Number(candidate.characterId) <= 0 ||
    typeof candidate.name !== "string" ||
    candidate.name.trim() !== candidate.name ||
    candidate.name.length < 1 ||
    candidate.name.length > 100 ||
    !Array.isArray(candidate.scopes) ||
    candidate.scopes.length < 1 ||
    !candidate.scopes.every(
      (scope) => typeof scope === "string" && scope.startsWith("esi-") && scope.endsWith(".v1"),
    ) ||
    new Set(candidate.scopes).size !== candidate.scopes.length
  ) {
    throw new Error("The native runtime returned invalid EVE character metadata.");
  }
  return candidate as unknown as EveCharacterIdentity;
}

function parseEveCharacter(candidate: unknown): EveCharacter {
  const identity = parseEveCharacterIdentity(candidate);
  if (
    !isRecord(candidate) ||
    (candidate.alias !== null &&
      (typeof candidate.alias !== "string" ||
        candidate.alias.trim() !== candidate.alias ||
        candidate.alias.length < 1 ||
        candidate.alias.length > 80)) ||
    (candidate.accountGroupId !== null &&
      (!Number.isSafeInteger(candidate.accountGroupId) || Number(candidate.accountGroupId) <= 0)) ||
    !(candidate.accountGroupLabel === null ||
      (typeof candidate.accountGroupLabel === "string" &&
        candidate.accountGroupLabel.trim() === candidate.accountGroupLabel &&
        candidate.accountGroupLabel.length >= 1 &&
        candidate.accountGroupLabel.length <= 80)) ||
    typeof candidate.enabled !== "boolean" ||
    typeof candidate.credentialState !== "string" ||
    !credentialStates.includes(candidate.credentialState as CredentialState) ||
    !Array.isArray(candidate.scopePackages) ||
    candidate.scopePackages.length !== ssoScopePackages.length
  ) {
    throw new Error("The native runtime returned invalid EVE character metadata.");
  }

  const scopePackages = candidate.scopePackages.map((value): ScopePackageStatus => {
    if (
      !isRecord(value) ||
      typeof value.id !== "string" ||
      !ssoScopePackages.includes(value.id as SsoScopePackage) ||
      typeof value.status !== "string" ||
      !scopePackageStates.includes(value.status as ScopePackageState) ||
      !Number.isSafeInteger(value.grantedCount) ||
      !Number.isSafeInteger(value.requiredCount)
    ) {
      throw new Error("The native runtime returned invalid EVE character metadata.");
    }
    const status = value as unknown as ScopePackageStatus;
    const expectedRequired = scopePackageRequirements[status.id];
    const expectedState = status.grantedCount === 0
      ? "missing"
      : status.grantedCount === status.requiredCount
        ? "granted"
        : "partial";
    if (
      status.requiredCount !== expectedRequired ||
      status.grantedCount < 0 ||
      status.grantedCount > status.requiredCount ||
      status.status !== expectedState
    ) {
      throw new Error("The native runtime returned inconsistent scope-package metadata.");
    }
    return status;
  });
  if (
    new Set(scopePackages.map(({ id }) => id)).size !== ssoScopePackages.length ||
    !ssoScopePackages.every((id) => scopePackages.some((scopePackage) => scopePackage.id === id))
  ) {
    throw new Error("The native runtime returned duplicate or incomplete scope-package metadata.");
  }
  if ((candidate.accountGroupId === null) !== (candidate.accountGroupLabel === null)) {
    throw new Error("The native runtime returned inconsistent account-group metadata.");
  }
  return { ...candidate, ...identity, scopePackages } as unknown as EveCharacter;
}

function parseAccountGroup(candidate: unknown): AccountGroup {
  if (
    !isRecord(candidate) ||
    !Number.isSafeInteger(candidate.id) ||
    Number(candidate.id) <= 0 ||
    typeof candidate.label !== "string" ||
    candidate.label.trim() !== candidate.label ||
    candidate.label.length < 1 ||
    candidate.label.length > 80 ||
    !Number.isSafeInteger(candidate.sortOrder) ||
    Number(candidate.sortOrder) < 0 ||
    !Number.isSafeInteger(candidate.characterCount) ||
    Number(candidate.characterCount) < 0
  ) {
    throw new Error("The native runtime returned invalid account-group metadata.");
  }
  return candidate as unknown as AccountGroup;
}

function isPositiveSafeInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && Number(value) > 0;
}

function isNonNegativeSafeInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && Number(value) >= 0;
}

function isSignedSafeInteger(value: unknown): value is number {
  return Number.isSafeInteger(value);
}

function isBoundedText(value: unknown, maximum: number): value is string {
  return typeof value === "string" && value.trim() === value && value.length >= 1 && value.length <= maximum;
}

function parseAssetLocationNode(candidate: unknown): AssetLocationNode {
  if (
    !isRecord(candidate) ||
    !isPositiveSafeInteger(candidate.locationId) ||
    !isBoundedText(candidate.kind, 40) ||
    !(candidate.name === null || isBoundedText(candidate.name, 200)) ||
    !isBoundedText(candidate.access, 40) ||
    !(candidate.typeId === null || isPositiveSafeInteger(candidate.typeId))
  ) {
    throw new Error("The native runtime returned invalid asset-location metadata.");
  }
  return candidate as unknown as AssetLocationNode;
}

function parseAssetRecord(candidate: unknown): AssetRecord {
  if (
    !isRecord(candidate) ||
    !isPositiveSafeInteger(candidate.itemId) ||
    !isPositiveSafeInteger(candidate.typeId) ||
    !isBoundedText(candidate.typeName, 200) ||
    !isNonNegativeSafeInteger(candidate.quantity) ||
    !isPositiveSafeInteger(candidate.ownerCharacterId) ||
    !isBoundedText(candidate.ownerName, 100) ||
    !isBoundedText(candidate.locationFlag, 100) ||
    typeof candidate.locationStatus !== "string" ||
    !assetLocationStatuses.includes(candidate.locationStatus as AssetLocationStatus) ||
    typeof candidate.locationPath !== "string" ||
    candidate.locationPath.length > 20_000 ||
    !Array.isArray(candidate.locationNodes) ||
    candidate.locationNodes.length > 64 ||
    !isBoundedText(candidate.observedAt, 50) ||
    !isNonNegativeSafeInteger(candidate.ageSeconds)
  ) {
    throw new Error("The native runtime returned invalid asset metadata.");
  }
  const locationNodes = candidate.locationNodes.map(parseAssetLocationNode);
  if (
    (candidate.locationStatus === "pending" &&
      (candidate.locationPath !== "" || locationNodes.length !== 0)) ||
    (candidate.locationStatus !== "pending" &&
      (candidate.locationPath === "" || locationNodes.length === 0))
  ) {
    throw new Error("The native runtime returned inconsistent asset-location metadata.");
  }
  return { ...candidate, locationNodes } as unknown as AssetRecord;
}

function parseAssetPage(candidate: unknown): AssetPage {
  if (
    !isRecord(candidate) ||
    !Array.isArray(candidate.items) ||
    !isNonNegativeSafeInteger(candidate.total) ||
    !isNonNegativeSafeInteger(candidate.quantityTotal) ||
    !isNonNegativeSafeInteger(candidate.offset) ||
    !Number.isSafeInteger(candidate.limit) ||
    Number(candidate.limit) < 1 ||
    Number(candidate.limit) > 200 ||
    !Array.isArray(candidate.owners) ||
    !Array.isArray(candidate.locationStatuses) ||
    candidate.locationStatuses.length !== assetLocationStatuses.length ||
    !assetLocationStatuses.every((status) =>
      (candidate.locationStatuses as unknown[]).includes(status)) ||
    !(candidate.observedAt === null || isBoundedText(candidate.observedAt, 50)) ||
    !(candidate.ageSeconds === null || isNonNegativeSafeInteger(candidate.ageSeconds)) ||
    (candidate.observedAt === null) !== (candidate.ageSeconds === null)
  ) {
    throw new Error("The native runtime returned an invalid asset page.");
  }
  const items = candidate.items.map(parseAssetRecord);
  const owners = candidate.owners.map((owner): AssetOwner => {
    if (
      !isRecord(owner) ||
      !isPositiveSafeInteger(owner.characterId) ||
      !isBoundedText(owner.name, 100)
    ) {
      throw new Error("The native runtime returned invalid asset-owner metadata.");
    }
    return owner as unknown as AssetOwner;
  });
  if (
    items.length > Number(candidate.limit) ||
    items.length > Number(candidate.total) ||
    new Set(items.map(({ itemId }) => itemId)).size !== items.length ||
    new Set(owners.map(({ characterId }) => characterId)).size !== owners.length ||
    items.some((item) => !owners.some((owner) => owner.characterId === item.ownerCharacterId))
  ) {
    throw new Error("The native runtime returned inconsistent asset-page metadata.");
  }
  return { ...candidate, items, owners } as unknown as AssetPage;
}

function validateAssetQuery(query: AssetQuery): AssetQuery {
  const search = query.search.trim().replace(/\s+/g, " ");
  if (
    search.length > 120 ||
    !(query.ownerCharacterId === null || isPositiveSafeInteger(query.ownerCharacterId)) ||
    !(query.locationStatus === null || assetLocationStatuses.includes(query.locationStatus)) ||
    !isNonNegativeSafeInteger(query.offset) ||
    !Number.isSafeInteger(query.limit) ||
    query.limit < 1 ||
    query.limit > 200
    || !assetSortFields.includes(query.sortBy)
    || !["asc", "desc"].includes(query.sortDirection)
  ) {
    throw new Error("The asset query is invalid.");
  }
  return { ...query, search };
}

function parseNullablePositiveInteger(value: unknown): number | null {
  if (value === null) return null;
  if (!isPositiveSafeInteger(value)) {
    throw new Error("The native runtime returned invalid asset-delta identifiers.");
  }
  return value;
}

function parseNullableQuantity(value: unknown): number | null {
  if (value === null) return null;
  if (!isNonNegativeSafeInteger(value)) {
    throw new Error("The native runtime returned invalid asset-delta quantities.");
  }
  return value;
}

function parseNullableBoundedText(value: unknown, maximum: number): string | null {
  if (value === null) return null;
  if (!isBoundedText(value, maximum)) {
    throw new Error("The native runtime returned invalid asset-delta text.");
  }
  return value;
}

function parseAssetDeltaRecord(candidate: unknown): AssetDeltaRecord {
  if (
    !isRecord(candidate) ||
    typeof candidate.eventId !== "string" ||
    !/^[0-9a-f]{64}$/.test(candidate.eventId) ||
    !isPositiveSafeInteger(candidate.itemId) ||
    !isPositiveSafeInteger(candidate.typeId) ||
    !isBoundedText(candidate.typeName, 220) ||
    !isPositiveSafeInteger(candidate.ownerCharacterId) ||
    !isBoundedText(candidate.ownerName, 100) ||
    !Array.isArray(candidate.changeTypes) ||
    candidate.changeTypes.length < 1 ||
    candidate.changeTypes.length > 2 ||
    !candidate.changeTypes.every(
      (value) => typeof value === "string" &&
        assetDeltaChangeTypes.includes(value as AssetDeltaChangeType),
    ) ||
    new Set(candidate.changeTypes).size !== candidate.changeTypes.length ||
    !isSignedSafeInteger(candidate.quantityDelta) ||
    !isPositiveSafeInteger(candidate.previousAssetSnapshotId) ||
    !isPositiveSafeInteger(candidate.currentAssetSnapshotId) ||
    !isPositiveSafeInteger(candidate.currentAssetSyncRunId) ||
    !isBoundedText(candidate.observedAt, 64) ||
    !isNonNegativeSafeInteger(candidate.ageSeconds) ||
    !isRecord(candidate.jobCorrelation) ||
    !["linked", "ambiguous", "unmatched", "unavailable", "not-applicable"].includes(String(candidate.jobCorrelation.state)) ||
    !isBoundedText(candidate.jobCorrelation.key, 64) ||
    !["inbound", "outbound", "neutral"].includes(String(candidate.jobCorrelation.direction)) ||
    !isBoundedText(candidate.jobCorrelation.windowStart, 64) ||
    !isBoundedText(candidate.jobCorrelation.windowEnd, 64) ||
    !Array.isArray(candidate.jobCorrelation.jobIds) ||
    candidate.jobCorrelation.jobIds.length > 20 ||
    !candidate.jobCorrelation.jobIds.every(isPositiveSafeInteger) ||
    new Set(candidate.jobCorrelation.jobIds).size !== candidate.jobCorrelation.jobIds.length ||
    !isNonNegativeSafeInteger(candidate.jobCorrelation.candidateCount) ||
    typeof candidate.jobCorrelation.locationMatched !== "boolean"
  ) {
    throw new Error("The native runtime returned invalid asset-delta metadata.");
  }
  const quantityBefore = parseNullableQuantity(candidate.quantityBefore);
  const quantityAfter = parseNullableQuantity(candidate.quantityAfter);
  const locationIdBefore = parseNullablePositiveInteger(candidate.locationIdBefore);
  const locationIdAfter = parseNullablePositiveInteger(candidate.locationIdAfter);
  const locationTypeBefore = parseNullableBoundedText(candidate.locationTypeBefore, 40);
  const locationTypeAfter = parseNullableBoundedText(candidate.locationTypeAfter, 40);
  const locationFlagBefore = parseNullableBoundedText(candidate.locationFlagBefore, 100);
  const locationFlagAfter = parseNullableBoundedText(candidate.locationFlagAfter, 100);
  const changeTypes = candidate.changeTypes as AssetDeltaChangeType[];
  const locationChanged =
    locationIdBefore !== locationIdAfter ||
    locationTypeBefore !== locationTypeAfter ||
    locationFlagBefore !== locationFlagAfter;
  const expectedDirection = candidate.quantityDelta > 0
    ? "inbound"
    : candidate.quantityDelta < 0
      ? "outbound"
      : "neutral";
  if (
    candidate.quantityDelta !== (quantityAfter ?? 0) - (quantityBefore ?? 0) ||
    candidate.jobCorrelation.key !== `${candidate.ownerCharacterId}:${candidate.typeId}` ||
    candidate.jobCorrelation.direction !== expectedDirection ||
    (candidate.jobCorrelation.state === "linked" &&
      (candidate.jobCorrelation.candidateCount !== 1 || candidate.jobCorrelation.jobIds.length !== 1)) ||
    (candidate.jobCorrelation.state === "ambiguous" &&
      (candidate.jobCorrelation.candidateCount < 2 || candidate.jobCorrelation.jobIds.length < 1)) ||
    (["unmatched", "unavailable", "not-applicable"].includes(String(candidate.jobCorrelation.state)) &&
      (candidate.jobCorrelation.candidateCount !== 0 || candidate.jobCorrelation.jobIds.length !== 0 || candidate.jobCorrelation.locationMatched)) ||
    changeTypes.includes("added") !== (quantityBefore === null && quantityAfter !== null) ||
    changeTypes.includes("removed") !== (quantityBefore !== null && quantityAfter === null) ||
    changeTypes.includes("quantity") !==
      (quantityBefore !== null && quantityAfter !== null && candidate.quantityDelta !== 0) ||
    changeTypes.includes("location") !==
      (quantityBefore !== null && quantityAfter !== null && locationChanged)
  ) {
    throw new Error("The native runtime returned inconsistent asset-delta metadata.");
  }
  return {
    ...candidate,
    quantityBefore,
    quantityAfter,
    locationIdBefore,
    locationIdAfter,
    locationTypeBefore,
    locationTypeAfter,
    locationFlagBefore,
    locationFlagAfter,
  } as unknown as AssetDeltaRecord;
}

function parseAssetDeltaPage(candidate: unknown): AssetDeltaPage {
  if (
    !isRecord(candidate) ||
    !Array.isArray(candidate.items) ||
    !isNonNegativeSafeInteger(candidate.total) ||
    !isNonNegativeSafeInteger(candidate.offset) ||
    !Number.isSafeInteger(candidate.limit) ||
    Number(candidate.limit) < 1 ||
    Number(candidate.limit) > 200 ||
    !Array.isArray(candidate.owners) ||
    !Array.isArray(candidate.changeTypes) ||
    candidate.changeTypes.length !== assetDeltaChangeTypes.length ||
    !assetDeltaChangeTypes.every((type) =>
      (candidate.changeTypes as unknown[]).includes(type)) ||
    !isRecord(candidate.summary) ||
    !assetDeltaChangeTypes.every((type) =>
      isNonNegativeSafeInteger((candidate.summary as Record<string, unknown>)[type]) &&
      Number((candidate.summary as Record<string, unknown>)[type]) <= Number(candidate.total)) ||
    typeof candidate.hasBaseline !== "boolean" ||
    !(candidate.observedAt === null || isBoundedText(candidate.observedAt, 64)) ||
    !(candidate.ageSeconds === null || isNonNegativeSafeInteger(candidate.ageSeconds)) ||
    (candidate.observedAt === null) !== (candidate.ageSeconds === null) ||
    candidate.hasBaseline !== (candidate.observedAt !== null)
  ) {
    throw new Error("The native runtime returned an invalid asset-delta page.");
  }
  const items = candidate.items.map(parseAssetDeltaRecord);
  const owners = candidate.owners.map((owner): AssetOwner => {
    if (!isRecord(owner) || !isPositiveSafeInteger(owner.characterId) || !isBoundedText(owner.name, 100)) {
      throw new Error("The native runtime returned invalid asset-delta owners.");
    }
    return owner as unknown as AssetOwner;
  });
  if (
    items.length > Number(candidate.limit) ||
    items.length > Number(candidate.total) ||
    new Set(items.map(({ eventId }) => eventId)).size !== items.length ||
    new Set(owners.map(({ characterId }) => characterId)).size !== owners.length ||
    items.some((item) => !owners.some((owner) => owner.characterId === item.ownerCharacterId))
  ) {
    throw new Error("The native runtime returned inconsistent asset-delta page metadata.");
  }
  return { ...candidate, items, owners } as unknown as AssetDeltaPage;
}

function validateAssetDeltaQuery(query: AssetDeltaQuery): AssetDeltaQuery {
  const search = query.search.trim().replace(/\s+/g, " ");
  if (
    search.length > 120 ||
    !(query.ownerCharacterId === null || isPositiveSafeInteger(query.ownerCharacterId)) ||
    !(query.changeType === null || assetDeltaChangeTypes.includes(query.changeType)) ||
    !isNonNegativeSafeInteger(query.offset) ||
    !Number.isSafeInteger(query.limit) ||
    query.limit < 1 ||
    query.limit > 200
  ) {
    throw new Error("The asset-delta query is invalid.");
  }
  return { ...query, search };
}

function parseSsoLoginStatus(candidate: unknown): SsoLoginStatus {
  if (
    !isRecord(candidate) ||
    typeof candidate.state !== "string" ||
    !ssoLoginStates.includes(candidate.state as SsoLoginState) ||
    !isNullableText(candidate.attemptId) ||
    !Array.isArray(candidate.scopePackages) ||
    !candidate.scopePackages.every(
      (value) => typeof value === "string" && ssoScopePackages.includes(value as SsoScopePackage),
    ) ||
    new Set(candidate.scopePackages).size !== candidate.scopePackages.length ||
    !isNullableText(candidate.expiresAt) ||
    !isNullableText(candidate.errorCode) ||
    !(candidate.character === null || isRecord(candidate.character))
  ) {
    throw new Error("The native runtime returned invalid SSO metadata.");
  }

  const status = candidate as unknown as SsoLoginStatus;
  const attemptFieldsAreValid = status.state === "idle"
    ? status.attemptId === null && status.scopePackages.length === 0 && status.expiresAt === null
    : status.attemptId !== null && status.scopePackages.length > 0 && status.expiresAt !== null;
  const errorIsValid = status.state === "timed-out"
    ? status.errorCode === "login-timeout"
    : status.state === "failed"
      ? [
          "authorization-denied", "authorization-failed", "callback-invalid",
          "pkce-state-missing", "sso-metadata-unavailable", "sso-metadata-invalid",
          "token-request-invalid", "token-exchange-failed", "token-response-invalid",
          "jwks-unavailable", "jwks-invalid", "jwt-malformed", "jwt-header-invalid",
          "jwt-key-not-found", "jwt-signature-invalid", "jwt-claims-invalid", "jwt-expired",
          "jwt-identity-invalid", "jwt-scopes-missing", "character-save-failed",
        ].includes(status.errorCode ?? "")
      : status.errorCode === null;
  const characterIsValid = status.state === "connected"
    ? status.character !== null && (() => {
        try {
          parseEveCharacterIdentity(status.character);
          return true;
        } catch {
          return false;
        }
      })()
    : status.character === null;
  if (!attemptFieldsAreValid || !errorIsValid || !characterIsValid) {
    throw new Error("The native runtime returned inconsistent SSO metadata.");
  }
  return status;
}

function parseReadyStatus(rawStatus: string): DesktopRuntimeStatus {
  const candidate: unknown = JSON.parse(rawStatus);
  if (
    !isRecord(candidate) ||
    candidate.state !== "ready" ||
    typeof candidate.version !== "string" ||
    candidate.version.trim().length === 0 ||
    candidate.desktopShell !== true ||
    candidate.singleInstance !== true ||
    !["starting", "ready", "error"].includes(String(candidate.sidecar)) ||
    !["starting", "ready", "error"].includes(String(candidate.database)) ||
    candidate.databaseLocation !== "data/foundry.sqlite3" ||
    (candidate.schemaVersion !== null &&
      (!Number.isInteger(candidate.schemaVersion) || Number(candidate.schemaVersion) < 1)) ||
    !isNullableText(candidate.errorCode)
  ) {
    throw new Error("The native runtime returned an invalid status payload.");
  }

  const sidecar = candidate.sidecar as "starting" | "ready" | "error";
  const database = candidate.database as "starting" | "ready" | "error";
  const schemaVersion = candidate.schemaVersion as number | null;
  const errorCode = candidate.errorCode as string | null;
  const data = parseLocalDataStatus(candidate.data);
  const updater = parseUpdaterStatus(candidate.updater);
  const appearance = parseAppearanceStatus(candidate.appearance);
  const hasValidStateCombination =
    (sidecar === "starting" &&
      database === "starting" &&
      schemaVersion === null &&
      errorCode === null &&
      data.state === "loading" &&
      updater.manifestState === "checking") ||
    (sidecar === "ready" &&
      database === "ready" &&
      schemaVersion !== null &&
      errorCode === null &&
      ["verified", "invalid"].includes(updater.manifestState)) ||
    (sidecar === "error" &&
      database === "error" &&
      schemaVersion === null &&
      errorCode !== null &&
      data.state === "error" &&
      updater.manifestState === "unavailable");
  if (!hasValidStateCombination) {
    throw new Error("The native runtime returned an inconsistent status payload.");
  }

  return {
    state: "ready",
    version: candidate.version,
    desktopShell: true,
    singleInstance: true,
    sidecar,
    database,
    databaseLocation: "data/foundry.sqlite3",
    schemaVersion,
    errorCode,
    data,
    updater,
    appearance,
  };
}

export async function loadDesktopRuntimeStatus(
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<DesktopRuntimeStatus> {
  try {
    if (!adapter.isAvailable()) {
      return { state: "preview" };
    }

    const rawStatus = await adapter.invoke("desktop_runtime_status");
    return parseReadyStatus(rawStatus);
  } catch {
    return { state: "unavailable" };
  }
}

export async function setDesktopUpdateChannel(
  channel: UpdateChannel,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<UpdaterStatus> {
  if (!adapter.isAvailable()) {
    throw new Error("The desktop updater is unavailable in browser preview mode.");
  }
  const rawStatus = await adapter.invoke("set_update_channel", { channel });
  const status = parseUpdaterStatus(JSON.parse(rawStatus));
  if (status.channel !== channel) {
    throw new Error("The desktop updater returned a different channel.");
  }
  return status;
}

export async function setDesktopFontScale(
  fontScale: FontScale,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<AppearanceStatus> {
  if (!fontScales.includes(fontScale)) {
    throw new Error("The selected font scale is unsupported.");
  }
  if (!adapter.isAvailable()) {
    return { fontScale };
  }
  const status = parseAppearanceStatus(
    JSON.parse(await adapter.invoke("set_font_scale", { fontScale })),
  );
  if (status.fontScale !== fontScale) {
    throw new Error("The desktop runtime returned a different font scale.");
  }
  return status;
}

export async function loadEveCharacters(
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<EveCharacter[]> {
  if (!adapter.isAvailable()) return [];
  const candidate: unknown = JSON.parse(await adapter.invoke("list_eve_characters"));
  if (!isRecord(candidate) || !Array.isArray(candidate.characters)) {
    throw new Error("The native runtime returned an invalid character list.");
  }
  const characters = candidate.characters.map(parseEveCharacter);
  if (new Set(characters.map((character) => character.characterId)).size !== characters.length) {
    throw new Error("The native runtime returned duplicate EVE characters.");
  }
  return characters;
}

async function invokeSsoCommand(
  command: string,
  adapter: RuntimeAdapter,
  arguments_?: Record<string, unknown>,
): Promise<SsoLoginStatus> {
  if (!adapter.isAvailable()) {
    throw new Error("EVE SSO is available only in the desktop application.");
  }
  return parseSsoLoginStatus(JSON.parse(await adapter.invoke(command, arguments_)));
}

export async function startEveSso(
  scopePackages: SsoScopePackage[],
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<SsoLoginStatus> {
  if (!adapter.isAvailable()) {
    throw new Error("EVE SSO is available only in the desktop application.");
  }
  if (
    scopePackages.length !== ssoScopePackages.length ||
    new Set(scopePackages).size !== scopePackages.length ||
    !scopePackages.every((value, index) => value === ssoScopePackages[index])
  ) {
    throw new Error("Every required SSO scope package must be requested automatically.");
  }
  const status = await invokeSsoCommand("start_eve_sso", adapter, { scopePackages });
  if (status.state !== "waiting") {
    throw new Error("The EVE SSO attempt did not start waiting for a callback.");
  }
  return status;
}

export async function loadEveSsoStatus(
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<SsoLoginStatus> {
  return invokeSsoCommand("eve_sso_status", adapter);
}

export async function cancelEveSso(
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<SsoLoginStatus> {
  const status = await invokeSsoCommand("cancel_eve_sso", adapter);
  if (!["idle", "cancelled"].includes(status.state)) {
    throw new Error("The EVE SSO attempt was not cancelled.");
  }
  return status;
}


export async function loadAccountGroups(
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<AccountGroup[]> {
  if (!adapter.isAvailable()) return [];
  const candidate: unknown = JSON.parse(await adapter.invoke("list_account_groups"));
  if (!isRecord(candidate) || !Array.isArray(candidate.groups)) {
    throw new Error("The native runtime returned an invalid account-group list.");
  }
  const groups = candidate.groups.map(parseAccountGroup);
  if (new Set(groups.map(({ id }) => id)).size !== groups.length) {
    throw new Error("The native runtime returned duplicate account groups.");
  }
  return groups;
}

export async function loadAssets(
  query: AssetQuery,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<AssetPage> {
  const validated = validateAssetQuery(query);
  if (!adapter.isAvailable()) {
    return {
      items: [],
      total: 0,
      quantityTotal: 0,
      offset: validated.offset,
      limit: validated.limit,
      owners: [],
      locationStatuses: [...assetLocationStatuses],
      observedAt: null,
      ageSeconds: null,
    };
  }
  const page = parseAssetPage(
    JSON.parse(await adapter.invoke("query_assets", {
      search: validated.search,
      ownerCharacterId: validated.ownerCharacterId,
      locationStatus: validated.locationStatus,
      sortBy: validated.sortBy,
      sortDirection: validated.sortDirection,
      offset: validated.offset,
      limit: validated.limit,
    })),
  );
  if (page.offset !== validated.offset || page.limit !== validated.limit) {
    throw new Error("The native runtime returned a different asset window.");
  }
  return page;
}

export async function syncAssets(
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<AssetSyncResult> {
  if (!adapter.isAvailable()) {
    throw new Error("Asset sync is available only in the desktop application.");
  }
  const candidate: unknown = JSON.parse(await adapter.invoke("sync_assets"));
  if (
    !isRecord(candidate) ||
    !Array.isArray(candidate.characters) ||
    !isNonNegativeSafeInteger(candidate.completed) ||
    !isNonNegativeSafeInteger(candidate.failed) ||
    !isNonNegativeSafeInteger(candidate.assets)
  ) {
    throw new Error("The native runtime returned an invalid asset-sync result.");
  }
  const characters = candidate.characters.map((value) => {
    if (
      !isRecord(value) ||
      !Number.isSafeInteger(value.characterId) ||
      Number(value.characterId) <= 0 ||
      !["completed", "failed"].includes(String(value.status)) ||
      !["pages", "assets", "resolved", "restricted", "unresolved", "cycles"].every(
        (key) => isNonNegativeSafeInteger(value[key]),
      ) ||
      !(value.errorCode === null || (typeof value.errorCode === "string" && value.errorCode.length <= 120))
    ) {
      throw new Error("The native runtime returned an invalid asset-sync result.");
    }
    return value as unknown as AssetSyncResult["characters"][number];
  });
  if (
    candidate.completed + candidate.failed !== characters.length ||
    candidate.assets !== characters.reduce((total, character) => total + character.assets, 0)
  ) {
    throw new Error("The native runtime returned an inconsistent asset-sync result.");
  }
  return { ...candidate, characters } as AssetSyncResult;
}

function validateBlueprintQuery(query: BlueprintQuery): BlueprintQuery {
  const search = query.search.trim().replace(/\s+/g, " ");
  if (
    search.length > 120 ||
    !(query.ownerCharacterId === null || isPositiveSafeInteger(query.ownerCharacterId)) ||
    !(query.kind === null || ["original", "copy"].includes(query.kind)) ||
    !isNonNegativeSafeInteger(query.offset) ||
    !Number.isSafeInteger(query.limit) || query.limit < 1 || query.limit > 200 ||
    !blueprintSortFields.includes(query.sortBy) ||
    !["asc", "desc"].includes(query.sortDirection)
  ) throw new Error("The blueprint query is invalid.");
  return { ...query, search };
}

function parseBlueprintPage(candidate: unknown): BlueprintPage {
  if (
    !isRecord(candidate) || !Array.isArray(candidate.items) || !Array.isArray(candidate.owners) ||
    !isNonNegativeSafeInteger(candidate.total) || !isNonNegativeSafeInteger(candidate.offset) ||
    !Number.isSafeInteger(candidate.limit) || Number(candidate.limit) < 1 || Number(candidate.limit) > 200 ||
    !(candidate.observedAt === null || isBoundedText(candidate.observedAt, 64)) ||
    !(candidate.ageSeconds === null || isNonNegativeSafeInteger(candidate.ageSeconds)) ||
    (candidate.observedAt === null) !== (candidate.ageSeconds === null)
  ) throw new Error("The native runtime returned invalid blueprint data.");
  const owners = candidate.owners.map((owner) => {
    if (!isRecord(owner) || !isPositiveSafeInteger(owner.characterId) || !isBoundedText(owner.name, 100)) {
      throw new Error("The native runtime returned invalid blueprint owners.");
    }
    return owner as unknown as AssetOwner;
  });
  const items = candidate.items.map((item) => {
    if (
      !isRecord(item) || !isPositiveSafeInteger(item.itemId) || !isPositiveSafeInteger(item.typeId) ||
      !isBoundedText(item.typeName, 220) || !isPositiveSafeInteger(item.ownerCharacterId) ||
      !isBoundedText(item.ownerName, 100) || !["original", "copy"].includes(String(item.kind)) ||
      !Number.isInteger(item.materialEfficiency) || Number(item.materialEfficiency) < 0 || Number(item.materialEfficiency) > 10 ||
      !Number.isInteger(item.timeEfficiency) || Number(item.timeEfficiency) < 0 || Number(item.timeEfficiency) > 20 ||
      !Number.isSafeInteger(item.runs) || Number(item.runs) < -1 ||
      !isPositiveSafeInteger(item.locationId) || !isBoundedText(item.locationFlag, 100) ||
      !isBoundedText(item.observedAt, 64) || !isNonNegativeSafeInteger(item.ageSeconds)
    ) throw new Error("The native runtime returned invalid blueprint records.");
    return item as unknown as BlueprintRecord;
  });
  if (
    items.length > Number(candidate.limit) || items.length > Number(candidate.total) ||
    new Set(items.map(({ itemId }) => itemId)).size !== items.length ||
    new Set(owners.map(({ characterId }) => characterId)).size !== owners.length ||
    items.some((item) => !owners.some((owner) => owner.characterId === item.ownerCharacterId))
  ) throw new Error("The native runtime returned inconsistent blueprint data.");
  return { ...candidate, items, owners } as unknown as BlueprintPage;
}

export async function loadBlueprints(
  query: BlueprintQuery,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<BlueprintPage> {
  const validated = validateBlueprintQuery(query);
  if (!adapter.isAvailable()) return {
    items: [], total: 0, offset: validated.offset, limit: validated.limit,
    owners: [], observedAt: null, ageSeconds: null,
  };
  const page = parseBlueprintPage(JSON.parse(await adapter.invoke("query_blueprints", {
    search: validated.search,
    ownerCharacterId: validated.ownerCharacterId,
    kind: validated.kind,
    offset: validated.offset,
    limit: validated.limit,
    sortBy: validated.sortBy,
    sortDirection: validated.sortDirection,
  })));
  if (page.offset !== validated.offset || page.limit !== validated.limit) {
    throw new Error("The native runtime returned a different blueprint window.");
  }
  return page;
}

export async function syncBlueprints(
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<BlueprintSyncResult> {
  if (!adapter.isAvailable()) throw new Error("Blueprint sync is available only in the desktop application.");
  const candidate: unknown = JSON.parse(await adapter.invoke("sync_blueprints"));
  if (!isRecord(candidate) || !Array.isArray(candidate.characters) ||
    !isNonNegativeSafeInteger(candidate.completed) || !isNonNegativeSafeInteger(candidate.failed) ||
    !isNonNegativeSafeInteger(candidate.blueprints)) {
    throw new Error("The native runtime returned an invalid blueprint-sync result.");
  }
  const characters = candidate.characters.map((value) => {
    if (!isRecord(value) || !isPositiveSafeInteger(value.characterId) ||
      !["completed", "failed"].includes(String(value.status)) ||
      !isNonNegativeSafeInteger(value.pages) || !isNonNegativeSafeInteger(value.blueprints) ||
      !(value.errorCode === null || (typeof value.errorCode === "string" && value.errorCode.length <= 120))) {
      throw new Error("The native runtime returned an invalid blueprint-sync result.");
    }
    return value as unknown as BlueprintSyncResult["characters"][number];
  });
  if (candidate.completed + candidate.failed !== characters.length ||
    candidate.blueprints !== characters.reduce((sum, value) => sum + value.blueprints, 0)) {
    throw new Error("The native runtime returned an inconsistent blueprint-sync result.");
  }
  return { ...candidate, characters } as unknown as BlueprintSyncResult;
}

const industryActivityKeys: Readonly<Record<IndustryActivityId, IndustryActivityKey>> = {
  1: "manufacturing",
  3: "research-time",
  4: "research-material",
  5: "copying",
  7: "reverse-engineering",
  8: "invention",
  9: "reactions",
  11: "reactions",
};

function validateIndustryJobQuery(query: IndustryJobQuery): IndustryJobQuery {
  const search = query.search.trim().replace(/\s+/g, " ");
  if (
    search.length > 120 ||
    !(query.ownerCharacterId === null || isPositiveSafeInteger(query.ownerCharacterId)) ||
    !(query.status === null || industryJobStatuses.includes(query.status)) ||
    !(query.activityId === null || industryActivityIds.includes(query.activityId)) ||
    !(query.correlation === null || industryCorrelationStates.includes(query.correlation)) ||
    !isNonNegativeSafeInteger(query.offset) ||
    !Number.isSafeInteger(query.limit) || query.limit < 1 || query.limit > 200 ||
    !industryJobSortFields.includes(query.sortBy) ||
    !["asc", "desc"].includes(query.sortDirection)
  ) {
    throw new Error("The industry-job query is invalid.");
  }
  return { ...query, search };
}

function parseIndustryJobRecord(candidate: unknown): IndustryJobRecord {
  if (
    !isRecord(candidate) ||
    !isPositiveSafeInteger(candidate.jobId) ||
    !isPositiveSafeInteger(candidate.ownerCharacterId) ||
    !isBoundedText(candidate.ownerName, 100) ||
    !industryActivityIds.includes(candidate.activityId as IndustryActivityId) ||
    candidate.activityKey !== industryActivityKeys[candidate.activityId as IndustryActivityId] ||
    !industryJobStatuses.includes(candidate.status as IndustryJobStatus) ||
    !isPositiveSafeInteger(candidate.blueprintItemId) ||
    !isPositiveSafeInteger(candidate.blueprintTypeId) ||
    !isBoundedText(candidate.blueprintName, 220) ||
    !((candidate.productTypeId === null && candidate.productName === null) ||
      (isPositiveSafeInteger(candidate.productTypeId) && isBoundedText(candidate.productName, 220))) ||
    !isPositiveSafeInteger(candidate.runs) ||
    !(candidate.successfulRuns === null ||
      (isNonNegativeSafeInteger(candidate.successfulRuns) && candidate.successfulRuns <= candidate.runs)) ||
    !(candidate.licensedRuns === null || isNonNegativeSafeInteger(candidate.licensedRuns)) ||
    !(candidate.probability === null ||
      (typeof candidate.probability === "number" && Number.isFinite(candidate.probability) && candidate.probability >= 0 && candidate.probability <= 1)) ||
    !(candidate.cost === null ||
      (typeof candidate.cost === "number" && Number.isFinite(candidate.cost) && candidate.cost >= 0 && Number.isSafeInteger(Math.trunc(candidate.cost)))) ||
    !isNonNegativeSafeInteger(candidate.durationSeconds) ||
    ![candidate.facilityId, candidate.stationId, candidate.blueprintLocationId, candidate.outputLocationId,
      candidate.jobSnapshotId, candidate.jobSyncRunId].every(isPositiveSafeInteger) ||
    !isBoundedText(candidate.startDate, 64) ||
    !isBoundedText(candidate.endDate, 64) ||
    !(candidate.completedDate === null || isBoundedText(candidate.completedDate, 64)) ||
    !(candidate.pauseDate === null || isBoundedText(candidate.pauseDate, 64)) ||
    !isRecord(candidate.blueprintCorrelation) ||
    !["current", "historical", "unmatched", "unavailable"].includes(String(candidate.blueprintCorrelation.state)) ||
    !isRecord(candidate.assetCorrelation) ||
    !["linked", "ambiguous", "unmatched", "unavailable", "pending", "not-applicable"].includes(String(candidate.assetCorrelation.state)) ||
    !Array.isArray(candidate.assetCorrelation.eventIds) ||
    candidate.assetCorrelation.eventIds.length > 20 ||
    !candidate.assetCorrelation.eventIds.every((value) => typeof value === "string" && /^[0-9a-f]{64}$/.test(value)) ||
    new Set(candidate.assetCorrelation.eventIds).size !== candidate.assetCorrelation.eventIds.length ||
    !isNonNegativeSafeInteger(candidate.assetCorrelation.candidateCount) ||
    typeof candidate.assetCorrelation.locationMatched !== "boolean" ||
    !industryCorrelationStates.includes(candidate.correlationState as IndustryCorrelationState) ||
    !isBoundedText(candidate.observedAt, 64) ||
    !isNonNegativeSafeInteger(candidate.ageSeconds)
  ) {
    throw new Error("The native runtime returned invalid industry-job records.");
  }
  const blueprintLinked = ["current", "historical"].includes(String(candidate.blueprintCorrelation.state));
  const blueprintHasEvidence = candidate.blueprintCorrelation.snapshotId !== null ||
    candidate.blueprintCorrelation.syncRunId !== null || candidate.blueprintCorrelation.observedAt !== null;
  const assetState = String(candidate.assetCorrelation.state);
  const assetLinked = assetState === "linked";
  const expectedCorrelation = ["active", "paused", "ready"].includes(String(candidate.status))
    ? "pending"
    : assetState === "ambiguous"
      ? "ambiguous"
      : blueprintLinked && (assetLinked || assetState === "not-applicable")
        ? "linked"
        : blueprintLinked || assetLinked
          ? "partial"
          : "unmatched";
  if (
    (blueprintLinked !== blueprintHasEvidence) ||
    (blueprintLinked && (!isPositiveSafeInteger(candidate.blueprintCorrelation.snapshotId) ||
      !isPositiveSafeInteger(candidate.blueprintCorrelation.syncRunId) ||
      !isBoundedText(candidate.blueprintCorrelation.observedAt, 64))) ||
    (assetState === "linked" &&
      (candidate.assetCorrelation.candidateCount !== 1 || candidate.assetCorrelation.eventIds.length !== 1)) ||
    (assetState === "ambiguous" &&
      (candidate.assetCorrelation.candidateCount < 2 || candidate.assetCorrelation.eventIds.length < 1)) ||
    (["unmatched", "unavailable", "pending", "not-applicable"].includes(assetState) &&
      (candidate.assetCorrelation.candidateCount !== 0 || candidate.assetCorrelation.eventIds.length !== 0 || candidate.assetCorrelation.locationMatched)) ||
    candidate.correlationState !== expectedCorrelation
  ) {
    throw new Error("The native runtime returned inconsistent industry-job records.");
  }
  return candidate as unknown as IndustryJobRecord;
}

function parseIndustryJobPage(candidate: unknown): IndustryJobPage {
  if (
    !isRecord(candidate) || !Array.isArray(candidate.items) || !Array.isArray(candidate.owners) ||
    !Array.isArray(candidate.statuses) || !Array.isArray(candidate.activities) ||
    !Array.isArray(candidate.correlations) || !isNonNegativeSafeInteger(candidate.total) ||
    !isNonNegativeSafeInteger(candidate.activeTotal) || candidate.activeTotal > candidate.total ||
    !isNonNegativeSafeInteger(candidate.offset) || !Number.isSafeInteger(candidate.limit) ||
    Number(candidate.limit) < 1 || Number(candidate.limit) > 200 ||
    candidate.statuses.length !== industryJobStatuses.length ||
    !industryJobStatuses.every((value, index) => (candidate.statuses as unknown[])[index] === value) ||
    candidate.correlations.length !== industryCorrelationStates.length ||
    !industryCorrelationStates.every((value, index) => (candidate.correlations as unknown[])[index] === value) ||
    !candidate.activities.every((value) => industryActivityIds.includes(value as IndustryActivityId)) ||
    new Set(candidate.activities).size !== candidate.activities.length ||
    !(candidate.observedAt === null || isBoundedText(candidate.observedAt, 64)) ||
    !(candidate.ageSeconds === null || isNonNegativeSafeInteger(candidate.ageSeconds)) ||
    (candidate.observedAt === null) !== (candidate.ageSeconds === null)
  ) {
    throw new Error("The native runtime returned invalid industry-job data.");
  }
  const items = candidate.items.map(parseIndustryJobRecord);
  const owners = candidate.owners.map((owner) => {
    if (!isRecord(owner) || !isPositiveSafeInteger(owner.characterId) || !isBoundedText(owner.name, 100)) {
      throw new Error("The native runtime returned invalid industry-job owners.");
    }
    return owner as unknown as AssetOwner;
  });
  if (
    items.length > Number(candidate.limit) || items.length > Number(candidate.total) ||
    items.filter(({ status }) => ["active", "paused", "ready"].includes(status)).length >
      Number(candidate.activeTotal) ||
    new Set(items.map(({ jobId }) => jobId)).size !== items.length ||
    new Set(owners.map(({ characterId }) => characterId)).size !== owners.length ||
    items.some((item) => !owners.some((owner) => owner.characterId === item.ownerCharacterId && owner.name === item.ownerName))
  ) {
    throw new Error("The native runtime returned inconsistent industry-job data.");
  }
  return { ...candidate, items, owners } as unknown as IndustryJobPage;
}

export async function loadIndustryJobs(
  query: IndustryJobQuery,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<IndustryJobPage> {
  const validated = validateIndustryJobQuery(query);
  if (!adapter.isAvailable()) return {
    items: [], total: 0, activeTotal: 0, offset: validated.offset, limit: validated.limit,
    owners: [], statuses: [...industryJobStatuses], activities: [],
    correlations: [...industryCorrelationStates], observedAt: null, ageSeconds: null,
  };
  const page = parseIndustryJobPage(JSON.parse(await adapter.invoke("query_industry_jobs", {
    search: validated.search,
    ownerCharacterId: validated.ownerCharacterId,
    status: validated.status,
    activityId: validated.activityId,
    correlation: validated.correlation,
    offset: validated.offset,
    limit: validated.limit,
    sortBy: validated.sortBy,
    sortDirection: validated.sortDirection,
  })));
  if (page.offset !== validated.offset || page.limit !== validated.limit) {
    throw new Error("The native runtime returned a different industry-job window.");
  }
  return page;
}

export async function syncIndustryJobs(
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<IndustryJobSyncResult> {
  if (!adapter.isAvailable()) {
    throw new Error("Industry-job sync is available only in the desktop application.");
  }
  const candidate: unknown = JSON.parse(await adapter.invoke("sync_industry_jobs"));
  if (
    !isRecord(candidate) || !Array.isArray(candidate.characters) ||
    ![candidate.completed, candidate.failed, candidate.jobs, candidate.active,
      candidate.completedJobs].every(isNonNegativeSafeInteger)
  ) {
    throw new Error("The native runtime returned an invalid industry-job sync result.");
  }
  const characters = candidate.characters.map((value) => {
    if (
      !isRecord(value) || !isPositiveSafeInteger(value.characterId) ||
      !["completed", "failed"].includes(String(value.status)) ||
      ![value.jobs, value.active, value.completedJobs].every(isNonNegativeSafeInteger) ||
      Number(value.active) + Number(value.completedJobs) !== Number(value.jobs) ||
      !((value.status === "completed" && value.errorCode === null) ||
        (value.status === "failed" && value.jobs === 0 && value.active === 0 &&
          value.completedJobs === 0 && isBoundedText(value.errorCode, 120)))
    ) {
      throw new Error("The native runtime returned an invalid industry-job sync result.");
    }
    return value as unknown as IndustryJobSyncResult["characters"][number];
  });
  if (
    Number(candidate.completed) + Number(candidate.failed) !== characters.length ||
    candidate.jobs !== characters.reduce((sum, value) => sum + value.jobs, 0) ||
    candidate.active !== characters.reduce((sum, value) => sum + value.active, 0) ||
    candidate.completedJobs !== characters.reduce((sum, value) => sum + value.completedJobs, 0)
  ) {
    throw new Error("The native runtime returned an inconsistent industry-job sync result.");
  }
  return { ...candidate, characters } as unknown as IndustryJobSyncResult;
}

function validateCharacterSkillQuery(query: CharacterSkillQuery): CharacterSkillQuery {
  const search = query.search.trim().replace(/\s+/g, " ");
  if (
    search.length > 120 ||
    !(query.ownerCharacterId === null || isPositiveSafeInteger(query.ownerCharacterId)) ||
    !(query.trainedLevel === null || characterSkillLevels.includes(query.trainedLevel as 0 | 1 | 2 | 3 | 4 | 5)) ||
    !(query.activeState === null || characterSkillActiveStates.includes(query.activeState)) ||
    !isNonNegativeSafeInteger(query.offset) ||
    !Number.isSafeInteger(query.limit) || query.limit < 1 || query.limit > 200 ||
    !characterSkillSortFields.includes(query.sortBy) ||
    !["asc", "desc"].includes(query.sortDirection)
  ) {
    throw new Error("The character-skill query is invalid.");
  }
  return { ...query, search };
}

function parseCharacterSkillPage(candidate: unknown): CharacterSkillPage {
  if (
    !isRecord(candidate) || !Array.isArray(candidate.items) || !Array.isArray(candidate.owners) ||
    !Array.isArray(candidate.levels) || !Array.isArray(candidate.activeStates) ||
    ![candidate.total, candidate.totalSp, candidate.unallocatedSp, candidate.offset].every(isNonNegativeSafeInteger) ||
    !Number.isSafeInteger(candidate.limit) || Number(candidate.limit) < 1 || Number(candidate.limit) > 200 ||
    candidate.levels.length !== characterSkillLevels.length ||
    !characterSkillLevels.every((value, index) => (candidate.levels as unknown[])[index] === value) ||
    candidate.activeStates.length !== characterSkillActiveStates.length ||
    !characterSkillActiveStates.every((value, index) => (candidate.activeStates as unknown[])[index] === value) ||
    !(candidate.observedAt === null || isBoundedText(candidate.observedAt, 64)) ||
    !(candidate.ageSeconds === null || isNonNegativeSafeInteger(candidate.ageSeconds)) ||
    (candidate.observedAt === null) !== (candidate.ageSeconds === null)
  ) {
    throw new Error("The native runtime returned invalid character-skill data.");
  }
  const owners = candidate.owners.map((owner) => {
    if (!isRecord(owner) || !isPositiveSafeInteger(owner.characterId) || !isBoundedText(owner.name, 100)) {
      throw new Error("The native runtime returned invalid character-skill owners.");
    }
    return owner as unknown as AssetOwner;
  });
  const items = candidate.items.map((item) => {
    if (
      !isRecord(item) || !isPositiveSafeInteger(item.skillId) || !isBoundedText(item.skillName, 220) ||
      !isPositiveSafeInteger(item.ownerCharacterId) || !isBoundedText(item.ownerName, 100) ||
      !Number.isInteger(item.trainedLevel) || Number(item.trainedLevel) < 0 || Number(item.trainedLevel) > 5 ||
      !Number.isInteger(item.activeLevel) || Number(item.activeLevel) < 0 || Number(item.activeLevel) > 5 ||
      !isNonNegativeSafeInteger(item.skillpoints) ||
      !characterSkillActiveStates.includes(item.activeState as CharacterSkillActiveState) ||
      !isPositiveSafeInteger(item.snapshotId) || !isPositiveSafeInteger(item.syncRunId) ||
      !isBoundedText(item.observedAt, 64) || !isNonNegativeSafeInteger(item.ageSeconds)
    ) {
      throw new Error("The native runtime returned invalid character-skill records.");
    }
    const expectedState = Number(item.activeLevel) < Number(item.trainedLevel)
      ? "limited"
      : Number(item.activeLevel) > Number(item.trainedLevel) ? "boosted" : "normal";
    if (item.activeState !== expectedState) {
      throw new Error("The native runtime returned inconsistent character-skill records.");
    }
    return item as unknown as CharacterSkillRecord;
  });
  if (
    items.length > Number(candidate.limit) || items.length > Number(candidate.total) ||
    new Set(owners.map(({ characterId }) => characterId)).size !== owners.length ||
    new Set(items.map(({ ownerCharacterId, skillId }) => `${ownerCharacterId}:${skillId}`)).size !== items.length ||
    items.some((item) => !owners.some((owner) => owner.characterId === item.ownerCharacterId && owner.name === item.ownerName))
  ) {
    throw new Error("The native runtime returned inconsistent character-skill data.");
  }
  return { ...candidate, items, owners } as unknown as CharacterSkillPage;
}

export async function loadCharacterSkills(
  query: CharacterSkillQuery,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<CharacterSkillPage> {
  const validated = validateCharacterSkillQuery(query);
  if (!adapter.isAvailable()) return {
    items: [], total: 0, totalSp: 0, unallocatedSp: 0,
    offset: validated.offset, limit: validated.limit, owners: [],
    levels: [...characterSkillLevels], activeStates: [...characterSkillActiveStates],
    observedAt: null, ageSeconds: null,
  };
  const page = parseCharacterSkillPage(JSON.parse(await adapter.invoke("query_character_skills", {
    search: validated.search,
    ownerCharacterId: validated.ownerCharacterId,
    trainedLevel: validated.trainedLevel,
    activeState: validated.activeState,
    offset: validated.offset,
    limit: validated.limit,
    sortBy: validated.sortBy,
    sortDirection: validated.sortDirection,
  })));
  if (page.offset !== validated.offset || page.limit !== validated.limit) {
    throw new Error("The native runtime returned a different character-skill window.");
  }
  return page;
}

export async function syncCharacterSkills(
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<CharacterSkillSyncResult> {
  if (!adapter.isAvailable()) {
    throw new Error("Character-skill sync is available only in the desktop application.");
  }
  const candidate: unknown = JSON.parse(await adapter.invoke("sync_character_skills"));
  if (
    !isRecord(candidate) || !Array.isArray(candidate.characters) ||
    ![candidate.completed, candidate.failed, candidate.skills, candidate.totalSp,
      candidate.unallocatedSp].every(isNonNegativeSafeInteger)
  ) {
    throw new Error("The native runtime returned an invalid character-skill sync result.");
  }
  const characters = candidate.characters.map((value) => {
    if (
      !isRecord(value) || !isPositiveSafeInteger(value.characterId) ||
      !["completed", "failed"].includes(String(value.status)) ||
      ![value.skills, value.totalSp, value.unallocatedSp].every(isNonNegativeSafeInteger) ||
      !((value.status === "completed" && value.errorCode === null) ||
        (value.status === "failed" && value.skills === 0 && value.totalSp === 0 &&
          value.unallocatedSp === 0 && isBoundedText(value.errorCode, 120)))
    ) {
      throw new Error("The native runtime returned an invalid character-skill sync result.");
    }
    return value as unknown as CharacterSkillSyncResult["characters"][number];
  });
  if (
    Number(candidate.completed) + Number(candidate.failed) !== characters.length ||
    candidate.skills !== characters.reduce((sum, value) => sum + value.skills, 0) ||
    candidate.totalSp !== characters.reduce((sum, value) => sum + value.totalSp, 0) ||
    candidate.unallocatedSp !== characters.reduce((sum, value) => sum + value.unallocatedSp, 0)
  ) {
    throw new Error("The native runtime returned an inconsistent character-skill sync result.");
  }
  return { ...candidate, characters } as unknown as CharacterSkillSyncResult;
}

export async function exportAssetsCsv(
  query: Omit<AssetQuery, "offset" | "limit">,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<AssetCsvExport> {
  if (!adapter.isAvailable()) {
    throw new Error("Asset export is available only in the desktop application.");
  }
  const validated = validateAssetQuery({ ...query, offset: 0, limit: assetPageSize });
  const candidate: unknown = JSON.parse(
    await adapter.invoke("export_assets_csv", {
      search: validated.search,
      ownerCharacterId: validated.ownerCharacterId,
      locationStatus: validated.locationStatus,
      sortBy: validated.sortBy,
      sortDirection: validated.sortDirection,
    }),
  );
  if (
    !isRecord(candidate) ||
    typeof candidate.filename !== "string" ||
    !/^[a-z0-9][a-z0-9.-]*\.csv$/i.test(candidate.filename) ||
    candidate.filename.length > 80 ||
    candidate.relativePath !== `data/exports/${candidate.filename}` ||
    !isNonNegativeSafeInteger(candidate.rows)
  ) {
    throw new Error("The native runtime returned invalid asset-export metadata.");
  }
  return candidate as unknown as AssetCsvExport;
}

export async function loadAssetDeltas(
  query: AssetDeltaQuery,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<AssetDeltaPage> {
  const validated = validateAssetDeltaQuery(query);
  if (!adapter.isAvailable()) {
    return {
      items: [],
      total: 0,
      offset: validated.offset,
      limit: validated.limit,
      owners: [],
      changeTypes: [...assetDeltaChangeTypes],
      summary: { added: 0, removed: 0, quantity: 0, location: 0 },
      hasBaseline: false,
      observedAt: null,
      ageSeconds: null,
    };
  }
  const page = parseAssetDeltaPage(
    JSON.parse(await adapter.invoke("query_asset_deltas", {
      search: validated.search,
      ownerCharacterId: validated.ownerCharacterId,
      changeType: validated.changeType,
      offset: validated.offset,
      limit: validated.limit,
    })),
  );
  if (page.offset !== validated.offset || page.limit !== validated.limit) {
    throw new Error("The native runtime returned a different asset-delta window.");
  }
  return page;
}

function requireDesktopAdapter(adapter: RuntimeAdapter): void {
  if (!adapter.isAvailable()) {
    throw new Error("Character management is available only in the desktop application.");
  }
}

function requirePositiveIdentifier(value: number, field: string): void {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new Error(`${field} must be a positive integer.`);
  }
}

export async function updateEveCharacter(
  characterId: number,
  update: CharacterUpdate,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<EveCharacter> {
  requireDesktopAdapter(adapter);
  requirePositiveIdentifier(characterId, "Character ID");
  if (
    (update.alias !== null &&
      (typeof update.alias !== "string" ||
        update.alias.trim() !== update.alias ||
        update.alias.length < 1 ||
        update.alias.length > 80)) ||
    (update.accountGroupId !== null &&
      (!Number.isSafeInteger(update.accountGroupId) || update.accountGroupId <= 0)) ||
    typeof update.enabled !== "boolean"
  ) {
    throw new Error("The character update is invalid.");
  }
  const candidate: unknown = JSON.parse(
    await adapter.invoke("update_eve_character", {
      characterId,
      alias: update.alias,
      accountGroupId: update.accountGroupId,
      enabled: update.enabled,
    }),
  );
  if (!isRecord(candidate) || !isRecord(candidate.character)) {
    throw new Error("The native runtime returned an invalid character update.");
  }
  return parseEveCharacter(candidate.character);
}

export async function deleteEveCharacter(
  characterId: number,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<void> {
  requireDesktopAdapter(adapter);
  requirePositiveIdentifier(characterId, "Character ID");
  const candidate: unknown = JSON.parse(
    await adapter.invoke("delete_eve_character", { characterId }),
  );
  if (!isRecord(candidate) || candidate.deleted !== true || candidate.characterId !== characterId) {
    throw new Error("The native runtime returned an invalid character deletion.");
  }
}

function validateGroupLabel(label: string): void {
  if (
    typeof label !== "string" ||
    label.trim() !== label ||
    label.length < 1 ||
    label.length > 80
  ) {
    throw new Error("The account-group label is invalid.");
  }
}

export async function createAccountGroup(
  label: string,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<AccountGroup> {
  requireDesktopAdapter(adapter);
  validateGroupLabel(label);
  const candidate: unknown = JSON.parse(
    await adapter.invoke("create_account_group", { label }),
  );
  if (!isRecord(candidate) || !isRecord(candidate.group)) {
    throw new Error("The native runtime returned an invalid account-group update.");
  }
  return parseAccountGroup(candidate.group);
}

export async function renameAccountGroup(
  groupId: number,
  label: string,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<AccountGroup> {
  requireDesktopAdapter(adapter);
  requirePositiveIdentifier(groupId, "Account-group ID");
  validateGroupLabel(label);
  const candidate: unknown = JSON.parse(
    await adapter.invoke("rename_account_group", { groupId, label }),
  );
  if (!isRecord(candidate) || !isRecord(candidate.group)) {
    throw new Error("The native runtime returned an invalid account-group update.");
  }
  return parseAccountGroup(candidate.group);
}

export async function deleteAccountGroup(
  groupId: number,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<void> {
  requireDesktopAdapter(adapter);
  requirePositiveIdentifier(groupId, "Account-group ID");
  const candidate: unknown = JSON.parse(
    await adapter.invoke("delete_account_group", { groupId }),
  );
  if (!isRecord(candidate) || candidate.deleted !== true || candidate.groupId !== groupId) {
    throw new Error("The native runtime returned an invalid account-group deletion.");
  }
}
