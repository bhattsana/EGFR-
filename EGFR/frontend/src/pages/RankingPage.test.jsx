import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RankingPage from "./RankingPage";

const { analyzeMolecule, getApiStatus, getApiErrorMessage } = vi.hoisted(() => ({
  analyzeMolecule: vi.fn(),
  getApiStatus: vi.fn(),
  getApiErrorMessage: vi.fn((error) => error.message),
}));

vi.mock("../lib/api", () => ({
  analyzeMolecule,
  getApiStatus,
  getApiErrorMessage,
}));

function renderRankingPage() {
  return render(
    <MemoryRouter>
      <RankingPage />
    </MemoryRouter>
  );
}

function analysisResult(smiles, prediction = null) {
  return {
    smiles,
    descriptors: {
      molecular_weight_da: 46.069,
      crippen_logp: -0.001,
      tpsa_a2: 20.23,
      h_bond_donors: 1,
      h_bond_acceptors: 1,
    },
    prediction_model_available: Boolean(prediction),
    prediction,
  };
}

describe("RankingPage", () => {
  beforeEach(() => {
    getApiStatus.mockResolvedValue({ prediction_model_available: false });
  });

  it("allows structure comparison but does not show potency scores without a model", async () => {
    analyzeMolecule.mockResolvedValue(analysisResult("CCO"));
    renderRankingPage();

    fireEvent.change(screen.getByLabelText(/candidate smiles/i), {
      target: { value: "OCC" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze candidates/i }));

    expect(await screen.findByText("Structure validated; no model prediction was generated.")).toBeInTheDocument();
    expect(screen.getByText("Potency ranking is unavailable")).toBeInTheDocument();
    expect(screen.queryByText(/Rank 1/)).not.toBeInTheDocument();
    expect(analyzeMolecule).toHaveBeenCalledWith("OCC");
  });

  it("sorts only actual model predictions by descending pIC50", async () => {
    analyzeMolecule.mockImplementation(async (smiles) => {
      const value = smiles === "CCO" ? 5.2 : 7.1;
      const domainStatus = smiles === "CCO" ? "in_domain" : "out_of_domain";
      return analysisResult(smiles, {
        value,
        empirical_interval: { lower: value - 0.6, upper: value + 0.6 },
        applicability_domain: {
          status: domainStatus,
          nearest_training_similarity: smiles === "CCO" ? 0.62 : 0.08,
          thresholds: {
            out_of_domain_below: 0.15,
            in_domain_at_or_above: 0.4,
          },
          nearest_neighbors: [
            { smiles: "CCN", tanimoto_similarity: 0.62 },
          ],
          reference_version: "egfr-wt-ic50-test-domain-v1",
          method: "Morgan radius 2 / 2048-bit Tanimoto",
          interpretation:
            "Structural similarity describes resemblance only; it does not establish EGFR activity or prediction accuracy.",
        },
        model: {
          version: "egfr-wt-ic50-test",
          dataset_release: "ChEMBL_37",
          test_metrics: {
            random_forest: { mae_pIC50: 1.23 },
            empirical_interval_90: { test_coverage: 0.84 },
          },
        },
      });
    });
    renderRankingPage();

    fireEvent.change(screen.getByLabelText(/candidate smiles/i), {
      target: { value: "CCO\nCCC" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze candidates/i }));

    const rankOne = await screen.findByText("Rank 1");
    const rankOneCard = rankOne.closest("li");
    expect(within(rankOneCard).getByText("CCC")).toBeInTheDocument();
    expect(within(rankOneCard).getByText("7.10 pIC50")).toBeInTheDocument();
    expect(screen.getByText(/Sorted by predicted pIC50/)).toBeInTheDocument();
    expect(screen.getByText(/ChEMBL release: ChEMBL_37/)).toBeInTheDocument();
    expect(screen.getByText(/Held-out scaffold test MAE: 1.23 pIC50/)).toBeInTheDocument();
    expect(screen.getByText(/Held-out coverage of nominal 90% interval: 84.0%/)).toBeInTheDocument();
    expect(screen.getByText("Below calibration similarity range")).toBeInTheDocument();
    expect(screen.getByText("Within calibration similarity range")).toBeInTheDocument();
    expect(screen.getAllByText(/does not establish EGFR activity/)).toHaveLength(2);
    fireEvent.click(screen.getAllByText(/Nearest training neighbors/)[0]);
    expect(screen.getAllByText("CCN")).toHaveLength(2);
  });

  it("shows individual structure errors and enforces the candidate limit", async () => {
    analyzeMolecule.mockRejectedValue(new Error("Invalid SMILES."));
    renderRankingPage();

    fireEvent.change(screen.getByLabelText(/candidate smiles/i), {
      target: { value: "invalid" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze candidates/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid SMILES.");

    fireEvent.change(screen.getByLabelText(/candidate smiles/i), {
      target: { value: Array(11).fill("CCO").join("\n") },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze candidates/i }));
    expect(await screen.findByText("Analyze no more than 10 structures at a time.")).toBeInTheDocument();
    expect(analyzeMolecule).toHaveBeenCalledTimes(1);
  });
});
