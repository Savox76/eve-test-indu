import { describe, expect, it, vi } from "vitest";

import { loadDesktopRuntimeStatus, type RuntimeAdapter } from "./runtime";

describe("desktop runtime status", () => {
  it("identifies the browser build as a design preview", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>();

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => false, invoke }),
    ).resolves.toEqual({ state: "preview" });
    expect(invoke).not.toHaveBeenCalled();
  });

  it("accepts the versioned status from the native Tauri shell", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(
      JSON.stringify({
        state: "ready",
        version: "0.0.3-preview.2",
        desktopShell: true,
        singleInstance: true,
        sidecar: "ready",
        database: "ready",
        databaseLocation: "data/foundry.sqlite3",
        schemaVersion: 3,
        errorCode: null,
      }),
    );

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => true, invoke }),
    ).resolves.toEqual({
      state: "ready",
      version: "0.0.3-preview.2",
      desktopShell: true,
      singleInstance: true,
      sidecar: "ready",
      database: "ready",
      databaseLocation: "data/foundry.sqlite3",
      schemaVersion: 3,
      errorCode: null,
    });
    expect(invoke).toHaveBeenCalledWith("desktop_runtime_status");
  });

  it("accepts the bounded native startup state", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(
      JSON.stringify({
        state: "ready",
        version: "0.0.3-preview.2",
        desktopShell: true,
        singleInstance: true,
        sidecar: "starting",
        database: "starting",
        databaseLocation: "data/foundry.sqlite3",
        schemaVersion: null,
        errorCode: null,
      }),
    );

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => true, invoke }),
    ).resolves.toMatchObject({ state: "ready", sidecar: "starting" });
  });

  it("accepts a sanitized native failure without exposing local paths", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(
      JSON.stringify({
        state: "ready",
        version: "0.0.3-preview.2",
        desktopShell: true,
        singleInstance: true,
        sidecar: "error",
        database: "error",
        databaseLocation: "data/foundry.sqlite3",
        schemaVersion: null,
        errorCode: "program-storage-unavailable",
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
      JSON.stringify({
        state: "ready",
        version: "0.0.3-preview.2",
        desktopShell: true,
        singleInstance: true,
        sidecar: "ready",
        database: "starting",
        databaseLocation: "data/foundry.sqlite3",
        schemaVersion: 3,
        errorCode: null,
      }),
    );

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => true, invoke }),
    ).resolves.toEqual({ state: "unavailable" });
  });
});
