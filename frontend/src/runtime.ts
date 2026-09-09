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

export interface EveCharacter extends EveCharacterIdentity {
  accountGroupId: number | null;
  accountGroupLabel: string | null;
  enabled: boolean;
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
    (candidate.accountGroupId !== null &&
      (!Number.isSafeInteger(candidate.accountGroupId) || Number(candidate.accountGroupId) <= 0)) ||
    !isNullableText(candidate.accountGroupLabel) ||
    typeof candidate.enabled !== "boolean"
  ) {
    throw new Error("The native runtime returned invalid EVE character metadata.");
  }
  return { ...candidate, ...identity } as unknown as EveCharacter;
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
