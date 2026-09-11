import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type {
  AssetDeltaPage,
  AssetPage,
  AssetSummaryPage,
  BlueprintPage,
  CharacterSkillPage,
  DesktopRuntimeStatus,
  EveCharacter,
  IndustryFacilityPage,
  IndustryJobPage,
  IndustrySlotPage,
  ProductionCatalogPage,
  ProductionPlanPage,
  ResearchPlanPage,
  SsoLoginStatus,
} from "./runtime";

const idleSso: SsoLoginStatus = {
  state: "idle",
  attemptId: null,
  scopePackages: [],
  expiresAt: null,
  errorCode: null,
  character: null,
};

const nativeRuntime = (overrides: Partial<Extract<DesktopRuntimeStatus, { state: "ready" }>> = {}) =>
  Promise.resolve<DesktopRuntimeStatus>({
    state: "ready",
    version: "0.0.5-preview.14",
    desktopShell: true,
    singleInstance: true,
    distribution: "installed",
    sidecar: "ready",
    database: "ready",
    databaseLocation: "data/foundry.sqlite3",
    schemaVersion: 9,
    errorCode: null,
    data: {
      state: "empty",
      hasCachedData: false,
      observedAt: null,
      expiresAt: null,
      ageSeconds: null,
      lastSyncStatus: "never",
      errorCode: null,
    },
    updater: {
      channel: "stable",
      manifestState: "verified",
      publicDistribution: false,
    },
    appearance: { fontScale: "normal" },
    ...overrides,
  });

const assetPage = (overrides: Partial<AssetPage> = {}): AssetPage => ({
  items: [
    {
      itemId: 9_800_001,
      typeId: 98_001,
      typeName: "Synthetic Component",
      quantity: 17,
      ownerCharacterId: 90_888_001,
      ownerName: "Builder",
      locationFlag: "SyntheticHangar",
      locationStatus: "resolved",
      locationPath: "Synthetic System / Synthetic Station",
      locationNodes: [
        {
          locationId: 30_888_001,
          kind: "solar_system",
          name: "Synthetic System",
          access: "available",
          typeId: null,
        },
      ],
      observedAt: "2026-09-10T10:00:00Z",
      ageSeconds: 3_600,
    },
  ],
  total: 100_000,
  quantityTotal: 230_000,
  offset: 0,
  limit: 100,
  owners: [{ characterId: 90_888_001, name: "Builder" }],
  locationStatuses: ["resolved", "restricted", "unresolved", "cycle", "pending"],
  observedAt: "2026-09-10T10:00:00Z",
  ageSeconds: 3_600,
  ...overrides,
});

const assetSummaryPage = (overrides: Partial<AssetSummaryPage> = {}): AssetSummaryPage => ({
  items: [{
    typeId: 98_001,
    typeName: "Synthetic Component",
    quantityTotal: 34,
    positionCount: 2,
    ownerCount: 1,
    locationCount: 2,
    owners: [{ characterId: 90_888_001, name: "Builder", quantity: 34, positionCount: 2 }],
    locationStatuses: ["resolved"],
    ageSeconds: 3_600,
  }],
  total: 1,
  positionTotal: 2,
  quantityTotal: 34,
  offset: 0,
  limit: 100,
  owners: [{ characterId: 90_888_001, name: "Builder" }],
  locationStatuses: ["resolved", "restricted", "unresolved", "cycle", "pending"],
  observedAt: "2026-09-10T10:00:00Z",
  ageSeconds: 3_600,
  ...overrides,
});

const blueprintPage: BlueprintPage = {
  items: [{ itemId: 7_001, typeId: 681, typeName: "Bantam Blueprint",
    ownerCharacterId: 90_888_001, ownerName: "Builder", kind: "copy",
    materialEfficiency: 8, timeEfficiency: 16, runs: 12,
    locationId: 60_003_760, locationFlag: "Hangar",
    observedAt: "2026-09-10T10:00:00Z", ageSeconds: 3_600 }],
  total: 1, offset: 0, limit: 100,
  owners: [{ characterId: 90_888_001, name: "Builder" }],
  snapshots: [{ characterId: 90_888_001, name: "Builder", state: "available",
    itemCount: 1, observedAt: "2026-09-10T10:00:00Z", ageSeconds: 3_600 }],
  observedAt: "2026-09-10T10:00:00Z", ageSeconds: 3_600,
};

const assetDeltaPage = (overrides: Partial<AssetDeltaPage> = {}): AssetDeltaPage => ({
  items: [{
    eventId: "a".repeat(64),
    itemId: 9_800_001,
    typeId: 98_001,
    typeName: "Synthetic Component",
    ownerCharacterId: 90_888_001,
    ownerName: "Builder",
    changeTypes: ["quantity", "location"],
    quantityBefore: 17,
    quantityAfter: 9,
    quantityDelta: -8,
    locationIdBefore: 60_888_001,
    locationIdAfter: 60_888_002,
    locationTypeBefore: "station",
    locationTypeAfter: "station",
    locationFlagBefore: "Input",
    locationFlagAfter: "Output",
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
  summary: { added: 0, removed: 0, quantity: 1, location: 1 },
  hasBaseline: true,
  observedAt: "2026-09-10T11:00:00Z",
  ageSeconds: 60,
  ...overrides,
});

const industryJobPage: IndustryJobPage = {
  items: [{
    jobId: 8_001, ownerCharacterId: 90_888_001, ownerName: "Builder",
    activityId: 1, activityKey: "manufacturing", status: "delivered",
    blueprintItemId: 7_001, blueprintTypeId: 681, blueprintName: "Bantam Blueprint",
    productTypeId: 582, productName: "Bantam", runs: 2, successfulRuns: 2,
    licensedRuns: 0, probability: 1, cost: 1234.5, durationSeconds: 3600,
    facilityId: 60_003_760, facilityName: "Jita IV - Moon 4", facilityKind: "station",
    facilityAccess: "public", solarSystemId: 30_000_142, solarSystemName: "Jita",
    systemCostIndex: 0.0125, stationId: 60_003_760,
    blueprintLocationId: 60_003_760, outputLocationId: 60_003_760,
    startDate: "2026-09-10T10:00:00Z", endDate: "2026-09-10T11:00:00Z",
    completedDate: "2026-09-10T11:00:00Z", pauseDate: null,
    blueprintCorrelation: { state: "current", snapshotId: 2, syncRunId: 3,
      observedAt: "2026-09-10T11:01:00Z" },
    assetCorrelation: { state: "linked", eventIds: ["a".repeat(64)],
      candidateCount: 1, locationMatched: true },
    correlationState: "linked", jobSnapshotId: 4, jobSyncRunId: 5,
    observedAt: "2026-09-10T11:02:00Z", ageSeconds: 60,
  }],
  total: 1, activeTotal: 0, offset: 0, limit: 100,
  owners: [{ characterId: 90_888_001, name: "Builder" }],
  statuses: ["active", "cancelled", "delivered", "paused", "ready", "reverted"],
  activities: [1], correlations: ["linked", "partial", "ambiguous", "unmatched", "pending"],
  observedAt: "2026-09-10T11:02:00Z", ageSeconds: 60,
};

const characterSkillPage: CharacterSkillPage = {
  items: [{
    skillId: 33_550, skillName: "Industry", ownerCharacterId: 90_888_001,
    ownerName: "Builder", trainedLevel: 5, activeLevel: 4,
    skillpoints: 512_000, activeState: "limited", snapshotId: 8, syncRunId: 9,
    observedAt: "2026-09-11T00:00:00Z", ageSeconds: 60,
  }],
  total: 1, totalSp: 512_000, unallocatedSp: 12_500, offset: 0, limit: 100,
  owners: [{ characterId: 90_888_001, name: "Builder" }],
  levels: [0, 1, 2, 3, 4, 5], activeStates: ["normal", "limited", "boosted"],
  observedAt: "2026-09-11T00:00:00Z", ageSeconds: 60,
};

const industryFacilityPage: IndustryFacilityPage = {
  items: [{
    facilityId: 60_003_760, facilityName: "Jita IV - Moon 4", kind: "station",
    access: "public", typeId: 1_928, typeName: "Caldari Station",
    ownerId: 1_000_001, ownerName: "Caldari Navy", regionId: 10_000_002,
    regionName: "The Forge", solarSystemId: 30_000_142, solarSystemName: "Jita",
    securityStatus: 0.9, securityClass: "highsec",
    tax: null, activityCostIndex: 0.0125, usedByCharacterIds: [90_888_001],
    observedActivityIds: [1], jobCount: 1, activeJobs: 0, errorCode: null,
    snapshotId: 10, syncRunId: 11, observedAt: "2026-09-11T00:00:00Z", ageSeconds: 60,
  }],
  total: 1, npcFacilities: 1, observedFacilities: 0, restrictedStructures: 0,
  systems: 1, offset: 0, limit: 100, activity: "manufacturing",
  activities: ["manufacturing", "reaction", "copying", "invention",
    "researching_material_efficiency", "researching_time_efficiency"],
  kinds: ["station", "structure", "unknown"],
  accessStates: ["public", "available", "restricted", "scope-missing", "unknown"],
  securityClasses: ["highsec", "lowsec", "nullsec", "unknown"],
  observedAt: "2026-09-11T00:00:00Z", ageSeconds: 60,
};

const industrySlotPage: IndustrySlotPage = {
  items: [{
    characterId: 90_888_001, name: "Builder",
    activities: [{
      activity: "manufacturing", capacity: 7, occupied: 2, available: 5,
      utilizationState: "available", activeJobs: 1, pausedJobs: 0, readyJobs: 1,
      nextJobEndDate: "2026-09-11T12:00:00Z", primarySkillId: 3387,
      primarySkillLevel: 4, advancedSkillId: 24625, advancedSkillLevel: 2,
      queuedPlans: 1, blockedPlans: 0, runningPlans: 1, completePlans: 0,
      planningAvailable: true,
    }, {
      activity: "reactions", capacity: 5, occupied: 1, available: 4,
      utilizationState: "available", activeJobs: 1, pausedJobs: 0, readyJobs: 0,
      nextJobEndDate: "2026-09-11T13:00:00Z", primarySkillId: 45748,
      primarySkillLevel: 3, advancedSkillId: 45749, advancedSkillLevel: 1,
      queuedPlans: 0, blockedPlans: 1, runningPlans: 1, completePlans: 0,
      planningAvailable: true,
    }, {
      activity: "science", capacity: 6, occupied: 2, available: 4,
      utilizationState: "available", activeJobs: 2, pausedJobs: 0, readyJobs: 0,
      nextJobEndDate: "2026-09-11T14:00:00Z", primarySkillId: 3406,
      primarySkillLevel: 3, advancedSkillId: 24624, advancedSkillLevel: 2,
      queuedPlans: 1, blockedPlans: 1, runningPlans: 1, completePlans: 0,
      planningAvailable: true,
    }],
    skillSnapshotId: 2, skillSyncRunId: 3,
    skillObservedAt: "2026-09-11T11:00:00Z",
    jobSnapshotId: 4, jobSyncRunId: 5,
    jobObservedAt: "2026-09-11T11:01:00Z",
    observedAt: "2026-09-11T11:00:00Z", ageSeconds: 60,
  }],
  total: 1, offset: 0, limit: 50,
  owners: [{ characterId: 90_888_001, name: "Builder" }],
  activities: ["manufacturing", "reactions", "science"],
  observedAt: "2026-09-11T11:00:00Z", ageSeconds: 60,
};

const researchPlanPage: ResearchPlanPage = {
  items: [{
    ownerCharacterId: 90_888_001, ownerName: "Builder", blueprintItemId: 7_010,
    blueprintTypeId: 681, blueprintName: "Merlin Blueprint", blueprintPresent: true,
    currentMaterialEfficiency: 6, currentTimeEfficiency: 12,
    locationId: 60_003_760, locationFlag: "Hangar", planned: true,
    nextActivity: "material", targetMaterialEfficiency: 10,
    targetTimeEfficiency: 20, priority: 80, note: "Doctrine first", state: "ready",
    slotCapacity: 6, slotsUsed: 2, slotsAvailable: 4, researchLevel: 4,
    metallurgyLevel: 5, activeJobId: null, activeJobActivity: null,
    activeJobStatus: null, activeJobStartDate: null, activeJobEndDate: null,
    activeJobCost: null, facilityId: 60_003_760, facilityName: "Jita IV - Moon 4",
    facilityAccess: "public", solarSystemName: "Jita", systemCostIndex: 0.0125,
    facilityEvidence: "last-owner-job", blueprintSnapshotId: 2, blueprintSyncRunId: 3,
    skillSnapshotId: 4, skillSyncRunId: 5, jobSnapshotId: 6, jobSyncRunId: 7,
    observedAt: "2026-09-11T12:01:00Z", ageSeconds: 60,
    createdAt: "2026-09-11T11:00:00Z", updatedAt: "2026-09-11T11:30:00Z",
  }],
  total: 1, offset: 0, limit: 100,
  owners: [{ characterId: 90_888_001, name: "Builder", slotCapacity: 6,
    slotsUsed: 2, slotsAvailable: 4, laboratoryOperationLevel: 3,
    advancedLaboratoryOperationLevel: 2, researchLevel: 4, metallurgyLevel: 5,
    skillSnapshotId: 4, skillSyncRunId: 5 }],
  states: ["unplanned", "ready", "queued", "running", "complete", "unverified", "missing"],
  activities: ["material", "time"],
  summary: { unplanned: 0, ready: 1, queued: 0, running: 0, complete: 0,
    unverified: 0, missing: 0 },
  observedAt: "2026-09-11T12:01:00Z", ageSeconds: 60, estimatesAvailable: false,
};

const productionCatalogPage: ProductionCatalogPage = {
  items: [{ blueprintTypeId: 100, blueprintName: "Synthetic Hull Blueprint",
    activity: "manufacturing", baseTimeSeconds: 100, productTypeId: 101,
    productName: "Synthetic Hull", outputQuantity: 2, materialCount: 1 }],
  total: 1, offset: 0, limit: 50,
  activities: ["manufacturing", "reaction"], buildNumber: "synthetic-production-1",
};

const productionPlanPage: ProductionPlanPage = {
  items: [{ planId: 1, ownerCharacterId: 90_888_001, ownerName: "Builder",
    blueprintTypeId: 100, blueprintName: "Synthetic Hull Blueprint",
    activity: "manufacturing", productTypeId: 101, productName: "Synthetic Hull",
    targetQuantity: 3, priority: 50, note: "Doctrine", state: "ready",
    buildNumber: "synthetic-production-1", steps: [{ sequence: 1,
      blueprintTypeId: 100, blueprintName: "Synthetic Hull Blueprint",
      activity: "manufacturing", productTypeId: 101, productName: "Synthetic Hull",
      requiredQuantity: 3, outputQuantityPerRun: 2, runs: 2,
      producedQuantity: 4, surplusQuantity: 1, baseTimeSecondsPerRun: 100,
      totalBaseTimeSeconds: 200, recipeAlternatives: 1,
      materials: [{ typeId: 900, typeName: "Synthetic Mineral", quantityPerRun: 5,
        grossQuantity: 10, producedByPlan: false }] }],
    grossMaterials: [{ typeId: 900, typeName: "Synthetic Mineral", quantity: 10 }],
    warnings: [], cycleTypeIds: [], totalBaseTimeSeconds: 200,
    createdAt: "2026-09-11T12:00:00Z", updatedAt: "2026-09-11T12:00:00Z" }],
  total: 1, offset: 0, limit: 50,
  owners: [{ characterId: 90_888_001, name: "Builder" }],
  activities: ["manufacturing", "reaction"],
  states: ["ready", "sde-unavailable", "recipe-missing", "cycle", "complexity-limit"],
  summary: { ready: 1, "sde-unavailable": 0, "recipe-missing": 0, cycle: 0,
    "complexity-limit": 0 }, buildNumber: "synthetic-production-1",
  inventoryApplied: false, modifiersApplied: false,
};

describe("New Eden Foundry design preview", () => {
  it("marks every displayed value as synthetic preview data", () => {
    render(<App />);

    expect(screen.getByText(/Design Preview/i)).toBeInTheDocument();
    expect(screen.getByText(/synthetische Daten/i)).toBeInTheDocument();
  });

  it("opens the asset workspace without presenting preview values as live data", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /Assets/i }));

    expect(screen.getByRole("heading", { name: "Assets" })).toBeInTheDocument();
    expect(screen.getByText(/echte Asset-Ansicht ist in der laufenden Desktop-App/)).toBeInTheDocument();
    expect(screen.queryByText("1,284")).not.toBeInTheDocument();
  });

  it("queries and pages only bounded asset windows while exposing every required field", async () => {
    const assetsLoader = vi.fn().mockImplementation((query) => Promise.resolve(assetPage({
      offset: query.offset,
      items: [{ ...assetPage().items[0], itemId: 9_800_001 + query.offset }],
    })));
    render(
      <App
        runtimeLoader={() => nativeRuntime()}
        ssoStatusLoader={() => Promise.resolve(idleSso)}
        charactersLoader={() => Promise.resolve([])}
        accountGroupsLoader={() => Promise.resolve([])}
        assetsLoader={assetsLoader}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Assets/i }));
    fireEvent.click(screen.getByRole("button", { name: "Einzelpositionen" }));

    expect(await screen.findByText("Synthetic Component")).toBeInTheDocument();
    expect(screen.getAllByText("Builder")).toHaveLength(2);
    expect(screen.getByText("Synthetic System / Synthetic Station")).toBeInTheDocument();
    expect(screen.getByText("17")).toBeInTheDocument();
    expect(screen.getAllByText("1 Std.").length).toBeGreaterThan(0);
    expect(assetsLoader).toHaveBeenCalledWith({
      search: "",
      ownerCharacterId: null,
      locationStatus: null,
      offset: 0,
      limit: 100,
      sortBy: "type",
      sortDirection: "asc",
    });

    fireEvent.click(screen.getByRole("button", { name: "Nächste Seite" }));
    await waitFor(() => expect(assetsLoader).toHaveBeenLastCalledWith({
      search: "",
      ownerCharacterId: null,
      locationStatus: null,
      offset: 100,
      limit: 100,
      sortBy: "type",
      sortDirection: "asc",
    }));
    expect((await screen.findByText(/101–101 von 100\.000/))).toBeInTheDocument();
  });

  it("starts with a grouped stock overview and drills into matching positions", async () => {
    const assetSummaryLoader = vi.fn().mockResolvedValue(assetSummaryPage());
    const assetsLoader = vi.fn().mockResolvedValue(assetPage());
    render(
      <App
        runtimeLoader={() => nativeRuntime()}
        ssoStatusLoader={() => Promise.resolve(idleSso)}
        charactersLoader={() => Promise.resolve([])}
        accountGroupsLoader={() => Promise.resolve([])}
        assetSummaryLoader={assetSummaryLoader}
        assetsLoader={assetsLoader}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Assets/i }));
    expect(await screen.findByText("Synthetic Component")).toBeInTheDocument();
    expect(screen.getByText("Verteilung: Builder 34")).toBeInTheDocument();
    expect(assetSummaryLoader).toHaveBeenCalledWith({
      search: "",
      ownerCharacterId: null,
      locationStatus: null,
      offset: 0,
      limit: 100,
      sortBy: "type",
      sortDirection: "asc",
    });

    fireEvent.click(screen.getByRole("button", { name: "Einzelpositionen anzeigen" }));
    await waitFor(() => expect(assetsLoader).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: "Synthetic Component" }),
    ));
  });

  it("sorts asset columns before requesting the first page", async () => {
    const assetsLoader = vi.fn().mockResolvedValue(assetPage());
    render(
      <App
        runtimeLoader={() => nativeRuntime()}
        ssoStatusLoader={() => Promise.resolve(idleSso)}
        charactersLoader={() => Promise.resolve([])}
        accountGroupsLoader={() => Promise.resolve([])}
        assetsLoader={assetsLoader}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Assets/i }));
    fireEvent.click(screen.getByRole("button", { name: "Einzelpositionen" }));
    await screen.findByText("Synthetic Component");

    fireEvent.click(screen.getByRole("button", { name: "Menge" }));
    await waitFor(() => expect(assetsLoader).toHaveBeenLastCalledWith(
      expect.objectContaining({ offset: 0, sortBy: "quantity", sortDirection: "asc" }),
    ));
    fireEvent.click(screen.getByRole("button", { name: "Menge" }));
    await waitFor(() => expect(assetsLoader).toHaveBeenLastCalledWith(
      expect.objectContaining({ offset: 0, sortBy: "quantity", sortDirection: "desc" }),
    ));
  });

  it("composes asset search and filters and reports the local CSV target", async () => {
    const assetsLoader = vi.fn().mockResolvedValue(assetPage());
    const assetsCsvExporter = vi.fn().mockResolvedValue({
      filename: "assets-20260910-110203.csv",
      relativePath: "data/exports/assets-20260910-110203.csv",
      rows: 1,
    });
    render(
      <App
        runtimeLoader={() => nativeRuntime()}
        ssoStatusLoader={() => Promise.resolve(idleSso)}
        charactersLoader={() => Promise.resolve([])}
        accountGroupsLoader={() => Promise.resolve([])}
        assetsLoader={assetsLoader}
        assetsCsvExporter={assetsCsvExporter}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Assets/i }));
    fireEvent.click(screen.getByRole("button", { name: "Einzelpositionen" }));
    await screen.findByText("Synthetic Component");

    fireEvent.change(screen.getByPlaceholderText(/Typ, Standort, Besitzer oder ID suchen/), {
      target: { value: "  component   station " },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Besitzer" }), {
      target: { value: "90888001" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Standortstatus" }), {
      target: { value: "resolved" },
    });

    await waitFor(() => expect(assetsLoader).toHaveBeenLastCalledWith({
      search: "component station",
      ownerCharacterId: 90_888_001,
      locationStatus: "resolved",
      offset: 0,
      limit: 100,
      sortBy: "type",
      sortDirection: "asc",
    }));
    fireEvent.click(screen.getByRole("button", { name: "Treffer als CSV" }));
    await waitFor(() => expect(assetsCsvExporter).toHaveBeenCalledWith({
      search: "component station",
      ownerCharacterId: 90_888_001,
      locationStatus: "resolved",
      sortBy: "type",
      sortDirection: "asc",
    }));
    expect(await screen.findByText(/data\/exports\/assets-20260910-110203\.csv/))
      .toBeInTheDocument();
  });

  it("runs the real asset sync and reloads the visible snapshots", async () => {
    const assetsLoader = vi.fn().mockResolvedValue(assetPage());
    const assetSyncer = vi.fn().mockResolvedValue({
      characters: [{
        characterId: 90_888_001,
        status: "partial",
        pages: 1,
        assets: 1,
        resolved: 0,
        restricted: 0,
        unresolved: 0,
        cycles: 0,
        errorCode: "locations/esi-request-rejected-403",
      }],
      completed: 0,
      partial: 1,
      failed: 0,
      assets: 1,
    });
    render(
      <App
        runtimeLoader={() => nativeRuntime()}
        ssoStatusLoader={() => Promise.resolve(idleSso)}
        charactersLoader={() => Promise.resolve([])}
        accountGroupsLoader={() => Promise.resolve([])}
        assetsLoader={assetsLoader}
        assetSyncer={assetSyncer}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Assets/i }));
    fireEvent.click(screen.getByRole("button", { name: "Einzelpositionen" }));
    await screen.findByText("Synthetic Component");

    fireEvent.click(screen.getByRole("button", { name: "Assets aktualisieren" }));

    await waitFor(() => expect(assetSyncer).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/0 vollständig, 1 mit Teilfehler/)).toBeInTheDocument();
    expect(await screen.findByText(/Builder: Standorte: EVE-Berechtigung fehlt/)).toBeInTheDocument();
    await waitFor(() => expect(assetsLoader.mock.calls.length).toBeGreaterThan(1));
  });

  it("shows traceable delta evidence and filters the bounded history", async () => {
    const assetDeltasLoader = vi.fn().mockResolvedValue(assetDeltaPage());
    render(
      <App
        runtimeLoader={() => nativeRuntime()}
        ssoStatusLoader={() => Promise.resolve(idleSso)}
        charactersLoader={() => Promise.resolve([])}
        accountGroupsLoader={() => Promise.resolve([])}
        assetsLoader={() => Promise.resolve(assetPage())}
        assetDeltasLoader={assetDeltasLoader}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Assets/i }));

    expect(await screen.findByText("Nachvollziehbare Änderungen")).toBeInTheDocument();
    expect(await screen.findByText("Kein passender Job")).toBeInTheDocument();
    expect(screen.getAllByText("Menge geändert").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Verschoben").length).toBeGreaterThan(0);
    expect(screen.getByText((_, element) => element?.tagName === "STRONG" && element.textContent === "17 → 9"))
      .toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.tagName === "STRONG" && element.textContent === "Input → Output"))
      .toBeInTheDocument();
    expect(assetDeltasLoader).toHaveBeenCalledWith({
      search: "",
      ownerCharacterId: null,
      changeType: null,
      offset: 0,
      limit: 50,
    });

    fireEvent.change(screen.getByRole("combobox", { name: "Änderungsart" }), {
      target: { value: "location" },
    });
    await waitFor(() => expect(assetDeltasLoader).toHaveBeenLastCalledWith({
      search: "",
      ownerCharacterId: null,
      changeType: "location",
      offset: 0,
      limit: 50,
    }));
  });

  it("switches the visible interface language", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "EN" }));

    expect(screen.getByText("Good morning, pilot.")).toBeInTheDocument();
    expect(screen.getByText(/synthetic data/i)).toBeInTheDocument();
  });

  it("keeps the asset workspace fully bilingual", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /Assets/i }));
    fireEvent.click(screen.getByRole("button", { name: "EN" }));

    expect(screen.getByText("LOCAL ASSET INVENTORY")).toBeInTheDocument();
    expect(screen.getByText(/live asset view is available in the running desktop app/i))
      .toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Owner" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Location status" })).toBeInTheDocument();
    expect(screen.getByText("Traceable changes")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Change type" })).toBeInTheDocument();
  });

  it("changes all interface typography through five global stages", async () => {
    const fontScaleSetter = vi.fn().mockResolvedValue({ fontScale: "large" });
    render(<App fontScaleSetter={fontScaleSetter} />);

    expect(document.documentElement.dataset.fontScale).toBe("normal");
    fireEvent.click(screen.getByRole("button", { name: "Schrift größer" }));

    await waitFor(() => expect(fontScaleSetter).toHaveBeenCalledWith("large"));
    expect(document.documentElement.dataset.fontScale).toBe("large");
    expect(screen.getByText("4/5")).toHaveAttribute("title", "Groß");
  });

  it("does not claim that the native desktop core is active in a browser", async () => {
    render(<App />);

    expect(await screen.findByText("Desktop-Kern nur in der App")).toBeInTheDocument();
  });

  it("credits Savoxmedia as the app creator next to the version", () => {
    render(<App />);

    expect(screen.getByText("v0.0.5-preview.18")).toBeInTheDocument();
    expect(screen.getByText("Savoxmedia")).toBeInTheDocument();
    expect(screen.getByText("Erstellt von", { exact: false })).toBeInTheDocument();
    expect(screen.queryByText("Lokaler Betreiber")).not.toBeInTheDocument();
  });

  it("switches between the combined and individual character overview", () => {
    render(<App />);
    const scopeSelector = screen.getByRole("combobox", { name: "Übersichtsbereich" });

    expect(screen.getByText("18.42 B")).toBeInTheDocument();
    expect(screen.getByText(/2 lokale Kontogruppen · 3 Charaktere/)).toBeInTheDocument();

    fireEvent.change(scopeSelector, { target: { value: "mara-venn" } });

    expect(screen.getByText("9.80 B")).toBeInTheDocument();
    expect(screen.getByText(/Industry Core · Produktion & Assets/)).toBeInTheDocument();
    expect(screen.queryByText("18.42 B")).not.toBeInTheDocument();
    expect(screen.getByText("Asterion Relay")).toBeInTheDocument();
    expect(screen.queryByText("Vesper Field Array")).not.toBeInTheDocument();
    expect(screen.getByText("Borealis structure access")).toBeInTheDocument();
    expect(screen.queryByText("Nereid extraction cycle")).not.toBeInTheDocument();

    fireEvent.change(scopeSelector, { target: { value: "all" } });
    expect(screen.getByText("18.42 B")).toBeInTheDocument();
  });

  it("keeps cached content visible and labels an offline start", async () => {
    render(
      <App
        runtimeLoader={() => nativeRuntime({
          data: {
            state: "offline",
            hasCachedData: true,
            observedAt: "2026-09-09T07:00:00Z",
            expiresAt: "2026-09-09T07:05:00Z",
            ageSeconds: 7_200,
            lastSyncStatus: "failed",
            errorCode: "network-unavailable",
          },
        })}
      />,
    );

    expect(await screen.findByText("Offline · Cache bleibt verfügbar")).toBeInTheDocument();
    expect(screen.getAllByText("Datenalter: 2 Std.")).toHaveLength(2);
    expect(screen.getByText("18.42 B")).toBeInTheDocument();
  });

  it("explains a program-folder startup failure without showing an absolute path", async () => {
    render(
      <App
        runtimeLoader={() => nativeRuntime({
          sidecar: "error",
          database: "error",
          schemaVersion: null,
          errorCode: "program-storage-unavailable",
          data: {
            state: "error",
            hasCachedData: false,
            observedAt: null,
            expiresAt: null,
            ageSeconds: null,
            lastSyncStatus: "never",
            errorCode: "program-storage-unavailable",
          },
        })}
      />,
    );

    expect(
      await screen.findByText(
        "Programmordner ist nicht beschreibbar · Fehlercode: program-storage-unavailable",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Users\\|AppData|tmp/i)).not.toBeInTheDocument();
  });

  it("distinguishes a failed previous-version migration from a missing sidecar", async () => {
    render(
      <App
        runtimeLoader={() => nativeRuntime({
          sidecar: "error",
          database: "error",
          schemaVersion: null,
          errorCode: "program-storage-migration-failed",
          data: {
            state: "error",
            hasCachedData: false,
            observedAt: null,
            expiresAt: null,
            ageSeconds: null,
            lastSyncStatus: "never",
            errorCode: "program-storage-migration-failed",
          },
        })}
      />,
    );

    expect(
      await screen.findByText(
        "Datenübernahme aus der vorherigen Version konnte nicht abgeschlossen werden · Fehlercode: program-storage-migration-failed",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Lokaler Dienst fehlt im Programmordner")).not.toBeInTheDocument();
  });

  it("stores a selected update channel while public downloads remain disabled", async () => {
    const updateChannelSetter = vi.fn().mockResolvedValue({
      channel: "beta",
      manifestState: "verified",
      publicDistribution: false,
    });
    render(
      <App
        runtimeLoader={() => nativeRuntime()}
        updateChannelSetter={updateChannelSetter}
      />,
    );

    const selector = await screen.findByRole("combobox", { name: "Update-Kanal auswählen" });
    await waitFor(() => expect(selector).toBeEnabled());
    fireEvent.change(selector, { target: { value: "beta" } });

    await waitFor(() => expect(updateChannelSetter).toHaveBeenCalledWith("beta"));
    expect(await screen.findByText(/Signiertes Testmanifest geprüft · Downloads noch deaktiviert/))
      .toBeInTheDocument();
  });

  it("shows the portable release notice and opens only its validated version", async () => {
    const releaseDownloadsOpener = vi.fn().mockResolvedValue(undefined);
    render(
      <App
        runtimeLoader={() => nativeRuntime({ distribution: "portable" })}
        releaseNoticeChecker={() => Promise.resolve({
          state: "available", channel: "preview", currentVersion: "0.0.5-preview.13",
          latestVersion: "0.0.5-preview.14",
          releaseUrl: "https://github.com/Savox76/eve-test-indu/releases/tag/v0.0.5-preview.14",
          publishedAt: "2026-09-11T12:00:00Z", automaticInstall: false, errorCode: null,
        })}
        releaseDownloadsOpener={releaseDownloadsOpener}
      />,
    );

    expect(await screen.findByText("Version 0.0.5-preview.14 ist verfügbar")).toBeInTheDocument();
    expect(screen.getByText(/Portable: Die ZIP vollständig an einen beliebigen beschreibbaren Ort/))
      .toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Release öffnen" }));
    expect(releaseDownloadsOpener).toHaveBeenCalledWith("0.0.5-preview.14");
  });

  it("renders and creates a deterministic production goal", async () => {
    const productionCatalogLoader = vi.fn().mockResolvedValue(productionCatalogPage);
    const productionPlansLoader = vi.fn().mockResolvedValue(productionPlanPage);
    const productionPlanSaver = vi.fn().mockResolvedValue({ saved: true, planId: 2 });
    render(
      <App
        runtimeLoader={() => nativeRuntime()}
        productionCatalogLoader={productionCatalogLoader}
        productionPlansLoader={productionPlansLoader}
        productionPlanSaver={productionPlanSaver}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Produktion" }));

    expect(await screen.findByText("Synthetic Mineral")).toBeInTheDocument();
    expect(screen.getByText(/Bruttobedarf ohne Bestandsabzug/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Synthetic Hull.*Auswählen$/ }));
    fireEvent.click(screen.getByRole("button", { name: "Ziel speichern" }));

    await waitFor(() => expect(productionPlanSaver).toHaveBeenCalledWith({
      planId: null, ownerCharacterId: 90_888_001, blueprintTypeId: 100,
      activity: "manufacturing", productTypeId: 101, targetQuantity: 2,
      priority: 0, note: null,
    }));
  });

  it("renders component steps before the selected production goal", async () => {
    const basePlan = productionPlanPage.items[0];
    const componentStep = {
      ...basePlan.steps[0],
      sequence: 1,
      blueprintTypeId: 110,
      blueprintName: "Synthetic Component Blueprint",
      productTypeId: 111,
      productName: "Synthetic Component",
      requiredQuantity: 4,
      outputQuantityPerRun: 1,
      runs: 4,
      producedQuantity: 4,
      surplusQuantity: 0,
      materials: [{ typeId: 901, typeName: "Synthetic Ore", quantityPerRun: 2,
        grossQuantity: 8, producedByPlan: false }],
    };
    const goalStep = {
      ...basePlan.steps[0],
      sequence: 2,
      materials: [{ typeId: 111, typeName: "Synthetic Component", quantityPerRun: 2,
        grossQuantity: 4, producedByPlan: true }],
    };
    const productionPlansLoader = vi.fn().mockResolvedValue({
      ...productionPlanPage,
      items: [{ ...basePlan, steps: [componentStep, goalStep] }],
    } satisfies ProductionPlanPage);
    render(<App runtimeLoader={() => nativeRuntime()}
      productionPlansLoader={productionPlansLoader} />);

    fireEvent.click(screen.getByRole("button", { name: "Produktion" }));
    const component = await screen.findByText(/Schritt 1 · Vorprodukt: Synthetic Component/);
    const goal = screen.getByText(/Schritt 2 · Zielprodukt: Synthetic Hull/);
    expect(component.closest("li")).not.toHaveClass("production-step--goal");
    expect(goal.closest("li")).toHaveClass("production-step--goal");
    expect(component.compareDocumentPosition(goal) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("starts and cancels one-character-at-a-time PKCE login with selected scopes", async () => {
    const waiting: SsoLoginStatus = {
      state: "waiting",
      attemptId: "opaque-attempt",
      scopePackages: ["industry-core", "market"],
      expiresAt: "2026-09-09T12:03:00Z",
      errorCode: null,
      character: null,
    };
    const cancelled: SsoLoginStatus = { ...waiting, state: "cancelled" };
    const ssoStarter = vi.fn().mockResolvedValue(waiting);
    const ssoCanceller = vi.fn().mockResolvedValue(cancelled);
    render(
      <App
        runtimeLoader={() => nativeRuntime()}
        ssoStatusLoader={() => Promise.resolve(idleSso)}
        ssoStarter={ssoStarter}
        ssoCanceller={ssoCanceller}
      />,
    );

    const startButton = await screen.findByRole("button", { name: "Charakter verbinden" });
    await waitFor(() => expect(startButton).toBeEnabled());
    expect(screen.getByText("Alle aktuell benötigten SSO-Pakete werden automatisch angefordert.")).toBeInTheDocument();
    fireEvent.click(startButton);

    await waitFor(() => expect(ssoStarter).toHaveBeenCalledWith([
      "industry-core", "market", "planetary-industry", "projects", "private-structures",
    ]));
    expect(await screen.findByText("Browser-Anmeldung läuft")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Abbrechen" }));

    await waitFor(() => expect(ssoCanceller).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("Anmeldung abgebrochen")).toBeInTheDocument();
  });

  it("shows a JWT-verified character immediately and in the persistent roster", async () => {
    const identity = {
      characterId: 2_112_345_678,
      name: "Synthetic Pilot",
      scopes: ["esi-assets.read_assets.v1"],
    };
    const connected: SsoLoginStatus = {
      state: "connected",
      attemptId: "opaque-attempt",
      scopePackages: ["industry-core"],
      expiresAt: "2026-09-09T12:03:00Z",
      errorCode: null,
      character: identity,
    };
    const character: EveCharacter = {
      ...identity,
      alias: null,
      accountGroupId: null,
      accountGroupLabel: null,
      enabled: true,
      credentialState: "stored",
      scopePackages: [
        { id: "industry-core", status: "partial", grantedCount: 1, requiredCount: 4 },
        { id: "market", status: "missing", grantedCount: 0, requiredCount: 2 },
        { id: "planetary-industry", status: "missing", grantedCount: 0, requiredCount: 1 },
        { id: "projects", status: "missing", grantedCount: 0, requiredCount: 1 },
        { id: "private-structures", status: "missing", grantedCount: 0, requiredCount: 1 },
      ],
    };
    const assetSyncer = vi.fn().mockResolvedValue({
      characters: [], completed: 0, partial: 0, failed: 0, assets: 0,
    });
    const blueprintSyncer = vi.fn().mockResolvedValue({
      characters: [], completed: 0, failed: 0, blueprints: 0,
    });
    const characterSkillSyncer = vi.fn().mockResolvedValue({
      characters: [], completed: 0, failed: 0, skills: 0, totalSp: 0, unallocatedSp: 0,
    });
    const industryJobSyncer = vi.fn().mockResolvedValue({
      characters: [], completed: 0, failed: 0, jobs: 0, active: 0, completedJobs: 0,
    });
    const industryFacilitySyncer = vi.fn().mockResolvedValue({
      syncRunId: 1, facilities: 1, npcFacilities: 1, observedFacilities: 0,
      restrictedStructures: 0, systems: 1, resolvedNames: 5,
    });
    render(
      <App
        runtimeLoader={() => nativeRuntime()}
        ssoStatusLoader={() => Promise.resolve(connected)}
        charactersLoader={() => Promise.resolve([character])}
        assetSyncer={assetSyncer}
        blueprintSyncer={blueprintSyncer}
        characterSkillSyncer={characterSkillSyncer}
        industryJobSyncer={industryJobSyncer}
        industryFacilitySyncer={industryFacilitySyncer}
      />,
    );

    expect(await screen.findByText("EVE-Charakter verbunden")).toBeInTheDocument();
    expect(screen.getByText("Verbunden: Synthetic Pilot")).toBeInTheDocument();
    expect(screen.getByText("1 lokal verbunden")).toBeInTheDocument();
    expect(screen.getByText("Bestätigte Scopes: 1")).toBeInTheDocument();
    await waitFor(() => expect(assetSyncer).toHaveBeenCalledTimes(1));
    expect(blueprintSyncer).toHaveBeenCalledTimes(1);
    expect(characterSkillSyncer).toHaveBeenCalledTimes(1);
    expect(industryJobSyncer).toHaveBeenCalledTimes(1);
    expect(industryFacilitySyncer).toHaveBeenCalledTimes(1);
  });

  it("edits aliases, groups, activity, and exposes guarded full deletion", async () => {
    const character: EveCharacter = {
      characterId: 2_112_345_678,
      name: "Synthetic Pilot",
      alias: null,
      accountGroupId: 3,
      accountGroupLabel: "Industry",
      enabled: true,
      credentialState: "stored",
      scopes: ["esi-assets.read_assets.v1"],
      scopePackages: [
        { id: "industry-core", status: "partial", grantedCount: 1, requiredCount: 4 },
        { id: "market", status: "missing", grantedCount: 0, requiredCount: 2 },
        { id: "planetary-industry", status: "missing", grantedCount: 0, requiredCount: 1 },
        { id: "projects", status: "missing", grantedCount: 0, requiredCount: 1 },
        { id: "private-structures", status: "missing", grantedCount: 0, requiredCount: 1 },
      ],
    };
    const characterUpdater = vi.fn().mockResolvedValue({ ...character, alias: "Builder" });
    const ssoStarter = vi.fn().mockResolvedValue({
      ...idleSso, state: "waiting", attemptId: "reauthorize", expiresAt: "2026-09-10T12:03:00Z",
      scopePackages: ["industry-core", "market", "planetary-industry", "projects", "private-structures"],
    });
    render(
      <App
        runtimeLoader={() => nativeRuntime()}
        ssoStatusLoader={() => Promise.resolve(idleSso)}
        charactersLoader={() => Promise.resolve([character])}
        accountGroupsLoader={() => Promise.resolve([
          { id: 3, label: "Industry", sortOrder: 0, characterCount: 1 },
        ])}
        characterUpdater={characterUpdater}
        ssoStarter={ssoStarter}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Verwalten" }));
    expect(screen.getByText("Berechtigungen müssen erneuert werden")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Jetzt neu anmelden" }));
    await waitFor(() => expect(ssoStarter).toHaveBeenCalledWith([
      "industry-core", "market", "planetary-industry", "projects", "private-structures",
    ]));
    expect(screen.getByText(/teilweise 1\/4/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Lokaler Alias"), { target: { value: "Builder" } });
    fireEvent.click(screen.getByRole("button", { name: "Änderungen speichern" }));

    await waitFor(() => expect(characterUpdater).toHaveBeenCalledWith(
      2_112_345_678,
      { alias: "Builder", accountGroupId: 3, enabled: true },
    ));
    fireEvent.click(screen.getByRole("button", { name: "Charakter vollständig löschen" }));
    expect(screen.getByRole("button", { name: "Löschen endgültig bestätigen" })).toBeInTheDocument();
    expect(screen.getByText(/Refresh Token dauerhaft/)).toBeInTheDocument();
  });

  it("keeps real EVE sign-in disabled in browser design preview", async () => {
    render(<App />);

    expect(await screen.findByRole("button", { name: "Charakter verbinden" })).toBeDisabled();
    expect(screen.getByText("Die echte Anmeldung ist in der Windows-App verfügbar.")).toBeInTheDocument();
  });

  it("shows sortable live BPO and BPC inventory", async () => {
    const blueprintsLoader = vi.fn().mockResolvedValue(blueprintPage);
    render(<App runtimeLoader={() => nativeRuntime()} ssoStatusLoader={() => Promise.resolve(idleSso)} blueprintsLoader={blueprintsLoader} />);
    fireEvent.click(await screen.findByRole("button", { name: "Blueprints & Jobs" }));
    expect(await screen.findByText("Bantam Blueprint")).toBeInTheDocument();
    expect(screen.getByText("Snapshot-Status")).toBeInTheDocument();
    expect(screen.getByText(/1 Blueprints · 1 Std\./)).toBeInTheDocument();
    expect(screen.getByText("BPC")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Blueprint, Besitzer, Ort oder ID suchen"), {
      target: { value: "Bantam" },
    });
    await waitFor(() => expect(blueprintsLoader).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: "Bantam" }),
    ));
    fireEvent.click(screen.getByRole("button", { name: "ME" }));
    await waitFor(() => expect(blueprintsLoader).toHaveBeenLastCalledWith(expect.objectContaining({ sortBy: "me", sortDirection: "asc" })));
  });

  it("shows, filters, sorts, and refreshes traceable personal industry jobs", async () => {
    const industryJobsLoader = vi.fn().mockResolvedValue(industryJobPage);
    const industryJobSyncer = vi.fn().mockResolvedValue({
      characters: [{ characterId: 90_888_001, status: "completed", jobs: 1,
        active: 0, completedJobs: 1, errorCode: null }],
      completed: 1, failed: 0, jobs: 1, active: 0, completedJobs: 1,
    });
    render(<App runtimeLoader={() => nativeRuntime()} ssoStatusLoader={() => Promise.resolve(idleSso)}
      industryJobsLoader={industryJobsLoader} industryJobSyncer={industryJobSyncer} />);
    fireEvent.click(await screen.findByRole("button", { name: "Blueprints & Jobs" }));
    expect(await screen.findByText("Bantam")).toBeInTheDocument();
    expect(screen.getAllByText("Belegt").length).toBeGreaterThan(0);
    expect(screen.getByText(/aktueller Blueprint · Asset-Änderung belegt/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "delivered" } });
    await waitFor(() => expect(industryJobsLoader).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: "delivered" }),
    ));
    fireEvent.click(screen.getByRole("button", { name: "Läufe" }));
    await waitFor(() => expect(industryJobsLoader).toHaveBeenLastCalledWith(
      expect.objectContaining({ sortBy: "runs", sortDirection: "asc" }),
    ));
    fireEvent.click(screen.getByRole("button", { name: "Jobs aktualisieren" }));
    await waitFor(() => expect(industryJobSyncer).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/1 Jobs von 1 Charakter/)).toBeInTheDocument();
  });

  it("separates running jobs from ready jobs and shows live remaining time", async () => {
    const endDate = new Date(Date.now() + 90 * 60_000).toISOString();
    const baseJob = industryJobPage.items[0];
    const industryJobsLoader = vi.fn().mockResolvedValue({
      ...industryJobPage,
      items: [
        {
          ...baseJob,
          jobId: 8_002,
          status: "active",
          endDate,
          completedDate: null,
          correlationState: "pending",
          assetCorrelation: { state: "pending", eventIds: [], candidateCount: 0, locationMatched: false },
        },
        {
          ...baseJob,
          jobId: 8_003,
          status: "ready",
          completedDate: null,
        },
      ],
      total: 2,
      activeTotal: 2,
    } satisfies IndustryJobPage);
    render(<App runtimeLoader={() => nativeRuntime()} ssoStatusLoader={() => Promise.resolve(idleSso)}
      industryJobsLoader={industryJobsLoader} />);

    fireEvent.click(await screen.findByRole("button", { name: "Blueprints & Jobs" }));
    expect((await screen.findAllByText("Läuft")).length).toBeGreaterThan(0);
    expect(screen.getByText(/Noch 1 Std\./)).toBeInTheDocument();
    expect(screen.getAllByText("Abholbereit").length).toBeGreaterThanOrEqual(2);
  });

  it("shows character-separated industry capacity and research work queues", async () => {
    const industrySlotsLoader = vi.fn().mockResolvedValue(industrySlotPage);
    render(<App runtimeLoader={() => nativeRuntime()} ssoStatusLoader={() => Promise.resolve(idleSso)}
      industrySlotsLoader={industrySlotsLoader} />);
    fireEvent.click(await screen.findByRole("button", { name: "Blueprints & Jobs" }));

    expect(await screen.findByText("Kapazität und Arbeitsvorrat")).toBeInTheDocument();
    expect(screen.getByText("5 frei · 2/7 belegt")).toBeInTheDocument();
    expect(screen.getByText("1 geplant · 1 laufend · 1 blockiert · 0 fertig")).toBeInTheDocument();
    expect(screen.getByText("Skills #2 / Lauf #3 · Jobs #4 / Lauf #5")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Charakter", { selector: ".industry-slots select" }), {
      target: { value: "90888001" },
    });
    await waitFor(() => expect(industrySlotsLoader).toHaveBeenLastCalledWith({
      ownerCharacterId: 90_888_001, offset: 0, limit: 50,
    }));
  });

  it("shows, filters, sorts, and refreshes character skills", async () => {
    const characterSkillsLoader = vi.fn().mockResolvedValue(characterSkillPage);
    const characterSkillSyncer = vi.fn().mockResolvedValue({
      characters: [{ characterId: 90_888_001, status: "completed", skills: 1,
        totalSp: 512_000, unallocatedSp: 12_500, errorCode: null }],
      completed: 1, failed: 0, skills: 1, totalSp: 512_000, unallocatedSp: 12_500,
    });
    render(<App runtimeLoader={() => nativeRuntime()} ssoStatusLoader={() => Promise.resolve(idleSso)}
      characterSkillsLoader={characterSkillsLoader} characterSkillSyncer={characterSkillSyncer} />);
    fireEvent.click(await screen.findByRole("button", { name: "Blueprints & Jobs" }));
    expect(await screen.findByText("Industry")).toBeInTheDocument();
    expect(screen.getAllByText("Aktiv eingeschränkt").length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Trainiertes Level"), { target: { value: "5" } });
    await waitFor(() => expect(characterSkillsLoader).toHaveBeenLastCalledWith(
      expect.objectContaining({ trainedLevel: 5 }),
    ));
    fireEvent.click(screen.getByRole("button", { name: "Skillpunkte" }));
    await waitFor(() => expect(characterSkillsLoader).toHaveBeenLastCalledWith(
      expect.objectContaining({ sortBy: "skillpoints", sortDirection: "asc" }),
    ));
    fireEvent.click(screen.getByRole("button", { name: "Skills aktualisieren" }));
    await waitFor(() => expect(characterSkillSyncer).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/1 Skills von 1 Charakter/)).toBeInTheDocument();
  });

  it("shows, filters, sorts, and refreshes facilities with cost provenance", async () => {
    const industryFacilitiesLoader = vi.fn().mockResolvedValue(industryFacilityPage);
    const industryFacilitySyncer = vi.fn().mockResolvedValue({
      syncRunId: 12, facilities: 1, npcFacilities: 1, observedFacilities: 0,
      restrictedStructures: 0, systems: 1, resolvedNames: 5,
    });
    render(<App runtimeLoader={() => nativeRuntime()} ssoStatusLoader={() => Promise.resolve(idleSso)}
      industryFacilitiesLoader={industryFacilitiesLoader}
      industryFacilitySyncer={industryFacilitySyncer} />);
    fireEvent.click(await screen.findByRole("button", { name: "Blueprints & Jobs" }));
    expect(await screen.findByText("Jita IV - Moon 4")).toBeInTheDocument();
    expect(screen.getByText(/keine Struktur- oder Rigboni/)).toBeInTheDocument();
    expect(screen.getByText(/1,25.*%/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Anlagenart"), { target: { value: "station" } });
    await waitFor(() => expect(industryFacilitiesLoader).toHaveBeenLastCalledWith(
      expect.objectContaining({ kind: "station" }),
    ));
    fireEvent.change(screen.getByLabelText("Sicherheitsraum"), { target: { value: "highsec" } });
    await waitFor(() => expect(industryFacilitiesLoader).toHaveBeenLastCalledWith(
      expect.objectContaining({ securityClass: "highsec" }),
    ));
    fireEvent.click(screen.getByRole("button", { name: "Systemkostenindex" }));
    await waitFor(() => expect(industryFacilitiesLoader).toHaveBeenLastCalledWith(
      expect.objectContaining({ sortBy: "cost", sortDirection: "asc" }),
    ));
    fireEvent.click(screen.getByRole("button", { name: "Nur in Jobs verwendet" }));
    await waitFor(() => expect(industryFacilitiesLoader).toHaveBeenLastCalledWith(
      expect.objectContaining({ usedOnly: true }),
    ));
    fireEvent.click(screen.getByRole("button", { name: "Anlagen aktualisieren" }));
    await waitFor(() => expect(industryFacilitySyncer).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/1 Anlagen und 1 Systemkostenstände/)).toBeInTheDocument();
  });

  it("edits persistent research goals with real slot and facility evidence", async () => {
    const researchPlansLoader = vi.fn().mockResolvedValue(researchPlanPage);
    const researchPlanSaver = vi.fn().mockResolvedValue({ saved: true });
    const researchPlanDeleter = vi.fn().mockResolvedValue(undefined);
    render(<App runtimeLoader={() => nativeRuntime()} ssoStatusLoader={() => Promise.resolve(idleSso)}
      researchPlansLoader={researchPlansLoader} researchPlanSaver={researchPlanSaver}
      researchPlanDeleter={researchPlanDeleter} />);
    fireEvent.click(await screen.findByRole("button", { name: "Blueprints & Jobs" }));

    expect(await screen.findByText("Merlin Blueprint")).toBeInTheDocument();
    expect(screen.getAllByText("Bereit").length).toBeGreaterThan(0);
    expect(screen.getByText(/4 frei · 2\/6 belegt/)).toBeInTheDocument();
    expect(screen.getByText(/zuletzt dort genutzt/)).toBeInTheDocument();
    expect(screen.getByText(/Zeiten und Gesamtkosten werden vor dem Einbau nicht geschätzt/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Planstatus"), { target: { value: "ready" } });
    await waitFor(() => expect(researchPlansLoader).toHaveBeenLastCalledWith(
      expect.objectContaining({ state: "ready" }),
    ));
    fireEvent.change(screen.getByLabelText("Priorität"), { target: { value: "90" } });
    fireEvent.click(screen.getByRole("button", { name: "Aktualisieren" }));
    await waitFor(() => expect(researchPlanSaver).toHaveBeenCalledWith(
      expect.objectContaining({ blueprintItemId: 7_010, priority: 90 }),
    ));
    fireEvent.click(screen.getByRole("button", { name: "Entfernen" }));
    await waitFor(() => expect(researchPlanDeleter).toHaveBeenCalledWith(90_888_001, 7_010));
  });
});
