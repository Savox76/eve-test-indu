import { describe, expect, it, vi } from "vitest";

import {
  loadDesktopRuntimeStatus,
  setDesktopUpdateChannel,
  type RuntimeAdapter,
} from "./runtime";

const emptyData = {
  state: "empty",
  hasCachedData: false,
  observedAt: null,
  expiresAt: null,
  ageSeconds: null,
  lastSyncStatus: "never",
  errorCode: null,
} as const;

function nativeStatus(overrides: Record<string, unknown> = {}) {
  return JSON.stringify({
    state: "ready",
    version: "0.0.4-preview.1",
    desktopShell: true,
    singleInstance: true,
    sidecar: "ready",
    database: "ready",
    databaseLocation: "data/foundry.sqlite3",
    schemaVersion: 5,
    errorCode: null,
    data: emptyData,
    updater: {
      channel: "stable",
      manifestState: "verified",
      publicDistribution: false,
    },
    ...overrides,
  });
}

describe("desktop runtime status", () => {
  it("identifies the browser build as a design preview", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>();

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => false, invoke }),
    ).resolves.toEqual({ state: "preview" });
    expect(invoke).not.toHaveBeenCalled();
  });

  it("accepts an empty cache from the native Tauri shell", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(nativeStatus());

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => true, invoke }),
    ).resolves.toEqual({
      state: "ready",
      version: "0.0.4-preview.1",
      desktopShell: true,
      singleInstance: true,
      sidecar: "ready",
      database: "ready",
      databaseLocation: "data/foundry.sqlite3",
      schemaVersion: 5,
      errorCode: null,
      data: emptyData,
      updater: {
        channel: "stable",
        manifestState: "verified",
        publicDistribution: false,
      },
    });
    expect(invoke).toHaveBeenCalledWith("desktop_runtime_status");
  });

  it("accepts a stale cache that remains available after expiry", async () => {
    const data = {
      state: "stale",
      hasCachedData: true,
      observedAt: "2026-09-09T08:00:00Z",
      expiresAt: "2026-09-09T08:05:00Z",
      ageSeconds: 7_200,
      lastSyncStatus: "completed",
      errorCode: null,
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(nativeStatus({ data }));

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => true, invoke }),
    ).resolves.toMatchObject({ state: "ready", data });
  });

  it("accepts offline state while retaining verified cache metadata", async () => {
    const data = {
      state: "offline",
      hasCachedData: true,
      observedAt: "2026-09-09T08:00:00Z",
      expiresAt: "2026-09-09T08:05:00Z",
      ageSeconds: 7_200,
      lastSyncStatus: "failed",
      errorCode: "network-unavailable",
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(nativeStatus({ data }));

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => true, invoke }),
    ).resolves.toMatchObject({ state: "ready", data });
  });

  it("accepts the bounded native startup state", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(
      nativeStatus({
        sidecar: "starting",
        database: "starting",
        schemaVersion: null,
        data: { ...emptyData, state: "loading" },
        updater: {
          channel: "stable",
          manifestState: "checking",
          publicDistribution: false,
        },
      }),
    );

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => true, invoke }),
    ).resolves.toMatchObject({ state: "ready", sidecar: "starting", data: { state: "loading" } });
  });

  it("accepts a sanitized native failure without exposing local paths", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(
      nativeStatus({
        sidecar: "error",
        database: "error",
        schemaVersion: null,
        errorCode: "program-storage-unavailable",
        data: {
          ...emptyData,
          state: "error",
          errorCode: "program-storage-unavailable",
        },
        updater: {
          channel: "stable",
          manifestState: "unavailable",
          publicDistribution: false,
        },
      }),
    );

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => true, invoke }),
    ).resolves.toMatchObject({
      state: "ready",
      sidecar: "error",
      errorCode: "program-storage-unavailable",
    });
  });

  it("reports an unavailable core when native IPC fails", async () => {
    const invoke = vi
      .fn<RuntimeAdapter["invoke"]>()
      .mockRejectedValue(new Error("synthetic IPC failure"));

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => true, invoke }),
    ).resolves.toEqual({ state: "unavailable" });
  });

  it("reports an unavailable core when native IPC is malformed", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue("{}");

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => true, invoke }),
    ).resolves.toEqual({ state: "unavailable" });
  });

  it("rejects inconsistent component states", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(
      nativeStatus({ database: "starting" }),
    );

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => true, invoke }),
    ).resolves.toEqual({ state: "unavailable" });
  });

  it("rejects a fresh state without cache metadata", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(
      nativeStatus({ data: { ...emptyData, state: "fresh" } }),
    );

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => true, invoke }),
    ).resolves.toEqual({ state: "unavailable" });
  });

  it("stores a selected update channel through native IPC", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(
      JSON.stringify({
        channel: "beta",
        manifestState: "verified",
        publicDistribution: false,
      }),
    );

    await expect(
      setDesktopUpdateChannel("beta", { isAvailable: () => true, invoke }),
    ).resolves.toEqual({
      channel: "beta",
      manifestState: "verified",
      publicDistribution: false,
    });
    expect(invoke).toHaveBeenCalledWith("set_update_channel", { channel: "beta" });
  });

  it("rejects updater responses that enable public distribution", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(
      JSON.stringify({
        channel: "preview",
        manifestState: "verified",
        publicDistribution: true,
      }),
    );

    await expect(
      setDesktopUpdateChannel("preview", { isAvailable: () => true, invoke }),
    ).rejects.toThrow("invalid updater metadata");
  });
});
