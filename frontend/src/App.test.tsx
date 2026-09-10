import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { DesktopRuntimeStatus, EveCharacter, SsoLoginStatus } from "./runtime";

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
    version: "0.0.5-preview.1",
    desktopShell: true,
    singleInstance: true,
    sidecar: "ready",
    database: "ready",
    databaseLocation: "data/foundry.sqlite3",
    schemaVersion: 6,
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

    expect(screen.getByText("v0.0.5-preview.1")).toBeInTheDocument();
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
    expect(screen.getByRole("checkbox", { name: "Industrie-Basis" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Industrie-Basis" })).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: "Markt" }));
    fireEvent.click(startButton);

    await waitFor(() => expect(ssoStarter).toHaveBeenCalledWith(["industry-core", "market"]));
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
    render(
      <App
        runtimeLoader={() => nativeRuntime()}
        ssoStatusLoader={() => Promise.resolve(connected)}
        charactersLoader={() => Promise.resolve([character])}
      />,
    );

    expect(await screen.findByText("EVE-Charakter verbunden")).toBeInTheDocument();
    expect(screen.getByText("Verbunden: Synthetic Pilot")).toBeInTheDocument();
    expect(screen.getByText("1 lokal verbunden")).toBeInTheDocument();
    expect(screen.getByText("Bestätigte Scopes: 1")).toBeInTheDocument();
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
    render(
      <App
        runtimeLoader={() => nativeRuntime()}
        ssoStatusLoader={() => Promise.resolve(idleSso)}
        charactersLoader={() => Promise.resolve([character])}
        accountGroupsLoader={() => Promise.resolve([
          { id: 3, label: "Industry", sortOrder: 0, characterCount: 1 },
        ])}
        characterUpdater={characterUpdater}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Verwalten" }));
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
});
