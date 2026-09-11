import { describe, expect, it, vi } from "vitest";

import {
  cancelEveSso,
  checkForUpdates,
  createAccountGroup,
  deleteAccountGroup,
  deleteEveCharacter,
  deleteResearchPlan,
  deleteProductionPlan,
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
  loadIndustryFacilities,
  loadIndustrySlots,
  loadProductionCatalog,
  loadProductionPlans,
  loadResearchPlans,
  renameAccountGroup,
  openReleaseDownloads,
  saveProductionPlan,
  saveResearchPlan,
  setDesktopFontScale,
  setDesktopUpdateChannel,
  startEveSso,
  ssoScopePackages,
  syncAssets,
  syncBlueprints,
  syncCharacterSkills,
  syncIndustryJobs,
  syncIndustryFacilities,
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
    version: "0.0.5-preview.13",
    desktopShell: true,
    singleInstance: true,
    distribution: "installed",
    sidecar: "ready",
    database: "ready",
    databaseLocation: "data/foundry.sqlite3",
    schemaVersion: 9,
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
      version: "0.0.5-preview.13",
      desktopShell: true,
      singleInstance: true,
      distribution: "installed",
      sidecar: "ready",
      database: "ready",
      databaseLocation: "data/foundry.sqlite3",
      schemaVersion: 9,
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
        facilityName: "Jita IV - Moon 4", facilityKind: "station", facilityAccess: "public",
        solarSystemId: 30_000_142, solarSystemName: "Jita", systemCostIndex: 0.0125,
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

  it("validates facility pages, cost context, and sync summaries", async () => {
    const page = {
      items: [{
        facilityId: 60_003_760, facilityName: "Jita IV - Moon 4", kind: "station",
        access: "public", typeId: 1_928, typeName: "Amarr Station", ownerId: 1_000_001,
        ownerName: "Caldari Navy", regionId: 10_000_002, regionName: "The Forge",
        solarSystemId: 30_000_142, solarSystemName: "Jita", tax: null,
        activityCostIndex: 0.0125, usedByCharacterIds: [7], observedActivityIds: [1],
        jobCount: 1, activeJobs: 0, errorCode: null, snapshotId: 10, syncRunId: 11,
        observedAt: "2026-09-11T00:00:00Z", ageSeconds: 60,
      }],
      total: 1, npcFacilities: 1, observedFacilities: 0, restrictedStructures: 0,
      systems: 1, offset: 0, limit: 100, activity: "manufacturing",
      activities: ["manufacturing", "reaction", "copying", "invention",
        "researching_material_efficiency", "researching_time_efficiency"],
      kinds: ["station", "structure", "unknown"],
      accessStates: ["public", "available", "restricted", "scope-missing", "unknown"],
      observedAt: "2026-09-11T00:00:00Z", ageSeconds: 60,
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValueOnce(JSON.stringify(page));
    const query = { search: "Jita", kind: null, access: null, activity: "manufacturing",
      usedOnly: true, offset: 0, limit: 100, sortBy: "cost", sortDirection: "asc" } as const;
    await expect(loadIndustryFacilities(query, { isAvailable: () => true, invoke }))
      .resolves.toEqual(page);
    expect(invoke).toHaveBeenCalledWith("query_industry_facilities", expect.objectContaining({
      activity: "manufacturing", usedOnly: true,
    }));

    const result = { syncRunId: 12, facilities: 2, npcFacilities: 1,
      observedFacilities: 1, restrictedStructures: 1, systems: 1, resolvedNames: 7 };
    invoke.mockResolvedValueOnce(JSON.stringify(result));
    await expect(syncIndustryFacilities({ isAvailable: () => true, invoke })).resolves.toEqual(result);
    expect(invoke).toHaveBeenLastCalledWith("sync_industry_facilities");
  });

  it("validates character-separated industry-slot capacity and work queues", async () => {
    const activities = [{
      activity: "manufacturing", capacity: 7, occupied: 2, available: 5,
      utilizationState: "available", activeJobs: 1, pausedJobs: 0, readyJobs: 1,
      nextJobEndDate: "2026-09-11T12:00:00Z", primarySkillId: 3387,
      primarySkillLevel: 4, advancedSkillId: 24625, advancedSkillLevel: 2,
      queuedPlans: 2, blockedPlans: 0, runningPlans: 1, completePlans: 0,
      planningAvailable: true,
    }, {
      activity: "reactions", capacity: 5, occupied: 1, available: 4,
      utilizationState: "available", activeJobs: 1, pausedJobs: 0, readyJobs: 0,
      nextJobEndDate: "2026-09-11T13:00:00Z", primarySkillId: 45748,
      primarySkillLevel: 3, advancedSkillId: 45749, advancedSkillLevel: 1,
      queuedPlans: 1, blockedPlans: 1, runningPlans: 0, completePlans: 0,
      planningAvailable: true,
    }, {
      activity: "science", capacity: 6, occupied: 2, available: 4,
      utilizationState: "available", activeJobs: 2, pausedJobs: 0, readyJobs: 0,
      nextJobEndDate: "2026-09-11T14:00:00Z", primarySkillId: 3406,
      primarySkillLevel: 3, advancedSkillId: 24624, advancedSkillLevel: 2,
      queuedPlans: 1, blockedPlans: 1, runningPlans: 1, completePlans: 0,
      planningAvailable: true,
    }] as const;
    const page = {
      items: [{ characterId: 7, name: "Pilot", activities,
        skillSnapshotId: 2, skillSyncRunId: 3,
        skillObservedAt: "2026-09-11T11:00:00Z",
        jobSnapshotId: 4, jobSyncRunId: 5,
        jobObservedAt: "2026-09-11T11:01:00Z",
        observedAt: "2026-09-11T11:00:00Z", ageSeconds: 60 }],
      total: 1, offset: 0, limit: 50, owners: [{ characterId: 7, name: "Pilot" }],
      activities: ["manufacturing", "reactions", "science"],
      observedAt: "2026-09-11T11:00:00Z", ageSeconds: 60,
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValue(JSON.stringify(page));
    const query = { ownerCharacterId: null, offset: 0, limit: 50 } as const;

    await expect(loadIndustrySlots(query, { isAvailable: () => true, invoke }))
      .resolves.toEqual(page);
    expect(invoke).toHaveBeenCalledWith("query_industry_slots", {
      ownerCharacterId: null, offset: 0, limit: 50,
    });

    const malformed = JSON.parse(JSON.stringify(page)) as {
      items: Array<{ activities: Array<{ available: number | null }> }>;
    };
    malformed.items[0].activities[0].available = 6;
    invoke.mockResolvedValueOnce(JSON.stringify(malformed));
    await expect(loadIndustrySlots(query, { isAvailable: () => true, invoke }))
      .rejects.toThrow("inconsistent industry-slot capacity");
  });

  it("validates production catalogs, deterministic plans, and mutations", async () => {
    const catalog = {
      items: [{ blueprintTypeId: 100, blueprintName: "Synthetic Hull Blueprint",
        activity: "manufacturing", baseTimeSeconds: 100, productTypeId: 101,
        productName: "Synthetic Hull", outputQuantity: 2, materialCount: 1 }],
      total: 1, offset: 0, limit: 50, activities: ["manufacturing", "reaction"],
      buildNumber: "synthetic-production-1",
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValueOnce(JSON.stringify(catalog));
    const catalogQuery = { search: "Hull", activity: null, offset: 0, limit: 50 } as const;
    await expect(loadProductionCatalog(catalogQuery, { isAvailable: () => true, invoke }))
      .resolves.toEqual(catalog);
    expect(invoke).toHaveBeenCalledWith("query_production_catalog", catalogQuery);

    const plan = {
      planId: 1, ownerCharacterId: 7, ownerName: "Pilot", blueprintTypeId: 100,
      blueprintName: "Synthetic Hull Blueprint", activity: "manufacturing",
      productTypeId: 101, productName: "Synthetic Hull", targetQuantity: 3,
      priority: 12, note: "main goal", state: "ready", buildNumber: "synthetic-production-1",
      steps: [{ sequence: 1, blueprintTypeId: 100, blueprintName: "Synthetic Hull Blueprint",
        activity: "manufacturing", productTypeId: 101, productName: "Synthetic Hull",
        requiredQuantity: 3, outputQuantityPerRun: 2, runs: 2, producedQuantity: 4,
        surplusQuantity: 1, baseTimeSecondsPerRun: 100, totalBaseTimeSeconds: 200,
        recipeAlternatives: 1, materials: [{ typeId: 900, typeName: "Synthetic Mineral",
          quantityPerRun: 5, grossQuantity: 10, producedByPlan: false }] }],
      grossMaterials: [{ typeId: 900, typeName: "Synthetic Mineral", quantity: 10 }],
      warnings: [], cycleTypeIds: [], totalBaseTimeSeconds: 200,
      createdAt: "2026-09-11T12:00:00Z", updatedAt: "2026-09-11T12:00:00Z",
    };
    const page = { items: [plan], total: 1, offset: 0, limit: 50,
      owners: [{ characterId: 7, name: "Pilot" }], activities: ["manufacturing", "reaction"],
      states: ["ready", "sde-unavailable", "recipe-missing", "cycle", "complexity-limit"],
      summary: { ready: 1, "sde-unavailable": 0, "recipe-missing": 0, cycle: 0,
        "complexity-limit": 0 }, buildNumber: "synthetic-production-1",
      inventoryApplied: false, modifiersApplied: false };
    invoke.mockResolvedValueOnce(JSON.stringify(page));
    const query = { search: "", ownerCharacterId: null, activity: null, state: null,
      offset: 0, limit: 50, sortBy: "priority", sortDirection: "desc" } as const;
    await expect(loadProductionPlans(query, { isAvailable: () => true, invoke })).resolves.toEqual(page);
    expect(invoke).toHaveBeenLastCalledWith("query_production_plans", expect.objectContaining({
      planState: null, sortBy: "priority",
    }));

    const input = { planId: null, ownerCharacterId: 7, blueprintTypeId: 100,
      activity: "manufacturing", productTypeId: 101, targetQuantity: 3,
      priority: 12, note: "main goal" } as const;
    const saved = { ...input, planId: 1, saved: true };
    invoke.mockResolvedValueOnce(JSON.stringify(saved));
    await expect(saveProductionPlan(input, { isAvailable: () => true, invoke })).resolves.toEqual(saved);
    invoke.mockResolvedValueOnce(JSON.stringify({ deleted: true, planId: 1 }));
    await expect(deleteProductionPlan(1, { isAvailable: () => true, invoke })).resolves.toBeUndefined();
  });

  it("validates advisory update notices and opens only a release version", async () => {
    const notice = { state: "available", channel: "preview", currentVersion: "0.0.5-preview.12",
      latestVersion: "0.0.5-preview.13",
      releaseUrl: "https://github.com/Savox76/eve-test-indu/releases/tag/v0.0.5-preview.13",
      publishedAt: "2026-09-11T12:00:00Z", automaticInstall: false, errorCode: null };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValueOnce(JSON.stringify(notice));
    await expect(checkForUpdates({ isAvailable: () => true, invoke })).resolves.toEqual(notice);
    invoke.mockResolvedValueOnce(JSON.stringify({ opened: true, url: notice.releaseUrl }));
    await expect(openReleaseDownloads(notice.latestVersion, { isAvailable: () => true, invoke }))
      .resolves.toBeUndefined();
    expect(invoke).toHaveBeenLastCalledWith("open_release_downloads", {
      version: "0.0.5-preview.13",
    });
  });

  it("validates research plans and persistent plan mutations", async () => {
    const page = {
      items: [{
        ownerCharacterId: 7, ownerName: "Pilot", blueprintItemId: 9,
        blueprintTypeId: 681, blueprintName: "Bantam Blueprint", blueprintPresent: true,
        currentMaterialEfficiency: 4, currentTimeEfficiency: 8,
        locationId: 60_003_760, locationFlag: "Hangar", planned: true,
        nextActivity: "material", targetMaterialEfficiency: 10,
        targetTimeEfficiency: 20, priority: 50, note: "First",
        state: "running", slotCapacity: 6, slotsUsed: 1, slotsAvailable: 5,
        researchLevel: 4, metallurgyLevel: 5, activeJobId: 8_001,
        activeJobActivity: "material", activeJobStatus: "active",
        activeJobStartDate: "2026-09-11T12:00:00Z",
        activeJobEndDate: "2026-09-11T14:00:00Z", activeJobCost: 125_000.5,
        facilityId: 60_003_760, facilityName: "Jita IV - Moon 4",
        facilityAccess: "public", solarSystemName: "Jita", systemCostIndex: 0.0125,
        facilityEvidence: "active-job", blueprintSnapshotId: 2, blueprintSyncRunId: 3,
        skillSnapshotId: 4, skillSyncRunId: 5, jobSnapshotId: 6, jobSyncRunId: 7,
        observedAt: "2026-09-11T12:01:00Z", ageSeconds: 60,
        createdAt: "2026-09-11T11:00:00Z", updatedAt: "2026-09-11T11:30:00Z",
      }],
      total: 1, offset: 0, limit: 100,
      owners: [{ characterId: 7, name: "Pilot", slotCapacity: 6, slotsUsed: 1,
        slotsAvailable: 5, laboratoryOperationLevel: 3,
        advancedLaboratoryOperationLevel: 2, researchLevel: 4, metallurgyLevel: 5,
        skillSnapshotId: 4, skillSyncRunId: 5 }],
      states: ["unplanned", "ready", "queued", "running", "complete", "unverified", "missing"],
      activities: ["material", "time"],
      summary: { unplanned: 0, ready: 0, queued: 0, running: 1,
        complete: 0, unverified: 0, missing: 0 },
      observedAt: "2026-09-11T12:01:00Z", ageSeconds: 60, estimatesAvailable: false,
    };
    const invoke = vi.fn<RuntimeAdapter["invoke"]>().mockResolvedValueOnce(JSON.stringify(page));
    const query = { search: "", ownerCharacterId: null, state: null, plannedOnly: true,
      offset: 0, limit: 100, sortBy: "priority", sortDirection: "desc" } as const;
    await expect(loadResearchPlans(query, { isAvailable: () => true, invoke })).resolves.toEqual(page);
    expect(invoke).toHaveBeenCalledWith("query_research_plans", expect.objectContaining({
      planState: null, plannedOnly: true,
    }));

    const input = { ownerCharacterId: 7, blueprintItemId: 9, nextActivity: "material",
      targetMaterialEfficiency: 10, targetTimeEfficiency: 20, priority: 50,
      note: "First" } as const;
    const saved = { ...input, blueprintTypeId: 681, saved: true };
    invoke.mockResolvedValueOnce(JSON.stringify(saved));
    await expect(saveResearchPlan(input, { isAvailable: () => true, invoke })).resolves.toEqual(saved);

    invoke.mockResolvedValueOnce(JSON.stringify({
      ownerCharacterId: 7, blueprintItemId: 9, deleted: true,
    }));
    await expect(deleteResearchPlan(7, 9, { isAvailable: () => true, invoke })).resolves.toBeUndefined();
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
