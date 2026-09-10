import { describe, expect, it, vi } from "vitest";

import {
  cancelEveSso,
  createAccountGroup,
  deleteAccountGroup,
  deleteEveCharacter,
  loadAccountGroups,
  loadDesktopRuntimeStatus,
  loadEveCharacters,
  loadEveSsoStatus,
  renameAccountGroup,
  setDesktopFontScale,
  setDesktopUpdateChannel,
  startEveSso,
  updateEveCharacter,
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

const scopePackages = [
  { id: "industry-core", status: "partial", grantedCount: 1, requiredCount: 4 },
  { id: "market", status: "missing", grantedCount: 0, requiredCount: 2 },
  { id: "planetary-industry", status: "missing", grantedCount: 0, requiredCount: 1 },
  { id: "projects", status: "missing", grantedCount: 0, requiredCount: 1 },
  { id: "private-structures", status: "missing", grantedCount: 0, requiredCount: 1 },
] as const;

function managedCharacter(overrides: Record<string, unknown> = {}) {
  return {
    characterId: 2_112_345_678,
    name: "Synthetic Pilot",
    alias: null,
    accountGroupId: null,
    accountGroupLabel: null,
    enabled: true,
    credentialState: "stored",
    scopes: ["esi-assets.read_assets.v1"],
    scopePackages,
    ...overrides,
  };
}

function nativeStatus(overrides: Record<string, unknown> = {}) {
  return JSON.stringify({
    state: "ready",
    version: "0.0.5-preview.1",
    desktopShell: true,
    singleInstance: true,
    sidecar: "ready",
    database: "ready",
    databaseLocation: "data/foundry.sqlite3",
    schemaVersion: 6,
    errorCode: null,
    data: emptyData,
    updater: {
      channel: "stable",
      manifestState: "verified",
      publicDistribution: false,
    },
    appearance: { fontScale: "normal" },
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
      version: "0.0.5-preview.1",
      desktopShell: true,
      singleInstance: true,
      sidecar: "ready",
      database: "ready",
      databaseLocation: "data/foundry.sqlite3",
      schemaVersion: 6,
      errorCode: null,
      data: emptyData,
      updater: {
        channel: "stable",
        manifestState: "verified",
        publicDistribution: false,
      },
      appearance: { fontScale: "normal" },
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
      character: null,
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

  it("stores one of five global font-size stages through native IPC", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(
      JSON.stringify({ fontScale: "large" }),
    );

    await expect(
      setDesktopFontScale("large", { isAvailable: () => true, invoke }),
    ).resolves.toEqual({ fontScale: "large" });
    expect(invoke).toHaveBeenCalledWith("set_font_scale", { fontScale: "large" });
  });

  it("loads strictly validated persisted EVE characters", async () => {
    const payload = { characters: [managedCharacter()] };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(JSON.stringify(payload));

    await expect(
      loadEveCharacters({ isAvailable: () => true, invoke }),
    ).resolves.toEqual(payload.characters);
    expect(invoke).toHaveBeenCalledWith("list_eve_characters");
  });

  it("rejects duplicate or malformed persisted character identities", async () => {
    const character = managedCharacter();
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(
      JSON.stringify({ characters: [character, character] }),
    );

    await expect(
      loadEveCharacters({ isAvailable: () => true, invoke }),
    ).rejects.toThrow("duplicate EVE characters");
  });

  it("rejects incomplete or inconsistent scope package metadata", async () => {
    const incomplete = managedCharacter({ scopePackages: scopePackages.slice(0, 4) });
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(
      JSON.stringify({ characters: [incomplete] }),
    );
    await expect(
      loadEveCharacters({ isAvailable: () => true, invoke }),
    ).rejects.toThrow("invalid EVE character metadata");

    invoke.mockResolvedValueOnce(JSON.stringify({
      characters: [managedCharacter({
        scopePackages: scopePackages.map((entry) => entry.id === "market"
          ? { ...entry, status: "granted" }
          : entry),
      })],
    }));
    await expect(
      loadEveCharacters({ isAvailable: () => true, invoke }),
    ).rejects.toThrow("inconsistent scope-package metadata");
  });

  it("loads and validates account groups", async () => {
    const groups = [{ id: 3, label: "Industry", sortOrder: 0, characterCount: 2 }];
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(
      JSON.stringify({ groups }),
    );
    await expect(
      loadAccountGroups({ isAvailable: () => true, invoke }),
    ).resolves.toEqual(groups);
    expect(invoke).toHaveBeenCalledWith("list_account_groups");
  });

  it("updates and fully deletes one character through native IPC", async () => {
    const updated = managedCharacter({
      alias: "Builder",
      accountGroupId: 3,
      accountGroupLabel: "Industry",
      enabled: false,
    });
    const invoke = vi.fn<RuntimeAdapter["invoke"]>()
      .mockResolvedValueOnce(JSON.stringify({ character: updated }))
      .mockResolvedValueOnce(JSON.stringify({ deleted: true, characterId: 2_112_345_678 }));
    const adapter = { isAvailable: () => true, invoke };

    await expect(
      updateEveCharacter(
        2_112_345_678,
        { alias: "Builder", accountGroupId: 3, enabled: false },
        adapter,
      ),
    ).resolves.toEqual(updated);
    await expect(deleteEveCharacter(2_112_345_678, adapter)).resolves.toBeUndefined();
    expect(invoke).toHaveBeenNthCalledWith(1, "update_eve_character", {
      characterId: 2_112_345_678,
      alias: "Builder",
      accountGroupId: 3,
      enabled: false,
    });
    expect(invoke).toHaveBeenNthCalledWith(
      2,
      "delete_eve_character",
      { characterId: 2_112_345_678 },
    );
  });

  it("creates, renames and deletes account groups through native IPC", async () => {
    const created = { id: 3, label: "Industry", sortOrder: 0, characterCount: 0 };
    const renamed = { ...created, label: "Production" };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>()
      .mockResolvedValueOnce(JSON.stringify({ group: created }))
      .mockResolvedValueOnce(JSON.stringify({ group: renamed }))
      .mockResolvedValueOnce(JSON.stringify({ deleted: true, groupId: 3 }));
    const adapter = { isAvailable: () => true, invoke };

    await expect(createAccountGroup("Industry", adapter)).resolves.toEqual(created);
    await expect(renameAccountGroup(3, "Production", adapter)).resolves.toEqual(renamed);
    await expect(deleteAccountGroup(3, adapter)).resolves.toBeUndefined();
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

  it("starts a PKCE login with selected per-character scope packages", async () => {
    const status = {
      state: "waiting",
      attemptId: "opaque-attempt",
      scopePackages: ["industry-core", "market"],
      expiresAt: "2026-09-09T12:03:00Z",
      errorCode: null,
      character: null,
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(JSON.stringify(status));

    await expect(
      startEveSso(["industry-core", "market"], { isAvailable: () => true, invoke }),
    ).resolves.toEqual(status);
    expect(invoke).toHaveBeenCalledWith("start_eve_sso", {
      scopePackages: ["industry-core", "market"],
    });
  });

  it("polls and cancels an active PKCE login through native IPC", async () => {
    const waiting = JSON.stringify({
      state: "waiting",
      attemptId: "opaque-attempt",
      scopePackages: ["industry-core"],
      expiresAt: "2026-09-09T12:03:00Z",
      errorCode: null,
      character: null,
    });
    const cancelled = JSON.stringify({
      state: "cancelled",
      attemptId: "opaque-attempt",
      scopePackages: ["industry-core"],
      expiresAt: "2026-09-09T12:03:00Z",
      errorCode: null,
      character: null,
    });
    const invoke = vi.fn<RuntimeAdapter["invoke"]>()
      .mockResolvedValueOnce(waiting)
      .mockResolvedValueOnce(cancelled);
    const adapter = { isAvailable: () => true, invoke };

    await expect(loadEveSsoStatus(adapter)).resolves.toMatchObject({ state: "waiting" });
    await expect(cancelEveSso(adapter)).resolves.toMatchObject({ state: "cancelled" });
    expect(invoke).toHaveBeenNthCalledWith(1, "eve_sso_status", undefined);
    expect(invoke).toHaveBeenNthCalledWith(2, "cancel_eve_sso", undefined);
  });

  it("accepts only a fully verified connected-character status", async () => {
    const connected = {
      state: "connected",
      attemptId: "opaque-attempt",
      scopePackages: ["industry-core"],
      expiresAt: "2026-09-09T12:03:00Z",
      errorCode: null,
      character: {
        characterId: 2_112_345_678,
        name: "Synthetic Pilot",
        scopes: ["esi-assets.read_assets.v1"],
      },
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(JSON.stringify(connected));

    await expect(
      loadEveSsoStatus({ isAvailable: () => true, invoke }),
    ).resolves.toEqual(connected);
  });

  it("rejects malformed or secret-bearing-equivalent SSO state combinations", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(JSON.stringify({
      state: "waiting",
      attemptId: null,
      scopePackages: ["industry-core"],
      expiresAt: "2026-09-09T12:03:00Z",
      errorCode: null,
    }));

    await expect(
      loadEveSsoStatus({ isAvailable: () => true, invoke }),
    ).rejects.toThrow("invalid SSO metadata");
  });

  it("does not expose EVE SSO commands in browser preview mode", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>();

    await expect(
      startEveSso(["industry-core"], { isAvailable: () => false, invoke }),
    ).rejects.toThrow("desktop application");
    expect(invoke).not.toHaveBeenCalled();
  });
});
