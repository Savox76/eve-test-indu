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
        version: "0.0.2-preview.1",
        desktopShell: true,
        sidecar: "pending",
        database: "foundation",
      }),
    );

    await expect(
      loadDesktopRuntimeStatus({ isAvailable: () => true, invoke }),
    ).resolves.toEqual({
      state: "ready",
      version: "0.0.2-preview.1",
      desktopShell: true,
      sidecar: "pending",
      database: "foundation",
    });
    expect(invoke).toHaveBeenCalledWith("desktop_runtime_status");
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
});
