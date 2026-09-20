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
use tauri::{AppHandle, Manager, PhysicalSize, RunEvent, Size, State, WindowEvent};

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
const WINDOW_SIZE_FILE: &str = "window-size.json";
const DEFAULT_WINDOW_WIDTH: u32 = 1440;
const DEFAULT_WINDOW_HEIGHT: u32 = 900;
const MIN_WINDOW_WIDTH: u32 = 1100;
const MIN_WINDOW_HEIGHT: u32 = 720;
const MAX_WINDOW_WIDTH: u32 = 7680;
const MAX_WINDOW_HEIGHT: u32 = 4320;
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
const INDUSTRY_SKILL_ID: u64 = 3380;
const ADVANCED_INDUSTRY_SKILL_ID: u64 = 3388;
const REACTIONS_SKILL_ID: u64 = 45746;
const PRODUCTION_PLAN_STATES: [&str; 5] = [
    "ready",
    "sde-unavailable",
    "recipe-missing",
    "cycle",
    "complexity-limit",
];
const PRODUCTION_INVENTORY_STATES: [&str; 4] =
    ["covered", "shortage", "snapshot-missing", "not-applicable"];
const PRODUCTION_FACILITY_STATES: [&str; 4] = ["ready", "partial", "missing", "not-applicable"];
const PRODUCTION_STEP_FACILITY_STATES: [&str; 6] = [
    "ready",
    "job-snapshot-missing",
    "job-missing",
    "facility-snapshot-missing",
    "facility-missing",
    "facility-unavailable",
];
const PRODUCTION_FACILITY_EVIDENCE: [&str; 4] = [
    "none",
    "assigned-blueprint-job",
    "active-blueprint-type-job",
    "latest-blueprint-type-job",
];
const PRODUCTION_SUPPLY_MODES: [&str; 3] = ["stock-first", "stock-only", "build"];
const PRODUCTION_LOCATION_SELECTION_STATES: [&str; 4] = [
    "unselected",
    "ready",
    "facility-missing",
    "material-location-missing",
];
const PRODUCTION_FACILITY_MODIFIER_STATES: [&str; 4] =
    ["not-selected", "unconfigured", "ready", "activity-mismatch"];
const PRODUCTION_INSTALLATION_COST_STATES: [&str; 9] = [
    "ready",
    "not-selected",
    "unconfigured",
    "facility-snapshot-missing",
    "facility-missing",
    "facility-unavailable",
    "cost-index-missing",
    "price-snapshot-missing",
    "price-missing",
];
const PRODUCTION_PLAN_INSTALLATION_COST_STATES: [&str; 5] = [
    "ready",
    "partial",
    "unconfigured",
    "unavailable",
    "not-applicable",
];
const SCC_SURCHARGE_BASIS_POINTS: u16 = 400;
const MARKET_HUB_IDS: [&str; 5] = ["jita", "amarr", "dodixie", "hek", "rens"];
const MARKET_ITEM_STATES: [&str; 4] = ["ready", "partial", "unavailable", "snapshot-missing"];
const MARKET_PRICING_STATES: [&str; 6] = [
    "ready",
    "partial",
    "unavailable",
    "snapshot-missing",
    "stale",
    "empty",
];
const MARKET_PRICE_TYPE_LIMIT: u64 = 250;
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
    location_path: Option<String>,
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
    prices: u64,
    resolved_names: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct MarketPriceSyncResponse {
    sync_run_id: u64,
    hub_id: String,
    type_count: u64,
    order_count: u64,
    page_count: u64,
    observed_at: String,
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
    unmodified_gross_quantity: u64,
    gross_quantity: u64,
    material_efficiency: u8,
    material_efficiency_savings: u64,
    produced_by_plan: bool,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionTimeSkill {
    skill_id: u64,
    skill_name: String,
    active_level: Option<u8>,
    percent_per_level: u8,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionFacilityEvidence {
    state: String,
    evidence: String,
    job_id: Option<u64>,
    job_status: Option<String>,
    facility_id: Option<u64>,
    facility_name: Option<String>,
    facility_kind: Option<String>,
    facility_access: Option<String>,
    solar_system_id: Option<u64>,
    solar_system_name: Option<String>,
    security_status: Option<f64>,
    security_class: Option<String>,
    system_cost_index: Option<f64>,
    job_snapshot_id: Option<u64>,
    job_sync_run_id: Option<u64>,
    job_observed_at: Option<String>,
    facility_snapshot_id: Option<u64>,
    facility_sync_run_id: Option<u64>,
    facility_observed_at: Option<String>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionInstallationCost {
    state: String,
    estimated_item_value: Option<u64>,
    system_cost_index: Option<f64>,
    system_cost: Option<u64>,
    facility_tax_basis_points: Option<u16>,
    facility_tax: Option<u64>,
    scc_surcharge_basis_points: u16,
    scc_surcharge: Option<u64>,
    estimated_installation_cost: Option<u64>,
    missing_adjusted_price_type_ids: Vec<u64>,
    price_snapshot_id: Option<u64>,
    price_sync_run_id: Option<u64>,
    price_observed_at: Option<String>,
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
    supply_mode: String,
    stock_used_quantity: u64,
    output_quantity_per_run: u64,
    runs: u64,
    unmodified_runs: u64,
    runs_saved_by_material_efficiency: u64,
    produced_quantity: u64,
    surplus_quantity: u64,
    base_time_seconds_per_run: u64,
    total_base_time_seconds: u64,
    time_efficiency: u8,
    time_efficiency_applied: bool,
    total_blueprint_time_seconds: u64,
    time_efficiency_savings_seconds: u64,
    time_skills: Vec<ProductionTimeSkill>,
    character_skill_time_applied: bool,
    total_character_time_seconds: Option<u64>,
    character_skill_time_savings_seconds: Option<u64>,
    facility_modifier_state: String,
    facility_material_bonus_basis_points: Option<u16>,
    facility_time_bonus_basis_points: Option<u16>,
    total_facility_time_seconds: Option<u64>,
    facility_time_savings_seconds: Option<u64>,
    recipe_alternatives: u64,
    material_efficiency: u8,
    material_efficiency_applied: bool,
    blueprint_assignment: ProductionStepBlueprintAssignment,
    facility_evidence: ProductionFacilityEvidence,
    installation_cost: ProductionInstallationCost,
    materials: Vec<ProductionStepMaterial>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionSupplyDecision {
    blueprint_type_id: u64,
    activity: String,
    product_type_id: u64,
    product_name: String,
    supply_mode: String,
    required_quantity: u64,
    stock_available_quantity: u64,
    stock_used_quantity: u64,
    build_quantity: u64,
    shortage_quantity: u64,
    blueprint_required: bool,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionMaterialLocationOption {
    location_id: u64,
    location_name: String,
    location_path: String,
    location_kind: String,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionFacilityOption {
    owner_character_id: u64,
    facility_id: u64,
    facility_name: String,
    facility_kind: String,
    facility_access: String,
    location_status: String,
    material_locations: Vec<ProductionMaterialLocationOption>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionGrossMaterial {
    type_id: u64,
    type_name: String,
    quantity: u64,
    unmodified_quantity: u64,
    material_efficiency_savings: u64,
    availability_state: String,
    available_quantity: Option<u64>,
    reserved_quantity: Option<u64>,
    reserved_by_prior_plans_quantity: Option<u64>,
    remaining_quantity: Option<u64>,
    inventory_shortage_quantity: Option<u64>,
    reservation_conflict_quantity: Option<u64>,
    missing_quantity: Option<u64>,
    prior_reservation_count: u64,
    prior_reservations: Vec<ProductionReservationClaim>,
    available_position_count: u64,
    available_location_count: u64,
    available_locations: Vec<ProductionStockLocation>,
    excluded_quantity: u64,
    excluded_position_count: u64,
    excluded_location_count: u64,
    excluded_locations: Vec<ProductionStockLocation>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionReservationClaim {
    plan_id: u64,
    product_type_id: u64,
    product_name: String,
    priority: u16,
    quantity: u64,
    created_at: String,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionStockLocation {
    owner_character_id: u64,
    owner_name: String,
    location_id: u64,
    location_status: String,
    location_path: String,
    location_flag: String,
    quantity: u64,
    position_count: u64,
    asset_snapshot_id: u64,
    asset_sync_run_id: u64,
    asset_observed_at: String,
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

#[derive(Deserialize, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionBlueprintCandidate {
    item_id: u64,
    kind: String,
    material_efficiency: u8,
    time_efficiency: u8,
    runs: i64,
    location_id: u64,
    location_flag: String,
    suitable: bool,
    reason: String,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionStepBlueprintAssignment {
    blueprint_assignment_state: String,
    blueprint_item_id: Option<u64>,
    blueprint_kind: Option<String>,
    blueprint_material_efficiency: Option<u8>,
    blueprint_time_efficiency: Option<u8>,
    blueprint_runs: Option<i64>,
    blueprint_location_id: Option<u64>,
    blueprint_location_flag: Option<String>,
    blueprint_snapshot_id: Option<u64>,
    blueprint_sync_run_id: Option<u64>,
    blueprint_observed_at: Option<String>,
    blueprint_candidate_count: u64,
    blueprint_candidates: Vec<ProductionBlueprintCandidate>,
}

#[derive(Deserialize, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionStepBlueprintInput {
    blueprint_type_id: u64,
    activity: String,
    product_type_id: u64,
    blueprint_item_id: u64,
}

#[derive(Deserialize, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionStepSupplyInput {
    blueprint_type_id: u64,
    activity: String,
    product_type_id: u64,
    supply_mode: String,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionPlanRecord {
    plan_id: u64,
    owner_character_id: u64,
    owner_name: String,
    blueprint_type_id: u64,
    blueprint_name: String,
    facility_id: Option<u64>,
    facility_name: Option<String>,
    material_location_id: Option<u64>,
    material_location_name: Option<String>,
    material_location_path: Option<String>,
    location_selection_state: String,
    facility_material_bonus_basis_points: Option<u16>,
    facility_time_bonus_basis_points: Option<u16>,
    facility_tax_basis_points: Option<u16>,
    facility_modifier_state: String,
    blueprint_item_id: Option<u64>,
    blueprint_assignment_state: String,
    blueprint_kind: Option<String>,
    blueprint_material_efficiency: Option<u8>,
    blueprint_time_efficiency: Option<u8>,
    blueprint_runs: Option<i64>,
    blueprint_location_id: Option<u64>,
    blueprint_location_flag: Option<String>,
    blueprint_snapshot_id: Option<u64>,
    blueprint_sync_run_id: Option<u64>,
    blueprint_observed_at: Option<String>,
    blueprint_candidate_count: u64,
    blueprint_candidates: Vec<ProductionBlueprintCandidate>,
    applied_material_efficiency: u8,
    applied_time_efficiency: u8,
    activity: String,
    product_type_id: u64,
    product_name: String,
    target_quantity: u64,
    priority: u16,
    note: Option<String>,
    state: String,
    build_number: Option<String>,
    steps: Vec<ProductionStep>,
    supply_decisions: Vec<ProductionSupplyDecision>,
    gross_materials: Vec<ProductionGrossMaterial>,
    warnings: Vec<ProductionWarning>,
    cycle_type_ids: Vec<u64>,
    total_base_time_seconds: Option<u64>,
    total_blueprint_time_seconds: Option<u64>,
    time_efficiency_savings_seconds: Option<u64>,
    total_character_time_seconds: Option<u64>,
    character_skill_time_savings_seconds: Option<u64>,
    total_facility_time_seconds: Option<u64>,
    facility_time_savings_seconds: Option<u64>,
    installation_cost_state: String,
    estimated_item_value: Option<u64>,
    system_cost: Option<u64>,
    facility_tax: Option<u64>,
    scc_surcharge: Option<u64>,
    estimated_installation_cost: Option<u64>,
    costed_step_count: u64,
    uncosted_step_count: u64,
    character_skill_state: String,
    skill_snapshot_id: Option<u64>,
    skill_sync_run_id: Option<u64>,
    skill_observed_at: Option<String>,
    facility_state: String,
    inventory_state: String,
    asset_snapshot_id: Option<u64>,
    asset_sync_run_id: Option<u64>,
    asset_observed_at: Option<String>,
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
struct ProductionPurchaseListItem {
    type_id: u64,
    type_name: String,
    quantity: u64,
    inventory_shortage_quantity: u64,
    reservation_conflict_quantity: u64,
    plan_count: u64,
    market_state: String,
    covered_quantity: Option<u64>,
    uncovered_quantity: Option<u64>,
    used_order_count: Option<u64>,
    lowest_unit_price_cents: Option<u64>,
    weighted_unit_price_cents: Option<u64>,
    purchase_cost_cents: Option<u64>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionMarketHub {
    hub_id: String,
    name: String,
    station_id: u64,
    station_name: String,
    solar_system_id: u64,
    region_id: u64,
    priority: u8,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionPurchaseList {
    state: String,
    items: Vec<ProductionPurchaseListItem>,
    item_count: u64,
    total_quantity: u64,
    included_plan_count: u64,
    unresolved_plan_count: u64,
    omitted_item_count: u64,
    market_hub: ProductionMarketHub,
    market_hubs: Vec<ProductionMarketHub>,
    market_price_rule: String,
    market_price_type_limit: u64,
    pricing_state: String,
    market_snapshot_id: Option<u64>,
    market_sync_run_id: Option<u64>,
    market_observed_at: Option<String>,
    market_age_seconds: Option<u64>,
    fully_covered_item_count: u64,
    partially_covered_item_count: u64,
    unavailable_item_count: u64,
    snapshot_missing_item_count: u64,
    total_purchase_cost_cents: u64,
    installation_cost_state: String,
    estimated_installation_cost: Option<u64>,
    additional_capital_need_cents: Option<u64>,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionPlanQueryResponse {
    items: Vec<ProductionPlanRecord>,
    total: u64,
    offset: u64,
    limit: u64,
    owners: Vec<AssetOwner>,
    location_options: Vec<ProductionFacilityOption>,
    activities: Vec<String>,
    states: Vec<String>,
    summary: ProductionPlanSummary,
    purchase_list: ProductionPurchaseList,
    build_number: Option<String>,
    inventory_applied: bool,
    reservations_applied: bool,
    reservation_rule: String,
    blueprint_material_efficiency_applied: bool,
    material_efficiency_rule: String,
    blueprint_time_efficiency_applied: bool,
    time_efficiency_rule: String,
    blueprint_chain_assignments_applied: bool,
    blueprint_chain_assignment_rule: String,
    character_skill_time_applied: bool,
    character_skill_time_rule: String,
    facility_evidence_applied: bool,
    facility_evidence_rule: String,
    supply_modes_applied: bool,
    supply_mode_rule: String,
    facility_modifiers_applied: bool,
    facility_modifier_rule: String,
    purchase_list_applied: bool,
    purchase_list_rule: String,
    market_prices_applied: bool,
    market_price_rule: String,
    installation_costs_applied: bool,
    installation_cost_rule: String,
    remaining_modifiers_applied: bool,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProductionPlanMutationResponse {
    saved: bool,
    plan_id: u64,
    owner_character_id: u64,
    blueprint_type_id: u64,
    blueprint_item_id: Option<u64>,
    step_blueprint_assignments: Vec<ProductionStepBlueprintInput>,
    facility_id: Option<u64>,
    material_location_id: Option<u64>,
    facility_material_bonus_basis_points: Option<u16>,
    facility_time_bonus_basis_points: Option<u16>,
    facility_tax_basis_points: Option<u16>,
    step_supply_modes: Vec<ProductionStepSupplyInput>,
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
    location_status_before: Option<String>,
    location_status_after: Option<String>,
    location_path_before: Option<String>,
    location_path_after: Option<String>,
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

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetDeltaCorrelationSummary {
    linked: u64,
    ambiguous: u64,
    unmatched: u64,
    unavailable: u64,
    #[serde(rename = "not-applicable")]
    not_applicable: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetDeltaGroupRecord {
    group_id: String,
    type_id: u64,
    type_name: String,
    owner_character_id: u64,
    owner_name: String,
    change_types: Vec<String>,
    event_count: u64,
    item_count: u64,
    quantity_before: u64,
    quantity_after: u64,
    quantity_delta: i64,
    location_count_before: u64,
    location_count_after: u64,
    location_id_before: Option<u64>,
    location_id_after: Option<u64>,
    location_flag_before: Option<String>,
    location_flag_after: Option<String>,
    location_path_before: Option<String>,
    location_path_after: Option<String>,
    previous_asset_snapshot_id: u64,
    current_asset_snapshot_id: u64,
    current_asset_sync_run_id: u64,
    observed_at: String,
    age_seconds: u64,
    job_correlation_summary: AssetDeltaCorrelationSummary,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetDeltaGroupQueryResponse {
    items: Vec<AssetDeltaGroupRecord>,
    total: u64,
    event_total: u64,
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
    window_size: Mutex<WindowSizePreference>,
    shutting_down: AtomicBool,
}

impl RuntimeState {
    fn new() -> Self {
        Self {
            snapshot: Mutex::new(RuntimeSnapshot::starting()),
            sidecar: Mutex::new(None),
            window_size: Mutex::new(WindowSizePreference::default()),
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

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct WindowSizePreference {
    width: u32,
    height: u32,
}

impl Default for WindowSizePreference {
    fn default() -> Self {
        Self {
            width: DEFAULT_WINDOW_WIDTH,
            height: DEFAULT_WINDOW_HEIGHT,
        }
    }
}

impl WindowSizePreference {
    fn is_valid(self) -> bool {
        (MIN_WINDOW_WIDTH..=MAX_WINDOW_WIDTH).contains(&self.width)
            && (MIN_WINDOW_HEIGHT..=MAX_WINDOW_HEIGHT).contains(&self.height)
    }
}

fn program_data_directory() -> Result<PathBuf, &'static str> {
    std::env::current_exe()
        .map_err(|_| "program-directory-unavailable")?
        .parent()
        .map(|directory| directory.join("data"))
        .ok_or("program-directory-unavailable")
}

fn read_window_size(path: &Path) -> Option<WindowSizePreference> {
    if path.is_symlink() || !path.is_file() {
        return None;
    }
    let preference = serde_json::from_slice::<WindowSizePreference>(&fs::read(path).ok()?).ok()?;
    preference.is_valid().then_some(preference)
}

fn write_window_size(path: &Path, preference: WindowSizePreference) -> Result<(), &'static str> {
    if !preference.is_valid() {
        return Err("window-size-invalid");
    }
    let directory = path.parent().ok_or("window-size-write-failed")?;
    if directory.is_symlink() || (path.exists() && path.is_symlink()) {
        return Err("window-size-write-failed");
    }
    fs::create_dir_all(directory).map_err(|_| "window-size-write-failed")?;
    let payload = serde_json::to_vec(&preference).map_err(|_| "window-size-write-failed")?;
    fs::write(path, payload).map_err(|_| "window-size-write-failed")
}

fn load_window_size() -> WindowSizePreference {
    program_data_directory()
        .ok()
        .and_then(|directory| read_window_size(&directory.join(WINDOW_SIZE_FILE)))
        .unwrap_or_default()
}

fn save_window_size(preference: WindowSizePreference) {
    if let Ok(directory) = program_data_directory() {
        let _ = write_window_size(&directory.join(WINDOW_SIZE_FILE), preference);
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
                && item
                    .location_path
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 16_000))
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
        && response.prices > 0
        && response.prices <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.resolved_names > 0
        && response.resolved_names <= JAVASCRIPT_MAX_SAFE_INTEGER
}

fn market_price_sync_response_is_valid(response: &MarketPriceSyncResponse) -> bool {
    response.sync_run_id > 0
        && response.sync_run_id <= JAVASCRIPT_MAX_SAFE_INTEGER
        && MARKET_HUB_IDS.contains(&response.hub_id.as_str())
        && response.type_count > 0
        && response.type_count <= MARKET_PRICE_TYPE_LIMIT
        && response.order_count <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.page_count >= response.type_count
        && response.page_count <= response.type_count.saturating_mul(1_000)
        && asset_text_is_valid(&response.observed_at, 64)
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

fn production_stock_location_is_valid(item: &ProductionStockLocation) -> bool {
    production_id_is_valid(item.owner_character_id)
        && asset_text_is_valid(&item.owner_name, 100)
        && production_id_is_valid(item.location_id)
        && ASSET_LOCATION_STATUSES.contains(&item.location_status.as_str())
        && item.location_path.chars().count() <= 4_096
        && ((item.location_status == "pending" && item.location_path.is_empty())
            || (item.location_status != "pending" && !item.location_path.is_empty()))
        && asset_text_is_valid(&item.location_flag, 100)
        && production_id_is_valid(item.quantity)
        && production_id_is_valid(item.position_count)
        && production_id_is_valid(item.asset_snapshot_id)
        && production_id_is_valid(item.asset_sync_run_id)
        && asset_text_is_valid(&item.asset_observed_at, 64)
}

fn production_reservation_claim_is_valid(
    claim: &ProductionReservationClaim,
    item: &ProductionPlanRecord,
) -> bool {
    let precedes_item = claim.priority > item.priority
        || (claim.priority == item.priority
            && (claim.created_at.as_str() < item.created_at.as_str()
                || (claim.created_at == item.created_at && claim.plan_id < item.plan_id)));
    production_id_is_valid(claim.plan_id)
        && claim.plan_id != item.plan_id
        && production_id_is_valid(claim.product_type_id)
        && asset_text_is_valid(&claim.product_name, 200)
        && claim.priority <= 999
        && production_id_is_valid(claim.quantity)
        && asset_text_is_valid(&claim.created_at, 64)
        && precedes_item
}

fn production_blueprint_candidate_is_valid(candidate: &ProductionBlueprintCandidate) -> bool {
    production_id_is_valid(candidate.item_id)
        && matches!(candidate.kind.as_str(), "original" | "copy")
        && candidate.material_efficiency <= 10
        && candidate.time_efficiency <= 20
        && (candidate.runs == -1 || candidate.runs >= 0)
        && production_id_is_valid(candidate.location_id)
        && asset_text_is_valid(&candidate.location_flag, 100)
        && matches!(candidate.reason.as_str(), "ready" | "runs-insufficient")
        && candidate.suitable == (candidate.reason == "ready")
        && (candidate.kind != "original" || (candidate.runs == -1 && candidate.suitable))
        && (candidate.kind != "copy" || candidate.runs != -1)
}

fn production_step_blueprint_assignment_is_valid(
    assignment: &ProductionStepBlueprintAssignment,
) -> bool {
    let source_complete = match (
        assignment.blueprint_snapshot_id,
        assignment.blueprint_sync_run_id,
        assignment.blueprint_observed_at.as_ref(),
    ) {
        (None, None, None) => false,
        (Some(snapshot_id), Some(sync_run_id), Some(observed_at)) => {
            production_id_is_valid(snapshot_id)
                && production_id_is_valid(sync_run_id)
                && asset_text_is_valid(observed_at, 64)
        }
        _ => return false,
    };
    let has_details = assignment.blueprint_kind.is_some();
    let details_valid = has_details
        && assignment
            .blueprint_item_id
            .is_some_and(production_id_is_valid)
        && assignment
            .blueprint_kind
            .as_ref()
            .is_some_and(|value| matches!(value.as_str(), "original" | "copy"))
        && assignment
            .blueprint_material_efficiency
            .is_some_and(|value| value <= 10)
        && assignment
            .blueprint_time_efficiency
            .is_some_and(|value| value <= 20)
        && assignment
            .blueprint_runs
            .is_some_and(|value| value == -1 || value >= 0)
        && assignment
            .blueprint_location_id
            .is_some_and(production_id_is_valid)
        && assignment
            .blueprint_location_flag
            .as_ref()
            .is_some_and(|value| asset_text_is_valid(value, 100));
    let candidate_ids = assignment
        .blueprint_candidates
        .iter()
        .map(|candidate| candidate.item_id)
        .collect::<HashSet<_>>();
    matches!(
        assignment.blueprint_assignment_state.as_str(),
        "ready"
            | "unassigned"
            | "snapshot-missing"
            | "missing"
            | "type-mismatch"
            | "runs-insufficient"
    ) && ((assignment.blueprint_assignment_state == "snapshot-missing") != source_complete)
        && match assignment.blueprint_assignment_state.as_str() {
            "snapshot-missing" | "unassigned" => {
                assignment.blueprint_item_id.is_none() && !has_details
            }
            "missing" => assignment.blueprint_item_id.is_some() && !has_details,
            "ready" | "type-mismatch" | "runs-insufficient" => details_valid,
            _ => false,
        }
        && assignment.blueprint_candidate_count <= JAVASCRIPT_MAX_SAFE_INTEGER
        && assignment.blueprint_candidates.len() <= 50
        && assignment.blueprint_candidate_count >= assignment.blueprint_candidates.len() as u64
        && (assignment.blueprint_candidate_count > 50
            || assignment.blueprint_candidate_count == assignment.blueprint_candidates.len() as u64)
        && candidate_ids.len() == assignment.blueprint_candidates.len()
        && assignment
            .blueprint_candidates
            .iter()
            .all(production_blueprint_candidate_is_valid)
}

fn production_facility_evidence_is_valid(evidence: &ProductionFacilityEvidence) -> bool {
    let job_source_complete = match (
        evidence.job_snapshot_id,
        evidence.job_sync_run_id,
        evidence.job_observed_at.as_ref(),
    ) {
        (None, None, None) => false,
        (Some(snapshot_id), Some(sync_run_id), Some(observed_at)) => {
            production_id_is_valid(snapshot_id)
                && production_id_is_valid(sync_run_id)
                && asset_text_is_valid(observed_at, 64)
        }
        _ => return false,
    };
    let facility_source_complete = match (
        evidence.facility_snapshot_id,
        evidence.facility_sync_run_id,
        evidence.facility_observed_at.as_ref(),
    ) {
        (None, None, None) => false,
        (Some(snapshot_id), Some(sync_run_id), Some(observed_at)) => {
            production_id_is_valid(snapshot_id)
                && production_id_is_valid(sync_run_id)
                && asset_text_is_valid(observed_at, 64)
        }
        _ => return false,
    };
    let has_job = evidence.evidence != "none";
    let job_details_complete = evidence.job_id.is_some_and(production_id_is_valid)
        && evidence
            .job_status
            .as_ref()
            .is_some_and(|value| INDUSTRY_JOB_STATUSES.contains(&value.as_str()))
        && evidence.facility_id.is_some_and(production_id_is_valid);
    let job_details_empty = evidence.job_id.is_none()
        && evidence.job_status.is_none()
        && evidence.facility_id.is_none();
    let expects_job = !matches!(
        evidence.state.as_str(),
        "job-snapshot-missing" | "job-missing"
    );
    let has_facility = matches!(evidence.state.as_str(), "ready" | "facility-unavailable");
    let facility_details_complete = evidence
        .facility_kind
        .as_ref()
        .is_some_and(|value| INDUSTRY_FACILITY_KINDS.contains(&value.as_str()))
        && evidence
            .facility_access
            .as_ref()
            .is_some_and(|value| INDUSTRY_FACILITY_ACCESS_STATES.contains(&value.as_str()))
        && evidence
            .security_class
            .as_ref()
            .is_some_and(|value| INDUSTRY_SECURITY_CLASSES.contains(&value.as_str()));
    let facility_details_empty = evidence.facility_name.is_none()
        && evidence.facility_kind.is_none()
        && evidence.facility_access.is_none()
        && evidence.solar_system_id.is_none()
        && evidence.solar_system_name.is_none()
        && evidence.security_status.is_none()
        && evidence.security_class.is_none()
        && evidence.system_cost_index.is_none();
    PRODUCTION_STEP_FACILITY_STATES.contains(&evidence.state.as_str())
        && PRODUCTION_FACILITY_EVIDENCE.contains(&evidence.evidence.as_str())
        && ((evidence.state == "job-snapshot-missing") != job_source_complete)
        && (if has_job {
            job_details_complete
        } else {
            job_details_empty
        })
        && has_job == expects_job
        && has_facility == facility_source_complete
        && has_facility == facility_details_complete
        && evidence
            .facility_name
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 200))
        && evidence.solar_system_id.is_none_or(production_id_is_valid)
        && evidence
            .solar_system_name
            .as_ref()
            .is_none_or(|value| asset_text_is_valid(value, 200))
        && evidence
            .security_status
            .is_none_or(|value| value.is_finite() && (-1.0..=1.0).contains(&value))
        && evidence
            .system_cost_index
            .is_none_or(|value| value.is_finite() && (0.0..=1.0).contains(&value))
        && (evidence.state != "ready"
            || evidence
                .facility_access
                .as_ref()
                .is_some_and(|value| matches!(value.as_str(), "public" | "available")))
        && (evidence.state != "facility-unavailable"
            || evidence
                .facility_access
                .as_ref()
                .is_some_and(|value| !matches!(value.as_str(), "public" | "available")))
        && (has_facility || facility_details_empty)
}

fn production_installation_cost_is_valid(cost: &ProductionInstallationCost) -> bool {
    let source_complete = match (
        cost.price_snapshot_id,
        cost.price_sync_run_id,
        cost.price_observed_at.as_ref(),
    ) {
        (None, None, None) => false,
        (Some(snapshot_id), Some(sync_run_id), Some(observed_at)) => {
            production_id_is_valid(snapshot_id)
                && production_id_is_valid(sync_run_id)
                && asset_text_is_valid(observed_at, 64)
        }
        _ => return false,
    };
    let values_ready = cost.estimated_item_value.is_some()
        && cost.system_cost.is_some()
        && cost.facility_tax.is_some()
        && cost.scc_surcharge.is_some()
        && cost.estimated_installation_cost.is_some();
    let values_missing = cost.estimated_item_value.is_none()
        && cost.system_cost.is_none()
        && cost.facility_tax.is_none()
        && cost.scc_surcharge.is_none()
        && cost.estimated_installation_cost.is_none();
    let missing_ids = cost
        .missing_adjusted_price_type_ids
        .iter()
        .copied()
        .collect::<HashSet<_>>();
    PRODUCTION_INSTALLATION_COST_STATES.contains(&cost.state.as_str())
        && cost
            .estimated_item_value
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && cost
            .system_cost_index
            .is_none_or(|value| value.is_finite() && (0.0..=1.0).contains(&value))
        && cost
            .system_cost
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && cost
            .facility_tax_basis_points
            .is_none_or(|value| value <= 10_000)
        && cost
            .facility_tax
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && cost.scc_surcharge_basis_points == SCC_SURCHARGE_BASIS_POINTS
        && cost
            .scc_surcharge
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && cost
            .estimated_installation_cost
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && missing_ids.len() == cost.missing_adjusted_price_type_ids.len()
        && missing_ids
            .iter()
            .all(|value| production_id_is_valid(*value))
        && if cost.state == "ready" {
            source_complete
                && values_ready
                && cost.system_cost_index.is_some()
                && cost.facility_tax_basis_points.is_some()
                && cost
                    .system_cost
                    .zip(cost.facility_tax)
                    .and_then(|(system, tax)| system.checked_add(tax))
                    .zip(cost.scc_surcharge)
                    .and_then(|(subtotal, scc)| subtotal.checked_add(scc))
                    == cost.estimated_installation_cost
                && cost.missing_adjusted_price_type_ids.is_empty()
        } else {
            values_missing
                && (cost.state == "price-missing")
                    == !cost.missing_adjusted_price_type_ids.is_empty()
                && (matches!(cost.state.as_str(), "not-selected" | "unconfigured")
                    == cost.facility_tax_basis_points.is_none())
                && (cost.state != "price-snapshot-missing" || !source_complete)
                && (cost.state != "price-missing" || source_complete)
        }
}

fn production_time_skills_are_valid(step: &ProductionStep) -> bool {
    let expected: &[(u64, &str, u8)] = if step.activity == "manufacturing" {
        &[
            (INDUSTRY_SKILL_ID, "Industry", 4),
            (ADVANCED_INDUSTRY_SKILL_ID, "Advanced Industry", 3),
        ]
    } else {
        &[(REACTIONS_SKILL_ID, "Reactions", 4)]
    };
    if step.time_skills.len() != expected.len()
        || !step.time_skills.iter().zip(expected).all(|(skill, rule)| {
            skill.skill_id == rule.0
                && skill.skill_name == rule.1
                && skill.percent_per_level == rule.2
                && skill.active_level.is_none_or(|level| level <= 5)
        })
    {
        return false;
    }
    let levels_missing = step
        .time_skills
        .iter()
        .all(|skill| skill.active_level.is_none());
    let levels_available = step
        .time_skills
        .iter()
        .all(|skill| skill.active_level.is_some());
    if levels_missing {
        return step.total_character_time_seconds.is_none()
            && step.character_skill_time_savings_seconds.is_none()
            && !step.character_skill_time_applied
            && step.total_facility_time_seconds.is_none()
            && step.facility_time_savings_seconds.is_none();
    }
    if !levels_available {
        return false;
    }
    let mut numerator =
        u128::from(step.total_base_time_seconds) * u128::from(100 - step.time_efficiency);
    let mut denominator = 100_u128;
    for skill in &step.time_skills {
        numerator *=
            u128::from(100 - skill.percent_per_level * skill.active_level.unwrap_or_default());
        denominator *= 100;
    }
    let adjusted = (numerator + denominator - 1) / denominator;
    let Ok(adjusted) = u64::try_from(adjusted) else {
        return false;
    };
    let character_valid = production_id_is_valid(adjusted)
        && step.total_character_time_seconds == Some(adjusted)
        && step.total_blueprint_time_seconds.checked_sub(adjusted)
            == step.character_skill_time_savings_seconds
        && step.character_skill_time_applied == (adjusted < step.total_blueprint_time_seconds);
    let facility_valid = if step.facility_modifier_state == "ready" {
        let Some(time_bonus) = step.facility_time_bonus_basis_points else {
            return false;
        };
        numerator *= u128::from(10_000 - time_bonus);
        denominator *= 10_000;
        let facility_adjusted = (numerator + denominator - 1) / denominator;
        let Ok(facility_adjusted) = u64::try_from(facility_adjusted) else {
            return false;
        };
        production_id_is_valid(facility_adjusted)
            && step.total_facility_time_seconds == Some(facility_adjusted)
            && adjusted.checked_sub(facility_adjusted) == step.facility_time_savings_seconds
    } else {
        step.total_facility_time_seconds.is_none() && step.facility_time_savings_seconds.is_none()
    };
    character_valid && facility_valid
}

fn production_supply_decision_is_valid(item: &ProductionSupplyDecision) -> bool {
    let quantities_valid = match item.supply_mode.as_str() {
        "stock-first" => {
            item.stock_used_quantity <= item.stock_available_quantity
                && item.stock_used_quantity.checked_add(item.build_quantity)
                    == Some(item.required_quantity)
                && item.shortage_quantity == 0
        }
        "stock-only" => {
            item.build_quantity == 0
                && item.stock_used_quantity <= item.stock_available_quantity
                && item.stock_used_quantity.checked_add(item.shortage_quantity)
                    == Some(item.required_quantity)
        }
        "build" => {
            item.stock_used_quantity == 0
                && item.build_quantity == item.required_quantity
                && item.shortage_quantity == 0
        }
        _ => false,
    };
    production_id_is_valid(item.blueprint_type_id)
        && PRODUCTION_ACTIVITIES.contains(&item.activity.as_str())
        && production_id_is_valid(item.product_type_id)
        && asset_text_is_valid(&item.product_name, 200)
        && PRODUCTION_SUPPLY_MODES.contains(&item.supply_mode.as_str())
        && production_id_is_valid(item.required_quantity)
        && item.stock_available_quantity <= JAVASCRIPT_MAX_SAFE_INTEGER
        && item.stock_used_quantity <= JAVASCRIPT_MAX_SAFE_INTEGER
        && item.build_quantity <= JAVASCRIPT_MAX_SAFE_INTEGER
        && item.shortage_quantity <= JAVASCRIPT_MAX_SAFE_INTEGER
        && item.blueprint_required == (item.build_quantity > 0)
        && quantities_valid
}

fn production_location_option_is_valid(item: &ProductionFacilityOption) -> bool {
    let location_ids = item
        .material_locations
        .iter()
        .map(|location| location.location_id)
        .collect::<HashSet<_>>();
    production_id_is_valid(item.owner_character_id)
        && production_id_is_valid(item.facility_id)
        && asset_text_is_valid(&item.facility_name, 200)
        && matches!(item.facility_kind.as_str(), "station" | "structure")
        && asset_text_is_valid(&item.facility_access, 40)
        && matches!(
            item.location_status.as_str(),
            "resolved" | "restricted" | "unresolved" | "cycle"
        )
        && !item.material_locations.is_empty()
        && item.material_locations.len() <= 200
        && location_ids.len() == item.material_locations.len()
        && item.material_locations.iter().all(|location| {
            production_id_is_valid(location.location_id)
                && asset_text_is_valid(&location.location_name, 200)
                && asset_text_is_valid(&location.location_path, 12_800)
                && matches!(location.location_kind.as_str(), "facility" | "container")
        })
        && item.material_locations.iter().any(|location| {
            location.location_id == item.facility_id && location.location_kind == "facility"
        })
}

fn production_plan_record_is_valid(item: &ProductionPlanRecord) -> bool {
    let steps_valid = item.steps.iter().enumerate().all(|(index, step)| {
        let facility_modifier_shape_valid = PRODUCTION_FACILITY_MODIFIER_STATES
            .contains(&step.facility_modifier_state.as_str())
            && step
                .facility_material_bonus_basis_points
                .is_none_or(|value| value <= 5_000)
            && step
                .facility_time_bonus_basis_points
                .is_none_or(|value| value <= 5_000)
            && if step.facility_modifier_state == "ready" {
                step.facility_material_bonus_basis_points.is_some()
                    && step.facility_time_bonus_basis_points.is_some()
            } else {
                step.facility_material_bonus_basis_points.is_none()
                    && step.facility_time_bonus_basis_points.is_none()
            };
        let facility_modifier_matches_plan = if item.facility_modifier_state == "ready" {
            if step.activity == item.activity {
                step.facility_modifier_state == "ready"
                    && step.facility_material_bonus_basis_points
                        == item.facility_material_bonus_basis_points
                    && step.facility_time_bonus_basis_points
                        == item.facility_time_bonus_basis_points
            } else {
                step.facility_modifier_state == "activity-mismatch"
            }
        } else {
            step.facility_modifier_state == item.facility_modifier_state
        };
        step.sequence == index as u64 + 1
            && production_id_is_valid(step.blueprint_type_id)
            && production_id_is_valid(step.product_type_id)
            && asset_text_is_valid(&step.blueprint_name, 200)
            && asset_text_is_valid(&step.product_name, 200)
            && PRODUCTION_ACTIVITIES.contains(&step.activity.as_str())
            && production_id_is_valid(step.required_quantity)
            && matches!(step.supply_mode.as_str(), "stock-first" | "build")
            && step.stock_used_quantity <= JAVASCRIPT_MAX_SAFE_INTEGER
            && (step.supply_mode != "build" || step.stock_used_quantity == 0)
            && production_id_is_valid(step.output_quantity_per_run)
            && production_id_is_valid(step.runs)
            && production_id_is_valid(step.unmodified_runs)
            && step.runs_saved_by_material_efficiency <= JAVASCRIPT_MAX_SAFE_INTEGER
            && production_id_is_valid(step.produced_quantity)
            && step.surplus_quantity <= JAVASCRIPT_MAX_SAFE_INTEGER
            && production_id_is_valid(step.base_time_seconds_per_run)
            && production_id_is_valid(step.total_base_time_seconds)
            && step.time_efficiency <= 20
            && step.time_efficiency_applied == (step.time_efficiency > 0)
            && production_id_is_valid(step.total_blueprint_time_seconds)
            && step.time_efficiency_savings_seconds <= JAVASCRIPT_MAX_SAFE_INTEGER
            && facility_modifier_shape_valid
            && facility_modifier_matches_plan
            && production_time_skills_are_valid(step)
            && production_id_is_valid(step.recipe_alternatives)
            && step.material_efficiency <= 10
            && step.material_efficiency_applied == (step.material_efficiency > 0)
            && production_step_blueprint_assignment_is_valid(&step.blueprint_assignment)
            && production_facility_evidence_is_valid(&step.facility_evidence)
            && production_installation_cost_is_valid(&step.installation_cost)
            && step.installation_cost.facility_tax_basis_points == item.facility_tax_basis_points
            && if step.blueprint_assignment.blueprint_assignment_state == "ready"
                && step.activity == "manufacturing"
            {
                step.material_efficiency
                    == step
                        .blueprint_assignment
                        .blueprint_material_efficiency
                        .unwrap_or_default()
                    && step.time_efficiency
                        == step
                            .blueprint_assignment
                            .blueprint_time_efficiency
                            .unwrap_or_default()
            } else {
                step.material_efficiency == 0 && step.time_efficiency == 0
            }
            && step.output_quantity_per_run.checked_mul(step.runs) == Some(step.produced_quantity)
            && step.produced_quantity.checked_sub(step.required_quantity)
                == Some(step.surplus_quantity)
            && step.base_time_seconds_per_run.checked_mul(step.runs)
                == Some(step.total_base_time_seconds)
            && step
                .total_base_time_seconds
                .checked_sub(step.total_blueprint_time_seconds)
                == Some(step.time_efficiency_savings_seconds)
            && step
                .total_base_time_seconds
                .checked_mul(u64::from(100 - step.time_efficiency))
                .and_then(|value| value.checked_add(99))
                .map(|value| value / 100)
                == Some(step.total_blueprint_time_seconds)
            && step.unmodified_runs.checked_sub(step.runs)
                == Some(step.runs_saved_by_material_efficiency)
            && step.materials.iter().all(|material| {
                let facility_factor = if step.facility_modifier_state == "ready" {
                    10_000_u128
                        - u128::from(
                            step.facility_material_bonus_basis_points
                                .unwrap_or_default(),
                        )
                } else {
                    10_000_u128
                };
                let numerator = u128::from(material.unmodified_gross_quantity)
                    * u128::from(100 - step.material_efficiency)
                    * facility_factor;
                let rounded = (numerator + 999_999) / 1_000_000;
                let expected_gross = rounded.max(u128::from(step.runs));
                production_id_is_valid(material.type_id)
                    && asset_text_is_valid(&material.type_name, 200)
                    && production_id_is_valid(material.quantity_per_run)
                    && production_id_is_valid(material.unmodified_gross_quantity)
                    && production_id_is_valid(material.gross_quantity)
                    && material.material_efficiency <= 10
                    && material.material_efficiency == step.material_efficiency
                    && material.material_efficiency_savings <= JAVASCRIPT_MAX_SAFE_INTEGER
                    && material.quantity_per_run.checked_mul(step.runs)
                        == Some(material.unmodified_gross_quantity)
                    && material
                        .unmodified_gross_quantity
                        .checked_sub(material.gross_quantity)
                        == Some(material.material_efficiency_savings)
                    && u128::from(material.gross_quantity) == expected_gross
            })
    });
    let gross_valid = item.gross_materials.iter().all(|material| {
        let represented_available = material
            .available_locations
            .iter()
            .try_fold(0_u64, |total, location| {
                total.checked_add(location.quantity)
            });
        let represented_available_positions = material
            .available_locations
            .iter()
            .try_fold(0_u64, |total, location| {
                total.checked_add(location.position_count)
            });
        let represented_excluded = material
            .excluded_locations
            .iter()
            .try_fold(0_u64, |total, location| {
                total.checked_add(location.quantity)
            });
        let represented_excluded_positions = material
            .excluded_locations
            .iter()
            .try_fold(0_u64, |total, location| {
                total.checked_add(location.position_count)
            });
        let represented_prior = material
            .prior_reservations
            .iter()
            .try_fold(0_u64, |total, claim| total.checked_add(claim.quantity));
        let prior_ids = material
            .prior_reservations
            .iter()
            .map(|claim| claim.plan_id)
            .collect::<HashSet<_>>();
        let prior_count_valid = material.prior_reservation_count
            >= material.prior_reservations.len() as u64
            && if material.prior_reservation_count <= 50 {
                material.prior_reservation_count == material.prior_reservations.len() as u64
            } else {
                material.prior_reservations.len() == 50
            };
        let availability_valid =
            match material.availability_state.as_str() {
                "snapshot-missing" => {
                    material.available_quantity.is_none()
                        && material.reserved_quantity.is_none()
                        && material.reserved_by_prior_plans_quantity.is_none()
                        && material.remaining_quantity.is_none()
                        && material.inventory_shortage_quantity.is_none()
                        && material.reservation_conflict_quantity.is_none()
                        && material.missing_quantity.is_none()
                        && material.prior_reservation_count == 0
                        && material.prior_reservations.is_empty()
                        && material.available_position_count == 0
                        && material.available_location_count == 0
                        && material.available_locations.is_empty()
                }
                "covered" | "shortage" => match (
                    material.available_quantity,
                    material.reserved_quantity,
                    material.reserved_by_prior_plans_quantity,
                    material.remaining_quantity,
                    material.inventory_shortage_quantity,
                    material.reservation_conflict_quantity,
                    material.missing_quantity,
                ) {
                    (
                        Some(available),
                        Some(reserved),
                        Some(reserved_by_prior),
                        Some(remaining),
                        Some(inventory_shortage),
                        Some(reservation_conflict),
                        Some(missing),
                    ) => available.checked_sub(reserved_by_prior).is_some_and(
                        |available_before_plan| {
                            reserved == material.quantity.min(available_before_plan)
                                && available_before_plan.checked_sub(reserved) == Some(remaining)
                                && material.quantity.checked_sub(reserved) == Some(missing)
                                && inventory_shortage == material.quantity.saturating_sub(available)
                                && missing.checked_sub(inventory_shortage)
                                    == Some(reservation_conflict)
                                && ((material.availability_state == "covered") == (missing == 0))
                                && represented_available.is_some_and(|value| value <= available)
                                && represented_prior.is_some_and(|value| value <= reserved_by_prior)
                        },
                    ),
                    _ => false,
                },
                _ => false,
            };
        production_id_is_valid(material.type_id)
            && asset_text_is_valid(&material.type_name, 200)
            && production_id_is_valid(material.quantity)
            && production_id_is_valid(material.unmodified_quantity)
            && material.material_efficiency_savings <= JAVASCRIPT_MAX_SAFE_INTEGER
            && material.unmodified_quantity.checked_sub(material.quantity)
                == Some(material.material_efficiency_savings)
            && availability_valid
            && material.prior_reservation_count <= JAVASCRIPT_MAX_SAFE_INTEGER
            && material.prior_reservations.len() <= 50
            && prior_count_valid
            && prior_ids.len() == material.prior_reservations.len()
            && material
                .prior_reservations
                .iter()
                .all(|claim| production_reservation_claim_is_valid(claim, item))
            && material.available_position_count <= JAVASCRIPT_MAX_SAFE_INTEGER
            && material.available_location_count <= JAVASCRIPT_MAX_SAFE_INTEGER
            && material.available_locations.len() <= 50
            && material.available_location_count >= material.available_locations.len() as u64
            && represented_available_positions
                .is_some_and(|value| value <= material.available_position_count)
            && material.excluded_quantity <= JAVASCRIPT_MAX_SAFE_INTEGER
            && material.excluded_position_count <= JAVASCRIPT_MAX_SAFE_INTEGER
            && material.excluded_location_count <= JAVASCRIPT_MAX_SAFE_INTEGER
            && material.excluded_locations.len() <= 50
            && material.excluded_location_count >= material.excluded_locations.len() as u64
            && represented_excluded.is_some_and(|value| value <= material.excluded_quantity)
            && represented_excluded_positions
                .is_some_and(|value| value <= material.excluded_position_count)
            && material.available_locations.iter().all(|location| {
                production_stock_location_is_valid(location)
                    && location.owner_character_id == item.owner_character_id
            })
            && material
                .excluded_locations
                .iter()
                .all(|location| production_stock_location_is_valid(location))
    });
    let warnings_valid = item.warnings.iter().all(|warning| {
        warning.code == "alternative-recipe"
            && production_id_is_valid(warning.type_id)
            && asset_text_is_valid(&warning.type_name, 200)
            && production_id_is_valid(warning.selected_blueprint_type_id)
            && warning.candidate_count >= 2
            && warning.candidate_count <= JAVASCRIPT_MAX_SAFE_INTEGER
    });
    let supply_keys = item
        .supply_decisions
        .iter()
        .map(|decision| {
            (
                decision.blueprint_type_id,
                decision.activity.as_str(),
                decision.product_type_id,
            )
        })
        .collect::<HashSet<_>>();
    let supply_decisions_valid = item.supply_decisions.len() <= 499
        && supply_keys.len() == item.supply_decisions.len()
        && item
            .supply_decisions
            .iter()
            .all(production_supply_decision_is_valid);
    let supply_shape_valid = item.supply_decisions.iter().all(|decision| {
        let matches = item
            .steps
            .iter()
            .take(item.steps.len().saturating_sub(1))
            .filter(|step| {
                step.blueprint_type_id == decision.blueprint_type_id
                    && step.activity == decision.activity
                    && step.product_type_id == decision.product_type_id
            })
            .collect::<Vec<_>>();
        if decision.build_quantity == 0 {
            matches.is_empty()
        } else {
            matches.len() == 1
                && matches[0].required_quantity == decision.build_quantity
                && matches[0].stock_used_quantity == decision.stock_used_quantity
                && matches[0].supply_mode == decision.supply_mode
        }
    }) && item
        .steps
        .iter()
        .take(item.steps.len().saturating_sub(1))
        .all(|step| {
            item.supply_decisions.iter().any(|decision| {
                decision.blueprint_type_id == step.blueprint_type_id
                    && decision.activity == step.activity
                    && decision.product_type_id == step.product_type_id
            })
        });
    let location_selection_valid = match item.location_selection_state.as_str() {
        "unselected" => {
            item.facility_id.is_none()
                && item.facility_name.is_none()
                && item.material_location_id.is_none()
                && item.material_location_name.is_none()
                && item.material_location_path.is_none()
        }
        "ready" => {
            item.facility_id.is_some_and(production_id_is_valid)
                && item
                    .facility_name
                    .as_ref()
                    .is_some_and(|value| asset_text_is_valid(value, 200))
                && match (
                    item.material_location_id,
                    item.material_location_name.as_ref(),
                    item.material_location_path.as_ref(),
                ) {
                    (None, None, None) => true,
                    (Some(location_id), Some(name), Some(path)) => {
                        production_id_is_valid(location_id)
                            && asset_text_is_valid(name, 200)
                            && asset_text_is_valid(path, 12_800)
                    }
                    _ => false,
                }
        }
        "facility-missing" => {
            item.facility_id.is_some_and(production_id_is_valid)
                && item.facility_name.is_none()
                && item.material_location_name.is_none()
                && item.material_location_path.is_none()
        }
        "material-location-missing" => {
            item.facility_id.is_some_and(production_id_is_valid)
                && item
                    .facility_name
                    .as_ref()
                    .is_some_and(|value| asset_text_is_valid(value, 200))
                && item
                    .material_location_id
                    .is_some_and(production_id_is_valid)
                && item.material_location_name.is_none()
                && item.material_location_path.is_none()
        }
        _ => false,
    };
    let facility_modifier_shape_valid = match item.facility_modifier_state.as_str() {
        "not-selected" => {
            item.facility_id.is_none()
                && item.facility_material_bonus_basis_points.is_none()
                && item.facility_time_bonus_basis_points.is_none()
        }
        "unconfigured" => {
            item.facility_id.is_some()
                && item.facility_material_bonus_basis_points.is_none()
                && item.facility_time_bonus_basis_points.is_none()
        }
        "ready" => {
            item.facility_id.is_some()
                && item
                    .facility_material_bonus_basis_points
                    .is_some_and(|value| value <= 5_000)
                && item
                    .facility_time_bonus_basis_points
                    .is_some_and(|value| value <= 5_000)
        }
        _ => false,
    };
    let assigned_step_blueprint_ids = item
        .steps
        .iter()
        .filter_map(|step| step.blueprint_assignment.blueprint_item_id)
        .collect::<Vec<_>>();
    let assigned_step_blueprint_id_count = assigned_step_blueprint_ids
        .iter()
        .copied()
        .collect::<HashSet<_>>()
        .len();
    let ready = item.state == "ready";
    let blueprint_source_valid = match (
        item.blueprint_snapshot_id,
        item.blueprint_sync_run_id,
        item.blueprint_observed_at.as_ref(),
    ) {
        (None, None, None) => true,
        (Some(snapshot_id), Some(sync_run_id), Some(observed_at)) => {
            production_id_is_valid(snapshot_id)
                && production_id_is_valid(sync_run_id)
                && asset_text_is_valid(observed_at, 64)
        }
        _ => false,
    };
    let blueprint_source_available = item.blueprint_snapshot_id.is_some();
    let assignment_has_details = item.blueprint_kind.is_some();
    let assigned_details_valid = assignment_has_details
        && item.blueprint_item_id.is_some_and(production_id_is_valid)
        && item
            .blueprint_material_efficiency
            .is_some_and(|value| value <= 10)
        && item
            .blueprint_time_efficiency
            .is_some_and(|value| value <= 20)
        && item
            .blueprint_runs
            .is_some_and(|value| value == -1 || value >= 0)
        && item
            .blueprint_location_id
            .is_some_and(production_id_is_valid)
        && item
            .blueprint_location_flag
            .as_ref()
            .is_some_and(|value| asset_text_is_valid(value, 100));
    let blueprint_candidate_ids = item
        .blueprint_candidates
        .iter()
        .map(|candidate| candidate.item_id)
        .collect::<HashSet<_>>();
    let blueprint_candidates_valid = item.blueprint_candidate_count <= JAVASCRIPT_MAX_SAFE_INTEGER
        && item.blueprint_candidates.len() <= 50
        && item.blueprint_candidate_count >= item.blueprint_candidates.len() as u64
        && (item.blueprint_candidate_count > 50
            || item.blueprint_candidate_count == item.blueprint_candidates.len() as u64)
        && blueprint_candidate_ids.len() == item.blueprint_candidates.len()
        && item
            .blueprint_candidates
            .iter()
            .all(production_blueprint_candidate_is_valid);
    let assignment_valid = matches!(
        item.blueprint_assignment_state.as_str(),
        "ready"
            | "unassigned"
            | "snapshot-missing"
            | "missing"
            | "type-mismatch"
            | "runs-insufficient"
    ) && blueprint_source_valid
        && ((item.blueprint_assignment_state == "snapshot-missing") != blueprint_source_available)
        && match item.blueprint_assignment_state.as_str() {
            "snapshot-missing" => item.blueprint_item_id.is_none() && !assignment_has_details,
            "unassigned" => item.blueprint_item_id.is_none() && !assignment_has_details,
            "missing" => item.blueprint_item_id.is_some() && !assignment_has_details,
            "ready" | "type-mismatch" | "runs-insufficient" => assigned_details_valid,
            _ => false,
        }
        && if item.blueprint_assignment_state == "ready" {
            item.applied_material_efficiency
                == (if item.activity == "manufacturing" {
                    item.blueprint_material_efficiency.unwrap_or(0)
                } else {
                    0
                })
                && item.applied_time_efficiency
                    == (if item.activity == "manufacturing" {
                        item.blueprint_time_efficiency.unwrap_or(0)
                    } else {
                        0
                    })
        } else {
            item.applied_material_efficiency == 0 && item.applied_time_efficiency == 0
        };
    let asset_source_valid = match (
        item.asset_snapshot_id,
        item.asset_sync_run_id,
        item.asset_observed_at.as_ref(),
    ) {
        (None, None, None) => true,
        (Some(snapshot_id), Some(sync_run_id), Some(observed_at)) => {
            production_id_is_valid(snapshot_id)
                && production_id_is_valid(sync_run_id)
                && asset_text_is_valid(observed_at, 64)
        }
        _ => false,
    };
    let owner_snapshot_available = item.asset_snapshot_id.is_some();
    let skill_source_valid = match (
        item.skill_snapshot_id,
        item.skill_sync_run_id,
        item.skill_observed_at.as_ref(),
    ) {
        (None, None, None) => true,
        (Some(snapshot_id), Some(sync_run_id), Some(observed_at)) => {
            production_id_is_valid(snapshot_id)
                && production_id_is_valid(sync_run_id)
                && asset_text_is_valid(observed_at, 64)
        }
        _ => false,
    };
    let skill_source_available = item.skill_snapshot_id.is_some();
    let ready_facility_steps = item
        .steps
        .iter()
        .filter(|step| step.facility_evidence.state == "ready")
        .count();
    let expected_facility_state = if !ready {
        "not-applicable"
    } else if ready_facility_steps == item.steps.len() {
        "ready"
    } else if ready_facility_steps > 0 {
        "partial"
    } else {
        "missing"
    };
    let expected_inventory_state = if !ready {
        "not-applicable"
    } else if item.gross_materials.is_empty() {
        "covered"
    } else if !owner_snapshot_available {
        "snapshot-missing"
    } else if item.gross_materials.iter().any(|material| {
        material
            .missing_quantity
            .is_some_and(|quantity| quantity > 0)
    }) {
        "shortage"
    } else {
        "covered"
    };
    let all_step_modifiers_ready = item
        .steps
        .iter()
        .all(|step| step.facility_modifier_state == "ready");
    let ready_costs = item
        .steps
        .iter()
        .filter(|step| step.installation_cost.state == "ready")
        .map(|step| &step.installation_cost)
        .collect::<Vec<_>>();
    let expected_installation_cost_state = if !ready {
        "not-applicable"
    } else if ready_costs.len() == item.steps.len() {
        "ready"
    } else if !ready_costs.is_empty() {
        "partial"
    } else if item
        .steps
        .iter()
        .all(|step| step.installation_cost.state == "unconfigured")
    {
        "unconfigured"
    } else {
        "unavailable"
    };
    let expected_estimated_item_value = if ready_costs.is_empty() {
        None
    } else {
        ready_costs.iter().try_fold(0_u64, |total, cost| {
            total.checked_add(cost.estimated_item_value?)
        })
    };
    let expected_system_cost = if ready_costs.is_empty() {
        None
    } else {
        ready_costs
            .iter()
            .try_fold(0_u64, |total, cost| total.checked_add(cost.system_cost?))
    };
    let expected_facility_tax = if ready_costs.is_empty() {
        None
    } else {
        ready_costs
            .iter()
            .try_fold(0_u64, |total, cost| total.checked_add(cost.facility_tax?))
    };
    let expected_scc_surcharge = if ready_costs.is_empty() {
        None
    } else {
        ready_costs
            .iter()
            .try_fold(0_u64, |total, cost| total.checked_add(cost.scc_surcharge?))
    };
    let expected_installation_cost = if ready_costs.is_empty() {
        None
    } else {
        ready_costs.iter().try_fold(0_u64, |total, cost| {
            total.checked_add(cost.estimated_installation_cost?)
        })
    };
    let installation_cost_shape_valid = item.installation_cost_state
        == expected_installation_cost_state
        && item.costed_step_count == ready_costs.len() as u64
        && item.uncosted_step_count
            == if ready {
                item.steps.len() as u64 - ready_costs.len() as u64
            } else {
                0
            }
        && (ready_costs.is_empty()
            || expected_estimated_item_value.is_some()
                && expected_system_cost.is_some()
                && expected_facility_tax.is_some()
                && expected_scc_surcharge.is_some()
                && expected_installation_cost.is_some())
        && expected_estimated_item_value == item.estimated_item_value
        && expected_system_cost == item.system_cost
        && expected_facility_tax == item.facility_tax
        && expected_scc_surcharge == item.scc_surcharge
        && expected_installation_cost == item.estimated_installation_cost;
    let facility_time_shape_valid = if ready
        && skill_source_available
        && item.facility_modifier_state == "ready"
        && all_step_modifiers_ready
    {
        item.total_facility_time_seconds.is_some()
            && item.facility_time_savings_seconds.is_some()
            && item.steps.iter().try_fold(0_u64, |total, step| {
                total.checked_add(step.total_facility_time_seconds?)
            }) == item.total_facility_time_seconds
            && item
                .total_character_time_seconds
                .zip(item.total_facility_time_seconds)
                .and_then(|(character, facility)| character.checked_sub(facility))
                == item.facility_time_savings_seconds
    } else {
        item.total_facility_time_seconds.is_none() && item.facility_time_savings_seconds.is_none()
    };
    let resolution_shape = if ready {
        item.build_number.is_some()
            && !item.steps.is_empty()
            && item.cycle_type_ids.is_empty()
            && item.total_base_time_seconds.is_some()
            && item.total_blueprint_time_seconds.is_some()
            && item.time_efficiency_savings_seconds.is_some()
            && item.steps.last().is_some_and(|step| {
                step.blueprint_type_id == item.blueprint_type_id
                    && step.product_type_id == item.product_type_id
                    && step.activity == item.activity
                    && step.required_quantity == item.target_quantity
                    && step.blueprint_assignment.blueprint_assignment_state
                        == item.blueprint_assignment_state
                    && step.blueprint_assignment.blueprint_item_id == item.blueprint_item_id
                    && step.blueprint_assignment.blueprint_kind == item.blueprint_kind
                    && step.blueprint_assignment.blueprint_material_efficiency
                        == item.blueprint_material_efficiency
                    && step.blueprint_assignment.blueprint_time_efficiency
                        == item.blueprint_time_efficiency
                    && step.blueprint_assignment.blueprint_runs == item.blueprint_runs
                    && step.blueprint_assignment.blueprint_location_id == item.blueprint_location_id
                    && step.blueprint_assignment.blueprint_location_flag
                        == item.blueprint_location_flag
                    && step.blueprint_assignment.blueprint_snapshot_id == item.blueprint_snapshot_id
                    && step.blueprint_assignment.blueprint_sync_run_id == item.blueprint_sync_run_id
                    && step.blueprint_assignment.blueprint_observed_at == item.blueprint_observed_at
                    && step.blueprint_assignment.blueprint_candidate_count
                        == item.blueprint_candidate_count
                    && step
                        .blueprint_assignment
                        .blueprint_candidates
                        .eq(&item.blueprint_candidates)
            })
            && item.steps.iter().all(|step| {
                step.blueprint_assignment.blueprint_snapshot_id == item.blueprint_snapshot_id
                    && step.blueprint_assignment.blueprint_sync_run_id == item.blueprint_sync_run_id
                    && step.blueprint_assignment.blueprint_observed_at == item.blueprint_observed_at
            })
            && item.steps.iter().try_fold(0_u64, |total, step| {
                total.checked_add(step.total_base_time_seconds)
            }) == item.total_base_time_seconds
            && item.steps.iter().try_fold(0_u64, |total, step| {
                total.checked_add(step.total_blueprint_time_seconds)
            }) == item.total_blueprint_time_seconds
            && item
                .total_base_time_seconds
                .zip(item.total_blueprint_time_seconds)
                .and_then(|(base, adjusted)| base.checked_sub(adjusted))
                == item.time_efficiency_savings_seconds
            && if skill_source_available {
                item.total_character_time_seconds.is_some()
                    && item.character_skill_time_savings_seconds.is_some()
                    && item.steps.iter().all(|step| {
                        step.total_character_time_seconds.is_some()
                            && step.character_skill_time_savings_seconds.is_some()
                            && step
                                .time_skills
                                .iter()
                                .all(|skill| skill.active_level.is_some())
                    })
                    && item.steps.iter().try_fold(0_u64, |total, step| {
                        total.checked_add(step.total_character_time_seconds?)
                    }) == item.total_character_time_seconds
                    && item
                        .total_blueprint_time_seconds
                        .zip(item.total_character_time_seconds)
                        .and_then(|(blueprint, character)| blueprint.checked_sub(character))
                        == item.character_skill_time_savings_seconds
            } else {
                item.total_character_time_seconds.is_none()
                    && item.character_skill_time_savings_seconds.is_none()
                    && item.steps.iter().all(|step| {
                        step.total_character_time_seconds.is_none()
                            && step.character_skill_time_savings_seconds.is_none()
                            && !step.character_skill_time_applied
                            && step
                                .time_skills
                                .iter()
                                .all(|skill| skill.active_level.is_none())
                    })
            }
            && item
                .steps
                .last()
                .is_some_and(|step| step.material_efficiency == item.applied_material_efficiency)
            && item
                .steps
                .last()
                .is_some_and(|step| step.time_efficiency == item.applied_time_efficiency)
    } else {
        item.steps.is_empty()
            && item.supply_decisions.is_empty()
            && item.gross_materials.is_empty()
            && item.total_base_time_seconds.is_none()
            && item.total_blueprint_time_seconds.is_none()
            && item.time_efficiency_savings_seconds.is_none()
            && item.total_character_time_seconds.is_none()
            && item.character_skill_time_savings_seconds.is_none()
            && item.total_facility_time_seconds.is_none()
            && item.facility_time_savings_seconds.is_none()
            && ((item.state == "cycle" && !item.cycle_type_ids.is_empty())
                || (item.state != "cycle" && item.cycle_type_ids.is_empty()))
    };
    production_id_is_valid(item.plan_id)
        && production_id_is_valid(item.owner_character_id)
        && asset_text_is_valid(&item.owner_name, 100)
        && production_id_is_valid(item.blueprint_type_id)
        && asset_text_is_valid(&item.blueprint_name, 200)
        && item.blueprint_item_id.is_none_or(production_id_is_valid)
        && item
            .blueprint_kind
            .as_ref()
            .is_none_or(|value| matches!(value.as_str(), "original" | "copy"))
        && item.applied_material_efficiency <= 10
        && item.applied_time_efficiency <= 20
        && PRODUCTION_LOCATION_SELECTION_STATES.contains(&item.location_selection_state.as_str())
        && location_selection_valid
        && facility_modifier_shape_valid
        && facility_time_shape_valid
        && item
            .facility_tax_basis_points
            .is_none_or(|value| value <= 10_000)
        && (item.facility_id.is_some() || item.facility_tax_basis_points.is_none())
        && PRODUCTION_PLAN_INSTALLATION_COST_STATES.contains(&item.installation_cost_state.as_str())
        && item
            .estimated_item_value
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && item
            .system_cost
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && item
            .facility_tax
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && item
            .scc_surcharge
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && item
            .estimated_installation_cost
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && item.costed_step_count <= JAVASCRIPT_MAX_SAFE_INTEGER
        && item.uncosted_step_count <= JAVASCRIPT_MAX_SAFE_INTEGER
        && installation_cost_shape_valid
        && blueprint_candidates_valid
        && assignment_valid
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
        && item
            .total_blueprint_time_seconds
            .is_none_or(production_id_is_valid)
        && item
            .time_efficiency_savings_seconds
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && item
            .total_character_time_seconds
            .is_none_or(production_id_is_valid)
        && item
            .character_skill_time_savings_seconds
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && item
            .total_facility_time_seconds
            .is_none_or(production_id_is_valid)
        && item
            .facility_time_savings_seconds
            .is_none_or(|value| value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && matches!(
            item.character_skill_state.as_str(),
            "ready" | "snapshot-missing"
        )
        && ((item.character_skill_state == "ready") == skill_source_available)
        && skill_source_valid
        && PRODUCTION_FACILITY_STATES.contains(&item.facility_state.as_str())
        && item.facility_state == expected_facility_state
        && PRODUCTION_INVENTORY_STATES.contains(&item.inventory_state.as_str())
        && item.inventory_state == expected_inventory_state
        && asset_source_valid
        && (ready || !owner_snapshot_available)
        && (!owner_snapshot_available
            || item
                .gross_materials
                .iter()
                .all(|material| material.availability_state != "snapshot-missing"))
        && (owner_snapshot_available
            || item.gross_materials.is_empty()
            || item
                .gross_materials
                .iter()
                .all(|material| material.availability_state == "snapshot-missing"))
        && asset_text_is_valid(&item.created_at, 64)
        && asset_text_is_valid(&item.updated_at, 64)
        && assigned_step_blueprint_id_count == assigned_step_blueprint_ids.len()
        && steps_valid
        && gross_valid
        && warnings_valid
        && supply_decisions_valid
        && supply_shape_valid
        && resolution_shape
}

fn production_market_hub_is_valid(hub: &ProductionMarketHub) -> bool {
    let expected = match hub.hub_id.as_str() {
        "jita" => (
            "Jita",
            60_003_760,
            "Jita IV - Moon 4 - Caldari Navy Assembly Plant",
            30_000_142,
            10_000_002,
            0,
        ),
        "amarr" => (
            "Amarr",
            60_008_494,
            "Amarr VIII (Oris) - Emperor Family Academy",
            30_002_187,
            10_000_043,
            1,
        ),
        "dodixie" => (
            "Dodixie",
            60_011_866,
            "Dodixie IX - Moon 20 - Federation Navy Assembly Plant",
            30_002_659,
            10_000_032,
            2,
        ),
        "hek" => (
            "Hek",
            60_005_686,
            "Hek VIII - Moon 12 - Boundless Creation Factory",
            30_002_053,
            10_000_042,
            3,
        ),
        "rens" => (
            "Rens",
            60_004_588,
            "Rens VI - Moon 8 - Brutor Tribe Treasury",
            30_002_510,
            10_000_030,
            4,
        ),
        _ => return false,
    };
    hub.name == expected.0
        && hub.station_id == expected.1
        && hub.station_name == expected.2
        && hub.solar_system_id == expected.3
        && hub.region_id == expected.4
        && hub.priority == expected.5
}

fn production_purchase_market_item_is_valid(item: &ProductionPurchaseListItem) -> bool {
    if !MARKET_ITEM_STATES.contains(&item.market_state.as_str()) {
        return false;
    }
    let all_missing = item.covered_quantity.is_none()
        && item.uncovered_quantity.is_none()
        && item.used_order_count.is_none()
        && item.lowest_unit_price_cents.is_none()
        && item.weighted_unit_price_cents.is_none()
        && item.purchase_cost_cents.is_none();
    if item.market_state == "snapshot-missing" {
        return all_missing;
    }
    let (Some(covered), Some(uncovered), Some(order_count), purchase_cost) = (
        item.covered_quantity,
        item.uncovered_quantity,
        item.used_order_count,
        item.purchase_cost_cents,
    ) else {
        return false;
    };
    if covered.checked_add(uncovered) != Some(item.quantity) {
        return false;
    }
    if item.market_state == "unavailable" {
        return covered == 0
            && uncovered == item.quantity
            && order_count == 0
            && item.lowest_unit_price_cents.is_none()
            && item.weighted_unit_price_cents.is_none()
            && purchase_cost == Some(0);
    }
    let (Some(lowest), Some(weighted), Some(cost)) = (
        item.lowest_unit_price_cents,
        item.weighted_unit_price_cents,
        purchase_cost,
    ) else {
        return false;
    };
    covered > 0
        && order_count > 0
        && lowest > 0
        && weighted >= lowest
        && cost > 0
        && cost
            .checked_add(covered - 1)
            .is_some_and(|value| value / covered == weighted)
        && ((item.market_state == "ready" && uncovered == 0)
            || (item.market_state == "partial" && uncovered > 0))
}

fn production_purchase_list_is_valid(list: &ProductionPurchaseList, plan_count: u64) -> bool {
    let type_ids = list
        .items
        .iter()
        .map(|item| item.type_id)
        .collect::<HashSet<_>>();
    let represented_quantity = list
        .items
        .iter()
        .try_fold(0_u64, |total, item| total.checked_add(item.quantity));
    let incomplete = list.unresolved_plan_count > 0 || list.omitted_item_count > 0;
    let expected_state = if incomplete {
        "incomplete"
    } else if list.items.is_empty() {
        "empty"
    } else {
        "ready"
    };
    let market_source_ready = list.market_snapshot_id.is_some()
        && list.market_sync_run_id.is_some()
        && list
            .market_observed_at
            .as_ref()
            .is_some_and(|value| asset_text_is_valid(value, 64))
        && list.market_age_seconds.is_some();
    let market_source_missing = list.market_snapshot_id.is_none()
        && list.market_sync_run_id.is_none()
        && list.market_observed_at.is_none()
        && list.market_age_seconds.is_none();
    let market_state_counts = list.items.iter().fold([0_u64; 4], |mut counts, item| {
        if let Some(index) = MARKET_ITEM_STATES
            .iter()
            .position(|state| *state == item.market_state)
        {
            counts[index] += 1;
        }
        counts
    });
    let total_purchase_cost = list.items.iter().try_fold(0_u64, |total, item| {
        total.checked_add(item.purchase_cost_cents.unwrap_or(0))
    });
    let hub_ids = list
        .market_hubs
        .iter()
        .map(|hub| hub.hub_id.as_str())
        .collect::<Vec<_>>();
    let selected_hub_count = list
        .market_hubs
        .iter()
        .filter(|hub| hub.hub_id == list.market_hub.hub_id)
        .count();
    let pricing_shape = match list.pricing_state.as_str() {
        "empty" => list.items.is_empty(),
        "snapshot-missing" => {
            !list.items.is_empty()
                && market_source_missing
                && market_state_counts[3] == list.items.len() as u64
        }
        "ready" => {
            !list.items.is_empty()
                && list.state == "ready"
                && market_source_ready
                && market_state_counts[0] == list.items.len() as u64
        }
        "unavailable" => {
            !list.items.is_empty()
                && market_source_ready
                && market_state_counts[2] == list.items.len() as u64
        }
        "stale" => !list.items.is_empty() && market_source_ready,
        "partial" => !list.items.is_empty() && market_source_ready,
        _ => false,
    };
    let installation_shape = match list.installation_cost_state.as_str() {
        "ready" | "partial" => list.estimated_installation_cost.is_some(),
        "unavailable" | "not-applicable" => list.estimated_installation_cost.is_none(),
        _ => false,
    };
    let expected_additional_capital = if list.installation_cost_state == "ready"
        && matches!(list.pricing_state.as_str(), "ready" | "empty")
    {
        list.estimated_installation_cost
            .and_then(|value| value.checked_mul(100))
            .and_then(|value| value.checked_add(list.total_purchase_cost_cents))
    } else {
        None
    };
    matches!(list.state.as_str(), "ready" | "empty" | "incomplete")
        && list.items.len() <= 1_000
        && type_ids.len() == list.items.len()
        && list.item_count <= JAVASCRIPT_MAX_SAFE_INTEGER
        && list.total_quantity <= JAVASCRIPT_MAX_SAFE_INTEGER
        && list.included_plan_count <= JAVASCRIPT_MAX_SAFE_INTEGER
        && list.unresolved_plan_count <= JAVASCRIPT_MAX_SAFE_INTEGER
        && list.omitted_item_count <= JAVASCRIPT_MAX_SAFE_INTEGER
        && list
            .included_plan_count
            .checked_add(list.unresolved_plan_count)
            == Some(plan_count)
        && (list.items.len() as u64).checked_add(list.omitted_item_count) == Some(list.item_count)
        && represented_quantity.is_some_and(|quantity| {
            quantity <= list.total_quantity
                && (list.omitted_item_count > 0 || quantity == list.total_quantity)
        })
        && list.state == expected_state
        && list.market_hubs.len() == MARKET_HUB_IDS.len()
        && hub_ids == MARKET_HUB_IDS
        && list.market_hubs.iter().all(production_market_hub_is_valid)
        && production_market_hub_is_valid(&list.market_hub)
        && selected_hub_count == 1
        && list.market_price_rule == "selected-hub-lowest-sell-orders-volume-weighted-cents"
        && list.market_price_type_limit == MARKET_PRICE_TYPE_LIMIT
        && MARKET_PRICING_STATES.contains(&list.pricing_state.as_str())
        && (market_source_ready || market_source_missing)
        && pricing_shape
        && list.fully_covered_item_count == market_state_counts[0]
        && list.partially_covered_item_count == market_state_counts[1]
        && list.unavailable_item_count == market_state_counts[2]
        && list.snapshot_missing_item_count == market_state_counts[3]
        && total_purchase_cost == Some(list.total_purchase_cost_cents)
        && installation_shape
        && list.additional_capital_need_cents == expected_additional_capital
        && list.items.iter().all(|item| {
            production_id_is_valid(item.type_id)
                && asset_text_is_valid(&item.type_name, 200)
                && production_id_is_valid(item.quantity)
                && item.inventory_shortage_quantity <= JAVASCRIPT_MAX_SAFE_INTEGER
                && item.reservation_conflict_quantity <= JAVASCRIPT_MAX_SAFE_INTEGER
                && item
                    .inventory_shortage_quantity
                    .checked_add(item.reservation_conflict_quantity)
                    == Some(item.quantity)
                && production_id_is_valid(item.plan_count)
                && item.plan_count <= plan_count
                && production_purchase_market_item_is_valid(item)
        })
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
    let location_keys = response
        .location_options
        .iter()
        .map(|item| (item.owner_character_id, item.facility_id))
        .collect::<HashSet<_>>();
    let assigned_blueprint_ids = response
        .items
        .iter()
        .flat_map(|item| item.steps.iter())
        .filter_map(|step| step.blueprint_assignment.blueprint_item_id)
        .collect::<Vec<_>>();
    let assigned_blueprint_id_count = assigned_blueprint_ids
        .iter()
        .copied()
        .collect::<HashSet<_>>()
        .len();
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
        && assigned_blueprint_id_count == assigned_blueprint_ids.len()
        && owner_ids.len() == response.owners.len()
        && response.location_options.len() <= 200
        && location_keys.len() == response.location_options.len()
        && response
            .location_options
            .iter()
            .all(production_location_option_is_valid)
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
        && response.inventory_applied
        && response.reservations_applied
        && response.reservation_rule == "priority-desc-created-asc-plan-id-asc"
        && response.blueprint_material_efficiency_applied
        && response.material_efficiency_rule == "max-runs-ceil-base-runs-percent"
        && response.blueprint_time_efficiency_applied
        && response.time_efficiency_rule == "max-one-ceil-base-runs-percent"
        && response.blueprint_chain_assignments_applied
        && response.blueprint_chain_assignment_rule == "explicit-per-recipe-unique-item"
        && response.character_skill_time_applied
        && response.character_skill_time_rule
            == "job-wide-ceil-industry-4-advanced-industry-3-reactions-4-active-levels"
        && response.facility_evidence_applied
        && response.facility_evidence_rule
            == "assigned-blueprint-before-active-before-latest-owner-job"
        && response.supply_modes_applied
        && response.supply_mode_rule == "stock-first-before-recursive-build"
        && response.facility_modifiers_applied
        && response.facility_modifier_rule == "explicit-basis-points-combined-before-single-ceil"
        && production_purchase_list_is_valid(&response.purchase_list, response.total)
        && response.purchase_list_applied
        && response.purchase_list_rule == "filtered-plans-sum-missing-by-type"
        && response.market_prices_applied
        && response.market_price_rule
            == "selected-hub-lowest-sell-orders-volume-weighted-cents"
        && response.installation_costs_applied
        && response.installation_cost_rule
            == "base-material-adjusted-price-times-runs-system-index-plus-explicit-tax-plus-scc-4-percent-ceil"
        && !response.remaining_modifiers_applied
}

fn production_plan_mutation_is_valid(item: &ProductionPlanMutationResponse) -> bool {
    let root_key = (
        item.blueprint_type_id,
        item.activity.as_str(),
        item.product_type_id,
    );
    let keys = item
        .step_blueprint_assignments
        .iter()
        .map(|assignment| {
            (
                assignment.blueprint_type_id,
                assignment.activity.as_str(),
                assignment.product_type_id,
            )
        })
        .collect::<HashSet<_>>();
    let item_ids = item
        .step_blueprint_assignments
        .iter()
        .map(|assignment| assignment.blueprint_item_id)
        .collect::<HashSet<_>>();
    let supply_keys = item
        .step_supply_modes
        .iter()
        .map(|supply| {
            (
                supply.blueprint_type_id,
                supply.activity.as_str(),
                supply.product_type_id,
            )
        })
        .collect::<HashSet<_>>();
    item.saved
        && production_id_is_valid(item.plan_id)
        && production_id_is_valid(item.owner_character_id)
        && production_id_is_valid(item.blueprint_type_id)
        && item.blueprint_item_id.is_none_or(production_id_is_valid)
        && item.facility_id.is_none_or(production_id_is_valid)
        && item.material_location_id.is_none_or(production_id_is_valid)
        && item
            .facility_material_bonus_basis_points
            .is_none_or(|value| value <= 5_000)
        && item
            .facility_time_bonus_basis_points
            .is_none_or(|value| value <= 5_000)
        && item
            .facility_tax_basis_points
            .is_none_or(|value| value <= 10_000)
        && ((item.facility_material_bonus_basis_points.is_none())
            == item.facility_time_bonus_basis_points.is_none())
        && (item.facility_id.is_some() || item.facility_material_bonus_basis_points.is_none())
        && (item.facility_id.is_some() || item.facility_tax_basis_points.is_none())
        && (item.material_location_id.is_none() || item.facility_id.is_some())
        && item.step_blueprint_assignments.len() <= 499
        && keys.len() == item.step_blueprint_assignments.len()
        && item_ids.len() == item.step_blueprint_assignments.len()
        && item
            .blueprint_item_id
            .is_none_or(|root_item_id| !item_ids.contains(&root_item_id))
        && item.step_blueprint_assignments.iter().all(|assignment| {
            production_id_is_valid(assignment.blueprint_type_id)
                && assignment.activity == "manufacturing"
                && production_id_is_valid(assignment.product_type_id)
                && production_id_is_valid(assignment.blueprint_item_id)
                && (
                    assignment.blueprint_type_id,
                    assignment.activity.as_str(),
                    assignment.product_type_id,
                ) != root_key
        })
        && item.step_supply_modes.len() <= 499
        && supply_keys.len() == item.step_supply_modes.len()
        && item.step_supply_modes.iter().all(|supply| {
            production_id_is_valid(supply.blueprint_type_id)
                && PRODUCTION_ACTIVITIES.contains(&supply.activity.as_str())
                && production_id_is_valid(supply.product_type_id)
                && PRODUCTION_SUPPLY_MODES.contains(&supply.supply_mode.as_str())
                && (
                    supply.blueprint_type_id,
                    supply.activity.as_str(),
                    supply.product_type_id,
                ) != root_key
        })
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
                && event.location_status_before.as_deref().is_none_or(|value| {
                    matches!(value, "resolved" | "restricted" | "unresolved" | "cycle")
                })
                && event.location_status_after.as_deref().is_none_or(|value| {
                    matches!(value, "resolved" | "restricted" | "unresolved" | "cycle")
                })
                && event
                    .location_path_before
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 16_000))
                && event
                    .location_path_after
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 16_000))
                && (event.location_path_before.is_none() || event.location_status_before.is_some())
                && (event.location_path_after.is_none() || event.location_status_after.is_some())
                && (event.quantity_before.is_some()
                    || event.location_status_before.is_none()
                        && event.location_path_before.is_none())
                && (event.quantity_after.is_some()
                    || event.location_status_after.is_none() && event.location_path_after.is_none())
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

fn asset_delta_group_response_is_valid(response: &AssetDeltaGroupQueryResponse) -> bool {
    let owner_ids = response
        .owners
        .iter()
        .map(|owner| owner.character_id)
        .collect::<HashSet<_>>();
    let group_ids = response
        .items
        .iter()
        .map(|group| group.group_id.as_str())
        .collect::<HashSet<_>>();
    response.limit > 0
        && response.limit <= MAX_ASSET_PAGE_SIZE
        && response.total <= response.event_total
        && response.event_total <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.offset <= JAVASCRIPT_MAX_SAFE_INTEGER
        && response.items.len() as u64 <= response.limit
        && response.items.len() as u64 <= response.total
        && response
            .change_types
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            == ASSET_DELTA_CHANGE_TYPES
        && group_ids.len() == response.items.len()
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
        .all(|value| value <= response.event_total && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
        && response.owners.iter().all(|owner| {
            owner.character_id > 0
                && owner.character_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&owner.name, 100)
        })
        && response.items.iter().all(|group| {
            let correlation_total = [
                group.job_correlation_summary.linked,
                group.job_correlation_summary.ambiguous,
                group.job_correlation_summary.unmatched,
                group.job_correlation_summary.unavailable,
                group.job_correlation_summary.not_applicable,
            ]
            .into_iter()
            .try_fold(0_u64, |sum, value| sum.checked_add(value));
            group.group_id.len() == 64
                && group
                    .group_id
                    .bytes()
                    .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
                && group.type_id > 0
                && group.type_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && owner_ids.contains(&group.owner_character_id)
                && asset_text_is_valid(&group.type_name, 220)
                && asset_text_is_valid(&group.owner_name, 100)
                && !group.change_types.is_empty()
                && group.change_types.len() <= ASSET_DELTA_CHANGE_TYPES.len()
                && group
                    .change_types
                    .iter()
                    .all(|value| ASSET_DELTA_CHANGE_TYPES.contains(&value.as_str()))
                && group.change_types.iter().collect::<HashSet<_>>().len()
                    == group.change_types.len()
                && group.event_count > 0
                && group.event_count <= JAVASCRIPT_MAX_SAFE_INTEGER
                && group.item_count > 0
                && group.item_count <= group.event_count
                && group.quantity_before <= JAVASCRIPT_MAX_SAFE_INTEGER
                && group.quantity_after <= JAVASCRIPT_MAX_SAFE_INTEGER
                && i128::from(group.quantity_after) - i128::from(group.quantity_before)
                    == i128::from(group.quantity_delta)
                && group.quantity_delta.unsigned_abs() <= JAVASCRIPT_MAX_SAFE_INTEGER
                && group.location_count_before <= group.event_count
                && group.location_count_after <= group.event_count
                && group.location_id_before.is_some() == (group.location_count_before == 1)
                && group.location_flag_before.is_some() == (group.location_count_before == 1)
                && group.location_id_after.is_some() == (group.location_count_after == 1)
                && group.location_flag_after.is_some() == (group.location_count_after == 1)
                && group
                    .location_id_before
                    .is_none_or(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && group
                    .location_id_after
                    .is_none_or(|value| value > 0 && value <= JAVASCRIPT_MAX_SAFE_INTEGER)
                && group
                    .location_flag_before
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 100))
                && group
                    .location_flag_after
                    .as_ref()
                    .is_none_or(|value| asset_text_is_valid(value, 100))
                && group.location_path_before.as_ref().is_none_or(|value| {
                    group.location_count_before == 1 && asset_text_is_valid(value, 16_000)
                })
                && group.location_path_after.as_ref().is_none_or(|value| {
                    group.location_count_after == 1 && asset_text_is_valid(value, 16_000)
                })
                && group.previous_asset_snapshot_id > 0
                && group.previous_asset_snapshot_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && group.current_asset_snapshot_id > 0
                && group.current_asset_snapshot_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && group.current_asset_sync_run_id > 0
                && group.current_asset_sync_run_id <= JAVASCRIPT_MAX_SAFE_INTEGER
                && asset_text_is_valid(&group.observed_at, 64)
                && correlation_total == Some(group.event_count)
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
    market_hub_id: String,
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
        || !MARKET_HUB_IDS.contains(&market_hub_id.as_str())
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
        "marketHubId": market_hub_id,
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
        || page.purchase_list.market_hub.hub_id != market_hub_id
    {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&page).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
fn sync_market_prices(
    market_hub_id: String,
    mut type_ids: Vec<u64>,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    let requested_type_count = type_ids.len();
    type_ids.sort_unstable();
    type_ids.dedup();
    if !MARKET_HUB_IDS.contains(&market_hub_id.as_str())
        || type_ids.is_empty()
        || type_ids.len() != requested_type_count
        || type_ids.len() as u64 > MARKET_PRICE_TYPE_LIMIT
        || type_ids
            .iter()
            .any(|type_id| *type_id == 0 || *type_id > JAVASCRIPT_MAX_SAFE_INTEGER)
    {
        return Err("market-price-request-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "hubId": market_hub_id,
        "typeIds": type_ids,
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
        sidecar_json_request_with_timeout(
            process,
            "POST",
            "/market-prices/sync",
            &body,
            ASSET_SYNC_TIMEOUT,
        )
        .map_err(str::to_owned)?
    };
    let result: MarketPriceSyncResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !market_price_sync_response_is_valid(&result) || result.hub_id != market_hub_id {
        return Err("sidecar-response-invalid".to_owned());
    }
    serde_json::to_string(&result).map_err(|_| "status-serialization-failed".to_owned())
}

#[tauri::command]
#[allow(clippy::too_many_arguments)]
fn save_production_plan(
    plan_id: Option<u64>,
    owner_character_id: u64,
    blueprint_type_id: u64,
    blueprint_item_id: Option<u64>,
    mut step_blueprint_assignments: Vec<ProductionStepBlueprintInput>,
    facility_id: Option<u64>,
    material_location_id: Option<u64>,
    facility_material_bonus_basis_points: Option<u16>,
    facility_time_bonus_basis_points: Option<u16>,
    facility_tax_basis_points: Option<u16>,
    mut step_supply_modes: Vec<ProductionStepSupplyInput>,
    activity: String,
    product_type_id: u64,
    target_quantity: u64,
    priority: u16,
    note: Option<String>,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    step_blueprint_assignments.sort_by(|left, right| {
        left.product_type_id
            .cmp(&right.product_type_id)
            .then_with(|| left.activity.cmp(&right.activity))
            .then_with(|| left.blueprint_type_id.cmp(&right.blueprint_type_id))
    });
    step_supply_modes.sort_by(|left, right| {
        left.product_type_id
            .cmp(&right.product_type_id)
            .then_with(|| left.activity.cmp(&right.activity))
            .then_with(|| left.blueprint_type_id.cmp(&right.blueprint_type_id))
    });
    let root_key = (blueprint_type_id, activity.as_str(), product_type_id);
    let step_keys = step_blueprint_assignments
        .iter()
        .map(|assignment| {
            (
                assignment.blueprint_type_id,
                assignment.activity.as_str(),
                assignment.product_type_id,
            )
        })
        .collect::<HashSet<_>>();
    let step_item_ids = step_blueprint_assignments
        .iter()
        .map(|assignment| assignment.blueprint_item_id)
        .collect::<HashSet<_>>();
    let supply_keys = step_supply_modes
        .iter()
        .map(|supply| {
            (
                supply.blueprint_type_id,
                supply.activity.as_str(),
                supply.product_type_id,
            )
        })
        .collect::<HashSet<_>>();
    if plan_id == Some(0)
        || plan_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || !production_id_is_valid(owner_character_id)
        || !production_id_is_valid(blueprint_type_id)
        || blueprint_item_id == Some(0)
        || blueprint_item_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || facility_id == Some(0)
        || facility_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || material_location_id == Some(0)
        || material_location_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || material_location_id.is_some() && facility_id.is_none()
        || facility_material_bonus_basis_points.is_some_and(|value| value > 5_000)
        || facility_time_bonus_basis_points.is_some_and(|value| value > 5_000)
        || facility_tax_basis_points.is_some_and(|value| value > 10_000)
        || facility_material_bonus_basis_points.is_none()
            != facility_time_bonus_basis_points.is_none()
        || facility_id.is_none() && facility_material_bonus_basis_points.is_some()
        || facility_id.is_none() && facility_tax_basis_points.is_some()
        || step_blueprint_assignments.len() > 499
        || step_keys.len() != step_blueprint_assignments.len()
        || step_item_ids.len() != step_blueprint_assignments.len()
        || blueprint_item_id.is_some_and(|value| step_item_ids.contains(&value))
        || step_blueprint_assignments.iter().any(|assignment| {
            !production_id_is_valid(assignment.blueprint_type_id)
                || assignment.activity != "manufacturing"
                || !production_id_is_valid(assignment.product_type_id)
                || !production_id_is_valid(assignment.blueprint_item_id)
                || (
                    assignment.blueprint_type_id,
                    assignment.activity.as_str(),
                    assignment.product_type_id,
                ) == root_key
        })
        || step_supply_modes.len() > 499
        || supply_keys.len() != step_supply_modes.len()
        || step_supply_modes.iter().any(|supply| {
            !production_id_is_valid(supply.blueprint_type_id)
                || !PRODUCTION_ACTIVITIES.contains(&supply.activity.as_str())
                || !production_id_is_valid(supply.product_type_id)
                || !PRODUCTION_SUPPLY_MODES.contains(&supply.supply_mode.as_str())
                || (
                    supply.blueprint_type_id,
                    supply.activity.as_str(),
                    supply.product_type_id,
                ) == root_key
        })
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
        "blueprintItemId": blueprint_item_id,
        "stepBlueprintAssignments": step_blueprint_assignments,
        "facilityId": facility_id,
        "materialLocationId": material_location_id,
        "facilityMaterialBonusBasisPoints": facility_material_bonus_basis_points,
        "facilityTimeBonusBasisPoints": facility_time_bonus_basis_points,
        "facilityTaxBasisPoints": facility_tax_basis_points,
        "stepSupplyModes": step_supply_modes,
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
        || saved.blueprint_item_id != blueprint_item_id
        || saved.step_blueprint_assignments != step_blueprint_assignments
        || saved.facility_id != facility_id
        || saved.material_location_id != material_location_id
        || saved.facility_material_bonus_basis_points != facility_material_bonus_basis_points
        || saved.facility_time_bonus_basis_points != facility_time_bonus_basis_points
        || saved.facility_tax_basis_points != facility_tax_basis_points
        || saved.step_supply_modes != step_supply_modes
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
    include_maxed: bool,
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
        "includeMaxed": include_maxed,
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
    type_id: Option<u64>,
    previous_asset_snapshot_id: Option<u64>,
    current_asset_snapshot_id: Option<u64>,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    let group_values = [
        type_id,
        previous_asset_snapshot_id,
        current_asset_snapshot_id,
    ];
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
        || (group_values.iter().any(Option::is_some)
            && !group_values.iter().all(|value| {
                value.is_some_and(|inner| inner > 0 && inner <= JAVASCRIPT_MAX_SAFE_INTEGER)
            }))
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
        "typeId": type_id,
        "previousAssetSnapshotId": previous_asset_snapshot_id,
        "currentAssetSnapshotId": current_asset_snapshot_id,
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
fn query_asset_delta_groups(
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
        sidecar_json_request(process, "POST", "/assets/deltas/groups/query", &body)
            .map_err(str::to_owned)?
    };
    let page: AssetDeltaGroupQueryResponse =
        serde_json::from_str(&response).map_err(|_| "sidecar-response-invalid".to_owned())?;
    if !asset_delta_group_response_is_valid(&page) || page.offset != offset || page.limit != limit {
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
            let preference = load_window_size();
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_size(Size::Physical(PhysicalSize::new(
                    preference.width,
                    preference.height,
                )));
                let _ = window.center();
                let _ = window.show();
            }
            *app.state::<RuntimeState>()
                .window_size
                .lock()
                .unwrap_or_else(|error| error.into_inner()) = preference;
            let app_handle = app.handle().clone();
            thread::spawn(move || supervise_sidecar(app_handle));
            Ok(())
        })
        .on_window_event(|window, event| {
            if window.label() != "main" || !matches!(event, WindowEvent::Resized(_)) {
                return;
            }
            let is_normal = window.is_maximized().is_ok_and(|value| !value)
                && window.is_minimized().is_ok_and(|value| !value)
                && window.is_fullscreen().is_ok_and(|value| !value);
            if !is_normal {
                return;
            }
            let WindowEvent::Resized(size) = event else {
                return;
            };
            let preference = WindowSizePreference {
                width: size.width,
                height: size.height,
            };
            if preference.is_valid() {
                *window
                    .state::<RuntimeState>()
                    .window_size
                    .lock()
                    .unwrap_or_else(|error| error.into_inner()) = preference;
            }
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
            sync_market_prices,
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
            query_asset_delta_groups,
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
            let preference = *app
                .state::<RuntimeState>()
                .window_size
                .lock()
                .unwrap_or_else(|error| error.into_inner());
            save_window_size(preference);
            stop_sidecar(app);
        }
    });
}

#[cfg(test)]
mod tests {
    use super::{
        account_group_record_is_valid, asset_delta_group_response_is_valid,
        asset_delta_response_is_valid, asset_export_response_is_valid,
        asset_query_response_is_valid, asset_summary_query_response_is_valid,
        authorization_url_is_valid, character_skill_query_response_is_valid,
        character_skill_sync_response_is_valid, eve_character_record_is_valid,
        industry_facility_query_response_is_valid, industry_facility_sync_response_is_valid,
        industry_job_query_response_is_valid, industry_job_sync_response_is_valid,
        industry_slot_query_response_is_valid, migrate_to_program_directory_storage,
        production_installation_cost_is_valid, production_plan_record_is_valid, read_window_size,
        release_page_url, research_plan_query_response_is_valid, sidecar_startup_error_code,
        sidecar_startup_error_is_retryable, sso_login_status_is_valid, write_window_size,
        AccountGroupRecord, AssetDeltaCorrelation, AssetDeltaCorrelationSummary,
        AssetDeltaGroupQueryResponse, AssetDeltaGroupRecord, AssetDeltaQueryResponse,
        AssetDeltaRecord, AssetDeltaSummary, AssetExportResponse, AssetLocationNode, AssetOwner,
        AssetQueryResponse, AssetRecord, AssetSummaryOwner, AssetSummaryQueryResponse,
        AssetSummaryRecord, CharacterSkillQueryResponse, CharacterSkillRecord,
        CharacterSkillSyncCharacterResponse, CharacterSkillSyncResponse, EveCharacterRecord,
        IndustryAssetCorrelation, IndustryBlueprintCorrelation, IndustryFacilityQueryResponse,
        IndustryFacilityRecord, IndustryFacilitySyncResponse, IndustryJobQueryResponse,
        IndustryJobRecord, IndustryJobSyncCharacterResponse, IndustryJobSyncResponse,
        IndustrySlotActivity, IndustrySlotQueryResponse, IndustrySlotRecord,
        ProductionBlueprintCandidate, ProductionFacilityEvidence, ProductionGrossMaterial,
        ProductionInstallationCost, ProductionPlanRecord, ProductionReservationClaim,
        ProductionStep, ProductionStepMaterial, ProductionSupplyDecision, ProductionTimeSkill,
        ResearchPlanOwner, ResearchPlanQueryResponse, ResearchPlanRecord, ResearchPlanSummary,
        RuntimeDataSnapshot, ScopePackageStatus, SsoCharacterIdentity, SsoLoginStatus,
        WindowSizePreference, ADVANCED_INDUSTRY_SKILL_ID, ASSET_LOCATION_STATUSES,
        INDUSTRY_COST_ACTIVITIES, INDUSTRY_FACILITY_ACCESS_STATES, INDUSTRY_FACILITY_KINDS,
        INDUSTRY_SECURITY_CLASSES, INDUSTRY_SKILL_ID, INDUSTRY_SLOT_ACTIVITIES,
        RESEARCH_PLAN_ACTIVITIES, RESEARCH_PLAN_STATES, SCC_SURCHARGE_BASIS_POINTS,
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
    fn persists_and_reads_a_valid_window_size() {
        let root = TestDirectory::new("window-size");
        let path = root.path().join("data/window-size.json");
        let preference = WindowSizePreference {
            width: 1680,
            height: 1050,
        };

        write_window_size(&path, preference).expect("window size must be written");

        assert_eq!(read_window_size(&path), Some(preference));
    }

    #[test]
    fn rejects_invalid_or_out_of_range_window_sizes() {
        let root = TestDirectory::new("invalid-window-size");
        let path = root.path().join("window-size.json");
        fs::write(&path, br#"{"width":800,"height":600}"#)
            .expect("invalid fixture must be written");
        assert_eq!(read_window_size(&path), None);

        let invalid = WindowSizePreference {
            width: 10_000,
            height: 900,
        };
        assert_eq!(
            write_window_size(&path, invalid),
            Err("window-size-invalid")
        );
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
                location_status_before: Some("resolved".to_owned()),
                location_status_after: Some("resolved".to_owned()),
                location_path_before: Some("Synthetic System / Input Hangar".to_owned()),
                location_path_after: Some("Synthetic System / Input Hangar".to_owned()),
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

        let grouped_page = AssetDeltaGroupQueryResponse {
            items: vec![AssetDeltaGroupRecord {
                group_id: "b".repeat(64),
                type_id: 98_001,
                type_name: "Synthetic Input".to_owned(),
                owner_character_id: 90_888_001,
                owner_name: "Builder".to_owned(),
                change_types: vec!["quantity".to_owned()],
                event_count: 2,
                item_count: 2,
                quantity_before: 17,
                quantity_after: 9,
                quantity_delta: -8,
                location_count_before: 1,
                location_count_after: 1,
                location_id_before: Some(60_888_001),
                location_id_after: Some(60_888_002),
                location_flag_before: Some("AutoFit".to_owned()),
                location_flag_after: Some("AutoFit".to_owned()),
                location_path_before: Some("Synthetic System / Input Box".to_owned()),
                location_path_after: Some("Synthetic System / Output Box".to_owned()),
                previous_asset_snapshot_id: 4,
                current_asset_snapshot_id: 6,
                current_asset_sync_run_id: 9,
                observed_at: "2026-09-10T11:00:00Z".to_owned(),
                age_seconds: 60,
                job_correlation_summary: AssetDeltaCorrelationSummary {
                    linked: 0,
                    ambiguous: 0,
                    unmatched: 2,
                    unavailable: 0,
                    not_applicable: 0,
                },
            }],
            total: 1,
            event_total: 2,
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
                quantity: 2,
                location: 0,
            },
            has_baseline: true,
            observed_at: Some("2026-09-10T11:00:00Z".to_owned()),
            age_seconds: Some(60),
        };
        assert!(asset_delta_group_response_is_valid(&grouped_page));

        let invalid_grouped = AssetDeltaGroupQueryResponse {
            event_total: 1,
            ..grouped_page
        };
        assert!(!asset_delta_group_response_is_valid(&invalid_grouped));
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
            prices: 2,
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

    fn missing_production_facility_evidence() -> ProductionFacilityEvidence {
        ProductionFacilityEvidence {
            state: "job-snapshot-missing".to_owned(),
            evidence: "none".to_owned(),
            job_id: None,
            job_status: None,
            facility_id: None,
            facility_name: None,
            facility_kind: None,
            facility_access: None,
            solar_system_id: None,
            solar_system_name: None,
            security_status: None,
            security_class: None,
            system_cost_index: None,
            job_snapshot_id: None,
            job_sync_run_id: None,
            job_observed_at: None,
            facility_snapshot_id: None,
            facility_sync_run_id: None,
            facility_observed_at: None,
        }
    }

    fn unselected_production_installation_cost() -> ProductionInstallationCost {
        ProductionInstallationCost {
            state: "not-selected".to_owned(),
            estimated_item_value: None,
            system_cost_index: None,
            system_cost: None,
            facility_tax_basis_points: None,
            facility_tax: None,
            scc_surcharge_basis_points: SCC_SURCHARGE_BASIS_POINTS,
            scc_surcharge: None,
            estimated_installation_cost: None,
            missing_adjusted_price_type_ids: Vec::new(),
            price_snapshot_id: None,
            price_sync_run_id: None,
            price_observed_at: None,
        }
    }

    #[test]
    fn validates_complete_installation_cost_with_official_scc_surcharge() {
        let mut cost = ProductionInstallationCost {
            state: "ready".to_owned(),
            estimated_item_value: Some(1_000),
            system_cost_index: Some(0.0125),
            system_cost: Some(13),
            facility_tax_basis_points: Some(100),
            facility_tax: Some(10),
            scc_surcharge_basis_points: SCC_SURCHARGE_BASIS_POINTS,
            scc_surcharge: Some(40),
            estimated_installation_cost: Some(63),
            missing_adjusted_price_type_ids: Vec::new(),
            price_snapshot_id: Some(18),
            price_sync_run_id: Some(19),
            price_observed_at: Some("2026-09-20T12:00:00Z".to_owned()),
        };
        assert!(production_installation_cost_is_valid(&cost));

        cost.scc_surcharge_basis_points = 150;
        assert!(!production_installation_cost_is_valid(&cost));
        cost.scc_surcharge_basis_points = SCC_SURCHARGE_BASIS_POINTS;
        cost.estimated_installation_cost = Some(62);
        assert!(!production_installation_cost_is_valid(&cost));
    }

    #[test]
    fn validates_multi_step_production_goal_at_end_of_execution_order() {
        let mut plan = ProductionPlanRecord {
            plan_id: 1,
            owner_character_id: 90_888_001,
            owner_name: "Builder".to_owned(),
            blueprint_type_id: 100,
            blueprint_name: "Synthetic Hull Blueprint".to_owned(),
            facility_id: None,
            facility_name: None,
            material_location_id: None,
            material_location_name: None,
            material_location_path: None,
            location_selection_state: "unselected".to_owned(),
            facility_material_bonus_basis_points: None,
            facility_time_bonus_basis_points: None,
            facility_tax_basis_points: None,
            facility_modifier_state: "not-selected".to_owned(),
            blueprint_item_id: Some(7_001),
            blueprint_assignment_state: "ready".to_owned(),
            blueprint_kind: Some("copy".to_owned()),
            blueprint_material_efficiency: Some(10),
            blueprint_time_efficiency: Some(20),
            blueprint_runs: Some(2),
            blueprint_location_id: Some(60_003_760),
            blueprint_location_flag: Some("Hangar".to_owned()),
            blueprint_snapshot_id: Some(12),
            blueprint_sync_run_id: Some(13),
            blueprint_observed_at: Some("2026-09-12T10:00:00Z".to_owned()),
            blueprint_candidate_count: 1,
            blueprint_candidates: vec![ProductionBlueprintCandidate {
                item_id: 7_001,
                kind: "copy".to_owned(),
                material_efficiency: 10,
                time_efficiency: 20,
                runs: 2,
                location_id: 60_003_760,
                location_flag: "Hangar".to_owned(),
                suitable: true,
                reason: "ready".to_owned(),
            }],
            applied_material_efficiency: 10,
            applied_time_efficiency: 20,
            activity: "manufacturing".to_owned(),
            product_type_id: 101,
            product_name: "Synthetic Hull".to_owned(),
            target_quantity: 2,
            priority: 10,
            note: Some("Main line".to_owned()),
            state: "ready".to_owned(),
            build_number: Some("synthetic-production-1".to_owned()),
            steps: vec![
                ProductionStep {
                    sequence: 1,
                    blueprint_type_id: 110,
                    blueprint_name: "Synthetic Frame Blueprint".to_owned(),
                    activity: "manufacturing".to_owned(),
                    product_type_id: 111,
                    product_name: "Synthetic Frame".to_owned(),
                    required_quantity: 2,
                    supply_mode: "stock-first".to_owned(),
                    stock_used_quantity: 0,
                    output_quantity_per_run: 2,
                    runs: 1,
                    unmodified_runs: 1,
                    runs_saved_by_material_efficiency: 0,
                    produced_quantity: 2,
                    surplus_quantity: 0,
                    base_time_seconds_per_run: 20,
                    total_base_time_seconds: 20,
                    time_efficiency: 0,
                    time_efficiency_applied: false,
                    total_blueprint_time_seconds: 20,
                    time_efficiency_savings_seconds: 0,
                    time_skills: vec![
                        ProductionTimeSkill {
                            skill_id: INDUSTRY_SKILL_ID,
                            skill_name: "Industry".to_owned(),
                            active_level: Some(5),
                            percent_per_level: 4,
                        },
                        ProductionTimeSkill {
                            skill_id: ADVANCED_INDUSTRY_SKILL_ID,
                            skill_name: "Advanced Industry".to_owned(),
                            active_level: Some(5),
                            percent_per_level: 3,
                        },
                    ],
                    character_skill_time_applied: true,
                    total_character_time_seconds: Some(14),
                    character_skill_time_savings_seconds: Some(6),
                    facility_modifier_state: "not-selected".to_owned(),
                    facility_material_bonus_basis_points: None,
                    facility_time_bonus_basis_points: None,
                    total_facility_time_seconds: None,
                    facility_time_savings_seconds: None,
                    recipe_alternatives: 1,
                    material_efficiency: 0,
                    material_efficiency_applied: false,
                    blueprint_assignment: super::ProductionStepBlueprintAssignment {
                        blueprint_assignment_state: "unassigned".to_owned(),
                        blueprint_item_id: None,
                        blueprint_kind: None,
                        blueprint_material_efficiency: None,
                        blueprint_time_efficiency: None,
                        blueprint_runs: None,
                        blueprint_location_id: None,
                        blueprint_location_flag: None,
                        blueprint_snapshot_id: Some(12),
                        blueprint_sync_run_id: Some(13),
                        blueprint_observed_at: Some("2026-09-12T10:00:00Z".to_owned()),
                        blueprint_candidate_count: 0,
                        blueprint_candidates: Vec::new(),
                    },
                    facility_evidence: missing_production_facility_evidence(),
                    installation_cost: unselected_production_installation_cost(),
                    materials: vec![ProductionStepMaterial {
                        type_id: 900,
                        type_name: "Synthetic Mineral".to_owned(),
                        quantity_per_run: 3,
                        unmodified_gross_quantity: 3,
                        gross_quantity: 3,
                        material_efficiency: 0,
                        material_efficiency_savings: 0,
                        produced_by_plan: false,
                    }],
                },
                ProductionStep {
                    sequence: 2,
                    blueprint_type_id: 100,
                    blueprint_name: "Synthetic Hull Blueprint".to_owned(),
                    activity: "manufacturing".to_owned(),
                    product_type_id: 101,
                    product_name: "Synthetic Hull".to_owned(),
                    required_quantity: 2,
                    supply_mode: "build".to_owned(),
                    stock_used_quantity: 0,
                    output_quantity_per_run: 1,
                    runs: 2,
                    unmodified_runs: 2,
                    runs_saved_by_material_efficiency: 0,
                    produced_quantity: 2,
                    surplus_quantity: 0,
                    base_time_seconds_per_run: 100,
                    total_base_time_seconds: 200,
                    time_efficiency: 20,
                    time_efficiency_applied: true,
                    total_blueprint_time_seconds: 160,
                    time_efficiency_savings_seconds: 40,
                    time_skills: vec![
                        ProductionTimeSkill {
                            skill_id: INDUSTRY_SKILL_ID,
                            skill_name: "Industry".to_owned(),
                            active_level: Some(5),
                            percent_per_level: 4,
                        },
                        ProductionTimeSkill {
                            skill_id: ADVANCED_INDUSTRY_SKILL_ID,
                            skill_name: "Advanced Industry".to_owned(),
                            active_level: Some(5),
                            percent_per_level: 3,
                        },
                    ],
                    character_skill_time_applied: true,
                    total_character_time_seconds: Some(109),
                    character_skill_time_savings_seconds: Some(51),
                    facility_modifier_state: "not-selected".to_owned(),
                    facility_material_bonus_basis_points: None,
                    facility_time_bonus_basis_points: None,
                    total_facility_time_seconds: None,
                    facility_time_savings_seconds: None,
                    recipe_alternatives: 1,
                    material_efficiency: 10,
                    material_efficiency_applied: true,
                    blueprint_assignment: super::ProductionStepBlueprintAssignment {
                        blueprint_assignment_state: "ready".to_owned(),
                        blueprint_item_id: Some(7_001),
                        blueprint_kind: Some("copy".to_owned()),
                        blueprint_material_efficiency: Some(10),
                        blueprint_time_efficiency: Some(20),
                        blueprint_runs: Some(2),
                        blueprint_location_id: Some(60_003_760),
                        blueprint_location_flag: Some("Hangar".to_owned()),
                        blueprint_snapshot_id: Some(12),
                        blueprint_sync_run_id: Some(13),
                        blueprint_observed_at: Some("2026-09-12T10:00:00Z".to_owned()),
                        blueprint_candidate_count: 1,
                        blueprint_candidates: vec![ProductionBlueprintCandidate {
                            item_id: 7_001,
                            kind: "copy".to_owned(),
                            material_efficiency: 10,
                            time_efficiency: 20,
                            runs: 2,
                            location_id: 60_003_760,
                            location_flag: "Hangar".to_owned(),
                            suitable: true,
                            reason: "ready".to_owned(),
                        }],
                    },
                    facility_evidence: missing_production_facility_evidence(),
                    installation_cost: unselected_production_installation_cost(),
                    materials: vec![ProductionStepMaterial {
                        type_id: 111,
                        type_name: "Synthetic Frame".to_owned(),
                        quantity_per_run: 1,
                        unmodified_gross_quantity: 2,
                        gross_quantity: 2,
                        material_efficiency: 10,
                        material_efficiency_savings: 0,
                        produced_by_plan: true,
                    }],
                },
            ],
            supply_decisions: vec![ProductionSupplyDecision {
                blueprint_type_id: 110,
                activity: "manufacturing".to_owned(),
                product_type_id: 111,
                product_name: "Synthetic Frame".to_owned(),
                supply_mode: "stock-first".to_owned(),
                required_quantity: 2,
                stock_available_quantity: 0,
                stock_used_quantity: 0,
                build_quantity: 2,
                shortage_quantity: 0,
                blueprint_required: true,
            }],
            gross_materials: vec![ProductionGrossMaterial {
                type_id: 900,
                type_name: "Synthetic Mineral".to_owned(),
                quantity: 3,
                unmodified_quantity: 3,
                material_efficiency_savings: 0,
                availability_state: "snapshot-missing".to_owned(),
                available_quantity: None,
                reserved_quantity: None,
                reserved_by_prior_plans_quantity: None,
                remaining_quantity: None,
                inventory_shortage_quantity: None,
                reservation_conflict_quantity: None,
                missing_quantity: None,
                prior_reservation_count: 0,
                prior_reservations: Vec::new(),
                available_position_count: 0,
                available_location_count: 0,
                available_locations: Vec::new(),
                excluded_quantity: 0,
                excluded_position_count: 0,
                excluded_location_count: 0,
                excluded_locations: Vec::new(),
            }],
            warnings: Vec::new(),
            cycle_type_ids: Vec::new(),
            total_base_time_seconds: Some(220),
            total_blueprint_time_seconds: Some(180),
            time_efficiency_savings_seconds: Some(40),
            total_character_time_seconds: Some(123),
            character_skill_time_savings_seconds: Some(57),
            total_facility_time_seconds: None,
            facility_time_savings_seconds: None,
            installation_cost_state: "unavailable".to_owned(),
            estimated_item_value: None,
            system_cost: None,
            facility_tax: None,
            scc_surcharge: None,
            estimated_installation_cost: None,
            costed_step_count: 0,
            uncosted_step_count: 2,
            character_skill_state: "ready".to_owned(),
            skill_snapshot_id: Some(14),
            skill_sync_run_id: Some(15),
            skill_observed_at: Some("2026-09-12T10:01:00Z".to_owned()),
            facility_state: "missing".to_owned(),
            inventory_state: "snapshot-missing".to_owned(),
            asset_snapshot_id: None,
            asset_sync_run_id: None,
            asset_observed_at: None,
            created_at: "2026-09-12T10:00:00Z".to_owned(),
            updated_at: "2026-09-12T10:00:00Z".to_owned(),
        };

        assert!(production_plan_record_is_valid(&plan));

        plan.steps[0].facility_evidence = ProductionFacilityEvidence {
            state: "ready".to_owned(),
            evidence: "active-blueprint-type-job".to_owned(),
            job_id: Some(9_001),
            job_status: Some("active".to_owned()),
            facility_id: Some(60_003_760),
            facility_name: Some("Synthetic Station".to_owned()),
            facility_kind: Some("station".to_owned()),
            facility_access: Some("public".to_owned()),
            solar_system_id: Some(30_000_142),
            solar_system_name: Some("Synthetic System".to_owned()),
            security_status: Some(0.9),
            security_class: Some("highsec".to_owned()),
            system_cost_index: Some(0.0125),
            job_snapshot_id: Some(16),
            job_sync_run_id: Some(17),
            job_observed_at: Some("2026-09-12T10:02:00Z".to_owned()),
            facility_snapshot_id: Some(18),
            facility_sync_run_id: Some(19),
            facility_observed_at: Some("2026-09-12T10:03:00Z".to_owned()),
        };
        plan.facility_state = "partial".to_owned();
        assert!(production_plan_record_is_valid(&plan));
        plan.steps[0].facility_evidence.facility_access = Some("restricted".to_owned());
        assert!(!production_plan_record_is_valid(&plan));
        plan.steps[0].facility_evidence.facility_access = Some("public".to_owned());

        plan.inventory_state = "covered".to_owned();
        plan.asset_snapshot_id = Some(8);
        plan.asset_sync_run_id = Some(9);
        plan.asset_observed_at = Some("2026-09-12T10:05:00Z".to_owned());
        let material = &mut plan.gross_materials[0];
        material.availability_state = "covered".to_owned();
        material.available_quantity = Some(100);
        material.reserved_quantity = Some(3);
        material.reserved_by_prior_plans_quantity = Some(60);
        material.remaining_quantity = Some(37);
        material.inventory_shortage_quantity = Some(0);
        material.reservation_conflict_quantity = Some(0);
        material.missing_quantity = Some(0);
        material.prior_reservation_count = 1;
        material.prior_reservations = vec![ProductionReservationClaim {
            plan_id: 2,
            product_type_id: 201,
            product_name: "Synthetic Composite".to_owned(),
            priority: 11,
            quantity: 60,
            created_at: "2026-09-12T09:00:00Z".to_owned(),
        }];
        assert!(production_plan_record_is_valid(&plan));

        plan.gross_materials[0].reserved_quantity = Some(4);
        assert!(!production_plan_record_is_valid(&plan));
        plan.gross_materials[0].reserved_quantity = Some(3);

        plan.steps.reverse();
        for (index, step) in plan.steps.iter_mut().enumerate() {
            step.sequence = index as u64 + 1;
        }
        assert!(!production_plan_record_is_valid(&plan));
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
