import { describe, expect, it } from "vitest";
import type { BlueprintProfitabilityComparison } from "./runtime";
import { blueprintResult } from "./blueprintProfitability";

const comparison: BlueprintProfitabilityComparison = {
  hubId: "jita", hubName: "Jita", pricingState: "ready", profitabilityState: "partial",
  tradeCostState: "ready", grossRevenueCents: 40_000, materialReplacementCostCents: 20_000,
  installationCostCents: null, totalProductionCostCents: null,
  brokerFeeCents: 600, salesTaxCents: 1_300, totalTradeCostCents: 1_900,
  netProfitCents: null, netMarginBasisPoints: null, marketObservedAt: "2026-09-24T12:00:00Z",
};

describe("blueprint results with incomplete costs", () => {
  it("keeps a known surplus visible without pretending installation is free", () => {
    expect(blueprintResult(comparison)).toEqual({ basis: "before-installation", cents: 18_100, marginBasisPoints: null });
  });
  it("identifies missing trading fees and retains evidenced installation costs", () => {
    expect(blueprintResult({ ...comparison, installationCostCents: 1_000, totalTradeCostCents: null,
      tradeCostState: "standing-snapshot-missing" })).toEqual({ basis: "before-trade", cents: 19_000, marginBasisPoints: null });
  });
  it("labels both missing cost categories and shows no net margin", () => {
    expect(blueprintResult({ ...comparison, totalTradeCostCents: null })).toEqual({ basis: "before-installation-and-trade", cents: 20_000, marginBasisPoints: null });
  });
  it.each(["grossRevenueCents", "materialReplacementCostCents"] as const)("does not invent missing %s", (field) => {
    expect(blueprintResult({ ...comparison, [field]: null })).toEqual({ basis: "unavailable", cents: null, marginBasisPoints: null });
  });
  it("preserves a real zero net result and its margin", () => {
    expect(blueprintResult({ ...comparison, netProfitCents: 0, netMarginBasisPoints: 0 })).toEqual({ basis: "net", cents: 0, marginBasisPoints: 0 });
  });
  it("preserves negative partial results", () => {
    expect(blueprintResult({ ...comparison, grossRevenueCents: 10_000 })).toEqual({ basis: "before-installation", cents: -11_900, marginBasisPoints: null });
  });
  it("does not fabricate a net result from an inconsistent response", () => {
    expect(blueprintResult({ ...comparison, installationCostCents: 1_000 }).basis).toBe("unavailable");
  });
});
