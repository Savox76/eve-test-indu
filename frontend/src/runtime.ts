import { invoke, isTauri } from "@tauri-apps/api/core";

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
    };

export interface RuntimeAdapter {
  isAvailable: () => boolean;
  invoke: (command: string) => Promise<string>;
}

const tauriAdapter: RuntimeAdapter = {
  isAvailable: isTauri,
  invoke: (command) => invoke<string>(command),
};

export const initialRuntimeStatus: DesktopRuntimeStatus = { state: "checking" };

function parseReadyStatus(rawStatus: string): DesktopRuntimeStatus {
  const candidate: unknown = JSON.parse(rawStatus);
  if (
    typeof candidate !== "object" ||
    candidate === null ||
    !("state" in candidate) ||
    candidate.state !== "ready" ||
    !("version" in candidate) ||
    typeof candidate.version !== "string" ||
    candidate.version.trim().length === 0 ||
    !("desktopShell" in candidate) ||
    candidate.desktopShell !== true ||
    !("singleInstance" in candidate) ||
    candidate.singleInstance !== true ||
    !("sidecar" in candidate) ||
    !["starting", "ready", "error"].includes(String(candidate.sidecar)) ||
    !("database" in candidate) ||
    !["starting", "ready", "error"].includes(String(candidate.database)) ||
    !("databaseLocation" in candidate) ||
    candidate.databaseLocation !== "data/foundry.sqlite3" ||
    !("schemaVersion" in candidate) ||
    (candidate.schemaVersion !== null &&
      (!Number.isInteger(candidate.schemaVersion) || Number(candidate.schemaVersion) < 1)) ||
    !("errorCode" in candidate) ||
    (candidate.errorCode !== null &&
      (typeof candidate.errorCode !== "string" || candidate.errorCode.trim().length === 0))
  ) {
    throw new Error("The native runtime returned an invalid status payload.");
  }

  const sidecar = candidate.sidecar as "starting" | "ready" | "error";
  const database = candidate.database as "starting" | "ready" | "error";
  const schemaVersion = candidate.schemaVersion as number | null;
  const errorCode = candidate.errorCode as string | null;
  const hasValidStateCombination =
    (sidecar === "starting" &&
      database === "starting" &&
      schemaVersion === null &&
      errorCode === null) ||
    (sidecar === "ready" &&
      database === "ready" &&
      schemaVersion !== null &&
      errorCode === null) ||
    (sidecar === "error" &&
      database === "error" &&
      schemaVersion === null &&
      errorCode !== null);
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
