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
});
