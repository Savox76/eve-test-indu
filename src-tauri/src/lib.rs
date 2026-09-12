Warning: truncated output (original token count: 58364)
Total output lines: 6410

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
            .is_none_or(|val…18364 tokens truncated…IPT_MAX_SAFE_INTEGER
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
        account_group_record_is_valid, asset_delta_response_is_valid,
        asset_export_response_is_valid, asset_query_response_is_valid, authorization_url_is_valid,
        character_skill_query_response_is_valid, character_skill_sync_response_is_valid,
        eve_character_record_is_valid, industry_job_query_response_is_valid,
        industry_job_sync_response_is_valid, industry_slot_query_response_is_valid,
        migrate_to_program_directory_storage, read_window_size, release_page_url,
        research_plan_query_response_is_valid, sidecar_startup_error_code,
        sidecar_startup_error_is_retryable, sso_login_status_is_valid, write_window_size,
        AccountGroupRecord, AssetDeltaCorrelation, AssetDeltaQueryResponse, AssetDeltaRecord,
        AssetDeltaSummary, AssetExportResponse, AssetLocationNode, AssetOwner, AssetQueryResponse,
        AssetRecord, CharacterSkillQueryResponse, CharacterSkillRecord,
        CharacterSkillSyncCharacterResponse, CharacterSkillSyncResponse, EveCharacterRecord,
        IndustryAssetCorrelation, IndustryBlueprintCorrelation, IndustryJobQueryResponse,
        IndustryJobRecord, IndustryJobSyncCharacterResponse, IndustryJobSyncResponse,
        IndustrySlotActivity, IndustrySlotQueryResponse, IndustrySlotRecord, ResearchPlanOwner,
        ResearchPlanQueryResponse, ResearchPlanRecord, ResearchPlanSummary, RuntimeDataSnapshot,
        ScopePackageStatus, SsoCharacterIdentity, SsoLoginStatus, WindowSizePreference,
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
    fn validates_multi_step_production_goal_at_end_of_execution_order() {
        let mut plan = ProductionPlanRecord {
            plan_id: 1,
            owner_character_id: 90_888_001,
            owner_name: "Builder".to_owned(),
            blueprint_type_id: 100,
            blueprint_name: "Synthetic Hull Blueprint".to_owned(),
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
                    output_quantity_per_run: 2,
                    runs: 1,
                    produced_quantity: 2,
                    surplus_quantity: 0,
                    base_time_seconds_per_run: 20,
                    total_base_time_seconds: 20,
                    recipe_alternatives: 1,
                    materials: vec![ProductionStepMaterial {
                        type_id: 900,
                        type_name: "Synthetic Mineral".to_owned(),
                        quantity_per_run: 3,
                        gross_quantity: 3,
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
                    output_quantity_per_run: 1,
                    runs: 2,
                    produced_quantity: 2,
                    surplus_quantity: 0,
                    base_time_seconds_per_run: 100,
                    total_base_time_seconds: 200,
                    recipe_alternatives: 1,
                    materials: vec![ProductionStepMaterial {
                        type_id: 111,
                        type_name: "Synthetic Frame".to_owned(),
                        quantity_per_run: 1,
                        gross_quantity: 2,
                        produced_by_plan: true,
                    }],
                },
            ],
            gross_materials: vec![ProductionGrossMaterial {
                type_id: 900,
                type_name: "Synthetic Mineral".to_owned(),
                quantity: 3,
            }],
            warnings: Vec::new(),
            cycle_type_ids: Vec::new(),
            total_base_time_seconds: Some(220),
            created_at: "2026-09-12T10:00:00Z".to_owned(),
            updated_at: "2026-09-12T10:00:00Z".to_owned(),
        };

        assert!(production_plan_record_is_valid(&plan));

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
