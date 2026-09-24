import type { BlueprintProfitabilityComparison } from "./runtime";

export type BlueprintResultBasis = "net" | "before-installation" | "before-trade" | "before-installation-and-trade" | "unavailable";

/** Keep missing costs explicit; a partial surplus is never a net profit. */
export function blueprintResult(comparison: BlueprintProfitabilityComparison): {
  basis: BlueprintResultBasis; cents: number | null; marginBasisPoints: number | null;
} {
  if (comparison.netProfitCents !== null) {
    return { basis: "net", cents: comparison.netProfitCents, marginBasisPoints: comparison.netMarginBasisPoints };
  }
  const { grossRevenueCents: revenue, materialReplacementCostCents: materials,
    installationCostCents: installation, totalTradeCostCents: trade } = comparison;
  const unavailable = { basis: "unavailable" as const, cents: null, marginBasisPoints: null };
  if (revenue === null || materials === null || (installation !== null && trade !== null)) return unavailable;
  // Subtract only evidenced costs. The basis labels every omitted category.
  const cents = revenue - materials - (installation ?? 0) - (trade ?? 0);
  if (!Number.isSafeInteger(cents)) return unavailable;
  return {
    basis: installation === null ? (trade === null ? "before-installation-and-trade" : "before-installation") : "before-trade",
    cents,
    marginBasisPoints: null,
  };
}
