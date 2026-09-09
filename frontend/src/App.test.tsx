import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { DesktopRuntimeStatus } from "./runtime";

const nativeRuntime = (overrides: Partial<Extract<DesktopRuntimeStatus, { state: "ready" }>> = {}) =>
  Promise.resolve<DesktopRuntimeStatus>({
    state: "ready",
    version: "0.0.4-preview.1",
    desktopShell: true,
    singleInstance: true,
    sidecar: "ready",
    database: "ready",
    databaseLocation: "data/foundry.sqlite3",
    schemaVersion: 5,
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
    ...overrides,
  });

describe("New Eden Foundry design preview", () => {
  it("marks every displayed value as synthetic preview data", () => {
    render(<App />);

    expect(screen.getByText(/Design Preview/i)).toBeInTheDocument();
    expect(screen.getByText(/synthetische Daten/i)).toBeInTheDocument();
  });

  it("opens a planned module from the navigation", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /Assets/i }));

    expect(screen.getByRole("heading", { name: "Assets" })).toBeInTheDocument();
    expect(screen.getByText("1,284")).toBeInTheDocument();
  });

  it("switches the visible interface language", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "EN" }));

    expect(screen.getByText("Good morning, pilot.")).toBeInTheDocument();
    expect(screen.getByText(/synthetic data/i)).toBeInTheDocument();
  });

  it("does not claim that the native desktop core is active in a browser", async () => {
    render(<App />);

    expect(await screen.findByText("Desktop-Kern nur in der App")).toBeInTheDocument();
  });

  it("credits Savoxmedia as the app creator next to the version", () => {
    render(<App />);

    expect(screen.getByText("v0.0.4-preview.1")).toBeInTheDocument();
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

    expect(await screen.findByText("Programmordner ist nicht beschreibbar")).toBeInTheDocument();
    expect(screen.queryByText(/Users\\|AppData|tmp/i)).not.toBeInTheDocument();
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
});
