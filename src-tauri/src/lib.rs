use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{Ipv4Addr, SocketAddrV4, TcpStream};
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
const SIDECAR_REQUEST_TIMEOUT: Duration = Duration::from_secs(3);
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
struct AssetExportResponse {
    filename: String,
    relative_path: String,
    rows: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetDeltaCorrelation {
    state: String,
    key: String,
    direction: String,
    window_start: String,
    window_end: String,
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
        "fresh" => data.has_cached_data && data.age_seconds.is_some() && data.expires_at.is_some(),
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
                && event.job_correlation.state == "unmatched"
                && event.job_correlation.key
                    == format!("{}:{}", event.owner_character_id, event.type_id)
                && ["inbound", "outbound", "neutral"]
                    .contains(&event.job_correlation.direction.as_str())
                && event.job_correlation.direction == expected_direction
                && asset_text_is_valid(&event.job_correlation.window_start, 64)
                && asset_text_is_valid(&event.job_correlation.window_end, 64)
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

fn open_system_browser(url: &str) -> Result<(), &'static str> {
    if !authorization_url_is_valid(url) {
        return Err("sso-authorization-url-invalid");
    }

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
    let program_directory = std::env::current_exe()
        .map_err(|_| "program-directory-unavailable")?
        .parent()
        .ok_or("program-directory-unavailable")?
        .to_path_buf();
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
        let ready: SidecarReady =
            serde_json::from_str(&readiness_line).map_err(|_| "sidecar-ready-invalid")?;
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
        }
        Err(error_code) => state.set_snapshot(RuntimeSnapshot::failed(error_code)),
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
        if let Some(stdin) = process.child.stdin.as_mut() {
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
    let address = SocketAddrV4::new(Ipv4Addr::LOCALHOST, process.port);
    let mut stream = TcpStream::connect_timeout(&address.into(), SIDECAR_REQUEST_TIMEOUT)
        .map_err(|_| "sidecar-request-failed")?;
    stream
        .set_read_timeout(Some(SIDECAR_REQUEST_TIMEOUT))
        .and_then(|_| stream.set_write_timeout(Some(SIDECAR_REQUEST_TIMEOUT)))
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
fn query_assets(
    search: String,
    owner_character_id: Option<u64>,
    location_status: Option<String>,
    offset: u64,
    limit: u64,
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
fn export_assets_csv(
    search: String,
    owner_character_id: Option<u64>,
    location_status: Option<String>,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    if search.chars().count() > MAX_ASSET_SEARCH_CHARACTERS
        || search.trim() != search
        || owner_character_id == Some(0)
        || owner_character_id.is_some_and(|value| value > JAVASCRIPT_MAX_SAFE_INTEGER)
        || location_status
            .as_deref()
            .is_some_and(|status| !ASSET_LOCATION_STATUSES.contains(&status))
    {
        return Err("asset-query-invalid".to_owned());
    }
    refresh_sidecar_status(&state);
    let body = serde_json::json!({
        "search": search,
        "ownerCharacterId": owner_character_id,
        "locationStatus": location_status,
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
    if scope_packages.is_empty()
        || scope_packages
            .iter()
            .any(|package| !EVE_SSO_SCOPE_PACKAGES.contains(&package.as_str()))
        || scope_packages.iter().collect::<HashSet<_>>().len() != scope_packages.len()
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
        r#"{"state":"ready","version":"unknown","desktopShell":true,"singleInstance":true,"sidecar":"error","database":"error","databaseLocation":"data/foundry.sqlite3","schemaVersion":null,"errorCode":"status-serialization-failed","data":{"state":"error","hasCachedData":false,"observedAt":null,"expiresAt":null,"ageSeconds":null,"lastSyncStatus":"never","errorCode":"status-serialization-failed"},"updater":{"channel":"stable","manifestState":"unavailable","publicDistribution":false},"appearance":{"fontScale":"normal"}}"#.to_owned()
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
            thread::spawn(move || start_sidecar(app_handle));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            desktop_runtime_status,
            set_update_channel,
            set_font_scale,
            list_eve_characters,
            list_account_groups,
            query_assets,
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
        eve_character_record_is_valid, sso_login_status_is_valid, AccountGroupRecord,
        AssetDeltaCorrelation, AssetDeltaQueryResponse, AssetDeltaRecord, AssetDeltaSummary,
        AssetExportResponse, AssetLocationNode, AssetOwner, AssetQueryResponse, AssetRecord,
        EveCharacterRecord, ScopePackageStatus, SsoCharacterIdentity, SsoLoginStatus,
    };

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
}
