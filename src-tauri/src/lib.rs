use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{Ipv4Addr, SocketAddrV4, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{mpsc, Mutex};
use std::thread;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Manager, RunEvent, State};

const SIDECAR_PROTOCOL_VERSION: u8 = 1;
const DATABASE_LOCATION: &str = "data/foundry.sqlite3";
const SIDECAR_READY_TIMEOUT: Duration = Duration::from_secs(25);
const SIDECAR_SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(4);
const SIDECAR_RESTART_RETRY_DELAY: Duration = Duration::from_millis(750);
const SIDECAR_RESTART_RETRY_COUNT: u8 = 3;
const SIDECAR_SUPERVISOR_INTERVAL: Duration = Duration::from_millis(250);
const SIDECAR_REQUEST_TIMEOUT: Duration = Duration::from_secs(3);
const ASSET_SYNC_TIMEOUT: Duration = Duration::from_secs(120);
const UPDATE_NOTICE_TIMEOUT: Duration = Duration::from_secs(8);
const PORTABLE_MARKER: &str = "PORTABLE-README-DE-EN.txt";
const PROGRAM_STORAGE_MARKER: &str = ".program-storage-v1";
const PREVIOUS_PROGRAM_DATA_BACKUP: &str = "data-before-appdata-migration";
const SIDECAR_MAX_RESPONSE_BYTES: u64 = 4_194_304;
const WINDOWS_CREATE_NO_WINDOW: u32 = 0x0800_0000;
const EVE_SSO_AUTHORIZATION_ENDPOINT: &str = "https://login.eveonline.com/v2/oauth/authorize";
const EVE_SSO_CLIENT_ID: &str = "a8409de72d5b4cab9b0424819d0abdec";
const EVE_SSO_REDIRECT_URI: &str = "http://127.0.0.1:17891/oauth/callback";
const EVE_SSO_SCOPE_PACKAGES: [&str; 5] = [
    "industry-core",
    "market",
    "planetary-industry",
    "projects",
    "private-structures",
];
const FONT_SCALES: [&str; 5] = ["very-small", "small", "normal", "large", "very-large"];
const ASSET_LOCATION_STATUSES: [&str; 5] =
    ["resolved", "restricted", "unresolved", "cycle", "pending"];
const ASSET_DELTA_CHANGE_TYPES: [&str; 4] = ["added", "removed", "quantity", "location"];
const ASSET_SORT_FIELDS: [&str; 6] = ["type", "owner", "location", "flag", "quantity", "age"];
const ASSET_SUMMARY_SORT_FIELDS: [&str; 6] = [
    "type",
    "quantity",
    "positions",
    "owners",
    "locations",
    "age",
];
const BLUEPRINT_SORT_FIELDS: [&str; 7] = ["type", "owner", "kind", "me", "te", "runs", "age"];
const INDUSTRY_JOB_SORT_FIELDS: [&str; 10] = [
    "start",
    "end",
    "type",
    "owner",
    "activity",
    "status",
    "runs",
    "cost",
    "correlation",
    "age",
];
const INDUSTRY_JOB_STATUSES: [&str; 6] = [
    "active",
    "cancelled",
    "delivered",
    "paused",
    "ready",
    "reverted",
];
const INDUSTRY_JOB_CORRELATIONS: [&str; 5] =
    ["linked", "partial", "ambiguous", "unmatched", "pending"];
const INDUSTRY_JOB_ACTIVITY_IDS: [u8; 8] = [1, 3, 4, 5, 7, 8, 9, 11];
const INDUSTRY_FACILITY_SORT_FIELDS: [&str; 7] = [
    "facility", "system", "type", "cost", "jobs", "access", "age",
];
const INDUSTRY_FACILITY_KINDS: [&str; 3] = ["station", "structure", "unknown"];
const INDUSTRY_FACILITY_ACCESS_STATES: [&str; 5] = [
    "public",
    "available",
    "restricted",
    "scope-missing",
    "unknown",
];
const INDUSTRY_SECURITY_CLASSES: [&str; 4] = ["highsec", "lowsec", "nullsec", "unknown"];
const INDUSTRY_COST_ACTIVITIES: [&str; 6] = [
    "manufacturing",
    "reaction",
    "copying",
    "invention",
    "researching_material_efficiency",
    "researching_time_efficiency",
];
const INDUSTRY_SLOT_ACTIVITIES: [&str; 3] = ["manufacturing", "reactions", "science"];
const INDUSTRY_SLOT_UTILIZATION_STATES: [&str; 4] = ["unknown", "available", "full", "overbooked"];
const INDUSTRY_SLOT_SKILL_IDS: [(u64, u64); 3] = [(3387, 24625), (45748, 45749), (3406, 24624)];
const CHARACTER_SKILL_SORT_FIELDS: [&str; 6] =
    ["skill", "owner", "trained", "active", "skillpoints", "age"];
const CHARACTER_SKILL_ACTIVE_STATES: [&str; 3] = ["normal", "limited", "boosted"];
const RESEARCH_PLAN_SORT_FIELDS: [&str; 7] =
    ["priority", "blueprint", "owner", "state", "me", "te", "age"];
const RESEARCH_PLAN_STATES: [&str; 7] = [
    "unplanned",
    "ready",
    "queued",
    "running",
    "complete",
    "unverified",
    "missing",
];
const RESEARCH_PLAN_ACTIVITIES: [&str; 2] = ["material", "time"];
const RESEARCH_ACTIVE_JOB_STATUSES: [&str; 3] = ["active", "paused", "ready"];
const RESEARCH_FACILITY_EVIDENCE: [&str; 3] = ["none", "active-job", "last-owner-job"];
const PRODUCTION_ACTIVITIES: [&str; 2] = ["manufacturing", "reaction"];
const PRODUCTION_PLAN_STATES: [&str; 5] = [
    "ready",
    "sde-unavailable",
    "recipe-missing",
    "cycle",
    "complexity-limit",
];
const PRODUCTION_PLAN_SORT_FIELDS: [&str; 6] = [
    "priority", "product", "owner", "activity", "state", "updated",
];
const SORT_DIRECTIONS: [&str; 2] = ["asc", "desc"];
const MAX_ASSET_PAGE_SIZE: u64 = 200;
const MAX_ASSET_SEARCH_CHARACTERS: usize = 120;
const JAVASCRIPT_MAX_SAFE_INTEGER: u64 = 9_007_199_254_740_991;

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeSnapshot {
    state: &'static str,
    version: &'static str,
    desktop_shell: bool,
    single_instance: bool,
    distribution: &'static str,
    sidecar: &'static str,
    database: &'static str,
    database_location: &'static str,
    schema_version: Option<u32>,
    error_code: Option<&'static str>,
    data: RuntimeDataSnapshot,
    updater: RuntimeUpdaterSnapshot,
    appearance: RuntimeAppearanceSnapshot,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeDataSnapshot {
    state: String,
    has_cached_data: bool,
    observed_at: Option<String>,
    expires_at: Option<String>,
    age_seconds: Option<u64>,
    last_sync_status: String,
    error_code: Option<String>,
}

impl RuntimeDataSnapshot {
    fn loading() -> Self {
        Self {
            state: "loading".to_owned(),
            has_cached_data: false,
            observed_at: None,
            expires_at: None,
            age_seconds: None,
            last_sync_status: "never".to_owned(),
            error_code: None,
        }
    }

    fn failed(error_code: &'static str) -> Self {
        Self {
            state: "error".to_owned(),
            error_code: Some(error_code.to_owned()),
            ..Self::loading()
        }
    }
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeUpdaterSnapshot {
    channel: String,
    manifest_state: String,
    public_distribution: bool,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeAppearanceSnapshot {
    font_scale: String,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct SsoCharacterIdentity {
    character_id: u64,
    name: String,
    scopes: Vec<String>,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct SsoLoginStatus {
    state: String,
    attempt_id: Option<String>,
    scope_packages: Vec<String>,
    expires_at: Option<String>,
    error_code: Option<String>,
    character: Option<SsoCharacterIdentity>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct SsoLoginStart {
    authorization_url: String,
    status: SsoLoginStatus,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ScopePackageStatus {
    id: String,
    status: String,
    granted_count: u8,
    required_count: u8,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct EveCharacterRecord {
    character_id: u64,
    name: String,
    alias: Option<String>,
    account_group_id: Option<u64>,
    account_group_label: Option<String>,
    enabled: bool,
    scopes: Vec<String>,
    credential_state: String,
    scope_packages: Vec<ScopePackageStatus>,
}

#[derive(Deserialize, Serialize)]
struct EveCharactersResponse {
    characters: Vec<EveCharacterRecord>,
}

#[derive(Deserialize, Serialize)]
struct EveCharacterResponse {
    character: EveCharacterRecord,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AccountGroupRecord {
    id: u64,
    label: String,
    sort_order: u64,
    character_count: u64,
}

#[derive(Deserialize, Serialize)]
struct AccountGroupsResponse {
    groups: Vec<AccountGroupRecord>,
}

#[derive(Deserialize, Serialize)]
struct AccountGroupResponse {
    group: AccountGroupRecord,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct CharacterDeletionResponse {
    deleted: bool,
    character_id: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AccountGroupDeletionResponse {
    deleted: bool,
    group_id: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetLocationNode {
    location_id: u64,
    kind: String,
    name: Option<String>,
    access: String,
    type_id: Option<u64>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetRecord {
    item_id: u64,
    type_id: u64,
    type_name: String,
    quantity: u64,
    owner_character_id: u64,
    owner_name: String,
    location_flag: String,
    location_status: String,
    location_path: String,
    location_nodes: Vec<AssetLocationNode>,
    observed_at: String,
    age_seconds: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetOwner {
    character_id: u64,
    name: String,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetQueryResponse {
    items: Vec<AssetRecord>,
    total: u64,
    quantity_total: u64,
    offset: u64,
    limit: u64,
    owners: Vec<AssetOwner>,
    location_statuses: Vec<String>,
    observed_at: Option<String>,
    age_seconds: Option<u64>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetSummaryOwner {
    character_id: u64,
    name: String,
    quantity: u64,
    position_count: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetSummaryRecord {
    type_id: u64,
    type_name: String,
    quantity_total: u64,
    position_count: u64,
    owner_count: u64,
    location_count: u64,
    owners: Vec<AssetSummaryOwner>,
    location_statuses: Vec<String>,
    age_seconds: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetSummaryQueryResponse {
    items: Vec<AssetSummaryRecord>,
    total: u64,
    position_total: u64,
    quantity_total: u64,
    offset: u64,
    limit: u64,
    owners: Vec<AssetOwner>,
    location_statuses: Vec<String>,
    observed_at: Option<String>,
    age_seconds: Option<u64>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetExportResponse {
    filename: String,
    relative_path: String,
    rows: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetSyncCharacterResponse {
    character_id: u64,
    status: String,
    pages: u64,
    assets: u64,
    resolved: u64,
    restricted: u64,
    unresolved: u64,
    cycles: u64,
    error_code: Option<String>,
}

#[derive(Deserialize, Serialize)]
struct AssetSyncResponse {
    characters: Vec<AssetSyncCharacterResponse>,
    completed: u64,
    partial: u64,
    failed: u64,
    assets: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct BlueprintRecord {
    item_id: u64,
    type_id: u64,
    type_name: String,
    owner_character_id: u64,
    owner_name: String,
    kind: String,
    material_efficiency: u8,
    time_efficiency: u8,
    runs: i64,
    location_id: u64,
    location_flag: String,
    observed_at: String,
    age_seconds: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct BlueprintQueryResponse {
    items: Vec<BlueprintRecord>,
    total: u64,
    offset: u64,
    limit: u64,
    owners: Vec<AssetOwner>,
    snapshots: Vec<BlueprintSnapshotStatus>,
    observed_at: Option<String>,
    age_seconds: Option<u64>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct BlueprintSnapshotStatus {
    character_id: u64,
    name: String,
    state: String,
    item_count: u64,
    observed_at: Option<String>,
    age_seconds: Option<u64>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct BlueprintSyncCharacterResponse {
    character_id: u64,
    status: String,
    pages: u64,
    blueprints: u64,
    error_code: Option<String>,
}

#[derive(Deserialize, Serialize)]
struct BlueprintSyncResponse {
    characters: Vec<BlueprintSyncCharacterResponse>,
    completed: u64,
    failed: u64,
    blueprints: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct IndustryBlueprintCorrelation {
    state: String,
    snapshot_id: Option<u64>,
    sync_run_id: Option<u64>,
    observed_at: Option<String>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct IndustryAssetCorrelation {
    state: String,
    event_ids: Vec<String>,
    candidate_count: u64,
    location_matched: bool,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct IndustryJobRecord {
    job_id: u64,
    owner_character_id: u64,
    owner_name: String,
    activity_id: u8,
    activity_key: String,
    status: String,
    blueprint_item_id: u64,
    blueprint_type_id: u64,
    blueprint_name: String,
    product_type_id: Option<u64>,
    product_name: Option<String>,
    runs: u64,
    successful_runs: Option<u64>,
    licensed_runs: Option<u64>,
    probability: Option<f64>,
    cost: Option<f64>,
    duration_seconds: u64,
    facility_id: u64,
    facility_name: Option<String>,
    facility_kind: String,
    facility_access: String,
    solar_system_id: Option<u64>,
    solar_system_name: Option<String>,
    system_cost_index: Option<f64>,
    station_id: u64,
    blueprint_location_id: u64,
    output_location_id: u64,
    start_date: String,
    end_date: String,
    completed_date: Option<String>,
    pause_date: Option<String>,
    blueprint_correlation: IndustryBlueprintCorrelation,
    asset_correlation: IndustryAssetCorrelation,
    correlation_state: String,
    job_snapshot_id: u64,
    job_sync_run_id: u64,
    observed_at: String,
    age_seconds: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct IndustryJobQueryResponse {
    items: Vec<IndustryJobRecord>,
    total: u64,
    active_total: u64,
    offset: u64,
    limit: u64,
    owners: Vec<AssetOwner>,
    statuses: Vec<String>,
    activities: Vec<u8>,
    correlations: Vec<String>,
    observed_at: Option<String>,
    age_seconds: Option<u64>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct IndustryJobSyncCharacterResponse {
    character_id: u64,
    status: String,
    jobs: u64,
    active: u64,
    completed_jobs: u64,
    error_code: Option<String>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct IndustryJobSyncResponse {
    characters: Vec<IndustryJobSyncCharacterResponse>,
    completed: u64,
    failed: u64,
    jobs: u64,
    active: u64,
    completed_jobs: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct IndustryFacilityRecord {
    facility_id: u64,
    facility_name: Option<String>,
    kind: String,
    access: String,
    type_id: Option<u64>,
    type_name: Option<String>,
    owner_id: Option<u64>,
    owner_name: Option<String>,
    region_id: Option<u64>,
    region_name: Option<String>,
    solar_system_id: Option<u64>,
    solar_system_name: Option<String>,
    security_status: Option<f64>,
    security_class: String,
    tax: Option<f64>,
    activity_cost_index: Option<f64>,
    used_by_character_ids: Vec<u64>,
    observed_activity_ids: Vec<u8>,
    job_count: u64,
    active_jobs: u64,
    error_code: Option<String>,
    snapshot_id: u64,
    sync_run_id: u64,
    observed_at: String,
    age_seconds: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct IndustryFacilityQueryResponse {
    items: Vec<IndustryFacilityRecord>,
    total: u64,
    npc_facilities: u64,
    observed_facilities: u64,
    restricted_structures: u64,
    systems: u64,
    offset: u64,
    limit: u64,
    activity: String,
    activities: Vec<String>,
    kinds: Vec<String>,
    access_states: Vec<String>,
    security_classes: Vec<String>,
    observed_at: Option<String>,
    age_seconds: Option<u64>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct IndustryFacilitySyncResponse {
    sync_run_id: u64,
    facilities: u64,
    npc_facilities: u64,
    observed_facilities: u64,
    restricted_structures: u64,
    systems: u64,
    resolved_names: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct IndustrySlotActivity {
    activity: String,
    capacity: Option<u8>,
    occupied: Option<u64>,
    available: Option<u8>,
    utilization_state: String,
    active_jobs: Option<u64>,
    paused_jobs: Option<u64>,
    ready_jobs: Option<u64>,
    next_job_end_date: Option<String>,
    primary_skill_id: u64,
    primary_skill_level: Option<u8>,
    advanced_skill_id: u64,
    advanced_skill_level: Option<u8>,
    queued_plans: Option<u64>,
    blocked_plans: Option<u64>,
    running_plans: Option<u64>,
    complete_plans: Option<u64>,
    planning_available: bool,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct IndustrySlotRecord {
    character_id: u64,
    name: String,
    activities: Vec<IndustrySlotActivity>,
    skill_snapshot_id: Option<u64>,
    skill_sync_run_id: Option<u64>,
    skill_observed_at: Option<String>,
    job_snapshot_id: Option<u64>,
    job_sync_run_id: Option<u64>,
    job_observed_at: Option<String>,
    observed_at: Option<String>,
    age_seconds: Option<u64>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct IndustrySlotQueryResponse {
    items: Vec<IndustrySlotRecord>,
    total: u64,
    offset: u64,
    limit: u64,
    owners: Vec<AssetOwner>,
    activities: Vec<String>,
    observed_at: Option<String>,
    age_seconds: Option<u64>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ResearchPlanOwner {
    character_id: u64,
    name: String,
    slot_capacity: Option<u8>,
    slots_used: u64,
    slots_available: Option<u8>,
    laboratory_operation_level: u8,
    advanced_laboratory_operation_level: u8,
    research_level: u8,
    metallurgy_level: u8,
    skill_snapshot_id: Option<u64>,
    skill_sync_run_id: Option<u64>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ResearchPlanRecord {
    owner_character_id: u64,
    owner_name: String,
    blueprint_item_id: u64,
    blueprint_type_id: u64,
    blueprint_name: String,
    blueprint_present: bool,
    current_material_efficiency: Option<u8>,
    current_time_efficiency: Option<u8>,
    location_id: Option<u64>,
    location_flag: Option<String>,
    planned: bool,
    next_activity: String,
    target_material_efficiency: u8,
    target_time_efficiency: u8,
    priority: u16,
    note: Option<String>,
    state: String,
    slot_capacity: Option<u8>,
    slots_used: u64,
    slots_available: Option<u8>,
    research_level: u8,
    metallurgy_level: u8,
    active_job_id: Option<u64>,
    active_job_activity: Option<String>,
    active_job_status: Option<String>,
    active_job_start_date: Option<String>,
    active_job_end_date: Option<String>,
    active_job_cost: Option<f64>,
    facility_id: Option<u64>,
    facility_name: Option<String>,
    facility_access: String,
    solar_system_name: Option<String>,
    system_cost_index: Option<f64>,
    facility_evidence: String,
    blueprint_snapshot_id: Option<u64>,
    blueprint_sync_run_id: Option<u64>,
    skill_snapshot_id: Option<u64>,
    skill_sync_run_id: Option<u64>,
    job_snapshot_id: Option<u64>,
    job_sync_run_id: Option<u64>,
    observed_at: Option<String>,
    age_seconds: Option<u64>,
    created_at: Option<String>,
    updated_at: Option<String>,
}

#[derive(Deserialize, Serialize)]
struct ResearchPlanSummary {
    unplanned: u64,
    ready: u64,
    queued: u64,
    running: u64,
    complete: u64,
    unverified: u64,
    missing: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ResearchPlanQueryResponse {
    items: Vec<ResearchPlanRecord>,
    total: u64,
    offset: u64,
    limit: u64,
    owners: Vec<ResearchPlanOwner>,
    states: Vec<String>,
    activities: Vec<String>,
    summary: ResearchPlanSummary,
    observed_at: Option<String>,
    age_seconds: Option<u64>,
    estimates_available: bool,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ResearchPlanMutationResponse {
    owner_character_id: u64,
    blueprint_item_id: u64,
    blueprint_type_id: u64,
    next_activity: String,
    target_material_efficiency: u8,
    target_time_efficiency: u8,
    priority: u16,
    note: Option<String>,
    saved: bool,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ResearchPlanDeleteResponse {
    owner_character_id: u64,
    blueprint_item_id: u64,
    deleted: bool,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionCatalogItem {
    blueprint_type_id: u64,
    blueprint_name: String,
    activity: String,
    base_time_seconds: u64,
    product_type_id: u64,
    product_name: String,
    output_quantity: u64,
    material_count: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionCatalogResponse {
    items: Vec<ProductionCatalogItem>,
    total: u64,
    offset: u64,
    limit: u64,
    activities: Vec<String>,
    build_number: Option<String>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionStepMaterial {
    type_id: u64,
    type_name: String,
    quantity_per_run: u64,
    gross_quantity: u64,
    produced_by_plan: bool,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionStep {
    sequence: u64,
    blueprint_type_id: u64,
    blueprint_name: String,
    activity: String,
    product_type_id: u64,
    product_name: String,
    required_quantity: u64,
    output_quantity_per_run: u64,
    runs: u64,
    produced_quantity: u64,
    surplus_quantity: u64,
    base_time_seconds_per_run: u64,
    total_base_time_seconds: u64,
    recipe_alternatives: u64,
    materials: Vec<ProductionStepMaterial>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionGrossMaterial {
    type_id: u64,
    type_name: String,
    quantity: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionWarning {
    code: String,
    type_id: u64,
    type_name: String,
    selected_blueprint_type_id: u64,
    candidate_count: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionPlanRecord {
    plan_id: u64,
    owner_character_id: u64,
    owner_name: String,
    blueprint_type_id: u64,
    blueprint_name: String,
    activity: String,
    product_type_id: u64,
    product_name: String,
    target_quantity: u64,
    priority: u16,
    note: Option<String>,
    state: String,
    build_number: Option<String>,
    steps: Vec<ProductionStep>,
    gross_materials: Vec<ProductionGrossMaterial>,
    warnings: Vec<ProductionWarning>,
    cycle_type_ids: Vec<u64>,
    total_base_time_seconds: Option<u64>,
    created_at: String,
    updated_at: String,
}

#[derive(Deserialize, Serialize)]
struct ProductionPlanSummary {
    ready: u64,
    #[serde(rename = "sde-unavailable")]
    sde_unavailable: u64,
    #[serde(rename = "recipe-missing")]
    recipe_missing: u64,
    cycle: u64,
    #[serde(rename = "complexity-limit")]
    complexity_limit: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionPlanQueryResponse {
    items: Vec<ProductionPlanRecord>,
    total: u64,
    offset: u64,
    limit: u64,
    owners: Vec<AssetOwner>,
    activities: Vec<String>,
    states: Vec<String>,
    summary: ProductionPlanSummary,
    build_number: Option<String>,
    inventory_applied: bool,
    modifiers_applied: bool,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionPlanMutationResponse {
    saved: bool,
    plan_id: u64,
    owner_character_id: u64,
    blueprint_type_id: u64,
    activity: String,
    product_type_id: u64,
    target_quantity: u64,
    priority: u16,
    note: Option<String>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionPlanDeleteResponse {
    deleted: bool,
    plan_id: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct PublicReleaseNotice {
    state: String,
    channel: String,
    current_version: String,
    latest_version: Option<String>,
    release_url: Option<String>,
    published_at: Option<String>,
    automatic_install: bool,
    error_code: Option<String>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct CharacterSkillRecord {
    skill_id: u64,
    skill_name: String,
    owner_character_id: u64,
    owner_name: String,
    trained_level: u8,
    active_level: u8,
    skillpoints: u64,
    active_state: String,
    snapshot_id: u64,
    sync_run_id: u64,
    observed_at: String,
    age_seconds: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct CharacterSkillQueryResponse {
    items: Vec<CharacterSkillRecord>,
    total: u64,
    total_sp: u64,
    unallocated_sp: u64,
    offset: u64,
    limit: u64,
    owners: Vec<AssetOwner>,
    levels: Vec<u8>,
    active_states: Vec<String>,
    observed_at: Option<String>,
    age_seconds: Option<u64>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct CharacterSkillSyncCharacterResponse {
    character_id: u64,
    status: String,
    skills: u64,
    total_sp: u64,
    unallocated_sp: u64,
    error_code: Option<String>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct CharacterSkillSyncResponse {
    characters: Vec<CharacterSkillSyncCharacterResponse>,
    completed: u64,
    failed: u64,
    skills: u64,
    total_sp: u64,
    unallocated_sp: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetDeltaCorrelation {
    state: String,
    key: String,
    direction: String,
    window_start: String,
    window_end: String,
    job_ids: Vec<u64>,
    candidate_count: u64,
    location_matched: bool,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetDeltaRecord {
    event_id: String,
    item_id: u64,
    type_id: u64,
    type_name: String,
    owner_character_id: u64,
    owner_name: String,
    change_types: Vec<String>,
    quantity_before: Option<u64>,
    quantity_after: Option<u64>,
    quantity_delta: i64,
    location_id_before: Option<u64>,
    location_id_after: Option<u64>,
    location_type_before: Option<String>,
    location_type_after: Option<String>,
    location_flag_before: Option<String>,
    location_flag_after: Option<String>,
    previous_asset_snapshot_id: u64,
    current_asset_snapshot_id: u64,
    current_asset_sync_run_id: u64,
    observed_at: String,
    age_seconds: u64,
    job_correlation: AssetDeltaCorrelation,
}

#[derive(Deserialize, Serialize)]
struct AssetDeltaSummary {
    added: u64,
    removed: u64,
    quantity: u64,
    location: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetDeltaQueryResponse {
    items: Vec<AssetDeltaRecord>,
    total: u64,
    offset: u64,
    limit: u64,
    owners: Vec<AssetOwner>,
    change_types: Vec<String>,
    summary: AssetDeltaSummary,
    has_baseline: bool,
    observed_at: Option<String>,
    age_seconds: Option<u64>,
}

impl RuntimeUpdaterSnapshot {
    fn checking() -> Self {
        Self {
            channel: "stable".to_owned(),
            manifest_state: "checking".to_owned(),
            public_distribution: false,
        }
    }

    fn unavailable() -> Self {
        Self {
            manifest_state: "unavailable".to_owned(),
            ..Self::checking()
        }
    }
}

impl RuntimeAppearanceSnapshot {
    fn normal() -> Self {
        Self {
            font_scale: "normal".to_owned(),
        }
    }
}

impl RuntimeSnapshot {
    fn starting() -> Self {
        Self {
            state: "ready",
            version: env!("CARGO_PKG_VERSION"),
            desktop_shell: true,
            single_instance: true,
            distribution: runtime_distribution(),
            sidecar: "starting",
            database: "starting",
            database_location: DATABASE_LOCATION,
            schema_version: None,
            error_code: None,
            data: RuntimeDataSnapshot::loading(),
            updater: RuntimeUpdaterSnapshot::checking(),
            appearance: RuntimeAppearanceSnapshot::normal(),
        }
    }

    fn ready(
        schema_version: u32,
        data: RuntimeDataSnapshot,
        updater: RuntimeUpdaterSnapshot,
        appearance: RuntimeAppearanceSnapshot,
    ) -> Self {
        Self {
            sidecar: "ready",
            database: "ready",
            schema_version: Some(schema_version),
            data,
            updater,
            appearance,
            ..Self::starting()
        }
    }

    fn failed(error_code: &'static str) -> Self {
        Self {
            sidecar: "error",
            database: "error",
            error_code: Some(error_code),
            data: RuntimeDataSnapshot::failed(error_code),
            updater: RuntimeUpdaterSnapshot::unavailable(),
            ..Self::starting()
        }
    }
}

fn runtime_distribution() -> &'static str {
    std::env::current_exe()
        .ok()
        .and_then(|path| path.parent().map(Path::to_path_buf))
        .is_some_and(|directory| directory.join(PORTABLE_MARKER).is_file())
        .then_some("portable")
        .unwrap_or("installed")
}

struct SidecarProcess {
    child: Child,
    session_token: String,
    port: u16,
}

struct RuntimeState {
    snapshot: Mutex<RuntimeSnapshot>,
    sidecar: Mutex<Option<SidecarProcess>>,
    shutting_down: AtomicBool,
}

impl RuntimeState {
    fn new() -> Self {
        Self {
            snapshot: Mutex::new(RuntimeSnapshot::starting()),
            sidecar: Mutex::new(None),
            shutting_down: AtomicBool::new(false),
        }
    }

    fn set_snapshot(&self, snapshot: RuntimeSnapshot) {
        *self
            .snapshot
            .lock()
            .unwrap_or_else(|error| error.into_inner()) = snapshot;
    }
}

#[derive(Deserialize)]
struct SidecarReady {
    event: String,
    protocol: u8,
    host: String,
    port: u16,
    database: SidecarDatabaseReady,
    data: RuntimeDataSnapshot,
    updater: RuntimeUpdaterSnapshot,
    appearance: RuntimeAppearanceSnapshot,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct SidecarDatabaseReady {
    state: String,
    schema_version: u32,
    location: String,
}

fn session_token() -> Result<String, &'static str> {
    let mut random_bytes = [0_u8; 32];
    getrandom::fill(&mut random_bytes).map_err(|_| "session-token-failed")?;
    Ok(random_bytes
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect())
}

fn terminate_child(child: &mut Child) {
    let _ = child.kill();
    let _ = child.wait();
}

fn data_snapshot_is_valid(data: &RuntimeDataSnapshot) -> bool {
    let state_is_valid = matches!(
        data.state.as_str(),
        "loading" | "refreshing" | "empty" | "fresh" | "stale" | "offline" | "error"
    );
    let sync_status_is_valid = matches!(
        data.last_sync_status.as_str(),
        "never" | "running" | "completed" | "failed" | "cancelled"
    );
    let cache_fields_are_valid = if data.has_cached_data {
        data.observed_at.is_some()
    } else {
        data.observed_at.is_none() && data.expires_at.is_none() && data.age_seconds.is_none()
    };
    let state_combination_is_valid = match data.state.as_str() {
        "loading" | "empty" => !data.has_cached_data && data.error_code.is_none(),
        "refreshing" | "stale" => data.has_cached_data && data.age_seconds.is_some(),
        // The backend intentionally treats snapshots without an explicit expiry as
        // fresh for the first two hours. Older databases can therefore report a
        // valid fresh cache with `expiresAt: null` during startup.
        "fresh" => data.has_cached_data && data.age_seconds.is_some(),
        "offline" | "error" => data.error_code.is_some(),
        _ => false,
    };
    state_is_valid && sync_status_is_valid && cache_fields_are_valid && state_combination_is_valid
}

fn updater_snapshot_is_valid(updater: &RuntimeUpdaterSnapshot) -> bool {
    matches!(updater.channel.as_str(), "stable" | "beta" | "preview")
        && matches!(updater.manifest_state.as_str(), "verified" | "invalid")
        && !updater.public_distribution
}

fn appearance_snapshot_is_valid(appearance: &RuntimeAppearanceSnapshot) -> bool {
    FONT_SCALES.contains(&appearance.font_scale.as_str())
}

fn sso_character_identity_is_valid(character: &SsoCharacterIdentity) -> bool {
    character.character_id > 0
        && !character.name.trim().is_empty()
        && character.name.trim() == character.name
        && character.name.len() <= 100
        && !character.scopes.is_empty()
        && character.scopes.iter().collect::<HashSet<_>>().len() == character.scopes.len()
        && character.scopes.iter().all(|scope| {
            !scope.is_empty()
                && scope.len() <= 200
                && scope.starts_with("esi-")
                && scope.ends_with(".v1")
        })
}

fn management_label_is_valid(label: &str) -> bool {
    !label.is_empty() && label.trim() == label && label.len() <= 80
}

fn scope_package_required_count(id: &str) -> Option<u8> {
    match id {
        "industry-core" => Some(4),
        "market" => Some(2),
        "planetary-industry" | "projects" | "private-structures" => Some(1),
        _ => None,
    }
}

fn scope_package_status_is_valid(package: &ScopePackageStatus) -> bool {
    let Some(required_count) = scope_package_required_count(&package.id) else {
        return false;
    };
    let expected_status = if package.granted_count == 0 {
        "missing"
    } else if package.granted_count == package.required_count {
        "granted"
    } else {
        "partial"
    };
    package.required_count == required_count
        && package.granted_count <= package.required_count
        && package.status == expected_status
}

fn account_group_record_is_valid(group: &AccountGroupRecord) -> bool {
    group.id > 0 && management_label_is_valid(&group.label)
}

fn asset_text_is_valid(value: &str, maximum: usize) -> bool {
    !value.is_empty() && value.trim() == value && value.chars().count() <= maximum
}

fn asset_query_response_is_valid(response: &AssetQueryResponse) -> bool {
    let owner_ids = response
        .owners
        .iter()
        .map(|owner| owner.character_id)
        .collect::<HashSet<_>>();
    let item_ids = response
        .items
        .iter()
        .map(|item| item.item_id)
        .collect::<HashSet<_>>();
    let statuses = response
        .location_statuses
        .iter()
        .map(String::as_str)
        .collect::<Vec<_>>();
    response.limit > 0
        && response.limit <= MAX_ASSET_PAGE_SIZE
        && response.total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.quantity_total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.offset <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.items.len() as u64 <= response.limit
        && response.items.len() as u64 <= response.total
        && item_ids.len() == response.items.len()
        && owner_ids.len() == response.owners.len()
        && response.owners.iter().all(|owner| {
            owner.character_id > 0
                && owner.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&owner.name, 100)
        })
        && statuses.as_slice() == ASSET_LOCATION_STATUSES.as_slice()
        && response.observed_at.is_some() == response.age_seconds.is_some()
        && response
            .observed_at
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 64))
        && response.items.iter().all(|item| {
            item.item_id > 0
                && item.item_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && item.type_id > 0
                && item.type_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && item.quantity <= JAVASCRIPT_MAX_SAFE_INTEGER
                && owner_ids.contains(&item.owner_character_id)
                && response.owners.iter().any(|owner| {
                    owner.character_id == item.owner_character_id && owner.name == item.owner_name
                })
                && asset_text_is_valid(&item.type_name, 220)
                && asset_text_is_valid(&item.owner_name, 100)
                && asset_text_is_valid(&item.location_flag, 100)
                && ASSET_LOCATION_STATUSES.contains(&item.location_status.as_str())
                && asset_text_is_valid(&item.observed_at, 64)
                && ((item.location_status == "pending"
                    && item.location_path.is_empty()
                    && item.location_nodes.is_empty())
                    || (item.location_status != "pending"
                        && !item.location_path.is_empty()
                        && !item.location_nodes.is_empty()))
                && item.location_path.chars().count() <= 20_000
                && item.location_nodes.len() <= 64
                && item.location_nodes.iter().all(|node| {
                    node.location_id > 0
                        && node.location_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                        && asset_text_is_valid(&node.kind, 40)
                        && asset_text_is_valid(&node.access, 40)
                        && node
                            .name
                            .as_ref()
                            .is_none_or(|name| asset_text_is_valid(name, 200))
                        && node.type_id != Some(0)
                        && node
                            .type_id
                            .is_none_or(|type_id| type_id <= JAVASCRIPT_MAX_SAFE_INTEGER)
                })
        })
}

fn asset_summary_query_response_is_valid(response: &AssetSummaryQueryResponse) -> bool {
    let owner_ids = response
        .owners
        .iter()
        .map(|owner| owner.character_id)
        .collect::<HashSet<_>>();
    let type_ids = response
        .items
        .iter()
        .map(|item| item.type_id)
        .collect::<HashSet<_>>();
    let statuses = response
        .location_statuses
        .iter()
        .map(String::as_str)
        .collect::<Vec<_>>();
    response.limit > 0
        && response.limit <= MAX_ASSET_PAGE_SIZE
        && response.total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.position_total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.quantity_total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.offset <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.items.len() as u64 <= response.limit
        && response.items.len() as u64 <= response.total
        && type_ids.len() == response.items.len()
        && owner_ids.len() == response.owners.len()
        && statuses.as_slice() == ASSET_LOCATION_STATUSES.as_slice()
        && response.observed_at.is_some() == response.age_seconds.is_some()
        && response
            .observed_at
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 64))
        && response.owners.iter().all(|owner| {
            owner.character_id > 0
                && owner.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&owner.name, 100)
        })
        && response.items.iter().all(|item| {
            let item_owner_ids = item
                .owners
                .iter()
                .map(|owner| owner.character_id)
                .collect::<HashSet<_>>();
            let item_statuses = item
                .location_statuses
                .iter()
                .map(String::as_str)
                .collect::<HashSet<_>>();
            let owner_quantity = item
                .owners
                .iter()
                .try_fold(0_u64, |sum, owner| sum.checked_add(owner.quantity));
            let owner_positions = item
                .owners
                .iter()
                .try_fold(0_u64, |sum, owner| sum.checked_add(owner.position_count));
            item.type_id > 0
                && item.type_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&item.type_name, 220)
                && item.quantity_total <= JAVASCRIPT_MAX_SAFE_INTEGER
                && item.position_count > 0
                && item.position_count <= response.position_total
                && item.owner_count == item.owners.len() as u64
                && item.owner_count > 0
                && item.location_count > 0
                && item.location_count <= item.position_count
                && item_owner_ids.len() == item.owners.len()
                && item_statuses.len() == item.location_statuses.len()
                && item
                    .location_statuses
                    .iter()
                    .all(|status| ASSET_LOCATION_STATUSES.contains(&status.as_str()))
                && !item.location_statuses.is_empty()
                && item.owners.iter().all(|owner| {
                    owner.character_id > 0
                        && owner.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                        && response.owners.iter().any(|candidate| {
                            candidate.character_id == owner.character_id
                                && candidate.name == owner.name
                        })
                        && asset_text_is_valid(&owner.name, 100)
                        && owner.quantity <= JAVASCRIPT_MAX_SAFE_INTEGER
                        && owner.position_count > 0
                        && owner.position_count <= item.position_count
                })
                && owner_quantity == Some(item.quantity_total)
                && owner_positions == Some(item.position_count)
        })
}

fn blueprint_query_response_is_valid(response: &BlueprintQueryResponse) -> bool {
    let owner_ids = response
        .owners
        .iter()
        .map(|owner| owner.character_id)
        .collect::<HashSet<_>>();
    let item_ids = response
        .items
        .iter()
        .map(|item| item.item_id)
        .collect::<HashSet<_>>();
    response.limit > 0
        && response.limit <= MAX_ASSET_PAGE_SIZE
        && response.total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.offset <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.items.len() as u64 <= response.limit
        && response.items.len() as u64 <= response.total
        && item_ids.len() == response.items.len()
        && owner_ids.len() == response.owners.len()
        && response.snapshots.len() == response.owners.len()
        && response
            .snapshots
            .iter()
            .map(|snapshot| snapshot.character_id)
            .collect::<HashSet<_>>()
            .len()
            == response.snapshots.len()
        && response.observed_at.is_some() == response.age_seconds.is_some()
        && response
            .observed_at
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 64))
        && response.owners.iter().all(|owner| {
            owner.character_id > 0
                && owner.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&owner.name, 100)
        })
        && response.snapshots.iter().all(|snapshot| {
            owner_ids.contains(&snapshot.character_id)
                && response.owners.iter().any(|owner| {
                    owner.character_id == snapshot.character_id && owner.name == snapshot.name
                })
                && matches!(snapshot.state.as_str(), "available" | "missing")
                && snapshot.item_count <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&snapshot.name, 100)
                && snapshot.observed_at.is_some() == snapshot.age_seconds.is_some()
                && ((snapshot.state == "available" && snapshot.observed_at.is_some())
                    || (snapshot.state == "missing"
                        && snapshot.item_count == 0
                        && snapshot.observed_at.is_none()))
                && snapshot
                    .observed_at
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 64))
        })
        && response.items.iter().all(|item| {
            item.item_id > 0
                && item.item_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && item.type_id > 0
                && item.type_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && owner_ids.contains(&item.owner_character_id)
                && asset_text_is_valid(&item.type_name, 220)
                && asset_text_is_valid(&item.owner_name, 100)
                && matches!(item.kind.as_str(), "original" | "copy")
                && item.material_efficiency <= 10
                && item.time_efficiency <= 20
                && item.runs >= -1
                && item.runs <= JAVASCRIPT_MAX_SAFE_INTEGER as i64
                && item.location_id > 0
                && item.location_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&item.location_flag, 100)
                && asset_text_is_valid(&item.observed_at, 64)
        })
}

fn blueprint_sync_response_is_valid(response: &BlueprintSyncResponse) -> bool {
    response.completed + response.failed == response.characters.len() as u64
        && response.blueprints
            == response
                .characters
                .iter()
                .map(|item| item.blueprints)
                .sum::<u64>()
        && response.characters.iter().all(|item| {
            item.character_id > 0
                && item.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && matches!(item.status.as_str(), "completed" | "failed")
                && ((item.status == "completed" && item.error_code.is_none())
                    || (item.status == "failed"
                        && item.pages == 0
                        && item.blueprints == 0
                        && item
                            .error_code
                            .as_ref()
                            .is_some_and(|code| !code.is_empty() && code.len() <= 120)))
        })
}

fn industry_activity_key(activity_id: u8) -> Option<&'static str> {
    match activity_id {
        1 => Some("manufacturing"),
        3 => Some("research-time"),
        4 => Some("research-material"),
        5 => Some("copying"),
        7 => Some("reverse-engineering"),
        8 => Some("invention"),
        9 | 11 => Some("reactions"),
        _ => None,
    }
}

fn industry_blueprint_correlation_is_valid(value: &IndustryBlueprintCorrelation) -> bool {
    match value.state.as_str() {
        "current" | "historical" => {
            value
                .snapshot_id
                .is_some_and(|id| id > 0 && id <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && value
                    .sync_run_id
                    .is_some_and(|id| id > 0 && id <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && value
                    .observed_at
                    .as_ref()
                    .is_some_and(|timestamp| asset_text_is_valid(timestamp, 64))
        }
        "unmatched" | "unavailable" => {
            value.snapshot_id.is_none()
                && value.sync_run_id.is_none()
                && value.observed_at.is_none()
        }
        _ => false,
    }
}

fn industry_asset_correlation_is_valid(value: &IndustryAssetCorrelation) -> bool {
    let unique_event_ids = value.event_ids.iter().collect::<HashSet<_>>();
    value.candidate_count <= JAVASCRIPT_MAX_SAFE_INTEGER
        && value.event_ids.len() <= 20
        && unique_event_ids.len() == value.event_ids.len()
        && value.event_ids.iter().all(|event_id| {
            event_id.len() == 64
                && event_id
                    .bytes()
                    .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
        })
        && match value.state.as_str() {
            "linked" => value.candidate_count == 1 && value.event_ids.len() == 1,
            "ambiguous" => value.candidate_count > 1 && !value.event_ids.is_empty(),
            "unmatched" | "unavailable" | "pending" | "not-applicable" => {
                value.candidate_count == 0 && value.event_ids.is_empty() && !value.location_matched
            }
            _ => false,
        }
}

fn industry_job_query_response_is_valid(response: &IndustryJobQueryResponse) -> bool {
    let owner_ids = response
        .owners
        .iter()
        .map(|owner| owner.character_id)
        .collect::<HashSet<_>>();
    let job_ids = response
        .items
        .iter()
        .map(|job| job.job_id)
        .collect::<HashSet<_>>();
    let activities = response.activities.iter().copied().collect::<HashSet<_>>();
    let active_items = response
        .items
        .iter()
        .filter(|job| matches!(job.status.as_str(), "active" | "paused" | "ready"))
        .count() as u64;
    response.limit > 0
        && response.limit <= MAX_ASSET_PAGE_SIZE
        && response.total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.active_total <= response.total
        && active_items <= response.active_total
        && response.offset <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.items.len() as u64 <= response.limit
        && response.items.len() as u64 <= response.total
        && response.observed_at.is_some() == response.age_seconds.is_some()
        && response
            .observed_at
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 64))
        && response
            .statuses
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == INDUSTRY_JOB_STATUSES
        && response
            .correlations
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == INDUSTRY_JOB_CORRELATIONS
        && activities.len() == response.activities.len()
        && response
            .activities
            .iter()
            .all(|activity| INDUSTRY_JOB_ACTIVITY_IDS.contains(activity))
        && owner_ids.len() == response.owners.len()
        && job_ids.len() == response.items.len()
        && response.owners.iter().all(|owner| {
            owner.character_id > 0
                && owner.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&owner.name, 100)
        })
        && response.items.iter().all(|job| {
            let blueprint_linked = matches!(
                job.blueprint_correlation.state.as_str(),
                "current" | "historical"
            );
            let asset_linked = job.asset_correlation.state == "linked";
            let expected_correlation =
                if matches!(job.status.as_str(), "active" | "paused" | "ready") {
                    "pending"
                } else if job.asset_correlation.state == "ambiguous" {
                    "ambiguous"
                } else if blueprint_linked
                    && (asset_linked || job.asset_correlation.state == "not-applicable")
                {
                    "linked"
                } else if blueprint_linked || asset_linked {
                    "partial"
                } else {
                    "unmatched"
                };
            job.job_id > 0
                && job.job_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && owner_ids.contains(&job.owner_character_id)
                && response.owners.iter().any(|owner| {
                    owner.character_id == job.owner_character_id && owner.name == job.owner_name
                })
                && industry_activity_key(job.activity_id) == Some(job.activity_key.as_str())
                && INDUSTRY_JOB_STATUSES.contains(&job.status.as_str())
                && job.blueprint_item_id > 0
                && job.blueprint_item_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && job.blueprint_type_id > 0
                && job.blueprint_type_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&job.blueprint_name, 220)
                && job.product_type_id.is_some() == job.product_name.is_some()
                && job
                    .product_type_id
                    .is_none_or(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && job
                    .product_name
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 220))
                && job.runs > 0
                && job.runs <= JAVASCRIPT_MAX_SAFE_INTEGER
                && job.successful_runs.is_none_or(|value| value <= job.runs)
                && job
                    .licensed_runs
                    .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && job
                    .probability
                    .is_none_or(|value| value.is_finite() && (0.0..=1.0).contains(&value))
                && job.cost.is_none_or(|value| {
                    value.is_finite() && (0.0..=JAVASCRIPT_MAX_SAFE_INTEGER as f64).contains(&value)
                })
                && job.duration_seconds <= JAVASCRIPT_MAX_SAFE_INTEGER
                && job
                    .facility_name
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 200))
                && INDUSTRY_FACILITY_KINDS.contains(&job.facility_kind.as_str())
                && INDUSTRY_FACILITY_ACCESS_STATES.contains(&job.facility_access.as_str())
                && job.solar_system_id.is_some() == job.solar_system_name.is_some()
                && job
                    .solar_system_id
                    .is_none_or(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && job
                    .solar_system_name
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 200))
                && job
                    .system_cost_index
                    .is_none_or(|value| value.is_finite() && (0.0..=1.0).contains(&value))
                && [
                    job.facility_id,
                    job.station_id,
                    job.blueprint_location_id,
                    job.output_location_id,
                    job.job_snapshot_id,
                    job.job_sync_run_id,
                ]
                .into_iter()
                .all(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && asset_text_is_valid(&job.start_date, 64)
                && asset_text_is_valid(&job.end_date, 64)
                && job
                    .completed_date
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 64))
                && job
                    .pause_date
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 64))
                && industry_blueprint_correlation_is_valid(&job.blueprint_correlation)
                && industry_asset_correlation_is_valid(&job.asset_correlation)
                && job.correlation_state == expected_correlation
                && asset_text_is_valid(&job.observed_at, 64)
                && asset_text_is_valid(&job.owner_name, 100)
        })
}

fn industry_job_sync_response_is_valid(response: &IndustryJobSyncResponse) -> bool {
    let jobs = response
        .characters
        .iter()
        .try_fold(0_u64, |sum, item| sum.checked_add(item.jobs));
    let active = response
        .characters
        .iter()
        .try_fold(0_u64, |sum, item| sum.checked_add(item.active));
    let completed_jobs = response
        .characters
        .iter()
        .try_fold(0_u64, |sum, item| sum.checked_add(item.completed_jobs));
    response.completed.checked_add(response.failed) == Some(response.characters.len() as u64)
        && jobs == Some(response.jobs)
        && active == Some(response.active)
        && completed_jobs == Some(response.completed_jobs)
        && response.characters.iter().all(|item| {
            item.character_id > 0
                && item.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && matches!(item.status.as_str(), "completed" | "failed")
                && item.active.checked_add(item.completed_jobs) == Some(item.jobs)
                && ((item.status == "completed" && item.error_code.is_none())
                    || (item.status == "failed"
                        && item.jobs == 0
                        && item.active == 0
                        && item.completed_jobs == 0
                        && item
                            .error_code
                            .as_ref()
                            .is_some_and(|code| asset_text_is_valid(code, 120))))
        })
}

fn optional_id_name_is_valid(id: Option<u64>, name: &Option<String>) -> bool {
    id.is_some() == name.is_some()
        && id.is_none_or(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && name
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 200))
}

fn industry_facility_record_is_valid(item: &IndustryFacilityRecord) -> bool {
    let character_ids = item.used_by_character_ids.iter().collect::<HashSet<_>>();
    let activity_ids = item.observed_activity_ids.iter().collect::<HashSet<_>>();
    let common = item.facility_id > 0
        && item.facility_id <= JAVASCRIPT_MAX_SAFE_INTEGER
        && item
            .facility_name
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 200))
        && INDUSTRY_FACILITY_KINDS.contains(&item.kind.as_str())
        && INDUSTRY_FACILITY_ACCESS_STATES.contains(&item.access.as_str())
        && optional_id_name_is_valid(item.type_id, &item.type_name)
        && optional_id_name_is_valid(item.owner_id, &item.owner_name)
        && optional_id_name_is_valid(item.region_id, &item.region_name)
        && optional_id_name_is_valid(item.solar_system_id, &item.solar_system_name)
        && item
            .security_status
            .is_none_or(|value| value.is_finite() && (-1.0..=1.0).contains(&value))
        && INDUSTRY_SECURITY_CLASSES.contains(&item.security_class.as_str())
        && (item.security_status.is_none() == (item.security_class == "unknown"))
        && item
            .tax
            .is_none_or(|value| value.is_finite() && (0.0..=1.0).contains(&value))
        && item
            .activity_cost_index
            .is_none_or(|value| value.is_finite() && (0.0..=1.0).contains(&value))
        && character_ids.len() == item.used_by_character_ids.len()
        && item
            .used_by_character_ids
            .iter()
            .all(|value| *value > 0 && *value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && activity_ids.len() == item.observed_activity_ids.len()
        && item
            .observed_activity_ids
            .iter()
            .all(|value| INDUSTRY_JOB_ACTIVITY_IDS.contains(value))
        && item.job_count <= JAVASCRIPT_MAX_SAFE_INTEGER
        && item.active_jobs <= item.job_count
        && item
            .error_code
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 120))
        && item.snapshot_id > 0
        && item.snapshot_id <= JAVASCRIPT_MAX_SAFE_INTEGER
        && item.sync_run_id > 0
        && item.sync_run_id <= JAVASCRIPT_MAX_SAFE_INTEGER
        && asset_text_is_valid(&item.observed_at, 64)
        && item.age_seconds <= JAVASCRIPT_MAX_SAFE_INTEGER;
    let state = match item.access.as_str() {
        "public" => {
            item.kind == "station"
                && item.facility_name.is_some()
                && item.type_id.is_some()
                && item.owner_id.is_some()
                && item.region_id.is_some()
                && item.solar_system_id.is_some()
                && item.error_code.is_none()
        }
        "available" => {
            item.kind == "structure"
                && item.facility_name.is_some()
                && item.owner_id.is_some()
                && item.region_id.is_none()
                && item.solar_system_id.is_some()
                && item.tax.is_none()
                && item.error_code.is_none()
        }
        "restricted" | "scope-missing" | "unknown" => {
            item.facility_name.is_none()
                && item.type_id.is_none()
                && item.owner_id.is_none()
                && item.region_id.is_none()
                && item.solar_system_id.is_none()
                && item.tax.is_none()
                && item.error_code.is_some()
        }
        _ => false,
    };
    common && state
}

fn industry_facility_query_response_is_valid(response: &IndustryFacilityQueryResponse) -> bool {
    let facility_ids = response
        .items
        .iter()
        .map(|item| item.facility_id)
        .collect::<HashSet<_>>();
    response.limit > 0
        && response.limit <= MAX_ASSET_PAGE_SIZE
        && response.total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.offset <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.npc_facilities <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.observed_facilities <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.restricted_structures <= response.observed_facilities
        && response.systems <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.items.len() as u64 <= response.limit
        && response.items.len() as u64 <= response.total
        && INDUSTRY_COST_ACTIVITIES.contains(&response.activity.as_str())
        && response
            .activities
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == INDUSTRY_COST_ACTIVITIES
        && response
            .kinds
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == INDUSTRY_FACILITY_KINDS
        && response
            .access_states
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == INDUSTRY_FACILITY_ACCESS_STATES
        && response
            .security_classes
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == INDUSTRY_SECURITY_CLASSES
        && response.observed_at.is_some() == response.age_seconds.is_some()
        && response
            .observed_at
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 64))
        && facility_ids.len() == response.items.len()
        && response.items.iter().all(|item| {
            industry_facility_record_is_valid(item)
                && response.observed_at.as_ref() == Some(&item.observed_at)
                && response.age_seconds == Some(item.age_seconds)
        })
        && (response.observed_at.is_some()
            || (response.items.is_empty()
                && response.npc_facilities == 0
                && response.observed_facilities == 0
                && response.restricted_structures == 0
                && response.systems == 0))
}

fn industry_facility_sync_response_is_valid(response: &IndustryFacilitySyncResponse) -> bool {
    response.sync_run_id > 0
        && response.sync_run_id <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response
            .npc_facilities
            .checked_add(response.observed_facilities)
            == Some(response.facilities)
        && response.facilities <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.npc_facilities > 0
        && response.restricted_structures <= response.observed_facilities
        && response.systems > 0
        && response.systems <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.resolved_names > 0
        && response.resolved_names <= JAVASCRIPT_MAX_SAFE_INTEGER
}

fn industry_slot_activity_is_valid(item: &IndustrySlotActivity, index: usize) -> bool {
    if index >= INDUSTRY_SLOT_ACTIVITIES.len()
        || item.activity != INDUSTRY_SLOT_ACTIVITIES[index]
        || !INDUSTRY_SLOT_UTILIZATION_STATES.contains(&item.utilization_state.as_str())
        || (item.primary_skill_id, item.advanced_skill_id) != INDUSTRY_SLOT_SKILL_IDS[index]
    {
        return false;
    }
    let skill_values_are_known = item.primary_skill_level.is_some()
        && item.advanced_skill_level.is_some()
        && item.capacity.is_some();
    let skill_values_are_unknown = item.primary_skill_level.is_none()
        && item.advanced_skill_level.is_none()
        && item.capacity.is_none();
    if !(skill_values_are_known || skill_values_are_unknown)
        || item.primary_skill_level.is_some_and(|value| value > 5)
        || item.advanced_skill_level.is_some_and(|value| value > 5)
        || item
            .capacity
            .is_some_and(|value| !(1..=11).contains(&value))
        || (skill_values_are_known
            && item.capacity
                != Some(
                    1 + item.primary_skill_level.unwrap_or(0)
                        + item.advanced_skill_level.unwrap_or(0),
                ))
    {
        return false;
    }
    let job_values_are_known = item.occupied.is_some()
        && item.active_jobs.is_some()
        && item.paused_jobs.is_some()
        && item.ready_jobs.is_some();
    let job_values_are_unknown = item.occupied.is_none()
        && item.active_jobs.is_none()
        && item.paused_jobs.is_none()
        && item.ready_jobs.is_none();
    if !(job_values_are_known || job_values_are_unknown)
        || [
            item.occupied,
            item.active_jobs,
            item.paused_jobs,
            item.ready_jobs,
        ]
        .into_iter()
        .flatten()
        .any(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || (job_values_are_known
            && item
                .active_jobs
                .and_then(|active| active.checked_add(item.paused_jobs.unwrap_or(0)))
                .and_then(|sum| sum.checked_add(item.ready_jobs.unwrap_or(0)))
                != item.occupied)
        || item
            .next_job_end_date
            .as_ref()
            .is_some_and(|value| !asset_text_is_valid(value, 64))
        || (item.next_job_end_date.is_some() && item.active_jobs == Some(0))
    {
        return false;
    }
    let utilization = match (item.capacity, item.occupied) {
        (Some(capacity), Some(occupied)) => {
            let expected_available = u64::from(capacity).saturating_sub(occupied) as u8;
            let expected_state = if occupied > u64::from(capacity) {
                "overbooked"
            } else if occupied == u64::from(capacity) {
                "full"
            } else {
                "available"
            };
            item.available == Some(expected_available) && item.utilization_state == expected_state
        }
        _ => item.available.is_none() && item.utilization_state == "unknown",
    };
    let plan_values = [
        item.queued_plans,
        item.blocked_plans,
        item.running_plans,
        item.complete_plans,
    ];
    let plans_are_bounded = plan_values
        .into_iter()
        .flatten()
        .all(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER);
    let planning = item.planning_available && plan_values.into_iter().all(|value| value.is_some());
    utilization && plans_are_bounded && planning
}

fn optional_industry_slot_source_is_valid(
    snapshot_id: Option<u64>,
    sync_run_id: Option<u64>,
    observed_at: &Option<String>,
) -> bool {
    snapshot_id.is_some() == sync_run_id.is_some()
        && snapshot_id.is_some() == observed_at.is_some()
        && snapshot_id.is_none_or(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && sync_run_id.is_none_or(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && observed_at
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 64))
}

fn industry_slot_record_is_valid(item: &IndustrySlotRecord) -> bool {
    let any_source = item.skill_snapshot_id.is_some() || item.job_snapshot_id.is_some();
    item.character_id > 0
        && item.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
        && asset_text_is_valid(&item.name, 100)
        && item.activities.len() == INDUSTRY_SLOT_ACTIVITIES.len()
        && item
            .activities
            .iter()
            .enumerate()
            .all(|(index, activity)| industry_slot_activity_is_valid(activity, index))
        && optional_industry_slot_source_is_valid(
            item.skill_snapshot_id,
            item.skill_sync_run_id,
            &item.skill_observed_at,
        )
        && optional_industry_slot_source_is_valid(
            item.job_snapshot_id,
            item.job_sync_run_id,
            &item.job_observed_at,
        )
        && item.observed_at.is_some() == item.age_seconds.is_some()
        && item.observed_at.is_some() == any_source
        && item
            .observed_at
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 64))
        && item
            .age_seconds
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
}

fn industry_slot_query_response_is_valid(response: &IndustrySlotQueryResponse) -> bool {
    let character_ids = response
        .items
        .iter()
        .map(|item| item.character_id)
        .collect::<HashSet<_>>();
    let owner_ids = response
        .owners
        .iter()
        .map(|owner| owner.character_id)
        .collect::<HashSet<_>>();
    response.limit > 0
        && response.limit <= MAX_ASSET_PAGE_SIZE
        && response.total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.offset <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.items.len() as u64 <= response.limit
        && response.items.len() as u64 <= response.total
        && response
            .activities
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == INDUSTRY_SLOT_ACTIVITIES
        && response.observed_at.is_some() == response.age_seconds.is_some()
        && response
            .observed_at
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 64))
        && response
            .age_seconds
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && character_ids.len() == response.items.len()
        && owner_ids.len() == response.owners.len()
        && response.items.iter().all(|item| {
            industry_slot_record_is_valid(item)
                && response
                    .owners
                    .iter()
                    .any(|owner| owner.character_id == item.character_id && owner.name == item.name)
        })
        && response.owners.iter().all(|owner| {
            owner.character_id > 0
                && owner.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&owner.name, 100)
        })
        && (response.observed_at.is_some()
            || response.items.iter().all(|item| item.observed_at.is_none()))
}

fn optional_source_pair_is_valid(first: Option<u64>, second: Option<u64>) -> bool {
    first.is_some() == second.is_some()
        && first.is_none_or(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && second.is_none_or(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
}

fn research_plan_owner_is_valid(owner: &ResearchPlanOwner) -> bool {
    owner.character_id > 0
        && owner.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
        && asset_text_is_valid(&owner.name, 100)
        && owner.slot_capacity.is_some() == owner.slots_available.is_some()
        && owner.slot_capacity.is_some() == owner.skill_snapshot_id.is_some()
        && owner
            .slot_capacity
            .is_none_or(|value| (1..=11).contains(&value))
        && owner.slots_available.is_none_or(|value| {
            owner
                .slot_capacity
                .is_some_and(|capacity| value <= capacity)
        })
        && owner.slots_used <= JAVASCRIPT_MAX_SAFE_INTEGER
        && [
            owner.laboratory_operation_level,
            owner.advanced_laboratory_operation_level,
            owner.research_level,
            owner.metallurgy_level,
        ]
        .into_iter()
        .all(|value| value <= 5)
        && optional_source_pair_is_valid(owner.skill_snapshot_id, owner.skill_sync_run_id)
}

fn research_plan_record_is_valid(item: &ResearchPlanRecord) -> bool {
    let current = item.current_material_efficiency.is_some()
        && item.current_time_efficiency.is_some()
        && item.location_id.is_some()
        && item.location_flag.is_some()
        && item.blueprint_snapshot_id.is_some()
        && item.blueprint_sync_run_id.is_some()
        && item.observed_at.is_some()
        && item.age_seconds.is_some();
    let no_current = item.current_material_efficiency.is_none()
        && item.current_time_efficiency.is_none()
        && item.location_id.is_none()
        && item.location_flag.is_none()
        && item.blueprint_snapshot_id.is_none()
        && item.blueprint_sync_run_id.is_none()
        && item.observed_at.is_none()
        && item.age_seconds.is_none();
    let active_job = match item.active_job_id {
        Some(job_id) => {
            job_id > 0
                && job_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && item
                    .active_job_activity
                    .as_deref()
                    .is_some_and(|value| RESEARCH_PLAN_ACTIVITIES.contains(&value))
                && item
                    .active_job_status
                    .as_deref()
                    .is_some_and(|value| RESEARCH_ACTIVE_JOB_STATUSES.contains(&value))
                && item
                    .active_job_start_date
                    .as_ref()
                    .is_some_and(|value| asset_text_is_valid(value, 64))
                && item
                    .active_job_end_date
                    .as_ref()
                    .is_some_and(|value| asset_text_is_valid(value, 64))
                && item.active_job_cost.is_none_or(|value| {
                    value.is_finite() && (0.0..=JAVASCRIPT_MAX_SAFE_INTEGER as f64).contains(&value)
                })
        }
        None => {
            item.active_job_activity.is_none()
                && item.active_job_status.is_none()
                && item.active_job_start_date.is_none()
                && item.active_job_end_date.is_none()
                && item.active_job_cost.is_none()
        }
    };
    let facility = match item.facility_evidence.as_str() {
        "none" => {
            item.facility_id.is_none()
                && item.facility_name.is_none()
                && item.solar_system_name.is_none()
                && item.system_cost_index.is_none()
                && item.facility_access == "unknown"
        }
        "active-job" | "last-owner-job" => {
            item.facility_id
                .is_some_and(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && INDUSTRY_FACILITY_ACCESS_STATES.contains(&item.facility_access.as_str())
                && item
                    .facility_name
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 200))
                && item
                    .solar_system_name
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 200))
                && item
                    .system_cost_index
                    .is_none_or(|value| value.is_finite() && (0.0..=1.0).contains(&value))
        }
        _ => false,
    };
    let persisted = if item.planned {
        item.state != "unplanned"
            && item
                .created_at
                .as_ref()
                .is_some_and(|value| asset_text_is_valid(value, 64))
            && item
                .updated_at
                .as_ref()
                .is_some_and(|value| asset_text_is_valid(value, 64))
    } else {
        item.state == "unplanned"
            && item.priority == 0
            && item.note.is_none()
            && item.created_at.is_none()
            && item.updated_at.is_none()
    };
    item.owner_character_id > 0
        && item.owner_character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
        && asset_text_is_valid(&item.owner_name, 100)
        && item.blueprint_item_id > 0
        && item.blueprint_item_id <= JAVASCRIPT_MAX_SAFE_INTEGER
        && item.blueprint_type_id > 0
        && item.blueprint_type_id <= JAVASCRIPT_MAX_SAFE_INTEGER
        && asset_text_is_valid(&item.blueprint_name, 200)
        && item.blueprint_present == current
        && (current || no_current)
        && item
            .current_material_efficiency
            .is_none_or(|value| value <= 10)
        && item.current_time_efficiency.is_none_or(|value| value <= 20)
        && item
            .location_id
            .is_none_or(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && item
            .location_flag
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 100))
        && RESEARCH_PLAN_ACTIVITIES.contains(&item.next_activity.as_str())
        && item.target_material_efficiency <= 10
        && item.target_time_efficiency <= 20
        && item.priority <= 999
        && item
            .note
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 240))
        && RESEARCH_PLAN_STATES.contains(&item.state.as_str())
        && item.slot_capacity.is_some() == item.slots_available.is_some()
        && item
            .slot_capacity
            .is_none_or(|value| (1..=11).contains(&value))
        && item
            .slots_available
            .is_none_or(|value| item.slot_capacity.is_some_and(|capacity| value <= capacity))
        && item.slots_used <= JAVASCRIPT_MAX_SAFE_INTEGER
        && item.research_level <= 5
        && item.metallurgy_level <= 5
        && active_job
        && facility
        && (item.facility_evidence != "active-job" || item.active_job_id.is_some())
        && RESEARCH_FACILITY_EVIDENCE.contains(&item.facility_evidence.as_str())
        && optional_source_pair_is_valid(item.blueprint_snapshot_id, item.blueprint_sync_run_id)
        && optional_source_pair_is_valid(item.skill_snapshot_id, item.skill_sync_run_id)
        && optional_source_pair_is_valid(item.job_snapshot_id, item.job_sync_run_id)
        && persisted
}

fn research_plan_query_response_is_valid(response: &ResearchPlanQueryResponse) -> bool {
    let item_keys = response
        .items
        .iter()
        .map(|item| (item.owner_character_id, item.blueprint_item_id))
        .collect::<HashSet<_>>();
    let owner_ids = response
        .owners
        .iter()
        .map(|owner| owner.character_id)
        .collect::<HashSet<_>>();
    let summary = [
        response.summary.unplanned,
        response.summary.ready,
        response.summary.queued,
        response.summary.running,
        response.summary.complete,
        response.summary.unverified,
        response.summary.missing,
    ];
    response.limit > 0
        && response.limit <= MAX_ASSET_PAGE_SIZE
        && response.total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.offset <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.items.len() as u64 <= response.limit
        && response.items.len() as u64 <= response.total
        && item_keys.len() == response.items.len()
        && owner_ids.len() == response.owners.len()
        && response.items.iter().all(research_plan_record_is_valid)
        && response.owners.iter().all(research_plan_owner_is_valid)
        && response
            .states
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == RESEARCH_PLAN_STATES
        && response
            .activities
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == RESEARCH_PLAN_ACTIVITIES
        && summary
            .into_iter()
            .all(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && response.observed_at.is_some() == response.age_seconds.is_some()
        && response
            .observed_at
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 64))
        && response
            .age_seconds
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && !response.estimates_available
}

fn research_plan_mutation_response_is_valid(response: &ResearchPlanMutationResponse) -> bool {
    response.owner_character_id > 0
        && response.owner_character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.blueprint_item_id > 0
        && response.blueprint_item_id <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.blueprint_type_id > 0
        && response.blueprint_type_id <= JAVASCRIPT_MAX_SAFE_INTEGER
        && RESEARCH_PLAN_ACTIVITIES.contains(&response.next_activity.as_str())
        && response.target_material_efficiency <= 10
        && response.target_time_efficiency <= 20
        && response.priority <= 999
        && response
            .note
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 240))
        && response.saved
}

fn production_id_is_valid(value: u64) -> bool {
    value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER
}

fn production_catalog_response_is_valid(response: &ProductionCatalogResponse) -> bool {
    let keys = response
        .items
        .iter()
        .map(|item| {
            (
                item.blueprint_type_id,
                item.activity.as_str(),
                item.product_type_id,
            )
        })
        .collect::<HashSet<_>>();
    response.limit > 0
        && response.limit <= 100
        && response.offset <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.items.len() as u64 <= response.limit
        && response.items.len() as u64 <= response.total
        && keys.len() == response.items.len()
        && response
            .activities
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == PRODUCTION_ACTIVITIES
        && response
            .build_number
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 80))
        && (response.build_number.is_some() || (response.total == 0 && response.items.is_empty()))
        && response.items.iter().all(|item| {
            production_id_is_valid(item.blueprint_type_id)
                && production_id_is_valid(item.product_type_id)
                && asset_text_is_valid(&item.blueprint_name, 200)
                && asset_text_is_valid(&item.product_name, 200)
                && PRODUCTION_ACTIVITIES.contains(&item.activity.as_str())
                && production_id_is_valid(item.base_time_seconds)
                && production_id_is_valid(item.output_quantity)
                && production_id_is_valid(item.material_count)
        })
}

fn production_plan_record_is_valid(item: &ProductionPlanRecord) -> bool {
    let steps_valid = item.steps.iter().enumerate().all(|(index, step)| {
        step.sequence == index as u64 + 1
            && production_id_is_valid(step.blueprint_type_id)
            && production_id_is_valid(step.product_type_id)
            && asset_text_is_valid(&step.blueprint_name, 200)
            && asset_text_is_valid(&step.product_name, 200)
            && PRODUCTION_ACTIVITIES.contains(&step.activity.as_str())
            && production_id_is_valid(step.required_quantity)
            && production_id_is_valid(step.output_quantity_per_run)
            && production_id_is_valid(step.runs)
            && production_id_is_valid(step.produced_quantity)
            && step.surplus_quantity <= JAVASCRIPT_MAX_SAFE_INTEGER
            && production_id_is_valid(step.base_time_seconds_per_run)
            && production_id_is_valid(step.total_base_time_seconds)
            && production_id_is_valid(step.recipe_alternatives)
            && step.output_quantity_per_run.checked_mul(step.runs) == Some(step.produced_quantity)
            && step.produced_quantity.checked_sub(step.required_quantity)
                == Some(step.surplus_quantity)
            && step.base_time_seconds_per_run.checked_mul(step.runs)
                == Some(step.total_base_time_seconds)
            && step.materials.iter().all(|material| {
                production_id_is_valid(material.type_id)
                    && asset_text_is_valid(&material.type_name, 200)
                    && production_id_is_valid(material.quantity_per_run)
                    && production_id_is_valid(material.gross_quantity)
                    && material.quantity_per_run.checked_mul(step.runs)
                        == Some(material.gross_quantity)
            })
    });
    let gross_valid = item.gross_materials.iter().all(|material| {
        production_id_is_valid(material.type_id)
            && asset_text_is_valid(&material.type_name, 200)
            && production_id_is_valid(material.quantity)
    });
    let warnings_valid = item.warnings.iter().all(|warning| {
        warning.code == "alternative-recipe"
            && production_id_is_valid(warning.type_id)
            && asset_text_is_valid(&warning.type_name, 200)
            && production_id_is_valid(warning.selected_blueprint_type_id)
            && warning.candidate_count >= 2
            && warning.candidate_count <= JAVASCRIPT_MAX_SAFE_INTEGER
    });
    let ready = item.state == "ready";
    let resolution_shape = if ready {
        item.build_number.is_some()
            && !item.steps.is_empty()
            && item.cycle_type_ids.is_empty()
            && item.total_base_time_seconds.is_some()
            && item.steps.first().is_some_and(|step| {
                step.blueprint_type_id == item.blueprint_type_id
                    && step.product_type_id == item.product_type_id
                    && step.activity == item.activity
                    && step.required_quantity == item.target_quantity
            })
            && item.steps.iter().try_fold(0_u64, |total, step| {
                total.checked_add(step.total_base_time_seconds)
            }) == item.total_base_time_seconds
    } else {
        item.steps.is_empty()
            && item.gross_materials.is_empty()
            && item.total_base_time_seconds.is_none()
            && ((item.state == "cycle" && !item.cycle_type_ids.is_empty())
                || (item.state != "cycle" && item.cycle_type_ids.is_empty()))
    };
    production_id_is_valid(item.plan_id)
        && production_id_is_valid(item.owner_character_id)
        && asset_text_is_valid(&item.owner_name, 100)
        && production_id_is_valid(item.blueprint_type_id)
        && asset_text_is_valid(&item.blueprint_name, 200)
        && PRODUCTION_ACTIVITIES.contains(&item.activity.as_str())
        && production_id_is_valid(item.product_type_id)
        && asset_text_is_valid(&item.product_name, 200)
        && production_id_is_valid(item.target_quantity)
        && item.priority <= 999
        && item
            .note
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 240))
        && PRODUCTION_PLAN_STATES.contains(&item.state.as_str())
        && item
            .build_number
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 80))
        && item
            .cycle_type_ids
            .iter()
            .all(|value| production_id_is_valid(*value))
        && item
            .total_base_time_seconds
            .is_none_or(production_id_is_valid)
        && asset_text_is_valid(&item.created_at, 64)
        && asset_text_is_valid(&item.updated_at, 64)
        && steps_valid
        && gross_valid
        && warnings_valid
        && resolution_shape
}

fn production_plan_query_response_is_valid(response: &ProductionPlanQueryResponse) -> bool {
    let ids = response
        .items
        .iter()
        .map(|item| item.plan_id)
        .collect::<HashSet<_>>();
    let owner_ids = response
        .owners
        .iter()
        .map(|owner| owner.character_id)
        .collect::<HashSet<_>>();
    let summary = [
        response.summary.ready,
        response.summary.sde_unavailable,
        response.summary.recipe_missing,
        response.summary.cycle,
        response.summary.complexity_limit,
    ];
    response.limit > 0
        && response.limit <= 100
        && response.offset <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.items.len() as u64 <= response.limit
        && response.items.len() as u64 <= response.total
        && ids.len() == response.items.len()
        && owner_ids.len() == response.owners.len()
        && response.items.iter().all(production_plan_record_is_valid)
        && response.owners.iter().all(|owner| {
            production_id_is_valid(owner.character_id) && asset_text_is_valid(&owner.name, 100)
        })
        && response
            .activities
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == PRODUCTION_ACTIVITIES
        && response
            .states
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == PRODUCTION_PLAN_STATES
        && summary
            .into_iter()
            .all(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && response
            .build_number
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 80))
        && !response.inventory_applied
        && !response.modifiers_applied
}

fn production_plan_mutation_is_valid(item: &ProductionPlanMutationResponse) -> bool {
    item.saved
        && production_id_is_valid(item.plan_id)
        && production_id_is_valid(item.owner_character_id)
        && production_id_is_valid(item.blueprint_type_id)
        && PRODUCTION_ACTIVITIES.contains(&item.activity.as_str())
        && production_id_is_valid(item.product_type_id)
        && production_id_is_valid(item.target_quantity)
        && item.priority <= 999
        && item
            .note
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 240))
}

fn public_release_notice_is_valid(notice: &PublicReleaseNotice) -> bool {
    let state_valid = matches!(
        notice.state.as_str(),
        "available" | "current" | "unavailable" | "error"
    );
    let version_fields = notice.latest_version.is_some()
        && notice.release_url.is_some()
        && notice.published_at.is_some();
    let empty_fields = notice.latest_version.is_none()
        && notice.release_url.is_none()
        && notice.published_at.is_none();
    let shape_valid = match notice.state.as_str() {
        "available" | "current" => version_fields && notice.error_code.is_none(),
        "unavailable" => empty_fields && notice.error_code.is_none(),
        "error" => empty_fields && notice.error_code.is_some(),
        _ => false,
    };
    state_valid
        && matches!(notice.channel.as_str(), "stable" | "beta" | "preview")
        && asset_text_is_valid(&notice.current_version, 80)
        && notice
            .latest_version
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 80))
        && notice.release_url.as_ref().is_none_or(|url| {
            url == &format!(
                "https://github.com/Savox76/eve-test-indu/releases/tag/v{}",
                notice.latest_version.as_deref().unwrap_or_default()
            )
        })
        && notice
            .published_at
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 64))
        && notice
            .error_code
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 120))
        && !notice.automatic_install
        && shape_valid
}

fn character_skill_query_response_is_valid(response: &CharacterSkillQueryResponse) -> bool {
    let owner_ids = response
        .owners
        .iter()
        .map(|owner| owner.character_id)
        .collect::<HashSet<_>>();
    let skill_keys = response
        .items
        .iter()
        .map(|skill| (skill.owner_character_id, skill.skill_id))
        .collect::<HashSet<_>>();
    response.limit > 0
        && response.limit <= MAX_ASSET_PAGE_SIZE
        && [
            response.total,
            response.total_sp,
            response.unallocated_sp,
            response.offset,
        ]
        .into_iter()
        .all(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && response.items.len() as u64 <= response.limit
        && response.items.len() as u64 <= response.total
        && response.levels == [0, 1, 2, 3, 4, 5]
        && response
            .active_states
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == CHARACTER_SKILL_ACTIVE_STATES
        && response.observed_at.is_some() == response.age_seconds.is_some()
        && response
            .observed_at
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 64))
        && owner_ids.len() == response.owners.len()
        && skill_keys.len() == response.items.len()
        && response.owners.iter().all(|owner| {
            owner.character_id > 0
                && owner.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&owner.name, 100)
        })
        && response.items.iter().all(|skill| {
            let expected_state = if skill.active_level < skill.trained_level {
                "limited"
            } else if skill.active_level > skill.trained_level {
                "boosted"
            } else {
                "normal"
            };
            skill.skill_id > 0
                && skill.skill_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && owner_ids.contains(&skill.owner_character_id)
                && response.owners.iter().any(|owner| {
                    owner.character_id == skill.owner_character_id && owner.name == skill.owner_name
                })
                && asset_text_is_valid(&skill.skill_name, 220)
                && asset_text_is_valid(&skill.owner_name, 100)
                && skill.trained_level <= 5
                && skill.active_level <= 5
                && skill.skillpoints <= JAVASCRIPT_MAX_SAFE_INTEGER
                && skill.active_state == expected_state
                && skill.snapshot_id > 0
                && skill.snapshot_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && skill.sync_run_id > 0
                && skill.sync_run_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&skill.observed_at, 64)
        })
}

fn character_skill_sync_response_is_valid(response: &CharacterSkillSyncResponse) -> bool {
    let skills = response
        .characters
        .iter()
        .try_fold(0_u64, |sum, item| sum.checked_add(item.skills));
    let total_sp = response
        .characters
        .iter()
        .try_fold(0_u64, |sum, item| sum.checked_add(item.total_sp));
    let unallocated_sp = response
        .characters
        .iter()
        .try_fold(0_u64, |sum, item| sum.checked_add(item.unallocated_sp));
    response.completed.checked_add(response.failed) == Some(response.characters.len() as u64)
        && skills == Some(response.skills)
        && total_sp == Some(response.total_sp)
        && unallocated_sp == Some(response.unallocated_sp)
        && [response.skills, response.total_sp, response.unallocated_sp]
            .into_iter()
            .all(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && response.characters.iter().all(|item| {
            item.character_id > 0
                && item.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && matches!(item.status.as_str(), "completed" | "failed")
                && [item.skills, item.total_sp, item.unallocated_sp]
                    .into_iter()
                    .all(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && ((item.status == "completed" && item.error_code.is_none())
                    || (item.status == "failed"
                        && item.skills == 0
                        && item.total_sp == 0
                        && item.unallocated_sp == 0
                        && item
                            .error_code
                            .as_ref()
                            .is_some_and(|code| asset_text_is_valid(code, 120))))
        })
}

fn asset_export_response_is_valid(response: &AssetExportResponse) -> bool {
    response.rows <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.filename.starts_with("assets-")
        && response.filename.ends_with(".csv")
        && response.filename.len() <= 64
        && response
            .filename
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'.'))
        && response.relative_path == format!("data/exports/{}", response.filename)
}

fn asset_delta_response_is_valid(response: &AssetDeltaQueryResponse) -> bool {
    let owner_ids = response
        .owners
        .iter()
        .map(|owner| owner.character_id)
        .collect::<HashSet<_>>();
    let event_ids = response
        .items
        .iter()
        .map(|event| event.event_id.as_str())
        .collect::<HashSet<_>>();
    response.limit > 0
        && response.limit <= MAX_ASSET_PAGE_SIZE
        && response.total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.offset <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.items.len() as u64 <= response.limit
        && response.items.len() as u64 <= response.total
        && response
            .change_types
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == ASSET_DELTA_CHANGE_TYPES
        && event_ids.len() == response.items.len()
        && owner_ids.len() == response.owners.len()
        && response.observed_at.is_some() == response.age_seconds.is_some()
        && response.has_baseline == response.observed_at.is_some()
        && response
            .observed_at
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 64))
        && [
            response.summary.added,
            response.summary.removed,
            response.summary.quantity,
            response.summary.location,
        ]
        .into_iter()
        .all(|value| value <= response.total && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && response.owners.iter().all(|owner| {
            owner.character_id > 0
                && owner.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&owner.name, 100)
        })
        && response.items.iter().all(|event| {
            let expected_delta = event.quantity_after.unwrap_or(0) as i128
                - event.quantity_before.unwrap_or(0) as i128;
            let location_changed = event.location_id_before != event.location_id_after
                || event.location_type_before != event.location_type_after
                || event.location_flag_before != event.location_flag_after;
            let expected_direction = if event.quantity_delta > 0 {
                "inbound"
            } else if event.quantity_delta < 0 {
                "outbound"
            } else {
                "neutral"
            };
            event.event_id.len() == 64
                && event
                    .event_id
                    .bytes()
                    .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
                && event.item_id > 0
                && event.item_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && event.type_id > 0
                && event.type_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && owner_ids.contains(&event.owner_character_id)
                && asset_text_is_valid(&event.type_name, 220)
                && asset_text_is_valid(&event.owner_name, 100)
                && !event.change_types.is_empty()
                && event.change_types.len() <= 2
                && event
                    .change_types
                    .iter()
                    .all(|value| ASSET_DELTA_CHANGE_TYPES.contains(&value.as_str()))
                && event.change_types.iter().collect::<HashSet<_>>().len()
                    == event.change_types.len()
                && event.change_types.iter().any(|value| value == "added")
                    == (event.quantity_before.is_none() && event.quantity_after.is_some())
                && event.change_types.iter().any(|value| value == "removed")
                    == (event.quantity_before.is_some() && event.quantity_after.is_none())
                && event.change_types.iter().any(|value| value == "quantity")
                    == (event.quantity_before.is_some()
                        && event.quantity_after.is_some()
                        && event.quantity_delta != 0)
                && event.change_types.iter().any(|value| value == "location")
                    == (event.quantity_before.is_some()
                        && event.quantity_after.is_some()
                        && location_changed)
                && expected_delta == i128::from(event.quantity_delta)
                && event.quantity_delta.unsigned_abs() <= JAVASCRIPT_MAX_SAFE_INTEGER
                && event
                    .quantity_before
                    .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && event
                    .quantity_after
                    .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && event
                    .location_id_before
                    .is_none_or(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && event
                    .location_id_after
                    .is_none_or(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && event
                    .location_type_before
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 40))
                && event
                    .location_type_after
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 40))
                && event
                    .location_flag_before
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 100))
                && event
                    .location_flag_after
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 100))
                && event.previous_asset_snapshot_id > 0
                && event.current_asset_snapshot_id > 0
                && event.current_asset_sync_run_id > 0
                && asset_text_is_valid(&event.observed_at, 64)
                && [
                    "linked",
                    "ambiguous",
                    "unmatched",
                    "unavailable",
                    "not-applicable",
                ]
                .contains(&event.job_correlation.state.as_str())
                && event.job_correlation.key
                    == format!("{}:{}", event.owner_character_id, event.type_id)
                && ["inbound", "outbound", "neutral"]
                    .contains(&event.job_correlation.direction.as_str())
                && event.job_correlation.direction == expected_direction
                && asset_text_is_valid(&event.job_correlation.window_start, 64)
                && asset_text_is_valid(&event.job_correlation.window_end, 64)
                && event.job_correlation.candidate_count <= JAVASCRIPT_MAX_SAFE_INTEGER
                && event.job_correlation.job_ids.len() <= 20
                && event
                    .job_correlation
                    .job_ids
                    .iter()
                    .all(|job_id| *job_id > 0 && *job_id <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && event
                    .job_correlation
                    .job_ids
                    .iter()
                    .collect::<HashSet<_>>()
                    .len()
                    == event.job_correlation.job_ids.len()
                && match event.job_correlation.state.as_str() {
                    "linked" => {
                        event.job_correlation.candidate_count == 1
                            && event.job_correlation.job_ids.len() == 1
                    }
                    "ambiguous" => {
                        event.job_correlation.candidate_count > 1
                            && !event.job_correlation.job_ids.is_empty()
                    }
                    _ => {
                        event.job_correlation.candidate_count == 0
                            && event.job_correlation.job_ids.is_empty()
                            && !event.job_correlation.location_matched
                    }
                }
        })
}

fn eve_character_record_is_valid(character: &EveCharacterRecord) -> bool {
    let package_ids = character
        .scope_packages
        .iter()
        .map(|package| package.id.as_str())
        .collect::<HashSet<_>>();
    sso_character_identity_is_valid(&SsoCharacterIdentity {
        character_id: character.character_id,
        name: character.name.clone(),
        scopes: character.scopes.clone(),
    }) && character
        .alias
        .as_deref()
        .is_none_or(management_label_is_valid)
        && character.account_group_id != Some(0)
        && character
            .account_group_label
            .as_deref()
            .is_none_or(management_label_is_valid)
        && character.account_group_id.is_some() == character.account_group_label.is_some()
        && matches!(
            character.credential_state.as_str(),
            "stored" | "missing" | "unavailable"
        )
        && character.scope_packages.len() == EVE_SSO_SCOPE_PACKAGES.len()
        && package_ids.len() == EVE_SSO_SCOPE_PACKAGES.len()
        && character
            .scope_packages
            .iter()
            .all(scope_package_status_is_valid)
}

fn sso_login_status_is_valid(status: &SsoLoginStatus) -> bool {
    let packages_are_valid = !status.scope_packages.is_empty()
        && status
            .scope_packages
            .iter()
            .all(|package| EVE_SSO_SCOPE_PACKAGES.contains(&package.as_str()))
        && status.scope_packages.iter().collect::<HashSet<_>>().len()
            == status.scope_packages.len();
    match status.state.as_str() {
        "idle" => {
            status.attempt_id.is_none()
                && status.scope_packages.is_empty()
                && status.expires_at.is_none()
                && status.error_code.is_none()
                && status.character.is_none()
        }
        "waiting" | "exchanging" | "cancelled" => {
            status
                .attempt_id
                .as_ref()
                .is_some_and(|value| !value.is_empty())
                && packages_are_valid
                && status
                    .expires_at
                    .as_ref()
                    .is_some_and(|value| !value.is_empty())
                && status.error_code.is_none()
                && status.character.is_none()
        }
        "connected" => {
            status
                .attempt_id
                .as_ref()
                .is_some_and(|value| !value.is_empty())
                && packages_are_valid
                && status
                    .expires_at
                    .as_ref()
                    .is_some_and(|value| !value.is_empty())
                && status.error_code.is_none()
                && status
                    .character
                    .as_ref()
                    .is_some_and(sso_character_identity_is_valid)
        }
        "timed-out" => {
            status
                .attempt_id
                .as_ref()
                .is_some_and(|value| !value.is_empty())
                && packages_are_valid
                && status
                    .expires_at
                    .as_ref()
                    .is_some_and(|value| !value.is_empty())
                && status.error_code.as_deref() == Some("login-timeout")
                && status.character.is_none()
        }
        "failed" => {
            status
                .attempt_id
                .as_ref()
                .is_some_and(|value| !value.is_empty())
                && packages_are_valid
                && status
                    .expires_at
                    .as_ref()
                    .is_some_and(|value| !value.is_empty())
                && status.error_code.as_ref().is_some_and(|code| {
                    matches!(
                        code.as_str(),
                        "authorization-denied"
                            | "authorization-failed"
                            | "callback-invalid"
                            | "pkce-state-missing"
                            | "sso-metadata-unavailable"
                            | "sso-metadata-invalid"
                            | "token-request-invalid"
                            | "token-exchange-failed"
                            | "token-response-invalid"
                            | "jwks-unavailable"
                            | "jwks-invalid"
                            | "jwt-malformed"
                            | "jwt-header-invalid"
                            | "jwt-key-not-found"
                            | "jwt-signature-invalid"
                            | "jwt-claims-invalid"
                            | "jwt-expired"
                            | "jwt-identity-invalid"
                            | "jwt-scopes-missing"
                            | "character-save-failed"
                    )
                })
                && status.character.is_none()
        }
        _ => false,
    }
}

fn authorization_url_is_valid(value: &str) -> bool {
    let Ok(url) = tauri::Url::parse(value) else {
        return false;
    };
    if url.as_str().len() > 8_192
        || url.scheme() != "https"
        || url.host_str() != Some("login.eveonline.com")
        || url.port_or_known_default() != Some(443)
        || url.path() != "/v2/oauth/authorize"
        || !url.username().is_empty()
        || url.password().is_some()
        || url.fragment().is_some()
        || !value.starts_with(EVE_SSO_AUTHORIZATION_ENDPOINT)
    {
        return false;
    }

    let mut parameters: HashMap<String, String> = HashMap::new();
    for (key, value) in url.query_pairs() {
        if parameters
            .insert(key.into_owned(), value.into_owned())
            .is_some()
        {
            return false;
        }
    }
    let expected_keys: HashSet<&str> = [
        "response_type",
        "client_id",
        "redirect_uri",
        "scope",
        "state",
        "code_challenge",
        "code_challenge_method",
    ]
    .into_iter()
    .collect();
    if parameters
        .keys()
        .map(String::as_str)
        .collect::<HashSet<_>>()
        != expected_keys
    {
        return false;
    }
    let is_pkce_token = |candidate: &str| {
        candidate.len() == 43
            && candidate
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-'))
    };
    parameters.get("response_type").map(String::as_str) == Some("code")
        && parameters.get("client_id").map(String::as_str) == Some(EVE_SSO_CLIENT_ID)
        && parameters.get("redirect_uri").map(String::as_str) == Some(EVE_SSO_REDIRECT_URI)
        && parameters.get("code_challenge_method").map(String::as_str) == Some("S256")
        && parameters
            .get("state")
            .is_some_and(|candidate| is_pkce_token(candidate))
        && parameters
            .get("code_challenge")
            .is_some_and(|candidate| is_pkce_token(candidate))
        && parameters.get("scope").is_some_and(|scope| {
            !scope.is_empty()
                && scope.split(' ').all(|item| {
                    item.starts_with("esi-")
                        && item.ends_with(".v1")
                        && item.bytes().all(|byte| {
                            byte.is_ascii_lowercase()
                                || byte.is_ascii_digit()
                                || matches!(byte, b'-' | b'_' | b'.')
                        })
                })
        })
}

fn launch_system_browser(url: &str) -> Result<(), &'static str> {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        Command::new("rundll32.exe")
            .arg("url.dll,FileProtocolHandler")
            .arg(url)
            .creation_flags(WINDOWS_CREATE_NO_WINDOW)
            .spawn()
            .map_err(|_| "system-browser-unavailable")?;
    }
    #[cfg(target_os = "macos")]
    Command::new("open")
        .arg(url)
        .spawn()
        .map_err(|_| "system-browser-unavailable")?;
    #[cfg(all(unix, not(target_os = "macos")))]
    Command::new("xdg-open")
        .arg(url)
        .spawn()
        .map_err(|_| "system-browser-unavailable")?;
    Ok(())
}

fn open_system_browser(url: &str) -> Result<(), &'static str> {
    if !authorization_url_is_valid(url) {
        return Err("sso-authorization-url-invalid");
    }
    launch_system_browser(url)
}

fn semantic_release_version_is_valid(value: &str) -> bool {
    if value.is_empty() || value.len() > 80 || value.contains('+') {
        return false;
    }
    let (core, prerelease) = value
        .split_once('-')
        .map_or((value, None), |(core, prerelease)| (core, Some(prerelease)));
    let core_parts = core.split('.').collect::<Vec<_>>();
    let numeric_component_is_valid = |part: &str| {
        !part.is_empty()
            && part.bytes().all(|byte| byte.is_ascii_digit())
            && (part == "0" || !part.starts_with('0'))
    };
    if core_parts.len() != 3 || !core_parts.into_iter().all(numeric_component_is_valid) {
        return false;
    }
    prerelease.is_none_or(|value| {
        !value.is_empty()
            && value.split('.').all(|part| {
                !part.is_empty()
                    && part
                        .bytes()
                        .all(|byte| byte.is_ascii_alphanumeric() || byte == b'-')
                    && (!part.bytes().all(|byte| byte.is_ascii_digit())
                        || numeric_component_is_valid(part))
            })
    })
}

fn release_page_url(version: Option<&str>) -> Result<String, &'static str> {
    let base = "https://github.com/Savox76/eve-test-indu/releases";
    let Some(version) = version else {
        return Ok(base.to_owned());
    };
    if !semantic_release_version_is_valid(version) {
        return Err("release-version-invalid");
    }
    Ok(format!("{base}/tag/v{version}"))
}

fn copy_directory_without_links(source: &Path, destination: &Path) -> Result<(), &'static str> {
    fs::create_dir(destination).map_err(|_| "program-storage-migration-failed")?;
    for entry in fs::read_dir(source).map_err(|_| "program-storage-migration-failed")? {
        let entry = entry.map_err(|_| "program-storage-migration-failed")?;
        let file_type = entry
            .file_type()
            .map_err(|_| "program-storage-migration-failed")?;
        if file_type.is_symlink() {
            return Err("program-storage-migration-failed");
        }
        let target = destination.join(entry.file_name());
        if file_type.is_dir() {
            copy_directory_without_links(&entry.path(), &target)?;
        } else if file_type.is_file() {
            copy_file_with_retry(&entry.path(), &target)?;
        } else {
            return Err("program-storage-migration-failed");
        }
    }
    Ok(())
}

fn copy_file_with_retry(source: &Path, destination: &Path) -> Result<(), &'static str> {
    for attempt in 0..5 {
        if fs::copy(source, destination).is_ok() {
            return Ok(());
        }
        if attempt < 4 {
            thread::sleep(Duration::from_millis(100));
        }
    }
    Err("program-storage-migration-failed")
}

fn copy_essential_program_data(source: &Path, destination: &Path) -> Result<(), &'static str> {
    fs::create_dir(destination).map_err(|_| "program-storage-migration-failed")?;
    let database = source.join("foundry.sqlite3");
    if database.exists() {
        if database.is_symlink() || !database.is_file() {
            return Err("program-storage-migration-failed");
        }
        copy_file_with_retry(&database, &destination.join("foundry.sqlite3"))?;

        let wal = source.join("foundry.sqlite3-wal");
        if wal.exists() {
            if wal.is_symlink() || !wal.is_file() {
                return Err("program-storage-migration-failed");
            }
            copy_file_with_retry(&wal, &destination.join("foundry.sqlite3-wal"))?;
        }
    } else if source.join("foundry.sqlite3-wal").exists() {
        return Err("program-storage-migration-failed");
    }

    for auxiliary_name in ["backups", "exports"] {
        let auxiliary_source = source.join(auxiliary_name);
        if auxiliary_source.is_dir() && !auxiliary_source.is_symlink() {
            let auxiliary_destination = destination.join(auxiliary_name);
            if copy_directory_without_links(&auxiliary_source, &auxiliary_destination).is_err() {
                let _ = fs::remove_dir_all(auxiliary_destination);
            }
        }
    }
    Ok(())
}

fn staged_program_data_is_usable(staging: &Path) -> bool {
    let database = staging.join("foundry.sqlite3");
    if database.exists() && (database.is_symlink() || !database.is_file()) {
        return false;
    }
    ["backups", "exports"].into_iter().all(|name| {
        let path = staging.join(name);
        !path.exists() || (!path.is_symlink() && path.is_dir())
    })
}

fn stage_program_data(source: &Path, staging: &Path) -> Result<&'static str, &'static str> {
    if copy_directory_without_links(source, staging).is_ok()
        && staged_program_data_is_usable(staging)
    {
        return Ok("complete");
    }
    let _ = fs::remove_dir_all(staging);
    copy_essential_program_data(source, staging)?;
    Ok("essential-recovery")
}

fn available_program_data_backup(executable_dir: &Path) -> Result<PathBuf, &'static str> {
    for suffix in 0..100_u8 {
        let name = if suffix == 0 {
            PREVIOUS_PROGRAM_DATA_BACKUP.to_owned()
        } else {
            format!("{PREVIOUS_PROGRAM_DATA_BACKUP}-{suffix}")
        };
        let candidate = executable_dir.join(name);
        if !candidate.exists() {
            return Ok(candidate);
        }
    }
    Err("program-storage-migration-failed")
}

fn migrate_to_program_directory_storage(
    executable_dir: &Path,
    previous_storage_root: &Path,
) -> Result<(), &'static str> {
    let program_data = executable_dir.join("data");
    let migration_marker = program_data.join(PROGRAM_STORAGE_MARKER);
    if migration_marker.is_file() {
        return Ok(());
    }

    let previous_data = previous_storage_root.join("data");
    if previous_data.is_symlink() || program_data.is_symlink() {
        return Err("program-storage-migration-failed");
    }
    if previous_data.is_dir() {
        let staging = executable_dir.join(format!("data-appdata-migration-{}", std::process::id()));
        if staging.exists() {
            fs::remove_dir_all(&staging).map_err(|_| "program-storage-migration-failed")?;
        }
        let staged = stage_program_data(&previous_data, &staging);
        if let Err(error) = staged.and_then(|migration_mode| {
            fs::write(
                staging.join(PROGRAM_STORAGE_MARKER),
                format!("program-directory\nmigration={migration_mode}\n"),
            )
            .map_err(|_| "program-storage-migration-failed")
        }) {
            let _ = fs::remove_dir_all(&staging);
            return Err(error);
        }

        let backup = if program_data.exists() {
            let backup = match available_program_data_backup(executable_dir) {
                Ok(value) => value,
                Err(error) => {
                    let _ = fs::remove_dir_all(&staging);
                    return Err(error);
                }
            };
            fs::rename(&program_data, &backup).map_err(|_| {
                let _ = fs::remove_dir_all(&staging);
                "program-storage-migration-failed"
            })?;
            Some(backup)
        } else {
            None
        };

        if fs::rename(&staging, &program_data).is_err() {
            if let Some(backup) = backup {
                let _ = fs::rename(backup, &program_data);
            }
            let _ = fs::remove_dir_all(&staging);
            return Err("program-storage-migration-failed");
        }
        return Ok(());
    }

    fs::create_dir_all(&program_data).map_err(|_| "program-storage-unavailable")?;
    fs::write(migration_marker, b"program-directory\n")
        .map_err(|_| "program-storage-unavailable")?;
    Ok(())
}

fn select_storage_root(app: &AppHandle, executable_dir: &Path) -> Result<PathBuf, &'static str> {
    if executable_dir.join(PORTABLE_MARKER).is_file() {
        return Ok(executable_dir.to_path_buf());
    }
    let previous_storage_root = app
        .path()
        .app_local_data_dir()
        .map_err(|_| "program-storage-unavailable")?;
    migrate_to_program_directory_storage(executable_dir, &previous_storage_root)?;
    Ok(executable_dir.to_path_buf())
}

fn sidecar_startup_error_code(value: &serde_json::Value) -> Option<&'static str> {
    if value.get("event").and_then(serde_json::Value::as_str) != Some("error") {
        return None;
    }
    match value.get("code").and_then(serde_json::Value::as_str) {
        Some("invalid-startup") => Some("sidecar-startup-rejected"),
        Some("program-storage-unavailable") => Some("program-storage-unavailable"),
        Some("database-startup-failed") => Some("database-startup-failed"),
        Some("loopback-bind-failed") => Some("sidecar-loopback-unavailable"),
        _ => Some("sidecar-ready-invalid"),
    }
}

fn sidecar_startup_error_is_retryable(error_code: &str) -> bool {
    matches!(
        error_code,
        "database-startup-failed"
            | "sidecar-spawn-failed"
            | "sidecar-startup-write-failed"
            | "sidecar-ready-read-failed"
            | "sidecar-ready-invalid"
            | "sidecar-loopback-unavailable"
    )
}

fn launch_sidecar(
    app: &AppHandle,
) -> Result<
    (
        SidecarProcess,
        u32,
        RuntimeDataSnapshot,
        RuntimeUpdaterSnapshot,
        RuntimeAppearanceSnapshot,
    ),
    &'static str,
> {
    let executable_directory = std::env::current_exe()
        .map_err(|_| "program-directory-unavailable")?
        .parent()
        .ok_or("program-directory-unavailable")?
        .to_path_buf();
    let program_directory = select_storage_root(app, &executable_directory)?;
    let sidecar_path = app
        .path()
        .resource_dir()
        .map_err(|_| "sidecar-resource-unavailable")?
        .join("foundry-sidecar.exe");
    if !sidecar_path.is_file() {
        return Err("sidecar-not-found");
    }

    let token = session_token()?;
    let mut command = Command::new(sidecar_path);
    command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(WINDOWS_CREATE_NO_WINDOW);
    }

    let mut child = command.spawn().map_err(|_| "sidecar-spawn-failed")?;
    let result = (|| {
        let startup_message = serde_json::json!({
            "protocol": SIDECAR_PROTOCOL_VERSION,
            "sessionToken": token.clone(),
            "programDirectory": program_directory,
        });
        let child_stdin = child.stdin.as_mut().ok_or("sidecar-stdin-unavailable")?;
        serde_json::to_writer(&mut *child_stdin, &startup_message)
            .map_err(|_| "sidecar-startup-write-failed")?;
        child_stdin
            .write_all(b"\n")
            .and_then(|_| child_stdin.flush())
            .map_err(|_| "sidecar-startup-write-failed")?;

        let child_stdout = child.stdout.take().ok_or("sidecar-stdout-unavailable")?;
        let (sender, receiver) = mpsc::sync_channel(1);
        thread::spawn(move || {
            let mut readiness_line = String::new();
            let result = BufReader::new(child_stdout).read_line(&mut readiness_line);
            let _ = sender.send(result.map(|_| readiness_line));
        });

        let readiness_line = receiver
            .recv_timeout(SIDECAR_READY_TIMEOUT)
            .map_err(|_| "sidecar-ready-timeout")?
            .map_err(|_| "sidecar-ready-read-failed")?;
        let readiness_value: serde_json::Value =
            serde_json::from_str(&readiness_line).map_err(|_| "sidecar-ready-invalid")?;
        if let Some(error_code) = sidecar_startup_error_code(&readiness_value) {
            return Err(error_code);
        }
        let ready: SidecarReady =
            serde_json::from_value(readiness_value).map_err(|_| "sidecar-ready-invalid")?;
        if ready.event != "ready"
            || ready.protocol != SIDECAR_PROTOCOL_VERSION
            || ready.host != "127.0.0.1"
            || ready.port == 0
            || ready.database.state != "ready"
            || ready.database.location != DATABASE_LOCATION
            || !data_snapshot_is_valid(&ready.data)
            || !updater_snapshot_is_valid(&ready.updater)
            || !appearance_snapshot_is_valid(&ready.appearance)
        {
            return Err("sidecar-ready-invalid");
        }

        Ok((
            ready.port,
            ready.database.schema_version,
            ready.data,
            ready.updater,
            ready.appearance,
        ))
    })();

    match result {
        Ok((port, schema_version, data, updater, appearance)) => Ok((
            SidecarProcess {
                child,
                session_token: token,
                port,
            },
            schema_version,
            data,
            updater,
            appearance,
        )),
        Err(error_code) => {
            terminate_child(&mut child);
            Err(error_code)
        }
    }
}

fn start_sidecar(app: AppHandle) {
    let state = app.state::<RuntimeState>();
    if state.shutting_down.load(Ordering::Acquire) {
        return;
    }

    let mut last_error = "sidecar-startup-failed";
    for attempt in 0..SIDECAR_RESTART_RETRY_COUNT {
        match launch_sidecar(&app) {
            Ok((mut process, schema_version, data, updater, appearance)) => {
                if state.shutting_down.load(Ordering::Acquire) {
                    terminate_child(&mut process.child);
                    return;
                }
                *state
                    .sidecar
                    .lock()
                    .unwrap_or_else(|error| error.into_inner()) = Some(process);
                state.set_snapshot(RuntimeSnapshot::ready(
                    schema_version,
                    data,
                    updater,
                    appearance,
                ));
                return;
            }
            Err(error_code) => last_error = error_code,
        }

        if attempt + 1 < SIDECAR_RESTART_RETRY_COUNT
            && sidecar_startup_error_is_retryable(last_error)
        {
            thread::sleep(SIDECAR_RESTART_RETRY_DELAY);
            if state.shutting_down.load(Ordering::Acquire) {
                return;
            }
        } else {
            break;
        }
    }
    state.set_snapshot(RuntimeSnapshot::failed(last_error));
}

fn supervise_sidecar(app: AppHandle) {
    start_sidecar(app.clone());
    let state = app.state::<RuntimeState>();

    loop {
        thread::sleep(SIDECAR_SUPERVISOR_INTERVAL);
        if state.shutting_down.load(Ordering::Acquire) {
            return;
        }

        let exited = {
            let mut sidecar = state
                .sidecar
                .lock()
                .unwrap_or_else(|error| error.into_inner());
            let exited = sidecar
                .as_mut()
                .is_some_and(|process| matches!(process.child.try_wait(), Ok(Some(_)) | Err(_)));
            if exited {
                sidecar.take();
            }
            exited
        };
        if !exited {
            continue;
        }

        state.set_snapshot(RuntimeSnapshot::failed("sidecar-exited"));
        thread::sleep(SIDECAR_RESTART_RETRY_DELAY);
        if state.shutting_down.load(Ordering::Acquire) {
            return;
        }
        state.set_snapshot(RuntimeSnapshot::starting());
        start_sidecar(app.clone());
    }
}

fn stop_sidecar(app: &AppHandle) {
    let state = app.state::<RuntimeState>();
    if state.shutting_down.swap(true, Ordering::AcqRel) {
        return;
    }

    let mut process = state
        .sidecar
        .lock()
        .unwrap_or_else(|error| error.into_inner())
        .take();
    if let Some(process) = process.as_mut() {
        if let Some(mut stdin) = process.child.stdin.take() {
            let _ = stdin.write_all(b"{\"command\":\"shutdown\"}\n");
            let _ = stdin.flush();
        }

        let deadline = Instant::now() + SIDECAR_SHUTDOWN_TIMEOUT;
        while Instant::now() < deadline {
            match process.child.try_wait() {
                Ok(Some(_)) => return,
                Ok(None) => thread::sleep(Duration::from_millis(50)),
                Err(_) => break,
            }
        }
        terminate_child(&mut process.child);
    }
}

fn refresh_sidecar_status(state: &RuntimeState) {
    if state.shutting_down.load(Ordering::Acquire) {
        return;
    }
    let exited = state
        .sidecar
        .lock()
        .unwrap_or_else(|error| error.into_inner())
        .as_mut()
        .is_some_and(|process| matches!(process.child.try_wait(), Ok(Some(_)) | Err(_)));
    if exited {
        state.set_snapshot(RuntimeSnapshot::failed("sidecar-exited"));
    }
}

fn sidecar_json_request(
    process: &SidecarProcess,
    method: &str,
    path: &str,
    body: &str,
) -> Result<String, &'static str> {
    sidecar_json_request_with_timeout(process, method, path, body, SIDECAR_REQUEST_TIMEOUT)
}

fn sidecar_json_request_with_timeout(
    process: &SidecarProcess,
    method: &str,
    path: &str,
    body: &str,
    timeout: Duration,
) -> Result<String, &'static str> {
    let address = SocketAddrV4::new(Ipv4Addr::LOCALHOST, process.port);
    let mut stream = TcpStream::connect_timeout(&address.into(), timeout)
        .map_err(|_| "sidecar-request-failed")?;
    stream
        .set_read_timeout(Some(timeout))
        .and_then(|_| stream.set_write_timeout(Some(timeout)))
        .map_err(|_| "sidecar-request-failed")?;

    let request = format!(
        "{method} {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nAuthorization: Bearer {}\r\nAccept: application/json\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        process.session_token,
        body.len(),
    );
    stream
        .write_all(request.as_bytes())
        .and_then(|_| stream.flush())
        .map_err(|_| "sidecar-request-failed")?;

    let mut response = String::new();
    stream
        .take(SIDECAR_MAX_RESPONSE_BYTES + 1)
        .read_to_string(&mut response)
        .map_err(|_| "sidecar-response-invalid")?;
    if response.len() as u64 > SIDECAR_MAX_RESPONSE_BYTES {
        return Err("sidecar-response-invalid");
    }
    let (headers, response_body) = response
        .split_once("\r\n\r\n")
        .ok_or("sidecar-response-invalid")?;
    let status_line = headers.lines().next().ok_or("sidecar-response-invalid")?;
    if status_line != "HTTP/1.1 200 OK" && status_line != "HTTP/1.0 200 OK" {
        return Err("sidecar-request-rejected");
    }
    Ok(response_body.to_owned())
}

fn asset_sync_response_is_valid(response: &AssetSyncResponse) -> bool {
    response
        .completed
        .checked_add(response.partial)
        .and_then(|value| value.checked_add(response.failed))
        == Some(response.characters.len() as u64)
        && response
            .characters
            .iter()
            .try_fold(0_u64, |total, character| {
                total.checked_add(character.assets)
            })
            == Some(response.assets)
        && response.characters.iter().all(|character| {
            character.character_id > 0
                && character.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && matches!(
                    character.status.as_str(),
                    "completed" | "partial" | "failed"
                )
                && ((character.status == "completed" && character.error_code.is_none())
                    || (character.status == "partial"
                        && character
                            .error_code
                            .as_ref()
                            .is_some_and(|code| asset_text_is_valid(code, 120)))
                    || (character.status == "failed"
                        && character.pages == 0
                        && character.assets == 0
                        && character.resolved == 0
                        && character.restricted == 0
                        && character.unresolved == 0
                        && character.cycles == 0
                        && character
                            .error_code
                            .as_ref()
                            .is_some_and(|code| asset_text_is_valid(code, 120))))
        })
}

#[tauri::command]
fn set_update_channel(channel: String, state: State<'_, RuntimeState>) -> Result<String, String> {
    if !matches!(channel.as_str(), "stable" | "beta" | "preview") {
        return Err("unsupported-update-channel".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({ "channel": channel.clone() }).to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "PUT", "/settings/update", &body).map_err(str::to_owned)?
    };
    let updater: RuntimeUpdaterSnapshot =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !updater_snapshot_is_valid(&updater) || updater.channel != channel {
        return Err("sidecar-response-invalid".to_owned());
    }

    state
        .snapshot
        .lock()
        .unwrap_or_else(|error| error.into_inner())
        .updater = updater.clone();
    serde_json::to_string(&updater).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn set_font_scale(font_scale: String, state: State<'_, RuntimeState>) -> Result<String, String> {
    if !FONT_SCALES.contains(&font_scale.as_str()) {
        return Err("unsupported-font-scale".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({ "fontScale": font_scale.clone() }).to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "PUT", "/settings/appearance", &body)
            .map_err(str::to_owned)?
    };
    let appearance: RuntimeAppearanceSnapshot =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !appearance_snapshot_is_valid(&appearance) || appearance.font_scale != font_scale {
        return Err("sidecar-response-invalid".to_owned());
    }
    state
        .snapshot
        .lock()
        .unwrap_or_else(|error| error.into_inner())
        .appearance = appearance.clone();
    serde_json::to_string(&appearance).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn list_eve_characters(state: State<'_, RuntimeState>) -> Result<String, String> {
    refresh_sidecar_status(&state);
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "GET", "/characters", "").map_err(str::to_owned)?
    };
    let characters: EveCharactersResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if characters
        .characters
        .iter()
        .any(|character| !eve_character_record_is_valid(character))
        || characters
            .characters
            .iter()
            .map(|character| character.character_id)
            .collect::<HashSet<_>>()
            .len()
            != characters.characters.len()
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&characters).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn list_account_groups(state: State<'_, RuntimeState>) -> Result<String, String> {
    refresh_sidecar_status(&state);
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "GET", "/account-groups", "").map_err(str::to_owned)?
    };
    let groups: AccountGroupsResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if groups
        .groups
        .iter()
        .any(|group| !account_group_record_is_valid(group))
        || groups
            .groups
            .iter()
            .map(|group| group.id)
            .collect::<HashSet<_>>()
            .len()
            != groups.groups.len()
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&groups).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn sync_assets(state: State<'_, RuntimeState>) -> Result<String, String> {
    refresh_sidecar_status(&state);
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request_with_timeout(process, "POST", "/assets/sync", "{}", ASSET_SYNC_TIMEOUT)
            .map_err(str::to_owned)?
    };
    let result: AssetSyncResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !asset_sync_response_is_valid(&result) {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&result).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn sync_blueprints(state: State<'_, RuntimeState>) -> Result<String, String> {
    refresh_sidecar_status(&state);
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request_with_timeout(
            process,
            "POST",
            "/blueprints/sync",
            "{}",
            ASSET_SYNC_TIMEOUT,
        )
        .map_err(str::to_owned)?
    };
    let result: BlueprintSyncResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !blueprint_sync_response_is_valid(&result) {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&result).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn sync_industry_jobs(state: State<'_, RuntimeState>) -> Result<String, String> {
    refresh_sidecar_status(&state);
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request_with_timeout(
            process,
            "POST",
            "/industry-jobs/sync",
            "{}",
            ASSET_SYNC_TIMEOUT,
        )
        .map_err(str::to_owned)?
    };
    let result: IndustryJobSyncResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !industry_job_sync_response_is_valid(&result) {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&result).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn sync_industry_facilities(state: State<'_, RuntimeState>) -> Result<String, String> {
    refresh_sidecar_status(&state);
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request_with_timeout(
            process,
            "POST",
            "/industry-facilities/sync",
            "{}",
            ASSET_SYNC_TIMEOUT,
        )
        .map_err(str::to_owned)?
    };
    let result: IndustryFacilitySyncResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !industry_facility_sync_response_is_valid(&result) {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&result).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn sync_character_skills(state: State<'_, RuntimeState>) -> Result<String, String> {
    refresh_sidecar_status(&state);
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request_with_timeout(process, "POST", "/skills/sync", "{}", ASSET_SYNC_TIMEOUT)
            .map_err(str::to_owned)?
    };
    let result: CharacterSkillSyncResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !character_skill_sync_response_is_valid(&result) {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&result).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn query_blueprints(
    search: String,
    owner_character_id: Option<u64>,
    kind: Option<String>,
    offset: u64,
    limit: u64,
    sort_by: String,
    sort_direction: String,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if search.chars().count() > MAX_ASSET_SEARCH_CHARACTERS
        || search.trim() != search
        || owner_character_id == Some(0)
        || owner_character_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || kind
            .as_deref()
            .is_some_and(|value| !matches!(value, "original" | "copy"))
        || limit == 0
        || limit > MAX_ASSET_PAGE_SIZE
        || offset > JAVASCRIPT_MAX_SAFE_INTEGER
        || !BLUEPRINT_SORT_FIELDS.contains(&sort_by.as_str())
        || !SORT_DIRECTIONS.contains(&sort_direction.as_str())
    {
        return Err("blueprint-query-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "search": search, "ownerCharacterId": owner_character_id, "kind": kind,
        "offset": offset, "limit": limit, "sortBy": sort_by, "sortDirection": sort_direction,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/blueprints/query", &body).map_err(str::to_owned)?
    };
    let page: BlueprintQueryResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !blueprint_query_response_is_valid(&page) || page.offset != offset || page.limit != limit {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&page).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn query_industry_jobs(
    search: String,
    owner_character_id: Option<u64>,
    status: Option<String>,
    activity_id: Option<u8>,
    correlation: Option<String>,
    offset: u64,
    limit: u64,
    sort_by: String,
    sort_direction: String,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if search.chars().count() > MAX_ASSET_SEARCH_CHARACTERS
        || search.trim() != search
        || owner_character_id == Some(0)
        || owner_character_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || status
            .as_deref()
            .is_some_and(|value| !INDUSTRY_JOB_STATUSES.contains(&value))
        || activity_id.is_some_and(|value| !INDUSTRY_JOB_ACTIVITY_IDS.contains(&value))
        || correlation
            .as_deref()
            .is_some_and(|value| !INDUSTRY_JOB_CORRELATIONS.contains(&value))
        || limit == 0
        || limit > MAX_ASSET_PAGE_SIZE
        || offset > JAVASCRIPT_MAX_SAFE_INTEGER
        || !INDUSTRY_JOB_SORT_FIELDS.contains(&sort_by.as_str())
        || !SORT_DIRECTIONS.contains(&sort_direction.as_str())
    {
        return Err("industry-job-query-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "search": search,
        "ownerCharacterId": owner_character_id,
        "status": status,
        "activityId": activity_id,
        "correlation": correlation,
        "offset": offset,
        "limit": limit,
        "sortBy": sort_by,
        "sortDirection": sort_direction,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/industry-jobs/query", &body)
            .map_err(str::to_owned)?
    };
    let page: IndustryJobQueryResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !industry_job_query_response_is_valid(&page) || page.offset != offset || page.limit != limit
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&page).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn query_industry_facilities(
    search: String,
    kind: Option<String>,
    access: Option<String>,
    security_class: Option<String>,
    activity: String,
    used_only: bool,
    offset: u64,
    limit: u64,
    sort_by: String,
    sort_direction: String,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if search.chars().count() > MAX_ASSET_SEARCH_CHARACTERS
        || search.trim() != search
        || kind
            .as_deref()
            .is_some_and(|value| !INDUSTRY_FACILITY_KINDS.contains(&value))
        || access
            .as_deref()
            .is_some_and(|value| !INDUSTRY_FACILITY_ACCESS_STATES.contains(&value))
        || security_class
            .as_deref()
            .is_some_and(|value| !INDUSTRY_SECURITY_CLASSES.contains(&value))
        || !INDUSTRY_COST_ACTIVITIES.contains(&activity.as_str())
        || limit == 0
        || limit > MAX_ASSET_PAGE_SIZE
        || offset > JAVASCRIPT_MAX_SAFE_INTEGER
        || !INDUSTRY_FACILITY_SORT_FIELDS.contains(&sort_by.as_str())
        || !SORT_DIRECTIONS.contains(&sort_direction.as_str())
    {
        return Err("industry-facility-query-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "search": search,
        "kind": kind,
        "access": access,
        "securityClass": security_class,
        "activity": activity,
        "usedOnly": used_only,
        "offset": offset,
        "limit": limit,
        "sortBy": sort_by,
        "sortDirection": sort_direction,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/industry-facilities/query", &body)
            .map_err(str::to_owned)?
    };
    let page: IndustryFacilityQueryResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !industry_facility_query_response_is_valid(&page)
        || page.offset != offset
        || page.limit != limit
        || page.activity != activity
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&page).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn query_industry_slots(
    owner_character_id: Option<u64>,
    offset: u64,
    limit: u64,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if owner_character_id == Some(0)
        || owner_character_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || limit == 0
        || limit > MAX_ASSET_PAGE_SIZE
        || offset > JAVASCRIPT_MAX_SAFE_INTEGER
    {
        return Err("industry-slot-query-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "ownerCharacterId": owner_character_id,
        "offset": offset,
        "limit": limit,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/industry-slots/query", &body)
            .map_err(str::to_owned)?
    };
    let page: IndustrySlotQueryResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !industry_slot_query_response_is_valid(&page) || page.offset != offset || page.limit != limit
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&page).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn query_production_catalog(
    search: String,
    activity: Option<String>,
    offset: u64,
    limit: u64,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if search.chars().count() > MAX_ASSET_SEARCH_CHARACTERS
        || search.trim() != search
        || activity
            .as_deref()
            .is_some_and(|value| !PRODUCTION_ACTIVITIES.contains(&value))
        || offset > JAVASCRIPT_MAX_SAFE_INTEGER
        || limit == 0
        || limit > 100
    {
        return Err("production-catalog-query-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "search": search,
        "activity": activity,
        "offset": offset,
        "limit": limit,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/production-plans/catalog", &body)
            .map_err(str::to_owned)?
    };
    let page: ProductionCatalogResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !production_catalog_response_is_valid(&page) || page.offset != offset || page.limit != limit
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&page).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn query_production_plans(
    search: String,
    owner_character_id: Option<u64>,
    activity: Option<String>,
    plan_state: Option<String>,
    offset: u64,
    limit: u64,
    sort_by: String,
    sort_direction: String,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if search.chars().count() > MAX_ASSET_SEARCH_CHARACTERS
        || search.trim() != search
        || owner_character_id == Some(0)
        || owner_character_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || activity
            .as_deref()
            .is_some_and(|value| !PRODUCTION_ACTIVITIES.contains(&value))
        || plan_state
            .as_deref()
            .is_some_and(|value| !PRODUCTION_PLAN_STATES.contains(&value))
        || offset > JAVASCRIPT_MAX_SAFE_INTEGER
        || limit == 0
        || limit > 100
        || !PRODUCTION_PLAN_SORT_FIELDS.contains(&sort_by.as_str())
        || !SORT_DIRECTIONS.contains(&sort_direction.as_str())
    {
        return Err("production-plan-query-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "search": search,
        "ownerCharacterId": owner_character_id,
        "activity": activity,
        "state": plan_state,
        "offset": offset,
        "limit": limit,
        "sortBy": sort_by,
        "sortDirection": sort_direction,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/production-plans/query", &body)
            .map_err(str::to_owned)?
    };
    let page: ProductionPlanQueryResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !production_plan_query_response_is_valid(&page)
        || page.offset != offset
        || page.limit != limit
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&page).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
#[allow(clippy::too_many_arguments)]
fn save_production_plan(
    plan_id: Option<u64>,
    owner_character_id: u64,
    blueprint_type_id: u64,
    activity: String,
    product_type_id: u64,
    target_quantity: u64,
    priority: u16,
    note: Option<String>,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if plan_id == Some(0)
        || plan_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || !production_id_is_valid(owner_character_id)
        || !production_id_is_valid(blueprint_type_id)
        || !PRODUCTION_ACTIVITIES.contains(&activity.as_str())
        || !production_id_is_valid(product_type_id)
        || !production_id_is_valid(target_quantity)
        || priority > 999
        || note
            .as_ref()
            .is_some_and(|value| !asset_text_is_valid(value, 240))
    {
        return Err("production-plan-input-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "planId": plan_id,
        "ownerCharacterId": owner_character_id,
        "blueprintTypeId": blueprint_type_id,
        "activity": activity,
        "productTypeId": product_type_id,
        "targetQuantity": target_quantity,
        "priority": priority,
        "note": note,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/production-plans/save", &body)
            .map_err(str::to_owned)?
    };
    let saved: ProductionPlanMutationResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !production_plan_mutation_is_valid(&saved)
        || saved.plan_id != plan_id.unwrap_or(saved.plan_id)
        || saved.owner_character_id != owner_character_id
        || saved.blueprint_type_id != blueprint_type_id
        || saved.activity != activity
        || saved.product_type_id != product_type_id
        || saved.target_quantity != target_quantity
        || saved.priority != priority
        || saved.note != note
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&saved).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn delete_production_plan(plan_id: u64, state: State<'_, RuntimeState>) -> Result<String, String> {
    if !production_id_is_valid(plan_id) {
        return Err("production-plan-delete-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({"planId": plan_id}).to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/production-plans/delete", &body)
            .map_err(str::to_owned)?
    };
    let deleted: ProductionPlanDeleteResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !deleted.deleted || deleted.plan_id != plan_id {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&deleted).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn check_for_updates(state: State<'_, RuntimeState>) -> Result<String, String> {
    refresh_sidecar_status(&state);
    let expected_channel = state
        .snapshot
        .lock()
        .unwrap_or_else(|error| error.into_inner())
        .updater
        .channel
        .clone();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request_with_timeout(
            process,
            "GET",
            "/updates/check",
            "",
            UPDATE_NOTICE_TIMEOUT,
        )
        .map_err(str::to_owned)?
    };
    let notice: PublicReleaseNotice =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !public_release_notice_is_valid(&notice)
        || notice.channel != expected_channel
        || notice.current_version != env!("CARGO_PKG_VERSION")
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&notice).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn open_release_downloads(version: Option<String>) -> Result<String, String> {
    let url = release_page_url(version.as_deref()).map_err(str::to_owned)?;
    launch_system_browser(&url).map_err(str::to_owned)?;
    Ok(serde_json::json!({"opened": true, "url": url}).to_string())
}

#[tauri::command]
fn query_research_plans(
    search: String,
    owner_character_id: Option<u64>,
    plan_state: Option<String>,
    planned_only: bool,
    offset: u64,
    limit: u64,
    sort_by: String,
    sort_direction: String,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if search.chars().count() > MAX_ASSET_SEARCH_CHARACTERS
        || search.trim() != search
        || owner_character_id == Some(0)
        || owner_character_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || plan_state
            .as_deref()
            .is_some_and(|value| !RESEARCH_PLAN_STATES.contains(&value))
        || limit == 0
        || limit > MAX_ASSET_PAGE_SIZE
        || offset > JAVASCRIPT_MAX_SAFE_INTEGER
        || !RESEARCH_PLAN_SORT_FIELDS.contains(&sort_by.as_str())
        || !SORT_DIRECTIONS.contains(&sort_direction.as_str())
    {
        return Err("research-query-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "search": search,
        "ownerCharacterId": owner_character_id,
        "state": plan_state,
        "plannedOnly": planned_only,
        "offset": offset,
        "limit": limit,
        "sortBy": sort_by,
        "sortDirection": sort_direction,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/research-plans/query", &body)
            .map_err(str::to_owned)?
    };
    let page: ResearchPlanQueryResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !research_plan_query_response_is_valid(&page) || page.offset != offset || page.limit != limit
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&page).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn save_research_plan(
    owner_character_id: u64,
    blueprint_item_id: u64,
    next_activity: String,
    target_material_efficiency: u8,
    target_time_efficiency: u8,
    priority: u16,
    note: Option<String>,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if owner_character_id == 0
        || owner_character_id > JAVASCRIPT_MAX_SAFE_INTEGER
        || blueprint_item_id == 0
        || blueprint_item_id > JAVASCRIPT_MAX_SAFE_INTEGER
        || !RESEARCH_PLAN_ACTIVITIES.contains(&next_activity.as_str())
        || target_material_efficiency > 10
        || target_time_efficiency > 20
        || priority > 999
        || note
            .as_ref()
            .is_some_and(|value| !asset_text_is_valid(value, 240))
    {
        return Err("research-plan-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "ownerCharacterId": owner_character_id,
        "blueprintItemId": blueprint_item_id,
        "nextActivity": next_activity,
        "targetMaterialEfficiency": target_material_efficiency,
        "targetTimeEfficiency": target_time_efficiency,
        "priority": priority,
        "note": note,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/research-plans/save", &body)
            .map_err(str::to_owned)?
    };
    let saved: ResearchPlanMutationResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !research_plan_mutation_response_is_valid(&saved)
        || saved.owner_character_id != owner_character_id
        || saved.blueprint_item_id != blueprint_item_id
        || saved.next_activity != next_activity
        || saved.target_material_efficiency != target_material_efficiency
        || saved.target_time_efficiency != target_time_efficiency
        || saved.priority != priority
        || saved.note != note
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&saved).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn delete_research_plan(
    owner_character_id: u64,
    blueprint_item_id: u64,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if owner_character_id == 0
        || owner_character_id > JAVASCRIPT_MAX_SAFE_INTEGER
        || blueprint_item_id == 0
        || blueprint_item_id > JAVASCRIPT_MAX_SAFE_INTEGER
    {
        return Err("research-plan-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "ownerCharacterId": owner_character_id,
        "blueprintItemId": blueprint_item_id,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/research-plans/delete", &body)
            .map_err(str::to_owned)?
    };
    let deleted: ResearchPlanDeleteResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if deleted.owner_character_id != owner_character_id
        || deleted.blueprint_item_id != blueprint_item_id
        || !deleted.deleted
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&deleted).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn query_character_skills(
    search: String,
    owner_character_id: Option<u64>,
    trained_level: Option<u8>,
    active_state: Option<String>,
    offset: u64,
    limit: u64,
    sort_by: String,
    sort_direction: String,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if search.chars().count() > MAX_ASSET_SEARCH_CHARACTERS
        || search.trim() != search
        || owner_character_id == Some(0)
        || owner_character_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || trained_level.is_some_and(|value| value > 5)
        || active_state
            .as_deref()
            .is_some_and(|value| !CHARACTER_SKILL_ACTIVE_STATES.contains(&value))
        || limit == 0
        || limit > MAX_ASSET_PAGE_SIZE
        || offset > JAVASCRIPT_MAX_SAFE_INTEGER
        || !CHARACTER_SKILL_SORT_FIELDS.contains(&sort_by.as_str())
        || !SORT_DIRECTIONS.contains(&sort_direction.as_str())
    {
        return Err("character-skill-query-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "search": search,
        "ownerCharacterId": owner_character_id,
        "trainedLevel": trained_level,
        "activeState": active_state,
        "offset": offset,
        "limit": limit,
        "sortBy": sort_by,
        "sortDirection": sort_direction,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/skills/query", &body).map_err(str::to_owned)?
    };
    let page: CharacterSkillQueryResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !character_skill_query_response_is_valid(&page)
        || page.offset != offset
        || page.limit != limit
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&page).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn query_assets(
    search: String,
    owner_character_id: Option<u64>,
    location_status: Option<String>,
    offset: u64,
    limit: u64,
    sort_by: String,
    sort_direction: String,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if search.chars().count() > MAX_ASSET_SEARCH_CHARACTERS
        || search.trim() != search
        || owner_character_id == Some(0)
        || owner_character_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || location_status
            .as_deref()
            .is_some_and(|status| !ASSET_LOCATION_STATUSES.contains(&status))
        || limit == 0
        || limit > MAX_ASSET_PAGE_SIZE
        || offset > JAVASCRIPT_MAX_SAFE_INTEGER
        || !ASSET_SORT_FIELDS.contains(&sort_by.as_str())
        || !SORT_DIRECTIONS.contains(&sort_direction.as_str())
    {
        return Err("asset-query-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "search": search,
        "ownerCharacterId": owner_character_id,
        "locationStatus": location_status,
        "offset": offset,
        "limit": limit,
        "sortBy": sort_by,
        "sortDirection": sort_direction,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/assets/query", &body).map_err(str::to_owned)?
    };
    let page: AssetQueryResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !asset_query_response_is_valid(&page) || page.offset != offset || page.limit != limit {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&page).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn query_asset_summary(
    search: String,
    owner_character_id: Option<u64>,
    location_status: Option<String>,
    offset: u64,
    limit: u64,
    sort_by: String,
    sort_direction: String,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if search.chars().count() > MAX_ASSET_SEARCH_CHARACTERS
        || search.trim() != search
        || owner_character_id == Some(0)
        || owner_character_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || location_status
            .as_deref()
            .is_some_and(|status| !ASSET_LOCATION_STATUSES.contains(&status))
        || limit == 0
        || limit > MAX_ASSET_PAGE_SIZE
        || offset > JAVASCRIPT_MAX_SAFE_INTEGER
        || !ASSET_SUMMARY_SORT_FIELDS.contains(&sort_by.as_str())
        || !SORT_DIRECTIONS.contains(&sort_direction.as_str())
    {
        return Err("asset-summary-query-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "search": search,
        "ownerCharacterId": owner_character_id,
        "locationStatus": location_status,
        "offset": offset,
        "limit": limit,
        "sortBy": sort_by,
        "sortDirection": sort_direction,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/assets/summary/query", &body)
            .map_err(str::to_owned)?
    };
    let page: AssetSummaryQueryResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !asset_summary_query_response_is_valid(&page) || page.offset != offset || page.limit != limit
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&page).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn export_assets_csv(
    search: String,
    owner_character_id: Option<u64>,
    location_status: Option<String>,
    sort_by: String,
    sort_direction: String,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if search.chars().count() > MAX_ASSET_SEARCH_CHARACTERS
        || search.trim() != search
        || owner_character_id == Some(0)
        || owner_character_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || location_status
            .as_deref()
            .is_some_and(|status| !ASSET_LOCATION_STATUSES.contains(&status))
        || !ASSET_SORT_FIELDS.contains(&sort_by.as_str())
        || !SORT_DIRECTIONS.contains(&sort_direction.as_str())
    {
        return Err("asset-query-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "search": search,
        "ownerCharacterId": owner_character_id,
        "locationStatus": location_status,
        "sortBy": sort_by,
        "sortDirection": sort_direction,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/assets/export", &body).map_err(str::to_owned)?
    };
    let exported: AssetExportResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !asset_export_response_is_valid(&exported) {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&exported).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn query_asset_deltas(
    search: String,
    owner_character_id: Option<u64>,
    change_type: Option<String>,
    offset: u64,
    limit: u64,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if search.chars().count() > MAX_ASSET_SEARCH_CHARACTERS
        || search.trim() != search
        || owner_character_id == Some(0)
        || owner_character_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || change_type
            .as_deref()
            .is_some_and(|value| !ASSET_DELTA_CHANGE_TYPES.contains(&value))
        || limit == 0
        || limit > MAX_ASSET_PAGE_SIZE
        || offset > JAVASCRIPT_MAX_SAFE_INTEGER
    {
        return Err("asset-delta-query-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "search": search,
        "ownerCharacterId": owner_character_id,
        "changeType": change_type,
        "offset": offset,
        "limit": limit,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/assets/deltas/query", &body)
            .map_err(str::to_owned)?
    };
    let page: AssetDeltaQueryResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !asset_delta_response_is_valid(&page) || page.offset != offset || page.limit != limit {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&page).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn update_eve_character(
    character_id: u64,
    alias: Option<String>,
    account_group_id: Option<u64>,
    enabled: bool,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if character_id == 0
        || account_group_id == Some(0)
        || alias
            .as_deref()
            .is_some_and(|value| !management_label_is_valid(value))
    {
        return Err("character-update-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "alias": alias,
        "accountGroupId": account_group_id,
        "enabled": enabled,
    })
    .to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(
            process,
            "PATCH",
            &format!("/characters/{character_id}"),
            &body,
        )
        .map_err(str::to_owned)?
    };
    let updated: EveCharacterResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if updated.character.character_id != character_id
        || !eve_character_record_is_valid(&updated.character)
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&updated).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn delete_eve_character(
    character_id: u64,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if character_id == 0 {
        return Err("character-delete-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(
            process,
            "DELETE",
            &format!("/characters/{character_id}"),
            "",
        )
        .map_err(str::to_owned)?
    };
    let deleted: CharacterDeletionResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !deleted.deleted || deleted.character_id != character_id {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&deleted).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn create_account_group(label: String, state: State<'_, RuntimeState>) -> Result<String, String> {
    if !management_label_is_valid(&label) {
        return Err("account-group-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({ "label": label }).to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/account-groups", &body).map_err(str::to_owned)?
    };
    let created: AccountGroupResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !account_group_record_is_valid(&created.group) {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&created).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn rename_account_group(
    group_id: u64,
    label: String,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if group_id == 0 || !management_label_is_valid(&label) {
        return Err("account-group-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({ "label": label }).to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(
            process,
            "PATCH",
            &format!("/account-groups/{group_id}"),
            &body,
        )
        .map_err(str::to_owned)?
    };
    let updated: AccountGroupResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if updated.group.id != group_id || !account_group_record_is_valid(&updated.group) {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&updated).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn delete_account_group(group_id: u64, state: State<'_, RuntimeState>) -> Result<String, String> {
    if group_id == 0 {
        return Err("account-group-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(
            process,
            "DELETE",
            &format!("/account-groups/{group_id}"),
            "",
        )
        .map_err(str::to_owned)?
    };
    let deleted: AccountGroupDeletionResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !deleted.deleted || deleted.group_id != group_id {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&deleted).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn start_eve_sso(
    scope_packages: Vec<String>,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if scope_packages.len() != EVE_SSO_SCOPE_PACKAGES.len()
        || scope_packages
            .iter()
            .map(String::as_str)
            .ne(EVE_SSO_SCOPE_PACKAGES.iter().copied())
    {
        return Err("invalid-scope-packages".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({ "scopePackages": scope_packages }).to_string();
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "POST", "/sso/login", &body).map_err(str::to_owned)?
    };
    let started: SsoLoginStart =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if started.status.state != "waiting"
        || !sso_login_status_is_valid(&started.status)
        || !authorization_url_is_valid(&started.authorization_url)
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    if let Err(error_code) = open_system_browser(&started.authorization_url) {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        if let Some(process) = sidecar.as_ref() {
            let _ = sidecar_json_request(process, "DELETE", "/sso/login", "");
        }
        return Err(error_code.to_owned());
    }
    serde_json::to_string(&started.status).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn eve_sso_status(state: State<'_, RuntimeState>) -> Result<String, String> {
    refresh_sidecar_status(&state);
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "GET", "/sso/login", "").map_err(str::to_owned)?
    };
    let status: SsoLoginStatus =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !sso_login_status_is_valid(&status) {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&status).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn cancel_eve_sso(state: State<'_, RuntimeState>) -> Result<String, String> {
    refresh_sidecar_status(&state);
    let response = {
        let sidecar = state
            .sidecar
            .lock()
            .unwrap_or_else(|error| error.into_inner());
        let process = sidecar
            .as_ref()
            .ok_or_else(|| "sidecar-unavailable".to_owned())?;
        sidecar_json_request(process, "DELETE", "/sso/login", "").map_err(str::to_owned)?
    };
    let status: SsoLoginStatus =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !sso_login_status_is_valid(&status) || !matches!(status.state.as_str(), "idle" | "cancelled")
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&status).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn desktop_runtime_status(state: State<'_, RuntimeState>) -> String {
    refresh_sidecar_status(&state);
    serde_json::to_string(
        &*state
            .snapshot
            .lock()
            .unwrap_or_else(|error| error.into_inner()),
    )
    .unwrap_or_else(|_| {
        r#"{"state":"ready","version":"unknown","desktopShell":true,"singleInstance":true,"distribution":"installed","sidecar":"error","database":"error","databaseLocation":"data/foundry.sqlite3","schemaVersion":null,"errorCode":"status-serialization-failed","data":{"state":"error","hasCachedData":false,"observedAt":null,"expiresAt":null,"ageSeconds":null,"lastSyncStatus":"never","errorCode":"status-serialization-failed"},"updater":{"channel":"stable","manifestState":"unavailable","publicDistribution":false},"appearance":{"fontScale":"normal"}}"#.to_owned()
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let builder = tauri::Builder::default();

    #[cfg(windows)]
    let builder = builder.plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
        if let Some(window) = app.get_webview_window("main") {
            let _ = window.unminimize();
            let _ = window.show();
            let _ = window.set_focus();
        }
    }));

    let application = builder
        .manage(RuntimeState::new())
        .setup(|app| {
            let app_handle = app.handle().clone();
            thread::spawn(move || supervise_sidecar(app_handle));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            desktop_runtime_status,
            set_update_channel,
            set_font_scale,
            list_eve_characters,
            list_account_groups,
            sync_assets,
            query_assets,
            query_asset_summary,
            sync_blueprints,
            query_blueprints,
            sync_industry_jobs,
            query_industry_jobs,
            sync_industry_facilities,
            query_industry_facilities,
            query_industry_slots,
            query_production_catalog,
            query_production_plans,
            save_production_plan,
            delete_production_plan,
            check_for_updates,
            open_release_downloads,
            query_research_plans,
            save_research_plan,
            delete_research_plan,
            sync_character_skills,
            query_character_skills,
            export_assets_csv,
            query_asset_deltas,
            update_eve_character,
            delete_eve_character,
            create_account_group,
            rename_account_group,
            delete_account_group,
            start_eve_sso,
            eve_sso_status,
            cancel_eve_sso
        ])
        .build(tauri::generate_context!())
        .expect("New Eden Foundry could not start");

    application.run(|app, event| {
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            stop_sidecar(app);
        }
    });
}

#[cfg(test)]
mod tests {
    use super::{
        account_group_record_is_valid, asset_delta_response_is_valid,
        asset_export_response_is_valid, asset_query_response_is_valid, authorization_url_is_valid,
        character_skill_query_response_is_valid, character_skill_sync_response_is_valid,
        eve_character_record_is_valid, industry_job_query_response_is_valid,
        industry_job_sync_response_is_valid, industry_slot_query_response_is_valid,
        migrate_to_program_directory_storage, release_page_url,
        research_plan_query_response_is_valid, sidecar_startup_error_code,
        sidecar_startup_error_is_retryable, sso_login_status_is_valid, AccountGroupRecord,
        AssetDeltaCorrelation, AssetDeltaQueryResponse, AssetDeltaRecord, AssetDeltaSummary,
        AssetExportResponse, AssetLocationNode, AssetOwner, AssetQueryResponse, AssetRecord,
        CharacterSkillQueryResponse, CharacterSkillRecord, CharacterSkillSyncCharacterResponse,
        CharacterSkillSyncResponse, EveCharacterRecord, IndustryAssetCorrelation,
        IndustryBlueprintCorrelation, IndustryJobQueryResponse, IndustryJobRecord,
        IndustryJobSyncCharacterResponse, IndustryJobSyncResponse, IndustrySlotActivity,
        IndustrySlotQueryResponse, IndustrySlotRecord, ResearchPlanOwner,
        ResearchPlanQueryResponse, ResearchPlanRecord, ResearchPlanSummary, RuntimeDataSnapshot,
        ScopePackageStatus, SsoCharacterIdentity, SsoLoginStatus,
    };
    use std::fs;
    use std::path::{Path, PathBuf};
    use std::time::{SystemTime, UNIX_EPOCH};

    struct TestDirectory(PathBuf);

    impl TestDirectory {
        fn new(label: &str) -> Self {
            let nonce = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .expect("system clock must be after the Unix epoch")
                .as_nanos();
            let path = std::env::temp_dir().join(format!(
                "new-eden-foundry-{label}-{}-{nonce}",
                std::process::id()
            ));
            fs::create_dir(&path).expect("test directory must be created");
            Self(path)
        }

        fn path(&self) -> &Path {
            &self.0
        }
    }

    impl Drop for TestDirectory {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    #[test]
    fn migrates_appdata_into_the_program_directory_once() {
        let root = TestDirectory::new("storage-migration");
        let executable_dir = root.path().join("program");
        let previous_root = root.path().join("appdata");
        fs::create_dir_all(executable_dir.join("data"))
            .expect("old program data directory must be created");
        fs::create_dir_all(previous_root.join("data/backups"))
            .expect("previous app data directory must be created");
        fs::write(executable_dir.join("data/foundry.sqlite3"), b"old-program")
            .expect("old program database must be written");
        fs::write(
            previous_root.join("data/foundry.sqlite3"),
            b"appdata-current",
        )
        .expect("current database must be written");
        fs::write(previous_root.join("data/backups/backup.sqlite3"), b"backup")
            .expect("backup must be written");

        migrate_to_program_directory_storage(&executable_dir, &previous_root)
            .expect("migration must succeed");

        assert_eq!(
            fs::read(executable_dir.join("data/foundry.sqlite3")).unwrap(),
            b"appdata-current"
        );
        assert_eq!(
            fs::read(executable_dir.join("data/backups/backup.sqlite3")).unwrap(),
            b"backup"
        );
        assert_eq!(
            fs::read(executable_dir.join("data-before-appdata-migration/foundry.sqlite3")).unwrap(),
            b"old-program"
        );
        assert!(executable_dir.join("data/.program-storage-v1").is_file());
        assert_eq!(
            fs::read(previous_root.join("data/foundry.sqlite3")).unwrap(),
            b"appdata-current"
        );

        fs::write(
            executable_dir.join("data/foundry.sqlite3"),
            b"program-newer",
        )
        .expect("program database must remain writable");
        migrate_to_program_directory_storage(&executable_dir, &previous_root)
            .expect("marked program storage must be reused");
        assert_eq!(
            fs::read(executable_dir.join("data/foundry.sqlite3")).unwrap(),
            b"program-newer"
        );
    }

    #[test]
    fn initializes_new_installs_in_the_program_directory() {
        let root = TestDirectory::new("storage-initialization");
        let executable_dir = root.path().join("program");
        let previous_root = root.path().join("appdata");
        fs::create_dir(&executable_dir).expect("program directory must be created");
        fs::create_dir(&previous_root).expect("previous root must be created");

        migrate_to_program_directory_storage(&executable_dir, &previous_root)
            .expect("program storage must initialize");

        assert!(executable_dir.join("data/.program-storage-v1").is_file());
        assert!(!previous_root.join("data").exists());
    }

    #[test]
    fn migration_recovers_the_database_when_an_auxiliary_path_is_invalid() {
        let root = TestDirectory::new("storage-essential-recovery");
        let executable_dir = root.path().join("program");
        let previous_root = root.path().join("appdata");
        fs::create_dir(&executable_dir).expect("program directory must be created");
        fs::create_dir_all(previous_root.join("data"))
            .expect("previous data directory must be created");
        fs::write(
            previous_root.join("data/foundry.sqlite3"),
            b"current-database",
        )
        .expect("previous database must be written");
        fs::write(
            previous_root.join("data/backups"),
            b"invalid-directory-shape",
        )
        .expect("invalid auxiliary path must be written");

        migrate_to_program_directory_storage(&executable_dir, &previous_root)
            .expect("essential database recovery must succeed");

        assert_eq!(
            fs::read(executable_dir.join("data/foundry.sqlite3")).unwrap(),
            b"current-database"
        );
        assert_eq!(
            fs::read_to_string(executable_dir.join("data/.program-storage-v1")).unwrap(),
            "program-directory\nmigration=essential-recovery\n"
        );
        assert!(previous_root.join("data/backups").is_file());
        assert!(!executable_dir.join("data/backups").exists());
    }

    #[test]
    fn preserves_specific_sidecar_startup_errors() {
        let storage_error = serde_json::json!({
            "event": "error",
            "code": "program-storage-unavailable"
        });
        let database_error = serde_json::json!({
            "event": "error",
            "code": "database-startup-failed"
        });
        let ready = serde_json::json!({"event": "ready"});

        assert_eq!(
            sidecar_startup_error_code(&storage_error),
            Some("program-storage-unavailable")
        );
        assert_eq!(
            sidecar_startup_error_code(&database_error),
            Some("database-startup-failed")
        );
        assert_eq!(sidecar_startup_error_code(&ready), None);
    }

    #[test]
    fn retries_only_transient_sidecar_startup_errors() {
        assert!(sidecar_startup_error_is_retryable(
            "database-startup-failed"
        ));
        assert!(sidecar_startup_error_is_retryable("sidecar-ready-invalid"));
        assert!(!sidecar_startup_error_is_retryable(
            "program-storage-unavailable"
        ));
        assert!(!sidecar_startup_error_is_retryable("sidecar-not-found"));
    }

    #[test]
    fn accepts_fresh_legacy_cache_without_explicit_expiry() {
        let data = RuntimeDataSnapshot {
            state: "fresh".to_owned(),
            has_cached_data: true,
            observed_at: Some("2026-09-12T10:00:00Z".to_owned()),
            expires_at: None,
            age_seconds: Some(60),
            last_sync_status: "completed".to_owned(),
            error_code: None,
        };

        assert!(super::data_snapshot_is_valid(&data));
    }

    fn valid_authorization_url() -> String {
        concat!(
            "https://login.eveonline.com/v2/oauth/authorize?",
            "response_type=code&",
            "client_id=a8409de72d5b4cab9b0424819d0abdec&",
            "redirect_uri=http%3A%2F%2F127.0.0.1%3A17891%2Foauth%2Fcallback&",
            "scope=esi-assets.read_assets.v1&",
            "state=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa&",
            "code_challenge=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb&",
            "code_challenge_method=S256"
        )
        .to_owned()
    }

    #[test]
    fn accepts_only_the_fixed_eve_pkce_authorization_target() {
        assert!(authorization_url_is_valid(&valid_authorization_url()));
        assert!(!authorization_url_is_valid(
            &valid_authorization_url().replace("login.eveonline.com", "login.invalid")
        ));
        assert!(!authorization_url_is_valid(
            &valid_authorization_url().replace("S256", "plain")
        ));
        assert!(!authorization_url_is_valid(&format!(
            "{}&state=duplicate",
            valid_authorization_url()
        )));
    }

    #[test]
    fn accepts_only_semantic_versions_for_the_fixed_release_page() {
        assert_eq!(
            release_page_url(Some("0.0.5-preview.13")),
            Ok(
                "https://github.com/Savox76/eve-test-indu/releases/tag/v0.0.5-preview.13"
                    .to_owned()
            )
        );
        assert!(release_page_url(Some("01.0.0")).is_err());
        assert!(release_page_url(Some("0.0.5-preview.01")).is_err());
        assert!(release_page_url(Some("0.0.5/elsewhere")).is_err());
    }

    #[test]
    fn validates_public_sso_status_without_sensitive_values() {
        let waiting = SsoLoginStatus {
            state: "waiting".to_owned(),
            attempt_id: Some("opaque-attempt".to_owned()),
            scope_packages: vec!["industry-core".to_owned()],
            expires_at: Some("2026-09-09T12:00:00Z".to_owned()),
            error_code: None,
            character: None,
        };
        assert!(sso_login_status_is_valid(&waiting));

        let invalid = SsoLoginStatus {
            scope_packages: vec!["industry-core".to_owned(), "industry-core".to_owned()],
            ..waiting.clone()
        };
        assert!(!sso_login_status_is_valid(&invalid));

        let connected = SsoLoginStatus {
            state: "connected".to_owned(),
            character: Some(SsoCharacterIdentity {
                character_id: 2_112_345_678,
                name: "Synthetic Pilot".to_owned(),
                scopes: vec!["esi-assets.read_assets.v1".to_owned()],
            }),
            ..waiting
        };
        assert!(sso_login_status_is_valid(&connected));
    }

    fn managed_character() -> EveCharacterRecord {
        EveCharacterRecord {
            character_id: 2_112_345_678,
            name: "Synthetic Pilot".to_owned(),
            alias: Some("Builder".to_owned()),
            account_group_id: Some(3),
            account_group_label: Some("Industry".to_owned()),
            enabled: true,
            scopes: vec!["esi-assets.read_assets.v1".to_owned()],
            credential_state: "stored".to_owned(),
            scope_packages: vec![
                ScopePackageStatus {
                    id: "industry-core".to_owned(),
                    status: "partial".to_owned(),
                    granted_count: 1,
                    required_count: 4,
                },
                ScopePackageStatus {
                    id: "market".to_owned(),
                    status: "missing".to_owned(),
                    granted_count: 0,
                    required_count: 2,
                },
                ScopePackageStatus {
                    id: "planetary-industry".to_owned(),
                    status: "missing".to_owned(),
                    granted_count: 0,
                    required_count: 1,
                },
                ScopePackageStatus {
                    id: "projects".to_owned(),
                    status: "missing".to_owned(),
                    granted_count: 0,
                    required_count: 1,
                },
                ScopePackageStatus {
                    id: "private-structures".to_owned(),
                    status: "missing".to_owned(),
                    granted_count: 0,
                    required_count: 1,
                },
            ],
        }
    }

    #[test]
    fn validates_complete_managed_character_metadata() {
        let character = managed_character();
        assert!(eve_character_record_is_valid(&character));

        let mut invalid = managed_character();
        invalid.scope_packages[1].status = "granted".to_owned();
        assert!(!eve_character_record_is_valid(&invalid));

        let mut incomplete = managed_character();
        incomplete.scope_packages.pop();
        assert!(!eve_character_record_is_valid(&incomplete));
    }

    #[test]
    fn validates_account_group_metadata() {
        assert!(account_group_record_is_valid(&AccountGroupRecord {
            id: 3,
            label: "Industry".to_owned(),
            sort_order: 0,
            character_count: 2,
        }));
        assert!(!account_group_record_is_valid(&AccountGroupRecord {
            id: 0,
            label: "Invalid".to_owned(),
            sort_order: 0,
            character_count: 0,
        }));
    }

    #[test]
    fn validates_bounded_asset_page_and_safe_export_path() {
        let page = AssetQueryResponse {
            items: vec![AssetRecord {
                item_id: 9_800_001,
                type_id: 98_001,
                type_name: "Synthetic Component".to_owned(),
                quantity: 17,
                owner_character_id: 90_888_001,
                owner_name: "Builder".to_owned(),
                location_flag: "SyntheticHangar".to_owned(),
                location_status: "resolved".to_owned(),
                location_path: "Synthetic System / Synthetic Station".to_owned(),
                location_nodes: vec![AssetLocationNode {
                    location_id: 30_888_001,
                    kind: "solar_system".to_owned(),
                    name: Some("Synthetic System".to_owned()),
                    access: "available".to_owned(),
                    type_id: None,
                }],
                observed_at: "2026-09-10T10:00:00Z".to_owned(),
                age_seconds: 3_600,
            }],
            total: 100_000,
            quantity_total: 230_000,
            offset: 0,
            limit: 100,
            owners: vec![AssetOwner {
                character_id: 90_888_001,
                name: "Builder".to_owned(),
            }],
            location_statuses: vec![
                "resolved".to_owned(),
                "restricted".to_owned(),
                "unresolved".to_owned(),
                "cycle".to_owned(),
                "pending".to_owned(),
            ],
            observed_at: Some("2026-09-10T10:00:00Z".to_owned()),
            age_seconds: Some(3_600),
        };
        assert!(asset_query_response_is_valid(&page));

        let oversized = AssetQueryResponse { limit: 201, ..page };
        assert!(!asset_query_response_is_valid(&oversized));
        assert!(asset_export_response_is_valid(&AssetExportResponse {
            filename: "assets-20260910-110203.csv".to_owned(),
            relative_path: "data/exports/assets-20260910-110203.csv".to_owned(),
            rows: 100_000,
        }));
        assert!(!asset_export_response_is_valid(&AssetExportResponse {
            filename: "outside.csv".to_owned(),
            relative_path: "../../outside.csv".to_owned(),
            rows: 1,
        }));
    }

    #[test]
    fn validates_bounded_grouped_asset_summary() {
        let page = AssetSummaryQueryResponse {
            items: vec![AssetSummaryRecord {
                type_id: 98_001,
                type_name: "Synthetic Component".to_owned(),
                quantity_total: 34,
                position_count: 2,
                owner_count: 1,
                location_count: 2,
                owners: vec![AssetSummaryOwner {
                    character_id: 90_888_001,
                    name: "Builder".to_owned(),
                    quantity: 34,
                    position_count: 2,
                }],
                location_statuses: vec!["resolved".to_owned()],
                age_seconds: 3_600,
            }],
            total: 1,
            position_total: 2,
            quantity_total: 34,
            offset: 0,
            limit: 100,
            owners: vec![AssetOwner {
                character_id: 90_888_001,
                name: "Builder".to_owned(),
            }],
            location_statuses: ASSET_LOCATION_STATUSES.map(str::to_owned).to_vec(),
            observed_at: Some("2026-09-10T10:00:00Z".to_owned()),
            age_seconds: Some(3_600),
        };
        assert!(asset_summary_query_response_is_valid(&page));

        let invalid = AssetSummaryQueryResponse { limit: 201, ..page };
        assert!(!asset_summary_query_response_is_valid(&invalid));
    }

    #[test]
    fn validates_bounded_asset_delta_history_and_correlation_evidence() {
        let page = AssetDeltaQueryResponse {
            items: vec![AssetDeltaRecord {
                event_id: "a".repeat(64),
                item_id: 9_800_001,
                type_id: 98_001,
                type_name: "Synthetic Input".to_owned(),
                owner_character_id: 90_888_001,
                owner_name: "Builder".to_owned(),
                change_types: vec!["quantity".to_owned()],
                quantity_before: Some(17),
                quantity_after: Some(9),
                quantity_delta: -8,
                location_id_before: Some(60_888_001),
                location_id_after: Some(60_888_001),
                location_type_before: Some("station".to_owned()),
                location_type_after: Some("station".to_owned()),
                location_flag_before: Some("SyntheticHangar".to_owned()),
                location_flag_after: Some("SyntheticHangar".to_owned()),
                previous_asset_snapshot_id: 4,
                current_asset_snapshot_id: 6,
                current_asset_sync_run_id: 9,
                observed_at: "2026-09-10T11:00:00Z".to_owned(),
                age_seconds: 60,
                job_correlation: AssetDeltaCorrelation {
                    state: "unmatched".to_owned(),
                    key: "90888001:98001".to_owned(),
                    direction: "outbound".to_owned(),
                    window_start: "2026-09-10T10:00:00Z".to_owned(),
                    window_end: "2026-09-10T11:00:00Z".to_owned(),
                    job_ids: Vec::new(),
                    candidate_count: 0,
                    location_matched: false,
                },
            }],
            total: 1,
            offset: 0,
            limit: 50,
            owners: vec![AssetOwner {
                character_id: 90_888_001,
                name: "Builder".to_owned(),
            }],
            change_types: vec![
                "added".to_owned(),
                "removed".to_owned(),
                "quantity".to_owned(),
                "location".to_owned(),
            ],
            summary: AssetDeltaSummary {
                added: 0,
                removed: 0,
                quantity: 1,
                location: 0,
            },
            has_baseline: true,
            observed_at: Some("2026-09-10T11:00:00Z".to_owned()),
            age_seconds: Some(60),
        };
        assert!(asset_delta_response_is_valid(&page));

        let invalid = AssetDeltaQueryResponse { limit: 201, ..page };
        assert!(!asset_delta_response_is_valid(&invalid));
    }

    #[test]
    fn validates_industry_job_pages_and_sync_aggregates() {
        let page = IndustryJobQueryResponse {
            items: vec![IndustryJobRecord {
                job_id: 8_001,
                owner_character_id: 90_888_001,
                owner_name: "Builder".to_owned(),
                activity_id: 1,
                activity_key: "manufacturing".to_owned(),
                status: "delivered".to_owned(),
                blueprint_item_id: 7_001,
                blueprint_type_id: 6_001,
                blueprint_name: "Synthetic Blueprint".to_owned(),
                product_type_id: Some(6_002),
                product_name: Some("Synthetic Product".to_owned()),
                runs: 2,
                successful_runs: Some(2),
                licensed_runs: Some(0),
                probability: Some(1.0),
                cost: Some(1_234.5),
                duration_seconds: 3_600,
                facility_id: 60_000_001,
                facility_name: Some("Synthetic Station".to_owned()),
                facility_kind: "station".to_owned(),
                facility_access: "public".to_owned(),
                solar_system_id: Some(30_000_001),
                solar_system_name: Some("Synthetic System".to_owned()),
                system_cost_index: Some(0.0125),
                station_id: 60_000_001,
                blueprint_location_id: 60_000_001,
                output_location_id: 60_000_001,
                start_date: "2026-09-10T10:00:00Z".to_owned(),
                end_date: "2026-09-10T11:00:00Z".to_owned(),
                completed_date: Some("2026-09-10T11:00:00Z".to_owned()),
                pause_date: None,
                blueprint_correlation: IndustryBlueprintCorrelation {
                    state: "current".to_owned(),
                    snapshot_id: Some(2),
                    sync_run_id: Some(3),
                    observed_at: Some("2026-09-10T11:01:00Z".to_owned()),
                },
                asset_correlation: IndustryAssetCorrelation {
                    state: "linked".to_owned(),
                    event_ids: vec!["a".repeat(64)],
                    candidate_count: 1,
                    location_matched: true,
                },
                correlation_state: "linked".to_owned(),
                job_snapshot_id: 4,
                job_sync_run_id: 5,
                observed_at: "2026-09-10T11:02:00Z".to_owned(),
                age_seconds: 60,
            }],
            total: 1,
            active_total: 0,
            offset: 0,
            limit: 100,
            owners: vec![AssetOwner {
                character_id: 90_888_001,
                name: "Builder".to_owned(),
            }],
            statuses: [
                "active",
                "cancelled",
                "delivered",
                "paused",
                "ready",
                "reverted",
            ]
            .map(str::to_owned)
            .to_vec(),
            activities: vec![1],
            correlations: ["linked", "partial", "ambiguous", "unmatched", "pending"]
                .map(str::to_owned)
                .to_vec(),
            observed_at: Some("2026-09-10T11:02:00Z".to_owned()),
            age_seconds: Some(60),
        };
        assert!(industry_job_query_response_is_valid(&page));

        let sync = IndustryJobSyncResponse {
            characters: vec![IndustryJobSyncCharacterResponse {
                character_id: 90_888_001,
                status: "completed".to_owned(),
                jobs: 1,
                active: 0,
                completed_jobs: 1,
                error_code: None,
            }],
            completed: 1,
            failed: 0,
            jobs: 1,
            active: 0,
            completed_jobs: 1,
        };
        assert!(industry_job_sync_response_is_valid(&sync));
    }

    #[test]
    fn validates_industry_facility_pages_and_sync_totals() {
        let page = IndustryFacilityQueryResponse {
            items: vec![IndustryFacilityRecord {
                facility_id: 60_000_001,
                facility_name: Some("Synthetic Station".to_owned()),
                kind: "station".to_owned(),
                access: "public".to_owned(),
                type_id: Some(1_928),
                type_name: Some("Synthetic Station Type".to_owned()),
                owner_id: Some(1_000_001),
                owner_name: Some("Synthetic Corporation".to_owned()),
                region_id: Some(10_000_001),
                region_name: Some("Synthetic Region".to_owned()),
                solar_system_id: Some(30_000_001),
                solar_system_name: Some("Synthetic System".to_owned()),
                security_status: Some(0.9),
                security_class: "highsec".to_owned(),
                tax: None,
                activity_cost_index: Some(0.0125),
                used_by_character_ids: vec![90_888_001],
                observed_activity_ids: vec![1],
                job_count: 1,
                active_jobs: 0,
                error_code: None,
                snapshot_id: 10,
                sync_run_id: 11,
                observed_at: "2026-09-11T00:00:00Z".to_owned(),
                age_seconds: 60,
            }],
            total: 1,
            npc_facilities: 1,
            observed_facilities: 0,
            restricted_structures: 0,
            systems: 1,
            offset: 0,
            limit: 100,
            activity: "manufacturing".to_owned(),
            activities: INDUSTRY_COST_ACTIVITIES.map(str::to_owned).to_vec(),
            kinds: INDUSTRY_FACILITY_KINDS.map(str::to_owned).to_vec(),
            access_states: INDUSTRY_FACILITY_ACCESS_STATES.map(str::to_owned).to_vec(),
            security_classes: INDUSTRY_SECURITY_CLASSES.map(str::to_owned).to_vec(),
            observed_at: Some("2026-09-11T00:00:00Z".to_owned()),
            age_seconds: Some(60),
        };
        assert!(industry_facility_query_response_is_valid(&page));

        let sync = IndustryFacilitySyncResponse {
            sync_run_id: 12,
            facilities: 2,
            npc_facilities: 1,
            observed_facilities: 1,
            restricted_structures: 1,
            systems: 1,
            resolved_names: 7,
        };
        assert!(industry_facility_sync_response_is_valid(&sync));
    }

    #[test]
    fn validates_character_separated_industry_slot_evidence() {
        let activities = vec![
            IndustrySlotActivity {
                activity: "manufacturing".to_owned(),
                capacity: Some(7),
                occupied: Some(2),
                available: Some(5),
                utilization_state: "available".to_owned(),
                active_jobs: Some(1),
                paused_jobs: Some(0),
                ready_jobs: Some(1),
                next_job_end_date: Some("2026-09-11T12:00:00Z".to_owned()),
                primary_skill_id: 3387,
                primary_skill_level: Some(4),
                advanced_skill_id: 24625,
                advanced_skill_level: Some(2),
                queued_plans: Some(2),
                blocked_plans: Some(0),
                running_plans: Some(1),
                complete_plans: Some(0),
                planning_available: true,
            },
            IndustrySlotActivity {
                activity: "reactions".to_owned(),
                capacity: Some(5),
                occupied: Some(1),
                available: Some(4),
                utilization_state: "available".to_owned(),
                active_jobs: Some(1),
                paused_jobs: Some(0),
                ready_jobs: Some(0),
                next_job_end_date: Some("2026-09-11T13:00:00Z".to_owned()),
                primary_skill_id: 45748,
                primary_skill_level: Some(3),
                advanced_skill_id: 45749,
                advanced_skill_level: Some(1),
                queued_plans: Some(1),
                blocked_plans: Some(1),
                running_plans: Some(0),
                complete_plans: Some(0),
                planning_available: true,
            },
            IndustrySlotActivity {
                activity: "science".to_owned(),
                capacity: Some(6),
                occupied: Some(2),
                available: Some(4),
                utilization_state: "available".to_owned(),
                active_jobs: Some(2),
                paused_jobs: Some(0),
                ready_jobs: Some(0),
                next_job_end_date: Some("2026-09-11T14:00:00Z".to_owned()),
                primary_skill_id: 3406,
                primary_skill_level: Some(3),
                advanced_skill_id: 24624,
                advanced_skill_level: Some(2),
                queued_plans: Some(1),
                blocked_plans: Some(1),
                running_plans: Some(1),
                complete_plans: Some(0),
                planning_available: true,
            },
        ];
        let page = IndustrySlotQueryResponse {
            items: vec![IndustrySlotRecord {
                character_id: 90_888_001,
                name: "Builder".to_owned(),
                activities,
                skill_snapshot_id: Some(2),
                skill_sync_run_id: Some(3),
                skill_observed_at: Some("2026-09-11T11:00:00Z".to_owned()),
                job_snapshot_id: Some(4),
                job_sync_run_id: Some(5),
                job_observed_at: Some("2026-09-11T11:01:00Z".to_owned()),
                observed_at: Some("2026-09-11T11:00:00Z".to_owned()),
                age_seconds: Some(60),
            }],
            total: 1,
            offset: 0,
            limit: 50,
            owners: vec![AssetOwner {
                character_id: 90_888_001,
                name: "Builder".to_owned(),
            }],
            activities: INDUSTRY_SLOT_ACTIVITIES.map(str::to_owned).to_vec(),
            observed_at: Some("2026-09-11T11:00:00Z".to_owned()),
            age_seconds: Some(60),
        };
        assert!(industry_slot_query_response_is_valid(&page));
    }

    #[test]
    fn validates_research_plans_with_traceable_snapshot_evidence() {
        let record = ResearchPlanRecord {
            owner_character_id: 90_888_001,
            owner_name: "Builder".to_owned(),
            blueprint_item_id: 7_001,
            blueprint_type_id: 6_001,
            blueprint_name: "Synthetic Blueprint".to_owned(),
            blueprint_present: true,
            current_material_efficiency: Some(5),
            current_time_efficiency: Some(10),
            location_id: Some(60_000_001),
            location_flag: Some("Hangar".to_owned()),
            planned: true,
            next_activity: "material".to_owned(),
            target_material_efficiency: 10,
            target_time_efficiency: 20,
            priority: 100,
            note: Some("Main line".to_owned()),
            state: "running".to_owned(),
            slot_capacity: Some(3),
            slots_used: 1,
            slots_available: Some(2),
            research_level: 4,
            metallurgy_level: 5,
            active_job_id: Some(8_001),
            active_job_activity: Some("material".to_owned()),
            active_job_status: Some("active".to_owned()),
            active_job_start_date: Some("2026-09-11T00:00:00Z".to_owned()),
            active_job_end_date: Some("2026-09-11T01:00:00Z".to_owned()),
            active_job_cost: Some(1_234.5),
            facility_id: Some(60_000_001),
            facility_name: Some("Synthetic Station".to_owned()),
            facility_access: "public".to_owned(),
            solar_system_name: Some("Synthetic System".to_owned()),
            system_cost_index: Some(0.0125),
            facility_evidence: "active-job".to_owned(),
            blueprint_snapshot_id: Some(2),
            blueprint_sync_run_id: Some(3),
            skill_snapshot_id: Some(4),
            skill_sync_run_id: Some(5),
            job_snapshot_id: Some(6),
            job_sync_run_id: Some(7),
            observed_at: Some("2026-09-11T00:00:00Z".to_owned()),
            age_seconds: Some(60),
            created_at: Some("2026-09-10T00:00:00Z".to_owned()),
            updated_at: Some("2026-09-11T00:00:00Z".to_owned()),
        };
        let mut page = ResearchPlanQueryResponse {
            items: vec![record],
            total: 1,
            offset: 0,
            limit: 100,
            owners: vec![ResearchPlanOwner {
                character_id: 90_888_001,
                name: "Builder".to_owned(),
                slot_capacity: Some(3),
                slots_used: 1,
                slots_available: Some(2),
                laboratory_operation_level: 2,
                advanced_laboratory_operation_level: 0,
                research_level: 4,
                metallurgy_level: 5,
                skill_snapshot_id: Some(4),
                skill_sync_run_id: Some(5),
            }],
            states: RESEARCH_PLAN_STATES.map(str::to_owned).to_vec(),
            activities: RESEARCH_PLAN_ACTIVITIES.map(str::to_owned).to_vec(),
            summary: ResearchPlanSummary {
                unplanned: 0,
                ready: 0,
                queued: 0,
                running: 1,
                complete: 0,
                unverified: 0,
                missing: 0,
            },
            observed_at: Some("2026-09-11T00:00:00Z".to_owned()),
            age_seconds: Some(60),
            estimates_available: false,
        };
        assert!(research_plan_query_response_is_valid(&page));

        page.estimates_available = true;
        assert!(!research_plan_query_response_is_valid(&page));
    }

    #[test]
    fn validates_character_skill_pages_and_sync_aggregates() {
        let page = CharacterSkillQueryResponse {
            items: vec![CharacterSkillRecord {
                skill_id: 33_550,
                skill_name: "Industry".to_owned(),
                owner_character_id: 90_888_001,
                owner_name: "Builder".to_owned(),
                trained_level: 5,
                active_level: 4,
                skillpoints: 512_000,
                active_state: "limited".to_owned(),
                snapshot_id: 8,
                sync_run_id: 9,
                observed_at: "2026-09-11T00:00:00Z".to_owned(),
                age_seconds: 60,
            }],
            total: 1,
            total_sp: 512_000,
            unallocated_sp: 12_500,
            offset: 0,
            limit: 100,
            owners: vec![AssetOwner {
                character_id: 90_888_001,
                name: "Builder".to_owned(),
            }],
            levels: vec![0, 1, 2, 3, 4, 5],
            active_states: ["normal", "limited", "boosted"].map(str::to_owned).to_vec(),
            observed_at: Some("2026-09-11T00:00:00Z".to_owned()),
            age_seconds: Some(60),
        };
        assert!(character_skill_query_response_is_valid(&page));

        let sync = CharacterSkillSyncResponse {
            characters: vec![CharacterSkillSyncCharacterResponse {
                character_id: 90_888_001,
                status: "completed".to_owned(),
                skills: 1,
                total_sp: 512_000,
                unallocated_sp: 12_500,
                error_code: None,
            }],
            completed: 1,
            failed: 0,
            skills: 1,
            total_sp: 512_000,
            unallocated_sp: 12_500,
        };
        assert!(character_skill_sync_response_is_valid(&sync));
    }
}
