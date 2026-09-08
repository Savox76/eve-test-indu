import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

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

  it("shows Savoxmedia as the local operator in the navigation", () => {
    render(<App />);

    expect(screen.getByText("Savoxmedia")).toBeInTheDocument();
    expect(screen.getByText("Lokaler Betreiber")).toBeInTheDocument();
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
});
