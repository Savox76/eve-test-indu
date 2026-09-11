import { describe, expect, it, vi } from "vitest";

import {
  cancelEveSso,
  createAccountGroup,
  deleteAccountGroup,
  deleteEveCharacter,
  exportAssetsCsv,
  loadAccountGroups,
  loadAssetDeltas,
  loadAssets,
  loadBlueprints,
  loadCharacterSkills,
  loadDesktopRuntimeStatus,
  loadEveCharacters,
  loadEveSsoStatus,
  loadIndustryJobs,
  renameAccountGroup,
  setDesktopFontScale,
  setDesktopUpdateChannel,
  startEveSso,
  ssoScopePackages,
  syncAssets,
  syncBlueprints,
  syncCharacterSkills,
  syncIndustryJobs,
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
    version: "0.0.5-preview.8",
    desktopShell: true,
    singleInstance: true,
    sidecar: "ready",
    database: "ready",
    databaseLocation: "data/foundry.sqlite3",
    schemaVersion: 7,
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
      version: "0.0.5-preview.8",
      desktopShell: true,
      singleInstance: true,
      sidecar: "ready",
      database: "ready",
      databaseLocation: "data/foundry.sqlite3",
      schemaVersion: 7,
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

  it("loads one strictly bounded, joined asset page", async () => {
    const query = {
      search: "component",
      ownerCharacterId: 90_888_001,
      locationStatus: "resolved" as const,
      offset: 100,
      limit: 100,
      sortBy: "type" as const,
      sortDirection: "asc" as const,
    };
    const page = {
      items: [{
        itemId: 9_800_001,
        typeId: 98_001,
        typeName: "Synthetic Component",
        quantity: 17,
        ownerCharacterId: 90_888_001,
        ownerName: "Builder",
        locationFlag: "SyntheticHangar",
        locationStatus: "resolved",
        locationPath: "Synthetic System / Synthetic Station",
        locationNodes: [{
          locationId: 30_888_001,
          kind: "solar_system",
          name: "Synthetic System",
          access: "available",
          typeId: null,
        }],
        observedAt: "2026-09-10T10:00:00Z",
        ageSeconds: 3_600,
      }],
      total: 100_000,
      quantityTotal: 230_000,
      offset: 100,
      limit: 100,
      owners: [{ characterId: 90_888_001, name: "Builder" }],
      locationStatuses: ["resolved", "restricted", "unresolved", "cycle", "pending"],
      observedAt: "2026-09-10T10:00:00Z",
      ageSeconds: 3_600,
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(JSON.stringify(page));

    await expect(loadAssets(query, { isAvailable: () => true, invoke })).resolves.toEqual(page);
    expect(invoke).toHaveBeenCalledWith("query_assets", query);
  });

  it("rejects oversized or internally inconsistent asset pages", async () => {
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(JSON.stringify({
      items: [],
      total: 100_000,
      quantityTotal: 0,
      offset: 0,
      limit: 201,
      owners: [],
      locationStatuses: ["resolved", "restricted", "unresolved", "cycle", "pending"],
      observedAt: null,
      ageSeconds: null,
    }));

    await expect(loadAssets(
      {
        search: "",
        ownerCharacterId: null,
        locationStatus: null,
        offset: 0,
        limit: 200,
        sortBy: "type",
        sortDirection: "asc",
      },
      { isAvailable: () => true, invoke },
    )).rejects.toThrow("invalid asset page");
  });

  it("accepts only bounded and internally consistent asset-delta history", async () => {
    const query = {
      search: "synthetic input",
      ownerCharacterId: 90_888_001,
      changeType: "quantity" as const,
      offset: 0,
      limit: 50,
    };
    const page = {
      items: [{
        eventId: "a".repeat(64),
        itemId: 9_800_001,
        typeId: 98_001,
        typeName: "Synthetic Input",
        ownerCharacterId: 90_888_001,
        ownerName: "Builder",
        changeTypes: ["quantity"],
        quantityBefore: 17,
        quantityAfter: 9,
        quantityDelta: -8,
        locationIdBefore: 60_888_001,
        locationIdAfter: 60_888_001,
        locationTypeBefore: "station",
        locationTypeAfter: "station",
        locationFlagBefore: "SyntheticHangar",
        locationFlagAfter: "SyntheticHangar",
        previousAssetSnapshotId: 4,
        currentAssetSnapshotId: 6,
        currentAssetSyncRunId: 9,
        observedAt: "2026-09-10T11:00:00Z",
        ageSeconds: 60,
        jobCorrelation: {
          state: "unmatched",
          key: "90888001:98001",
          direction: "outbound",
          windowStart: "2026-09-10T10:00:00Z",
          windowEnd: "2026-09-10T11:00:00Z",
          jobIds: [],
          candidateCount: 0,
          locationMatched: false,
        },
      }],
      total: 1,
      offset: 0,
      limit: 50,
      owners: [{ characterId: 90_888_001, name: "Builder" }],
      changeTypes: ["added", "removed", "quantity", "location"],
      summary: { added: 0, removed: 0, quantity: 1, location: 0 },
      hasBaseline: true,
      observedAt: "2026-09-10T11:00:00Z",
      ageSeconds: 60,
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(JSON.stringify(page));

    await expect(loadAssetDeltas(query, { isAvailable: () => true, invoke }))
      .resolves.toEqual(page);
    expect(invoke).toHaveBeenCalledWith("query_asset_deltas", query);

    invoke.mockResolvedValueOnce(JSON.stringify({
      ...page,
      items: [{ ...page.items[0], quantityDelta: 8 }],
    }));
    await expect(loadAssetDeltas(query, { isAvailable: () => true, invoke }))
      .rejects.toThrow("inconsistent asset-delta metadata");
  });

  it("requests a filtered CSV and accepts only a safe program-relative path", async () => {
    const exported = {
      filename: "assets-20260910-110203.csv",
      relativePath: "data/exports/assets-20260910-110203.csv",
      rows: 100_000,
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(JSON.stringify(exported));
    const filters = {
      search: "component",
      ownerCharacterId: 90_888_001,
      locationStatus: "restricted" as const,
      sortBy: "type" as const,
      sortDirection: "asc" as const,
    };

    await expect(exportAssetsCsv(filters, { isAvailable: () => true, invoke }))
      .resolves.toEqual(exported);
    expect(invoke).toHaveBeenCalledWith("export_assets_csv", filters);

    invoke.mockResolvedValueOnce(JSON.stringify({
      ...exported,
      relativePath: "../../outside.csv",
    }));
    await expect(exportAssetsCsv(filters, { isAvailable: () => true, invoke }))
      .rejects.toThrow("invalid asset-export metadata");
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

  it("starts a PKCE login with every required scope package", async () => {
    const status = {
      state: "waiting",
      attemptId: "opaque-attempt",
      scopePackages: [...ssoScopePackages],
      expiresAt: "2026-09-09T12:03:00Z",
      errorCode: null,
      character: null,
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(JSON.stringify(status));

    await expect(
      startEveSso([...ssoScopePackages], { isAvailable: () => true, invoke }),
    ).resolves.toEqual(status);
    expect(invoke).toHaveBeenCalledWith("start_eve_sso", {
      scopePackages: [...ssoScopePackages],
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

  it("validates and returns a bounded asset-sync summary", async () => {
    const result = {
      characters: [{
        characterId: 2_112_345_678,
        status: "completed",
        pages: 2,
        assets: 120,
        resolved: 118,
        restricted: 2,
        unresolved: 0,
        cycles: 0,
        errorCode: null,
      }],
      completed: 1,
      failed: 0,
      assets: 120,
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(JSON.stringify(result));

    await expect(syncAssets({ isAvailable: () => true, invoke })).resolves.toEqual(result);
    expect(invoke).toHaveBeenCalledWith("sync_assets");
  });

  it("validates blueprint pages and sync summaries", async () => {
    const page = {
      items: [{ itemId: 9, typeId: 681, typeName: "Bantam Blueprint", ownerCharacterId: 7,
        ownerName: "Pilot", kind: "original", materialEfficiency: 10, timeEfficiency: 20,
        runs: -1, locationId: 60_003_760, locationFlag: "Hangar",
        observedAt: "2026-09-10T00:00:00Z", ageSeconds: 1 }],
      total: 1, offset: 0, limit: 100, owners: [{ characterId: 7, name: "Pilot" }],
      observedAt: "2026-09-10T00:00:00Z", ageSeconds: 1,
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValueOnce(JSON.stringify(page));
    await expect(loadBlueprints({ search: "", ownerCharacterId: null, kind: null, offset: 0,
      limit: 100, sortBy: "type", sortDirection: "asc" }, { isAvailable: () => true, invoke }))
      .resolves.toEqual(page);
    const result = { characters: [{ characterId: 7, status: "completed", pages: 1,
      blueprints: 1, errorCode: null }], completed: 1, failed: 0, blueprints: 1 };
    invoke.mockResolvedValueOnce(JSON.stringify(result));
    await expect(syncBlueprints({ isAvailable: () => true, invoke })).resolves.toEqual(result);
  });

  it("validates traceable industry-job pages and sync summaries", async () => {
    const page = {
      items: [{
        jobId: 8_001, ownerCharacterId: 7, ownerName: "Pilot", activityId: 1,
        activityKey: "manufacturing", status: "delivered", blueprintItemId: 9,
        blueprintTypeId: 681, blueprintName: "Bantam Blueprint", productTypeId: 582,
        productName: "Bantam", runs: 2, successfulRuns: 2, licensedRuns: 0,
        probability: 1, cost: 1234.5, durationSeconds: 3600, facilityId: 60_003_760,
        stationId: 60_003_760, blueprintLocationId: 60_003_760,
        outputLocationId: 60_003_760, startDate: "2026-09-10T10:00:00Z",
        endDate: "2026-09-10T11:00:00Z", completedDate: "2026-09-10T11:00:00Z",
        pauseDate: null, blueprintCorrelation: { state: "current", snapshotId: 2,
          syncRunId: 3, observedAt: "2026-09-10T11:01:00Z" },
        assetCorrelation: { state: "linked", eventIds: ["a".repeat(64)],
          candidateCount: 1, locationMatched: true }, correlationState: "linked",
        jobSnapshotId: 4, jobSyncRunId: 5, observedAt: "2026-09-10T11:02:00Z",
        ageSeconds: 60,
      }],
      total: 1, activeTotal: 0, offset: 0, limit: 100, owners: [{ characterId: 7, name: "Pilot" }],
      statuses: ["active", "cancelled", "delivered", "paused", "ready", "reverted"],
      activities: [1], correlations: ["linked", "partial", "ambiguous", "unmatched", "pending"],
      observedAt: "2026-09-10T11:02:00Z", ageSeconds: 60,
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValueOnce(JSON.stringify(page));
    const query = { search: "", ownerCharacterId: null, status: null, activityId: null,
      correlation: null, offset: 0, limit: 100, sortBy: "end", sortDirection: "desc" } as const;
    await expect(loadIndustryJobs(query, { isAvailable: () => true, invoke })).resolves.toEqual(page);
    expect(invoke).toHaveBeenCalledWith("query_industry_jobs", expect.objectContaining({ sortBy: "end" }));

    const result = { characters: [{ characterId: 7, status: "completed", jobs: 1,
      active: 0, completedJobs: 1, errorCode: null }], completed: 1, failed: 0,
      jobs: 1, active: 0, completedJobs: 1 };
    invoke.mockResolvedValueOnce(JSON.stringify(result));
    await expect(syncIndustryJobs({ isAvailable: () => true, invoke })).resolves.toEqual(result);
    expect(invoke).toHaveBeenLastCalledWith("sync_industry_jobs");
  });

  it("validates bounded character-skill pages and sync summaries", async () => {
    const page = {
      items: [{
        skillId: 33_550, skillName: "Industry", ownerCharacterId: 7,
        ownerName: "Pilot", trainedLevel: 5, activeLevel: 4,
        skillpoints: 512_000, activeState: "limited", snapshotId: 8,
        syncRunId: 9, observedAt: "2026-09-11T00:00:00Z", ageSeconds: 60,
      }],
      total: 1, totalSp: 512_000, unallocatedSp: 12_500,
      offset: 0, limit: 100, owners: [{ characterId: 7, name: "Pilot" }],
      levels: [0, 1, 2, 3, 4, 5], activeStates: ["normal", "limited", "boosted"],
      observedAt: "2026-09-11T00:00:00Z", ageSeconds: 60,
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValueOnce(JSON.stringify(page));
    const query = { search: "", ownerCharacterId: null, trainedLevel: null,
      activeState: null, offset: 0, limit: 100, sortBy: "skill", sortDirection: "asc" } as const;
    await expect(loadCharacterSkills(query, { isAvailable: () => true, invoke })).resolves.toEqual(page);
    expect(invoke).toHaveBeenCalledWith("query_character_skills", expect.objectContaining({ sortBy: "skill" }));

    const result = { characters: [{ characterId: 7, status: "completed", skills: 1,
      totalSp: 512_000, unallocatedSp: 12_500, errorCode: null }], completed: 1,
      failed: 0, skills: 1, totalSp: 512_000, unallocatedSp: 12_500 };
    invoke.mockResolvedValueOnce(JSON.stringify(result));
    await expect(syncCharacterSkills({ isAvailable: () => true, invoke })).resolves.toEqual(result);
    expect(invoke).toHaveBeenLastCalledWith("sync_character_skills");
  });
});
