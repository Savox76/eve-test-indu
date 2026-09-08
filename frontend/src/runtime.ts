import { invoke, isTauri } from "@tauri-apps/api/core";

export type DesktopRuntimeStatus =
  | { state: "checking" }
  | { state: "preview" }
  | { state: "unavailable" }
  | {
      state: "ready";
      version: string;
      desktopShell: true;
      sidecar: "pending";
      database: "foundation";
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
    !("sidecar" in candidate) ||
    candidate.sidecar !== "pending" ||
    !("database" in candidate) ||
    candidate.database !== "foundation"
  ) {
    throw new Error("The native runtime returned an invalid status payload.");
  }

  return {
    state: "ready",
    version: candidate.version,
    desktopShell: true,
    sidecar: "pending",
    database: "foundation",
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
