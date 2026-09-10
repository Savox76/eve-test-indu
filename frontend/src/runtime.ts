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
}

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

export type AssetDeltaChangeType = "added" | "removed" | "quantity" | "location";
export type AssetDeltaDirection = "inbound" | "outbound" | "neutral";

export interface AssetDeltaCorrelation {
  state: "unmatched";
  key: string;
  direction: AssetDeltaDirection;
  windowStart: string;
  windowEnd: string;
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
    candidate.jobCorrelation.state !== "unmatched" ||
    !isBoundedText(candidate.jobCorrelation.key, 64) ||
    !["inbound", "outbound", "neutral"].includes(String(candidate.jobCorrelation.direction)) ||
    !isBoundedText(candidate.jobCorrelation.windowStart, 64) ||
    !isBoundedText(candidate.jobCorrelation.windowEnd, 64)
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
  if (
    scopePackages.length === 0 ||
    new Set(scopePackages).size !== scopePackages.length ||
    !scopePackages.every((value) => ssoScopePackages.includes(value))
  ) {
    throw new Error("At least one unique SSO scope package is required.");
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
      offset: validated.offset,
      limit: validated.limit,
    })),
  );
  if (page.offset !== validated.offset || page.limit !== validated.limit) {
    throw new Error("The native runtime returned a different asset window.");
  }
  return page;
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
