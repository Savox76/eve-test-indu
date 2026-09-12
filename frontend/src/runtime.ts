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
export type DesktopDistribution = "installed" | "portable";
export type PublicReleaseNoticeState = "available" | "current" | "unavailable" | "error";
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

export interface PublicReleaseNotice {
  state: PublicReleaseNoticeState;
  channel: UpdateChannel;
  currentVersion: string;
  latestVersion: string | null;
  releaseUrl: string | null;
  publishedAt: string | null;
  automaticInstall: false;
  errorCode: string | null;
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

export type AssetSummarySortField = "type" | "quantity" | "positions" | "owners" | "locations" | "age";
export const assetSummarySortFields: AssetSummarySortField[] = [
  "type", "quantity", "positions", "owners", "locations", "age",
];

export interface AssetSummaryOwner extends AssetOwner {
  quantity: number;
  positionCount: number;
}

export interface AssetSummaryRecord {
  typeId: number;
  typeName: string;
  quantityTotal: number;
  positionCount: number;
  ownerCount: number;
  locationCount: number;
  owners: AssetSummaryOwner[];
  locationStatuses: AssetLocationStatus[];
  ageSeconds: number;
}

export interface AssetSummaryQuery {
  search: string;
  ownerCharacterId: number | null;
  locationStatus: AssetLocationStatus | null;
  offset: number;
  limit: number;
  sortBy: AssetSummarySortField;
  sortDirection: SortDirection;
}

export interface AssetSummaryPage {
  items: AssetSummaryRecord[];
  total: number;
  positionTotal: number;
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
    status: "completed" | "partial" | "failed";
    pages: number;
    assets: number;
    resolved: number;
    restricted: number;
    unresolved: number;
    cycles: number;
    errorCode: string | null;
  }>;
  completed: number;
  partial: number;
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
  snapshots: Array<{
    characterId: number;
    name: string;
    state: "available" | "missing";
    itemCount: number;
    observedAt: string | null;
    ageSeconds: number | null;
  }>;
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
  facilityName: string | null;
  facilityKind: IndustryFacilityKind;
  facilityAccess: IndustryFacilityAccess;
  solarSystemId: number | null;
  solarSystemName: string | null;
  systemCostIndex: number | null;
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

export type IndustryFacilityKind = "station" | "structure" | "unknown";
export type IndustryFacilityAccess = "public" | "available" | "restricted" | "scope-missing" | "unknown";
export type IndustrySecurityClass = "highsec" | "lowsec" | "nullsec" | "unknown";
export type IndustryCostActivity = "manufacturing" | "reaction" | "copying" | "invention" | "researching_material_efficiency" | "researching_time_efficiency";
export type IndustryFacilitySortField = "facility" | "system" | "type" | "cost" | "jobs" | "access" | "age";
export const industryFacilityKinds: readonly IndustryFacilityKind[] = ["station", "structure", "unknown"];
export const industryFacilityAccessStates: readonly IndustryFacilityAccess[] = ["public", "available", "restricted", "scope-missing", "unknown"];
export const industrySecurityClasses: readonly IndustrySecurityClass[] = ["highsec", "lowsec", "nullsec", "unknown"];
export const industryCostActivities: readonly IndustryCostActivity[] = ["manufacturing", "reaction", "copying", "invention", "researching_material_efficiency", "researching_time_efficiency"];
export const industryFacilitySortFields: readonly IndustryFacilitySortField[] = ["facility", "system", "type", "cost", "jobs", "access", "age"];
export const industryFacilityPageSize = 100;

export interface IndustryFacilityRecord {
  facilityId: number;
  facilityName: string | null;
  kind: IndustryFacilityKind;
  access: IndustryFacilityAccess;
  typeId: number | null;
  typeName: string | null;
  ownerId: number | null;
  ownerName: string | null;
  regionId: number | null;
  regionName: string | null;
  solarSystemId: number | null;
  solarSystemName: string | null;
  securityStatus: number | null;
  securityClass: IndustrySecurityClass;
  tax: number | null;
  activityCostIndex: number | null;
  usedByCharacterIds: number[];
  observedActivityIds: IndustryActivityId[];
  jobCount: number;
  activeJobs: number;
  errorCode: string | null;
  snapshotId: number;
  syncRunId: number;
  observedAt: string;
  ageSeconds: number;
}

export interface IndustryFacilityQuery {
  search: string;
  kind: IndustryFacilityKind | null;
  access: IndustryFacilityAccess | null;
  securityClass: IndustrySecurityClass | null;
  activity: IndustryCostActivity;
  usedOnly: boolean;
  offset: number;
  limit: number;
  sortBy: IndustryFacilitySortField;
  sortDirection: SortDirection;
}

export interface IndustryFacilityPage {
  items: IndustryFacilityRecord[];
  total: number;
  npcFacilities: number;
  observedFacilities: number;
  restrictedStructures: number;
  systems: number;
  offset: number;
  limit: number;
  activity: IndustryCostActivity;
  activities: IndustryCostActivity[];
  kinds: IndustryFacilityKind[];
  accessStates: IndustryFacilityAccess[];
  securityClasses: IndustrySecurityClass[];
  observedAt: string | null;
  ageSeconds: number | null;
}

export interface IndustryFacilitySyncResult {
  syncRunId: number;
  facilities: number;
  npcFacilities: number;
  observedFacilities: number;
  restrictedStructures: number;
  systems: number;
  resolvedNames: number;
}

export type IndustrySlotActivityKey = "manufacturing" | "reactions" | "science";
export type IndustrySlotUtilizationState = "unknown" | "available" | "full" | "overbooked";
export const industrySlotActivities: readonly IndustrySlotActivityKey[] = [
  "manufacturing", "reactions", "science",
];
export const industrySlotPageSize = 50;

export interface IndustrySlotActivity {
  activity: IndustrySlotActivityKey;
  capacity: number | null;
  occupied: number | null;
  available: number | null;
  utilizationState: IndustrySlotUtilizationState;
  activeJobs: number | null;
  pausedJobs: number | null;
  readyJobs: number | null;
  nextJobEndDate: string | null;
  primarySkillId: number;
  primarySkillLevel: number | null;
  advancedSkillId: number;
  advancedSkillLevel: number | null;
  queuedPlans: number | null;
  blockedPlans: number | null;
  runningPlans: number | null;
  completePlans: number | null;
  planningAvailable: boolean;
}

export interface IndustrySlotRecord {
  characterId: number;
  name: string;
  activities: IndustrySlotActivity[];
  skillSnapshotId: number | null;
  skillSyncRunId: number | null;
  skillObservedAt: string | null;
  jobSnapshotId: number | null;
  jobSyncRunId: number | null;
  jobObservedAt: string | null;
  observedAt: string | null;
  ageSeconds: number | null;
}

export interface IndustrySlotQuery {
  ownerCharacterId: number | null;
  offset: number;
  limit: number;
}

export interface IndustrySlotPage {
  items: IndustrySlotRecord[];
  total: number;
  offset: number;
  limit: number;
  owners: AssetOwner[];
  activities: IndustrySlotActivityKey[];
  observedAt: string | null;
  ageSeconds: number | null;
}

export type ProductionActivity = "manufacturing" | "reaction";
export type ProductionPlanState = "ready" | "sde-unavailable" | "recipe-missing" | "cycle" | "complexity-limit";
export type ProductionPlanSortField = "priority" | "product" | "owner" | "activity" | "state" | "updated";
export const productionActivities: readonly ProductionActivity[] = ["manufacturing", "reaction"];
export const productionPlanStates: readonly ProductionPlanState[] = [
  "ready", "sde-unavailable", "recipe-missing", "cycle", "complexity-limit",
];
export const productionPlanSortFields: readonly ProductionPlanSortField[] = [
  "priority", "product", "owner", "activity", "state", "updated",
];
export const productionPlanPageSize = 50;
export const productionCatalogPageSize = 50;

export interface ProductionCatalogItem {
  blueprintTypeId: number;
  blueprintName: string;
  activity: ProductionActivity;
  baseTimeSeconds: number;
  productTypeId: number;
  productName: string;
  outputQuantity: number;
  materialCount: number;
}

export interface ProductionCatalogQuery {
  search: string;
  activity: ProductionActivity | null;
  offset: number;
  limit: number;
}

export interface ProductionCatalogPage {
  items: ProductionCatalogItem[];
  total: number;
  offset: number;
  limit: number;
  activities: ProductionActivity[];
  buildNumber: string | null;
}

export interface ProductionStepMaterial {
  typeId: number;
  typeName: string;
  quantityPerRun: number;
  grossQuantity: number;
  producedByPlan: boolean;
}

export interface ProductionStep {
  sequence: number;
  blueprintTypeId: number;
  blueprintName: string;
  activity: ProductionActivity;
  productTypeId: number;
  productName: string;
  requiredQuantity: number;
  outputQuantityPerRun: number;
  runs: number;
  producedQuantity: number;
  surplusQuantity: number;
  baseTimeSecondsPerRun: number;
  totalBaseTimeSeconds: number;
  recipeAlternatives: number;
  materials: ProductionStepMaterial[];
}

export interface ProductionGrossMaterial {
  typeId: number;
  typeName: string;
  quantity: number;
}

export interface ProductionWarning {
  code: "alternative-recipe";
  typeId: number;
  typeName: string;
  selectedBlueprintTypeId: number;
  candidateCount: number;
}

export interface ProductionPlanRecord {
  planId: number;
  ownerCharacterId: number;
  ownerName: string;
  blueprintTypeId: number;
  blueprintName: string;
  activity: ProductionActivity;
  productTypeId: number;
  productName: string;
  targetQuantity: number;
  priority: number;
  note: string | null;
  state: ProductionPlanState;
  buildNumber: string | null;
  steps: ProductionStep[];
  grossMaterials: ProductionGrossMaterial[];
  warnings: ProductionWarning[];
  cycleTypeIds: number[];
  totalBaseTimeSeconds: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProductionPlanQuery {
  search: string;
  ownerCharacterId: number | null;
  activity: ProductionActivity | null;
  state: ProductionPlanState | null;
  offset: number;
  limit: number;
  sortBy: ProductionPlanSortField;
  sortDirection: SortDirection;
}

export interface ProductionPlanPage {
  items: ProductionPlanRecord[];
  total: number;
  offset: number;
  limit: number;
  owners: AssetOwner[];
  activities: ProductionActivity[];
  states: ProductionPlanState[];
  summary: Record<ProductionPlanState, number>;
  buildNumber: string | null;
  inventoryApplied: false;
  modifiersApplied: false;
}

export interface ProductionPlanInput {
  planId: number | null;
  ownerCharacterId: number;
  blueprintTypeId: number;
  activity: ProductionActivity;
  productTypeId: number;
  targetQuantity: number;
  priority: number;
  note: string | null;
}

export interface ProductionPlanMutation extends ProductionPlanInput {
  planId: number;
  saved: true;
}

export type ResearchPlanActivity = "material" | "time";
export type ResearchPlanState = "unplanned" | "ready" | "queued" | "running" | "complete" | "unverified" | "missing";
export type ResearchPlanSortField = "priority" | "blueprint" | "owner" | "state" | "me" | "te" | "age";
export type ResearchFacilityEvidence = "none" | "active-job" | "last-owner-job";
export type ResearchActiveJobStatus = "active" | "paused" | "ready";
export const researchPlanActivities: readonly ResearchPlanActivity[] = ["material", "time"];
export const researchPlanStates: readonly ResearchPlanState[] = ["unplanned", "ready", "queued", "running", "complete", "unverified", "missing"];
export const researchPlanSortFields: readonly ResearchPlanSortField[] = ["priority", "blueprint", "owner", "state", "me", "te", "age"];
export const researchFacilityEvidence: readonly ResearchFacilityEvidence[] = ["none", "active-job", "last-owner-job"];
export const researchActiveJobStatuses: readonly ResearchActiveJobStatus[] = ["active", "paused", "ready"];
export const researchPlanPageSize = 100;

export interface ResearchPlanOwner {
  characterId: number;
  name: string;
  slotCapacity: number | null;
  slotsUsed: number;
  slotsAvailable: number | null;
  laboratoryOperationLevel: number;
  advancedLaboratoryOperationLevel: number;
  researchLevel: number;
  metallurgyLevel: number;
  skillSnapshotId: number | null;
  skillSyncRunId: number | null;
}

export interface ResearchPlanRecord {
  ownerCharacterId: number;
  ownerName: string;
  blueprintItemId: number;
  blueprintTypeId: number;
  blueprintName: string;
  blueprintPresent: boolean;
  currentMaterialEfficiency: number | null;
  currentTimeEfficiency: number | null;
  locationId: number | null;
  locationFlag: string | null;
  planned: boolean;
  nextActivity: ResearchPlanActivity;
  targetMaterialEfficiency: number;
  targetTimeEfficiency: number;
  priority: number;
  note: string | null;
  state: ResearchPlanState;
  slotCapacity: number | null;
  slotsUsed: number;
  slotsAvailable: number | null;
  researchLevel: number;
  metallurgyLevel: number;
  activeJobId: number | null;
  activeJobActivity: ResearchPlanActivity | null;
  activeJobStatus: ResearchActiveJobStatus | null;
  activeJobStartDate: string | null;
  activeJobEndDate: string | null;
  activeJobCost: number | null;
  facilityId: number | null;
  facilityName: string | null;
  facilityAccess: IndustryFacilityAccess;
  solarSystemName: string | null;
  systemCostIndex: number | null;
  facilityEvidence: ResearchFacilityEvidence;
  blueprintSnapshotId: number | null;
  blueprintSyncRunId: number | null;
  skillSnapshotId: number | null;
  skillSyncRunId: number | null;
  jobSnapshotId: number | null;
  jobSyncRunId: number | null;
  observedAt: string | null;
  ageSeconds: number | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface ResearchPlanQuery {
  search: string;
  ownerCharacterId: number | null;
  state: ResearchPlanState | null;
  plannedOnly: boolean;
  includeMaxed: boolean;
  offset: number;
  limit: number;
  sortBy: ResearchPlanSortField;
  sortDirection: SortDirection;
}

export interface ResearchPlanPage {
  items: ResearchPlanRecord[];
  total: number;
  offset: number;
  limit: number;
  owners: ResearchPlanOwner[];
  states: ResearchPlanState[];
  activities: ResearchPlanActivity[];
  summary: Record<ResearchPlanState, number>;
  observedAt: string | null;
  ageSeconds: number | null;
  estimatesAvailable: false;
}

export interface ResearchPlanInput {
  ownerCharacterId: number;
  blueprintItemId: number;
  nextActivity: ResearchPlanActivity;
  targetMaterialEfficiency: number;
  targetTimeEfficiency: number;
  priority: number;
  note: string | null;
}

export interface ResearchPlanMutation extends ResearchPlanInput {
  blueprintTypeId: number;
  saved: true;
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
      distribution: DesktopDistribution;
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

function validateAssetSummaryQuery(query: AssetSummaryQuery): AssetSummaryQuery {
  const search = query.search.trim().replace(/\s+/g, " ");
  if (
    search.length > 120 ||
    !(query.ownerCharacterId === null || isPositiveSafeInteger(query.ownerCharacterId)) ||
    !(query.locationStatus === null || assetLocationStatuses.includes(query.locationStatus)) ||
    !isNonNegativeSafeInteger(query.offset) ||
    !Number.isSafeInteger(query.limit) ||
    query.limit < 1 ||
    query.limit > 200 ||
    !assetSummarySortFields.includes(query.sortBy) ||
    !["asc", "desc"].includes(query.sortDirection)
  ) {
    throw new Error("The asset summary query is invalid.");
  }
  return { ...query, search };
}

function parseAssetSummaryPage(candidate: unknown): AssetSummaryPage {
  if (
    !isRecord(candidate) ||
    !Array.isArray(candidate.items) ||
    !isNonNegativeSafeInteger(candidate.total) ||
    !isNonNegativeSafeInteger(candidate.positionTotal) ||
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
    throw new Error("The native runtime returned an invalid asset summary.");
  }
  const owners = candidate.owners.map((owner): AssetOwner => {
    if (!isRecord(owner) || !isPositiveSafeInteger(owner.characterId) ||
      !isBoundedText(owner.name, 100)) {
      throw new Error("The native runtime returned invalid asset-summary owners.");
    }
    return owner as unknown as AssetOwner;
  });
  const items = candidate.items.map((item): AssetSummaryRecord => {
    if (
      !isRecord(item) ||
      !isPositiveSafeInteger(item.typeId) ||
      !isBoundedText(item.typeName, 220) ||
      !isNonNegativeSafeInteger(item.quantityTotal) ||
      !isPositiveSafeInteger(item.positionCount) ||
      !isPositiveSafeInteger(item.ownerCount) ||
      !isPositiveSafeInteger(item.locationCount) ||
      Number(item.locationCount) > Number(item.positionCount) ||
      !Array.isArray(item.owners) ||
      item.owners.length !== Number(item.ownerCount) ||
      !Array.isArray(item.locationStatuses) ||
      item.locationStatuses.length < 1 ||
      new Set(item.locationStatuses).size !== item.locationStatuses.length ||
      !item.locationStatuses.every((status) =>
        typeof status === "string" && assetLocationStatuses.includes(status as AssetLocationStatus)) ||
      !isNonNegativeSafeInteger(item.ageSeconds)
    ) {
      throw new Error("The native runtime returned invalid asset-summary records.");
    }
    const itemOwners = item.owners.map((owner) => {
      if (!isRecord(owner) || !isPositiveSafeInteger(owner.characterId) ||
        !isBoundedText(owner.name, 100) || !isNonNegativeSafeInteger(owner.quantity) ||
        !isPositiveSafeInteger(owner.positionCount)) {
        throw new Error("The native runtime returned invalid asset-summary distribution.");
      }
      return owner as unknown as AssetSummaryOwner;
    });
    return { ...item, owners: itemOwners } as unknown as AssetSummaryRecord;
  });
  if (
    items.length > Number(candidate.limit) ||
    items.length > Number(candidate.total) ||
    new Set(items.map(({ typeId }) => typeId)).size !== items.length ||
    new Set(owners.map(({ characterId }) => characterId)).size !== owners.length ||
    items.some((item) =>
      item.owners.some((owner) => !owners.some((candidateOwner) =>
        candidateOwner.characterId === owner.characterId && candidateOwner.name === owner.name)) ||
      item.owners.reduce((total, owner) => total + owner.quantity, 0) !== item.quantityTotal ||
      item.owners.reduce((total, owner) => total + owner.positionCount, 0) !== item.positionCount)
  ) {
    throw new Error("The native runtime returned inconsistent asset-summary metadata.");
  }
  return { ...candidate, items, owners } as unknown as AssetSummaryPage;
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
    !["installed", "portable"].includes(String(candidate.distribution)) ||
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
    distribution: candidate.distribution as DesktopDistribution,
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

function parsePublicReleaseNotice(candidate: unknown): PublicReleaseNotice {
  if (
    !isRecord(candidate) ||
    !["available", "current", "unavailable", "error"].includes(String(candidate.state)) ||
    !updateChannels.includes(candidate.channel as UpdateChannel) ||
    !isBoundedText(candidate.currentVersion, 80) ||
    !(candidate.latestVersion === null || isBoundedText(candidate.latestVersion, 80)) ||
    !(candidate.releaseUrl === null || isBoundedText(candidate.releaseUrl, 300)) ||
    !(candidate.publishedAt === null || isBoundedText(candidate.publishedAt, 64)) ||
    candidate.automaticInstall !== false ||
    !isNullableText(candidate.errorCode)
  ) {
    throw new Error("The native runtime returned an invalid release notice.");
  }
  const notice = candidate as unknown as PublicReleaseNotice;
  const hasRelease = notice.latestVersion !== null && notice.releaseUrl !== null && notice.publishedAt !== null;
  if (
    (["available", "current"].includes(notice.state) !== hasRelease) ||
    (notice.state === "error") !== (notice.errorCode !== null) ||
    (notice.state !== "error" && notice.errorCode !== null) ||
    (hasRelease && notice.releaseUrl !==
      `https://github.com/Savox76/eve-test-indu/releases/tag/v${notice.latestVersion}`)
  ) {
    throw new Error("The native runtime returned an inconsistent release notice.");
  }
  return notice;
}

export async function checkForUpdates(
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<PublicReleaseNotice> {
  if (!adapter.isAvailable()) {
    throw new Error("Update notices are available only in the desktop application.");
  }
  return parsePublicReleaseNotice(JSON.parse(await adapter.invoke("check_for_updates")));
}

export async function openReleaseDownloads(
  version: string | null,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<void> {
  if (!adapter.isAvailable()) {
    throw new Error("Release downloads are available only in the desktop application.");
  }
  if (version !== null && (!isBoundedText(version, 80) || !/^[0-9][0-9A-Za-z.+-]*$/.test(version))) {
    throw new Error("The release version is invalid.");
  }
  const candidate: unknown = JSON.parse(await adapter.invoke("open_release_downloads", { version }));
  if (!isRecord(candidate) || candidate.opened !== true || !isBoundedText(candidate.url, 300)) {
    throw new Error("The native runtime did not open the release page.");
  }
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

export async function loadAssetSummary(
  query: AssetSummaryQuery,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<AssetSummaryPage> {
  const validated = validateAssetSummaryQuery(query);
  if (!adapter.isAvailable()) {
    return {
      items: [],
      total: 0,
      positionTotal: 0,
      quantityTotal: 0,
      offset: validated.offset,
      limit: validated.limit,
      owners: [],
      locationStatuses: [...assetLocationStatuses],
      observedAt: null,
      ageSeconds: null,
    };
  }
  const page = parseAssetSummaryPage(
    JSON.parse(await adapter.invoke("query_asset_summary", {
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
    throw new Error("The native runtime returned a different asset-summary window.");
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
    !isNonNegativeSafeInteger(candidate.partial) ||
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
      !["completed", "partial", "failed"].includes(String(value.status)) ||
      !["pages", "assets", "resolved", "restricted", "unresolved", "cycles"].every(
        (key) => isNonNegativeSafeInteger(value[key]),
      ) ||
      !(value.errorCode === null || (typeof value.errorCode === "string" && value.errorCode.length <= 120))
    ) {
      throw new Error("The native runtime returned an invalid asset-sync result.");
    }
    if (
      (value.status === "completed" && value.errorCode !== null) ||
      (["partial", "failed"].includes(String(value.status)) && typeof value.errorCode !== "string") ||
      (value.status === "failed" && ["pages", "assets", "resolved", "restricted", "unresolved", "cycles"]
        .some((key) => value[key] !== 0))
    ) {
      throw new Error("The native runtime returned an invalid asset-sync result.");
    }
    return value as unknown as AssetSyncResult["characters"][number];
  });
  if (
    candidate.completed + candidate.partial + candidate.failed !== characters.length ||
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
    !Array.isArray(candidate.snapshots) ||
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
  const snapshots = candidate.snapshots.map((snapshot) => {
    if (!isRecord(snapshot) || !isPositiveSafeInteger(snapshot.characterId) ||
      !isBoundedText(snapshot.name, 100) ||
      !["available", "missing"].includes(String(snapshot.state)) ||
      !isNonNegativeSafeInteger(snapshot.itemCount) ||
      !(snapshot.observedAt === null || isBoundedText(snapshot.observedAt, 64)) ||
      !(snapshot.ageSeconds === null || isNonNegativeSafeInteger(snapshot.ageSeconds)) ||
      (snapshot.state === "available") !== (snapshot.observedAt !== null && snapshot.ageSeconds !== null) ||
      (snapshot.state === "missing" && Number(snapshot.itemCount) !== 0)) {
      throw new Error("The native runtime returned invalid blueprint snapshot status.");
    }
    return snapshot as unknown as BlueprintPage["snapshots"][number];
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
    snapshots.length !== owners.length ||
    new Set(snapshots.map(({ characterId }) => characterId)).size !== snapshots.length ||
    snapshots.some((snapshot) => !owners.some((owner) =>
      owner.characterId === snapshot.characterId && owner.name === snapshot.name)) ||
    items.some((item) => !owners.some((owner) => owner.characterId === item.ownerCharacterId))
  ) throw new Error("The native runtime returned inconsistent blueprint data.");
  return { ...candidate, items, owners, snapshots } as unknown as BlueprintPage;
}

export async function loadBlueprints(
  query: BlueprintQuery,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<BlueprintPage> {
  const validated = validateBlueprintQuery(query);
  if (!adapter.isAvailable()) return {
    items: [], total: 0, offset: validated.offset, limit: validated.limit,
    owners: [], snapshots: [], observedAt: null, ageSeconds: null,
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
    !(candidate.facilityName === null || isBoundedText(candidate.facilityName, 200)) ||
    !industryFacilityKinds.includes(candidate.facilityKind as IndustryFacilityKind) ||
    !industryFacilityAccessStates.includes(candidate.facilityAccess as IndustryFacilityAccess) ||
    !((candidate.solarSystemId === null && candidate.solarSystemName === null) ||
      (isPositiveSafeInteger(candidate.solarSystemId) && isBoundedText(candidate.solarSystemName, 200))) ||
    !(candidate.systemCostIndex === null ||
      (typeof candidate.systemCostIndex === "number" && Number.isFinite(candidate.systemCostIndex) &&
        candidate.systemCostIndex >= 0 && candidate.systemCostIndex <= 1)) ||
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

function validateIndustryFacilityQuery(query: IndustryFacilityQuery): IndustryFacilityQuery {
  const search = query.search.trim().replace(/\s+/g, " ");
  if (
    search.length > 120 ||
    !(query.kind === null || industryFacilityKinds.includes(query.kind)) ||
    !(query.access === null || industryFacilityAccessStates.includes(query.access)) ||
    !(query.securityClass === null || industrySecurityClasses.includes(query.securityClass)) ||
    !industryCostActivities.includes(query.activity) ||
    typeof query.usedOnly !== "boolean" ||
    !isNonNegativeSafeInteger(query.offset) ||
    !Number.isSafeInteger(query.limit) || query.limit < 1 || query.limit > 200 ||
    !industryFacilitySortFields.includes(query.sortBy) ||
    !["asc", "desc"].includes(query.sortDirection)
  ) {
    throw new Error("The industry-facility query is invalid.");
  }
  return { ...query, search };
}

function nullableIdAndName(candidate: Record<string, unknown>, id: string, name: string): boolean {
  return (candidate[id] === null && candidate[name] === null) ||
    (isPositiveSafeInteger(candidate[id]) && isBoundedText(candidate[name], 200));
}

function parseIndustryFacilityRecord(candidate: unknown): IndustryFacilityRecord {
  if (
    !isRecord(candidate) || !isPositiveSafeInteger(candidate.facilityId) ||
    !(candidate.facilityName === null || isBoundedText(candidate.facilityName, 200)) ||
    !industryFacilityKinds.includes(candidate.kind as IndustryFacilityKind) ||
    !industryFacilityAccessStates.includes(candidate.access as IndustryFacilityAccess) ||
    !nullableIdAndName(candidate, "typeId", "typeName") ||
    !nullableIdAndName(candidate, "ownerId", "ownerName") ||
    !nullableIdAndName(candidate, "regionId", "regionName") ||
    !nullableIdAndName(candidate, "solarSystemId", "solarSystemName") ||
    !(candidate.securityStatus === null || (typeof candidate.securityStatus === "number" &&
      Number.isFinite(candidate.securityStatus) && candidate.securityStatus >= -1 && candidate.securityStatus <= 1)) ||
    !industrySecurityClasses.includes(candidate.securityClass as IndustrySecurityClass) ||
    ((candidate.securityStatus === null) !== (candidate.securityClass === "unknown")) ||
    !(candidate.tax === null || (typeof candidate.tax === "number" && Number.isFinite(candidate.tax) &&
      candidate.tax >= 0 && candidate.tax <= 1)) ||
    !(candidate.activityCostIndex === null ||
      (typeof candidate.activityCostIndex === "number" && Number.isFinite(candidate.activityCostIndex) &&
        candidate.activityCostIndex >= 0 && candidate.activityCostIndex <= 1)) ||
    !Array.isArray(candidate.usedByCharacterIds) ||
    !candidate.usedByCharacterIds.every(isPositiveSafeInteger) ||
    new Set(candidate.usedByCharacterIds).size !== candidate.usedByCharacterIds.length ||
    !Array.isArray(candidate.observedActivityIds) ||
    !candidate.observedActivityIds.every((value) => industryActivityIds.includes(value as IndustryActivityId)) ||
    new Set(candidate.observedActivityIds).size !== candidate.observedActivityIds.length ||
    !isNonNegativeSafeInteger(candidate.jobCount) || !isNonNegativeSafeInteger(candidate.activeJobs) ||
    Number(candidate.activeJobs) > Number(candidate.jobCount) ||
    !(candidate.errorCode === null || isBoundedText(candidate.errorCode, 120)) ||
    !isPositiveSafeInteger(candidate.snapshotId) || !isPositiveSafeInteger(candidate.syncRunId) ||
    !isBoundedText(candidate.observedAt, 64) || !isNonNegativeSafeInteger(candidate.ageSeconds)
  ) {
    throw new Error("The native runtime returned invalid industry-facility records.");
  }
  if (
    (candidate.access === "public" &&
      (candidate.kind !== "station" || candidate.facilityName === null || candidate.typeId === null ||
        candidate.ownerId === null || candidate.regionId === null || candidate.solarSystemId === null ||
        candidate.errorCode !== null)) ||
    (candidate.access === "available" &&
      (candidate.kind !== "structure" || candidate.facilityName === null || candidate.ownerId === null ||
        candidate.solarSystemId === null || candidate.regionId !== null || candidate.tax !== null ||
        candidate.errorCode !== null)) ||
    (["restricted", "scope-missing", "unknown"].includes(String(candidate.access)) &&
      (candidate.facilityName !== null || candidate.typeId !== null || candidate.ownerId !== null ||
        candidate.regionId !== null || candidate.solarSystemId !== null || candidate.tax !== null ||
        candidate.errorCode === null))
  ) {
    throw new Error("The native runtime returned inconsistent industry-facility records.");
  }
  return candidate as unknown as IndustryFacilityRecord;
}

function parseIndustryFacilityPage(candidate: unknown): IndustryFacilityPage {
  if (
    !isRecord(candidate) || !Array.isArray(candidate.items) ||
    ![candidate.total, candidate.npcFacilities, candidate.observedFacilities,
      candidate.restrictedStructures, candidate.systems, candidate.offset].every(isNonNegativeSafeInteger) ||
    !Number.isSafeInteger(candidate.limit) || Number(candidate.limit) < 1 || Number(candidate.limit) > 200 ||
    Number(candidate.restrictedStructures) > Number(candidate.observedFacilities) ||
    !industryCostActivities.includes(candidate.activity as IndustryCostActivity) ||
    !Array.isArray(candidate.activities) || candidate.activities.length !== industryCostActivities.length ||
    !industryCostActivities.every((value, index) => (candidate.activities as unknown[])[index] === value) ||
    !Array.isArray(candidate.kinds) || candidate.kinds.length !== industryFacilityKinds.length ||
    !industryFacilityKinds.every((value, index) => (candidate.kinds as unknown[])[index] === value) ||
    !Array.isArray(candidate.accessStates) || candidate.accessStates.length !== industryFacilityAccessStates.length ||
    !industryFacilityAccessStates.every((value, index) => (candidate.accessStates as unknown[])[index] === value) ||
    !Array.isArray(candidate.securityClasses) || candidate.securityClasses.length !== industrySecurityClasses.length ||
    !industrySecurityClasses.every((value, index) => (candidate.securityClasses as unknown[])[index] === value) ||
    !(candidate.observedAt === null || isBoundedText(candidate.observedAt, 64)) ||
    !(candidate.ageSeconds === null || isNonNegativeSafeInteger(candidate.ageSeconds)) ||
    (candidate.observedAt === null) !== (candidate.ageSeconds === null)
  ) {
    throw new Error("The native runtime returned invalid industry-facility data.");
  }
  const items = candidate.items.map(parseIndustryFacilityRecord);
  if (
    items.length > Number(candidate.limit) || items.length > Number(candidate.total) ||
    new Set(items.map(({ facilityId }) => facilityId)).size !== items.length ||
    items.some((item) => item.observedAt !== candidate.observedAt || item.ageSeconds !== candidate.ageSeconds) ||
    (candidate.observedAt === null &&
      (items.length > 0 || candidate.npcFacilities !== 0 || candidate.observedFacilities !== 0 ||
        candidate.restrictedStructures !== 0 || candidate.systems !== 0))
  ) {
    throw new Error("The native runtime returned inconsistent industry-facility data.");
  }
  return { ...candidate, items } as unknown as IndustryFacilityPage;
}

export async function loadIndustryFacilities(
  query: IndustryFacilityQuery,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<IndustryFacilityPage> {
  const validated = validateIndustryFacilityQuery(query);
  if (!adapter.isAvailable()) return {
    items: [], total: 0, npcFacilities: 0, observedFacilities: 0, restrictedStructures: 0,
    systems: 0, offset: validated.offset, limit: validated.limit, activity: validated.activity,
    activities: [...industryCostActivities], kinds: [...industryFacilityKinds],
    accessStates: [...industryFacilityAccessStates], securityClasses: [...industrySecurityClasses],
    observedAt: null, ageSeconds: null,
  };
  const page = parseIndustryFacilityPage(JSON.parse(await adapter.invoke("query_industry_facilities", {
    search: validated.search,
    kind: validated.kind,
    access: validated.access,
    securityClass: validated.securityClass,
    activity: validated.activity,
    usedOnly: validated.usedOnly,
    offset: validated.offset,
    limit: validated.limit,
    sortBy: validated.sortBy,
    sortDirection: validated.sortDirection,
  })));
  if (page.offset !== validated.offset || page.limit !== validated.limit ||
      page.activity !== validated.activity) {
    throw new Error("The native runtime returned a different industry-facility window.");
  }
  return page;
}

export async function syncIndustryFacilities(
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<IndustryFacilitySyncResult> {
  if (!adapter.isAvailable()) {
    throw new Error("Industry-facility sync is available only in the desktop application.");
  }
  const candidate: unknown = JSON.parse(await adapter.invoke("sync_industry_facilities"));
  if (
    !isRecord(candidate) || !isPositiveSafeInteger(candidate.syncRunId) ||
    ![candidate.facilities, candidate.npcFacilities, candidate.observedFacilities,
      candidate.restrictedStructures, candidate.systems, candidate.resolvedNames]
      .every(isNonNegativeSafeInteger) ||
    Number(candidate.facilities) !== Number(candidate.npcFacilities) + Number(candidate.observedFacilities) ||
    Number(candidate.restrictedStructures) > Number(candidate.observedFacilities) ||
    Number(candidate.npcFacilities) === 0 || Number(candidate.systems) === 0 ||
    Number(candidate.resolvedNames) === 0
  ) {
    throw new Error("The native runtime returned an invalid industry-facility sync result.");
  }
  return candidate as unknown as IndustryFacilitySyncResult;
}

const industrySlotSkillIds: Readonly<Record<IndustrySlotActivityKey, readonly [number, number]>> = {
  manufacturing: [3387, 24625],
  reactions: [45748, 45749],
  science: [3406, 24624],
};

function parseIndustrySlotActivity(candidate: unknown): IndustrySlotActivity {
  if (
    !isRecord(candidate) ||
    !industrySlotActivities.includes(candidate.activity as IndustrySlotActivityKey) ||
    !["unknown", "available", "full", "overbooked"].includes(String(candidate.utilizationState)) ||
    typeof candidate.planningAvailable !== "boolean" ||
    !(candidate.nextJobEndDate === null || isBoundedText(candidate.nextJobEndDate, 64))
  ) {
    throw new Error("The native runtime returned invalid industry-slot activity data.");
  }
  const activity = candidate.activity as IndustrySlotActivityKey;
  const expectedSkills = industrySlotSkillIds[activity];
  const capacityKnown = candidate.capacity !== null;
  const occupancyKnown = candidate.occupied !== null;
  const skillLevelsKnown = candidate.primarySkillLevel !== null && candidate.advancedSkillLevel !== null;
  const jobCountsKnown = candidate.activeJobs !== null && candidate.pausedJobs !== null &&
    candidate.readyJobs !== null;
  if (
    candidate.primarySkillId !== expectedSkills[0] || candidate.advancedSkillId !== expectedSkills[1] ||
    capacityKnown !== skillLevelsKnown ||
    !(candidate.capacity === null ||
      (isPositiveSafeInteger(candidate.capacity) && Number(candidate.capacity) <= 11)) ||
    !(candidate.primarySkillLevel === null ||
      (isNonNegativeSafeInteger(candidate.primarySkillLevel) && Number(candidate.primarySkillLevel) <= 5)) ||
    !(candidate.advancedSkillLevel === null ||
      (isNonNegativeSafeInteger(candidate.advancedSkillLevel) && Number(candidate.advancedSkillLevel) <= 5)) ||
    (capacityKnown && Number(candidate.capacity) !== 1 + Number(candidate.primarySkillLevel) +
      Number(candidate.advancedSkillLevel)) ||
    occupancyKnown !== jobCountsKnown ||
    !(candidate.occupied === null || isNonNegativeSafeInteger(candidate.occupied)) ||
    !(candidate.activeJobs === null || isNonNegativeSafeInteger(candidate.activeJobs)) ||
    !(candidate.pausedJobs === null || isNonNegativeSafeInteger(candidate.pausedJobs)) ||
    !(candidate.readyJobs === null || isNonNegativeSafeInteger(candidate.readyJobs)) ||
    (occupancyKnown && Number(candidate.occupied) !== Number(candidate.activeJobs) +
      Number(candidate.pausedJobs) + Number(candidate.readyJobs)) ||
    (candidate.nextJobEndDate !== null && Number(candidate.activeJobs) < 1)
  ) {
    throw new Error("The native runtime returned inconsistent industry-slot activity data.");
  }
  const availabilityKnown = capacityKnown && occupancyKnown;
  const expectedAvailable = availabilityKnown
    ? Math.max(0, Number(candidate.capacity) - Number(candidate.occupied))
    : null;
  const expectedState = !availabilityKnown
    ? "unknown"
    : Number(candidate.occupied) > Number(candidate.capacity)
      ? "overbooked"
      : Number(candidate.occupied) === Number(candidate.capacity)
        ? "full"
        : "available";
  const planFields = [candidate.queuedPlans, candidate.blockedPlans,
    candidate.runningPlans, candidate.completePlans];
  if (
    candidate.available !== expectedAvailable || candidate.utilizationState !== expectedState ||
    (!candidate.planningAvailable || !planFields.every(isNonNegativeSafeInteger))
  ) {
    throw new Error("The native runtime returned inconsistent industry-slot capacity data.");
  }
  return candidate as unknown as IndustrySlotActivity;
}

function optionalSourceIsValid(id: unknown, runId: unknown, observedAt: unknown): boolean {
  const present = id !== null;
  return present === (runId !== null) && present === (observedAt !== null) &&
    (!present || (isPositiveSafeInteger(id) && isPositiveSafeInteger(runId) &&
      isBoundedText(observedAt, 64)));
}

function parseIndustrySlotRecord(candidate: unknown): IndustrySlotRecord {
  if (
    !isRecord(candidate) || !isPositiveSafeInteger(candidate.characterId) ||
    !isBoundedText(candidate.name, 100) || !Array.isArray(candidate.activities) ||
    candidate.activities.length !== industrySlotActivities.length ||
    !optionalSourceIsValid(candidate.skillSnapshotId, candidate.skillSyncRunId,
      candidate.skillObservedAt) ||
    !optionalSourceIsValid(candidate.jobSnapshotId, candidate.jobSyncRunId,
      candidate.jobObservedAt) ||
    !(candidate.observedAt === null || isBoundedText(candidate.observedAt, 64)) ||
    !(candidate.ageSeconds === null || isNonNegativeSafeInteger(candidate.ageSeconds)) ||
    (candidate.observedAt === null) !== (candidate.ageSeconds === null)
  ) {
    throw new Error("The native runtime returned invalid industry-slot records.");
  }
  const activities = candidate.activities.map(parseIndustrySlotActivity);
  if (!industrySlotActivities.every((value, index) => activities[index].activity === value)) {
    throw new Error("The native runtime returned an invalid industry-slot activity order.");
  }
  return { ...candidate, activities } as unknown as IndustrySlotRecord;
}

function validateIndustrySlotQuery(query: IndustrySlotQuery): IndustrySlotQuery {
  if (
    !(query.ownerCharacterId === null || isPositiveSafeInteger(query.ownerCharacterId)) ||
    !isNonNegativeSafeInteger(query.offset) || !Number.isSafeInteger(query.limit) ||
    query.limit < 1 || query.limit > 200
  ) {
    throw new Error("The industry-slot query is invalid.");
  }
  return query;
}

function parseIndustrySlotPage(candidate: unknown): IndustrySlotPage {
  const activities = isRecord(candidate) && Array.isArray(candidate.activities)
    ? candidate.activities
    : [];
  if (
    !isRecord(candidate) || !Array.isArray(candidate.items) || !Array.isArray(candidate.owners) ||
    activities.length !== industrySlotActivities.length ||
    !industrySlotActivities.every((value, index) => activities[index] === value) ||
    !isNonNegativeSafeInteger(candidate.total) || !isNonNegativeSafeInteger(candidate.offset) ||
    !Number.isSafeInteger(candidate.limit) || Number(candidate.limit) < 1 || Number(candidate.limit) > 200 ||
    !(candidate.observedAt === null || isBoundedText(candidate.observedAt, 64)) ||
    !(candidate.ageSeconds === null || isNonNegativeSafeInteger(candidate.ageSeconds)) ||
    (candidate.observedAt === null) !== (candidate.ageSeconds === null)
  ) {
    throw new Error("The native runtime returned invalid industry-slot data.");
  }
  const items = candidate.items.map(parseIndustrySlotRecord);
  const owners = candidate.owners.map((owner) => {
    if (!isRecord(owner) || !isPositiveSafeInteger(owner.characterId) || !isBoundedText(owner.name, 100)) {
      throw new Error("The native runtime returned invalid industry-slot owners.");
    }
    return owner as unknown as AssetOwner;
  });
  if (
    items.length > Number(candidate.limit) || items.length > Number(candidate.total) ||
    new Set(items.map(({ characterId }) => characterId)).size !== items.length ||
    new Set(owners.map(({ characterId }) => characterId)).size !== owners.length ||
    items.some((item) => !owners.some((owner) => owner.characterId === item.characterId &&
      owner.name === item.name))
  ) {
    throw new Error("The native runtime returned inconsistent industry-slot data.");
  }
  return { ...candidate, items, owners } as unknown as IndustrySlotPage;
}

export async function loadIndustrySlots(
  query: IndustrySlotQuery,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<IndustrySlotPage> {
  const validated = validateIndustrySlotQuery(query);
  if (!adapter.isAvailable()) return {
    items: [], total: 0, offset: validated.offset, limit: validated.limit, owners: [],
    activities: [...industrySlotActivities], observedAt: null, ageSeconds: null,
  };
  const page = parseIndustrySlotPage(JSON.parse(await adapter.invoke("query_industry_slots", {
    ownerCharacterId: validated.ownerCharacterId,
    offset: validated.offset,
    limit: validated.limit,
  })));
  if (page.offset !== validated.offset || page.limit !== validated.limit) {
    throw new Error("The native runtime returned a different industry-slot window.");
  }
  return page;
}

function validateProductionCatalogQuery(query: ProductionCatalogQuery): ProductionCatalogQuery {
  const search = query.search.trim().replace(/\s+/g, " ");
  if (
    search.length > 120 ||
    !(query.activity === null || productionActivities.includes(query.activity)) ||
    !isNonNegativeSafeInteger(query.offset) ||
    !Number.isSafeInteger(query.limit) || query.limit < 1 || query.limit > 100
  ) {
    throw new Error("The production catalog query is invalid.");
  }
  return { ...query, search };
}

function parseProductionCatalogPage(candidate: unknown): ProductionCatalogPage {
  if (
    !isRecord(candidate) || !Array.isArray(candidate.items) ||
    !isNonNegativeSafeInteger(candidate.total) || !isNonNegativeSafeInteger(candidate.offset) ||
    !Number.isSafeInteger(candidate.limit) || Number(candidate.limit) < 1 || Number(candidate.limit) > 100 ||
    !Array.isArray(candidate.activities) || candidate.activities.length !== productionActivities.length ||
    !productionActivities.every((value, index) => (candidate.activities as unknown[])[index] === value) ||
    !(candidate.buildNumber === null || isBoundedText(candidate.buildNumber, 80))
  ) {
    throw new Error("The native runtime returned an invalid production catalog.");
  }
  const items = candidate.items.map((item): ProductionCatalogItem => {
    if (
      !isRecord(item) || !isPositiveSafeInteger(item.blueprintTypeId) ||
      !isBoundedText(item.blueprintName, 200) ||
      !productionActivities.includes(item.activity as ProductionActivity) ||
      !isPositiveSafeInteger(item.baseTimeSeconds) || !isPositiveSafeInteger(item.productTypeId) ||
      !isBoundedText(item.productName, 200) || !isPositiveSafeInteger(item.outputQuantity) ||
      !isPositiveSafeInteger(item.materialCount)
    ) {
      throw new Error("The native runtime returned invalid production catalog entries.");
    }
    return item as unknown as ProductionCatalogItem;
  });
  if (
    items.length > Number(candidate.limit) || items.length > Number(candidate.total) ||
    new Set(items.map((item) => `${item.blueprintTypeId}:${item.activity}:${item.productTypeId}`)).size !== items.length ||
    (candidate.buildNumber === null && (candidate.total !== 0 || items.length !== 0))
  ) {
    throw new Error("The native runtime returned inconsistent production catalog metadata.");
  }
  return { ...candidate, items } as unknown as ProductionCatalogPage;
}

export async function loadProductionCatalog(
  query: ProductionCatalogQuery,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<ProductionCatalogPage> {
  const validated = validateProductionCatalogQuery(query);
  if (!adapter.isAvailable()) return {
    items: [], total: 0, offset: validated.offset, limit: validated.limit,
    activities: [...productionActivities], buildNumber: null,
  };
  const page = parseProductionCatalogPage(JSON.parse(await adapter.invoke("query_production_catalog", {
    search: validated.search, activity: validated.activity, offset: validated.offset, limit: validated.limit,
  })));
  if (page.offset !== validated.offset || page.limit !== validated.limit) {
    throw new Error("The native runtime returned a different production catalog window.");
  }
  return page;
}

function parseProductionStep(candidate: unknown, index: number): ProductionStep {
  if (
    !isRecord(candidate) || candidate.sequence !== index + 1 ||
    !isPositiveSafeInteger(candidate.blueprintTypeId) || !isBoundedText(candidate.blueprintName, 200) ||
    !productionActivities.includes(candidate.activity as ProductionActivity) ||
    !isPositiveSafeInteger(candidate.productTypeId) || !isBoundedText(candidate.productName, 200) ||
    ![candidate.requiredQuantity, candidate.outputQuantityPerRun, candidate.runs,
      candidate.producedQuantity, candidate.baseTimeSecondsPerRun, candidate.totalBaseTimeSeconds,
      candidate.recipeAlternatives].every(isPositiveSafeInteger) ||
    !isNonNegativeSafeInteger(candidate.surplusQuantity) || !Array.isArray(candidate.materials) ||
    Number(candidate.outputQuantityPerRun) * Number(candidate.runs) !== Number(candidate.producedQuantity) ||
    Number(candidate.producedQuantity) - Number(candidate.requiredQuantity) !== Number(candidate.surplusQuantity) ||
    Number(candidate.baseTimeSecondsPerRun) * Number(candidate.runs) !== Number(candidate.totalBaseTimeSeconds)
  ) {
    throw new Error("The native runtime returned invalid production steps.");
  }
  const materials = candidate.materials.map((material): ProductionStepMaterial => {
    if (
      !isRecord(material) || !isPositiveSafeInteger(material.typeId) ||
      !isBoundedText(material.typeName, 200) || !isPositiveSafeInteger(material.quantityPerRun) ||
      !isPositiveSafeInteger(material.grossQuantity) || typeof material.producedByPlan !== "boolean" ||
      Number(material.quantityPerRun) * Number(candidate.runs) !== Number(material.grossQuantity)
    ) {
      throw new Error("The native runtime returned invalid production-step materials.");
    }
    return material as unknown as ProductionStepMaterial;
  });
  return { ...candidate, materials } as unknown as ProductionStep;
}

function parseProductionPlanRecord(candidate: unknown): ProductionPlanRecord {
  if (
    !isRecord(candidate) || !isPositiveSafeInteger(candidate.planId) ||
    !isPositiveSafeInteger(candidate.ownerCharacterId) || !isBoundedText(candidate.ownerName, 100) ||
    !isPositiveSafeInteger(candidate.blueprintTypeId) || !isBoundedText(candidate.blueprintName, 200) ||
    !productionActivities.includes(candidate.activity as ProductionActivity) ||
    !isPositiveSafeInteger(candidate.productTypeId) || !isBoundedText(candidate.productName, 200) ||
    !isPositiveSafeInteger(candidate.targetQuantity) || !isNonNegativeSafeInteger(candidate.priority) ||
    Number(candidate.priority) > 999 || !(candidate.note === null || isBoundedText(candidate.note, 240)) ||
    !productionPlanStates.includes(candidate.state as ProductionPlanState) ||
    !(candidate.buildNumber === null || isBoundedText(candidate.buildNumber, 80)) ||
    !Array.isArray(candidate.steps) || !Array.isArray(candidate.grossMaterials) ||
    !Array.isArray(candidate.warnings) || !Array.isArray(candidate.cycleTypeIds) ||
    !(candidate.totalBaseTimeSeconds === null || isPositiveSafeInteger(candidate.totalBaseTimeSeconds)) ||
    !isBoundedText(candidate.createdAt, 64) || !isBoundedText(candidate.updatedAt, 64)
  ) {
    throw new Error("The native runtime returned invalid production plans.");
  }
  const steps = candidate.steps.map(parseProductionStep);
  const grossMaterials = candidate.grossMaterials.map((material): ProductionGrossMaterial => {
    if (!isRecord(material) || !isPositiveSafeInteger(material.typeId) ||
      !isBoundedText(material.typeName, 200) || !isPositiveSafeInteger(material.quantity)) {
      throw new Error("The native runtime returned invalid gross materials.");
    }
    return material as unknown as ProductionGrossMaterial;
  });
  const warnings = candidate.warnings.map((warning): ProductionWarning => {
    if (!isRecord(warning) || warning.code !== "alternative-recipe" ||
      !isPositiveSafeInteger(warning.typeId) || !isBoundedText(warning.typeName, 200) ||
      !isPositiveSafeInteger(warning.selectedBlueprintTypeId) ||
      !Number.isSafeInteger(warning.candidateCount) || Number(warning.candidateCount) < 2) {
      throw new Error("The native runtime returned invalid production warnings.");
    }
    return warning as unknown as ProductionWarning;
  });
  if (!candidate.cycleTypeIds.every(isPositiveSafeInteger)) {
    throw new Error("The native runtime returned invalid production cycles.");
  }
  const ready = candidate.state === "ready";
  if (
    ready !== (steps.length > 0 && candidate.totalBaseTimeSeconds !== null) ||
    (ready && (candidate.buildNumber === null || candidate.cycleTypeIds.length !== 0 ||
      steps.at(-1)?.blueprintTypeId !== candidate.blueprintTypeId ||
      steps.at(-1)?.productTypeId !== candidate.productTypeId ||
      steps.at(-1)?.activity !== candidate.activity || steps.at(-1)?.requiredQuantity !== candidate.targetQuantity ||
      steps.reduce((total, step) => total + step.totalBaseTimeSeconds, 0) !== candidate.totalBaseTimeSeconds)) ||
    (!ready && (grossMaterials.length !== 0 || candidate.totalBaseTimeSeconds !== null)) ||
    ((candidate.state === "cycle") !== (candidate.cycleTypeIds.length > 0))
  ) {
    throw new Error("The native runtime returned inconsistent production-plan data.");
  }
  return { ...candidate, steps, grossMaterials, warnings } as unknown as ProductionPlanRecord;
}

function validateProductionPlanQuery(query: ProductionPlanQuery): ProductionPlanQuery {
  const search = query.search.trim().replace(/\s+/g, " ");
  if (
    search.length > 120 || !(query.ownerCharacterId === null || isPositiveSafeInteger(query.ownerCharacterId)) ||
    !(query.activity === null || productionActivities.includes(query.activity)) ||
    !(query.state === null || productionPlanStates.includes(query.state)) ||
    !isNonNegativeSafeInteger(query.offset) || !Number.isSafeInteger(query.limit) ||
    query.limit < 1 || query.limit > 100 || !productionPlanSortFields.includes(query.sortBy) ||
    !["asc", "desc"].includes(query.sortDirection)
  ) throw new Error("The production-plan query is invalid.");
  return { ...query, search };
}

function emptyProductionSummary(): Record<ProductionPlanState, number> {
  return Object.fromEntries(productionPlanStates.map((state) => [state, 0])) as Record<ProductionPlanState, number>;
}

function parseProductionPlanPage(candidate: unknown): ProductionPlanPage {
  if (
    !isRecord(candidate) || !Array.isArray(candidate.items) || !Array.isArray(candidate.owners) ||
    !Array.isArray(candidate.activities) || !Array.isArray(candidate.states) || !isRecord(candidate.summary) ||
    !isNonNegativeSafeInteger(candidate.total) || !isNonNegativeSafeInteger(candidate.offset) ||
    !Number.isSafeInteger(candidate.limit) || Number(candidate.limit) < 1 || Number(candidate.limit) > 100 ||
    candidate.activities.length !== productionActivities.length ||
    !productionActivities.every((value, index) => (candidate.activities as unknown[])[index] === value) ||
    candidate.states.length !== productionPlanStates.length ||
    !productionPlanStates.every((value, index) => (candidate.states as unknown[])[index] === value) ||
    !productionPlanStates.every((state) => isNonNegativeSafeInteger(
      (candidate.summary as Record<string, unknown>)[state])) ||
    !(candidate.buildNumber === null || isBoundedText(candidate.buildNumber, 80)) ||
    candidate.inventoryApplied !== false || candidate.modifiersApplied !== false
  ) throw new Error("The native runtime returned invalid production-plan data.");
  const items = candidate.items.map(parseProductionPlanRecord);
  const owners = candidate.owners.map((owner): AssetOwner => {
    if (!isRecord(owner) || !isPositiveSafeInteger(owner.characterId) || !isBoundedText(owner.name, 100)) {
      throw new Error("The native runtime returned invalid production-plan owners.");
    }
    return owner as unknown as AssetOwner;
  });
  if (items.length > Number(candidate.limit) || items.length > Number(candidate.total) ||
    new Set(items.map((item) => item.planId)).size !== items.length ||
    new Set(owners.map((owner) => owner.characterId)).size !== owners.length) {
    throw new Error("The native runtime returned inconsistent production-plan metadata.");
  }
  return { ...candidate, items, owners } as unknown as ProductionPlanPage;
}

export async function loadProductionPlans(
  query: ProductionPlanQuery,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<ProductionPlanPage> {
  const validated = validateProductionPlanQuery(query);
  if (!adapter.isAvailable()) return {
    items: [], total: 0, offset: validated.offset, limit: validated.limit, owners: [],
    activities: [...productionActivities], states: [...productionPlanStates],
    summary: emptyProductionSummary(), buildNumber: null, inventoryApplied: false, modifiersApplied: false,
  };
  const page = parseProductionPlanPage(JSON.parse(await adapter.invoke("query_production_plans", {
    search: validated.search, ownerCharacterId: validated.ownerCharacterId,
    activity: validated.activity, planState: validated.state, offset: validated.offset,
    limit: validated.limit, sortBy: validated.sortBy, sortDirection: validated.sortDirection,
  })));
  if (page.offset !== validated.offset || page.limit !== validated.limit) {
    throw new Error("The native runtime returned a different production-plan window.");
  }
  return page;
}

function validateProductionPlanInput(input: ProductionPlanInput): ProductionPlanInput {
  const note = input.note === null ? null : input.note.trim().replace(/\s+/g, " ") || null;
  if (
    !(input.planId === null || isPositiveSafeInteger(input.planId)) ||
    !isPositiveSafeInteger(input.ownerCharacterId) || !isPositiveSafeInteger(input.blueprintTypeId) ||
    !productionActivities.includes(input.activity) || !isPositiveSafeInteger(input.productTypeId) ||
    !isPositiveSafeInteger(input.targetQuantity) || !isNonNegativeSafeInteger(input.priority) ||
    input.priority > 999 || !(note === null || note.length <= 240)
  ) throw new Error("The production plan is invalid.");
  return { ...input, note };
}

export async function saveProductionPlan(
  input: ProductionPlanInput,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<ProductionPlanMutation> {
  if (!adapter.isAvailable()) throw new Error("Production planning is available only in the desktop application.");
  const validated = validateProductionPlanInput(input);
  const candidate: unknown = JSON.parse(await adapter.invoke("save_production_plan", {
    planId: validated.planId, ownerCharacterId: validated.ownerCharacterId,
    blueprintTypeId: validated.blueprintTypeId, activity: validated.activity,
    productTypeId: validated.productTypeId, targetQuantity: validated.targetQuantity,
    priority: validated.priority, note: validated.note,
  }));
  if (!isRecord(candidate) || candidate.saved !== true || !isPositiveSafeInteger(candidate.planId) ||
    (validated.planId !== null && candidate.planId !== validated.planId) ||
    candidate.ownerCharacterId !== validated.ownerCharacterId ||
    candidate.blueprintTypeId !== validated.blueprintTypeId || candidate.activity !== validated.activity ||
    candidate.productTypeId !== validated.productTypeId || candidate.targetQuantity !== validated.targetQuantity ||
    candidate.priority !== validated.priority || candidate.note !== validated.note) {
    throw new Error("The native runtime returned an invalid production-plan update.");
  }
  return candidate as unknown as ProductionPlanMutation;
}

export async function deleteProductionPlan(
  planId: number,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<void> {
  if (!adapter.isAvailable()) throw new Error("Production planning is available only in the desktop application.");
  if (!isPositiveSafeInteger(planId)) throw new Error("The production-plan identity is invalid.");
  const candidate: unknown = JSON.parse(await adapter.invoke("delete_production_plan", { planId }));
  if (!isRecord(candidate) || candidate.deleted !== true || candidate.planId !== planId) {
    throw new Error("The native runtime returned an invalid production-plan deletion.");
  }
}

function validateResearchPlanQuery(query: ResearchPlanQuery): ResearchPlanQuery {
  const search = query.search.trim().replace(/\s+/g, " ");
  if (
    search.length > 120 ||
    !(query.ownerCharacterId === null || isPositiveSafeInteger(query.ownerCharacterId)) ||
    !(query.state === null || researchPlanStates.includes(query.state)) ||
    typeof query.plannedOnly !== "boolean" ||
    typeof query.includeMaxed !== "boolean" ||
    !isNonNegativeSafeInteger(query.offset) ||
    !Number.isSafeInteger(query.limit) || query.limit < 1 || query.limit > 200 ||
    !researchPlanSortFields.includes(query.sortBy) ||
    !["asc", "desc"].includes(query.sortDirection)
  ) {
    throw new Error("The research-plan query is invalid.");
  }
  return { ...query, search };
}

function sourcePairIsValid(first: unknown, second: unknown): boolean {
  return (first === null) === (second === null) &&
    (first === null || isPositiveSafeInteger(first)) &&
    (second === null || isPositiveSafeInteger(second));
}

function parseResearchPlanOwner(candidate: unknown): ResearchPlanOwner {
  if (
    !isRecord(candidate) || !isPositiveSafeInteger(candidate.characterId) ||
    !isBoundedText(candidate.name, 100) ||
    !isNonNegativeSafeInteger(candidate.slotsUsed) ||
    ![candidate.laboratoryOperationLevel, candidate.advancedLaboratoryOperationLevel,
      candidate.researchLevel, candidate.metallurgyLevel]
      .every((value) => isNonNegativeSafeInteger(value) && Number(value) <= 5) ||
    !sourcePairIsValid(candidate.skillSnapshotId, candidate.skillSyncRunId) ||
    (candidate.slotCapacity === null) !== (candidate.slotsAvailable === null) ||
    (candidate.slotCapacity === null) !== (candidate.skillSnapshotId === null) ||
    !(candidate.slotCapacity === null ||
      (isPositiveSafeInteger(candidate.slotCapacity) && candidate.slotCapacity <= 11)) ||
    !(candidate.slotsAvailable === null ||
      (isNonNegativeSafeInteger(candidate.slotsAvailable) &&
        candidate.slotCapacity !== null && candidate.slotsAvailable <= candidate.slotCapacity))
  ) {
    throw new Error("The native runtime returned invalid research-slot metadata.");
  }
  return candidate as unknown as ResearchPlanOwner;
}

function parseResearchPlanRecord(candidate: unknown): ResearchPlanRecord {
  if (
    !isRecord(candidate) || !isPositiveSafeInteger(candidate.ownerCharacterId) ||
    !isBoundedText(candidate.ownerName, 100) ||
    !isPositiveSafeInteger(candidate.blueprintItemId) ||
    !isPositiveSafeInteger(candidate.blueprintTypeId) || !isBoundedText(candidate.blueprintName, 200) ||
    typeof candidate.blueprintPresent !== "boolean" || typeof candidate.planned !== "boolean" ||
    !researchPlanActivities.includes(candidate.nextActivity as ResearchPlanActivity) ||
    !isNonNegativeSafeInteger(candidate.targetMaterialEfficiency) || candidate.targetMaterialEfficiency > 10 ||
    !isNonNegativeSafeInteger(candidate.targetTimeEfficiency) || candidate.targetTimeEfficiency > 20 ||
    !isNonNegativeSafeInteger(candidate.priority) || candidate.priority > 999 ||
    !(candidate.note === null || isBoundedText(candidate.note, 240)) ||
    !researchPlanStates.includes(candidate.state as ResearchPlanState) ||
    !isNonNegativeSafeInteger(candidate.slotsUsed) ||
    ![candidate.researchLevel, candidate.metallurgyLevel]
      .every((value) => isNonNegativeSafeInteger(value) && Number(value) <= 5) ||
    (candidate.slotCapacity === null) !== (candidate.slotsAvailable === null) ||
    !(candidate.slotCapacity === null ||
      (isPositiveSafeInteger(candidate.slotCapacity) && candidate.slotCapacity <= 11)) ||
    !(candidate.slotsAvailable === null ||
      (isNonNegativeSafeInteger(candidate.slotsAvailable) &&
        candidate.slotCapacity !== null && candidate.slotsAvailable <= candidate.slotCapacity)) ||
    !industryFacilityAccessStates.includes(candidate.facilityAccess as IndustryFacilityAccess) ||
    !researchFacilityEvidence.includes(candidate.facilityEvidence as ResearchFacilityEvidence) ||
    !sourcePairIsValid(candidate.blueprintSnapshotId, candidate.blueprintSyncRunId) ||
    !sourcePairIsValid(candidate.skillSnapshotId, candidate.skillSyncRunId) ||
    !sourcePairIsValid(candidate.jobSnapshotId, candidate.jobSyncRunId)
  ) {
    throw new Error("The native runtime returned invalid research-plan records.");
  }
  const currentFields = [candidate.currentMaterialEfficiency, candidate.currentTimeEfficiency,
    candidate.locationId, candidate.locationFlag, candidate.blueprintSnapshotId,
    candidate.blueprintSyncRunId, candidate.observedAt, candidate.ageSeconds];
  const currentPresent = currentFields.every((value) => value !== null);
  const currentMissing = currentFields.every((value) => value === null);
  if (
    candidate.blueprintPresent !== currentPresent || (!currentPresent && !currentMissing) ||
    (currentPresent && (
      !isNonNegativeSafeInteger(candidate.currentMaterialEfficiency) || candidate.currentMaterialEfficiency > 10 ||
      !isNonNegativeSafeInteger(candidate.currentTimeEfficiency) || candidate.currentTimeEfficiency > 20 ||
      !isPositiveSafeInteger(candidate.locationId) || !isBoundedText(candidate.locationFlag, 100) ||
      !isBoundedText(candidate.observedAt, 64) || !isNonNegativeSafeInteger(candidate.ageSeconds)
    )) ||
    (candidate.planned
      ? candidate.state === "unplanned" || !isBoundedText(candidate.createdAt, 64) || !isBoundedText(candidate.updatedAt, 64)
      : candidate.state !== "unplanned" || candidate.priority !== 0 || candidate.note !== null ||
        candidate.createdAt !== null || candidate.updatedAt !== null)
  ) {
    throw new Error("The native runtime returned inconsistent research-plan records.");
  }
  const hasActiveJob = candidate.activeJobId !== null;
  if (
    hasActiveJob !== [candidate.activeJobActivity, candidate.activeJobStatus,
      candidate.activeJobStartDate, candidate.activeJobEndDate].every((value) => value !== null) ||
    (hasActiveJob && (
      !isPositiveSafeInteger(candidate.activeJobId) ||
      !researchPlanActivities.includes(candidate.activeJobActivity as ResearchPlanActivity) ||
      !researchActiveJobStatuses.includes(candidate.activeJobStatus as ResearchActiveJobStatus) ||
      !isBoundedText(candidate.activeJobStartDate, 64) || !isBoundedText(candidate.activeJobEndDate, 64) ||
      !(candidate.activeJobCost === null ||
        (typeof candidate.activeJobCost === "number" && Number.isFinite(candidate.activeJobCost) && candidate.activeJobCost >= 0))
    )) ||
    (!hasActiveJob && candidate.activeJobCost !== null)
  ) {
    throw new Error("The native runtime returned inconsistent research-job evidence.");
  }
  const hasFacility = candidate.facilityEvidence !== "none";
  if (
    hasFacility !== (candidate.facilityId !== null) ||
    (hasFacility && (
      !isPositiveSafeInteger(candidate.facilityId) ||
      !(candidate.facilityName === null || isBoundedText(candidate.facilityName, 200)) ||
      !(candidate.solarSystemName === null || isBoundedText(candidate.solarSystemName, 200)) ||
      !(candidate.systemCostIndex === null ||
        (typeof candidate.systemCostIndex === "number" && Number.isFinite(candidate.systemCostIndex) &&
          candidate.systemCostIndex >= 0 && candidate.systemCostIndex <= 1))
    )) ||
    (!hasFacility && (candidate.facilityName !== null || candidate.solarSystemName !== null ||
      candidate.systemCostIndex !== null || candidate.facilityAccess !== "unknown")) ||
    (candidate.facilityEvidence === "active-job" && !hasActiveJob)
  ) {
    throw new Error("The native runtime returned inconsistent research-facility evidence.");
  }
  return candidate as unknown as ResearchPlanRecord;
}

function emptyResearchSummary(): Record<ResearchPlanState, number> {
  return Object.fromEntries(researchPlanStates.map((state) => [state, 0])) as Record<ResearchPlanState, number>;
}

function parseResearchPlanPage(candidate: unknown): ResearchPlanPage {
  if (
    !isRecord(candidate) || !Array.isArray(candidate.items) || !Array.isArray(candidate.owners) ||
    !Array.isArray(candidate.states) || !Array.isArray(candidate.activities) || !isRecord(candidate.summary) ||
    !isNonNegativeSafeInteger(candidate.total) || !isNonNegativeSafeInteger(candidate.offset) ||
    !Number.isSafeInteger(candidate.limit) || Number(candidate.limit) < 1 || Number(candidate.limit) > 200 ||
    candidate.states.length !== researchPlanStates.length ||
    !researchPlanStates.every((value, index) => (candidate.states as unknown[])[index] === value) ||
    candidate.activities.length !== researchPlanActivities.length ||
    !researchPlanActivities.every((value, index) => (candidate.activities as unknown[])[index] === value) ||
    !researchPlanStates.every((state) => isNonNegativeSafeInteger((candidate.summary as Record<string, unknown>)[state])) ||
    !(candidate.observedAt === null || isBoundedText(candidate.observedAt, 64)) ||
    !(candidate.ageSeconds === null || isNonNegativeSafeInteger(candidate.ageSeconds)) ||
    (candidate.observedAt === null) !== (candidate.ageSeconds === null) ||
    candidate.estimatesAvailable !== false
  ) {
    throw new Error("The native runtime returned invalid research-plan data.");
  }
  const items = candidate.items.map(parseResearchPlanRecord);
  const owners = candidate.owners.map(parseResearchPlanOwner);
  if (
    items.length > Number(candidate.limit) || items.length > Number(candidate.total) ||
    new Set(items.map((item) => `${item.ownerCharacterId}:${item.blueprintItemId}`)).size !== items.length ||
    new Set(owners.map((owner) => owner.characterId)).size !== owners.length
  ) {
    throw new Error("The native runtime returned inconsistent research-plan data.");
  }
  return { ...candidate, items, owners } as unknown as ResearchPlanPage;
}

export async function loadResearchPlans(
  query: ResearchPlanQuery,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<ResearchPlanPage> {
  const validated = validateResearchPlanQuery(query);
  if (!adapter.isAvailable()) return {
    items: [], total: 0, offset: validated.offset, limit: validated.limit, owners: [],
    states: [...researchPlanStates], activities: [...researchPlanActivities],
    summary: emptyResearchSummary(), observedAt: null, ageSeconds: null, estimatesAvailable: false,
  };
  const page = parseResearchPlanPage(JSON.parse(await adapter.invoke("query_research_plans", {
    search: validated.search,
    ownerCharacterId: validated.ownerCharacterId,
    planState: validated.state,
    plannedOnly: validated.plannedOnly,
    includeMaxed: validated.includeMaxed,
    offset: validated.offset,
    limit: validated.limit,
    sortBy: validated.sortBy,
    sortDirection: validated.sortDirection,
  })));
  if (page.offset !== validated.offset || page.limit !== validated.limit) {
    throw new Error("The native runtime returned a different research-plan window.");
  }
  return page;
}

function validateResearchPlanInput(input: ResearchPlanInput): ResearchPlanInput {
  const note = input.note === null ? null : input.note.trim().replace(/\s+/g, " ");
  if (
    !isPositiveSafeInteger(input.ownerCharacterId) || !isPositiveSafeInteger(input.blueprintItemId) ||
    !researchPlanActivities.includes(input.nextActivity) ||
    !isNonNegativeSafeInteger(input.targetMaterialEfficiency) || input.targetMaterialEfficiency > 10 ||
    !isNonNegativeSafeInteger(input.targetTimeEfficiency) || input.targetTimeEfficiency > 20 ||
    !isNonNegativeSafeInteger(input.priority) || input.priority > 999 ||
    !(note === null || note === "" || note.length <= 240)
  ) {
    throw new Error("The research plan is invalid.");
  }
  return { ...input, note: note || null };
}

export async function saveResearchPlan(
  input: ResearchPlanInput,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<ResearchPlanMutation> {
  if (!adapter.isAvailable()) throw new Error("Research planning is available only in the desktop application.");
  const validated = validateResearchPlanInput(input);
  const candidate: unknown = JSON.parse(await adapter.invoke("save_research_plan", { ...validated }));
  if (
    !isRecord(candidate) || candidate.saved !== true || !isPositiveSafeInteger(candidate.blueprintTypeId) ||
    candidate.ownerCharacterId !== validated.ownerCharacterId ||
    candidate.blueprintItemId !== validated.blueprintItemId ||
    candidate.nextActivity !== validated.nextActivity ||
    candidate.targetMaterialEfficiency !== validated.targetMaterialEfficiency ||
    candidate.targetTimeEfficiency !== validated.targetTimeEfficiency ||
    candidate.priority !== validated.priority || candidate.note !== validated.note
  ) {
    throw new Error("The native runtime returned an invalid research-plan update.");
  }
  return candidate as unknown as ResearchPlanMutation;
}

export async function deleteResearchPlan(
  ownerCharacterId: number,
  blueprintItemId: number,
  adapter: RuntimeAdapter = tauriAdapter,
): Promise<void> {
  if (!adapter.isAvailable()) throw new Error("Research planning is available only in the desktop application.");
  if (!isPositiveSafeInteger(ownerCharacterId) || !isPositiveSafeInteger(blueprintItemId)) {
    throw new Error("The research-plan identity is invalid.");
  }
  const candidate: unknown = JSON.parse(await adapter.invoke("delete_research_plan", {
    ownerCharacterId, blueprintItemId,
  }));
  if (!isRecord(candidate) || candidate.deleted !== true ||
      candidate.ownerCharacterId !== ownerCharacterId || candidate.blueprintItemId !== blueprintItemId) {
    throw new Error("The native runtime returned an invalid research-plan deletion.");
  }
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
