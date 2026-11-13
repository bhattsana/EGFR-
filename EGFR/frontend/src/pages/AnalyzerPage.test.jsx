import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AnalyzerPage from "./AnalyzerPage";

const { analyzeMolecule, generate3DStructure, getApiStatus } = vi.hoisted(() => ({
  analyzeMolecule: vi.fn(),
  generate3DStructure: vi.fn(),
  getApiStatus: vi.fn(),
}));

vi.mock("../lib/api", () => ({
  analyzeMolecule,
  generate3DStructure,
  getApiStatus,
  getApiErrorMessage: () => "Could not reach the analysis service.",
}));

vi.mock("../components/Molecule3DCanvas", () => ({
  default: ({ structure }) => (
    <div data-testid="molecule-3d-canvas">
      Rendered {structure.atoms.length} actual atoms
    </div>
  ),
}));

function renderAnalyzer() {
  return render(
    <MemoryRouter>
      <AnalyzerPage />
    </MemoryRouter>
  );
}

describe("AnalyzerPage", () => {
  beforeEach(() => {
    analyzeMolecule.mockReset();
    generate3DStructure.mockReset();
    getApiStatus.mockResolvedValue({ prediction_model_available: false });
  });

  it("disables submit for empty input and shows service errors", async () => {
    analyzeMolecule.mockRejectedValue(new Error("network error"));
    renderAnalyzer();

    const submit = screen.getByRole("button", { name: /analyze structure/i });
    expect(submit).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/smiles string/i), {
      target: { value: "CCO" },
    });
    expect(submit).toBeEnabled();
    fireEvent.click(submit);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not reach the analysis service."
    );
  });

  it("shows RDKit analysis without inventing a model prediction", async () => {
    analyzeMolecule.mockResolvedValue({
      smiles: "CCO",
      descriptors: {
        molecular_weight_da: 46.069,
        crippen_logp: -0.001,
        tpsa_a2: 20.23,
        h_bond_donors: 1,
        h_bond_acceptors: 1,
      },
      depiction_png_base64: "cG5n",
      prediction_model_available: false,
      prediction: null,
    });
    renderAnalyzer();
    fireEvent.change(screen.getByLabelText(/smiles string/i), {
      target: { value: "OCC" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze structure/i }));

    expect(await screen.findByText("Calculated molecular descriptors")).toBeInTheDocument();
    expect(screen.getByText("46.069")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /2d depiction of CCO/i })).toHaveAttribute(
      "src",
      "data:image/png;base64,cG5n"
    );
    expect(screen.getByText("Model prediction unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Predicted wild-type EGFR IC50")).not.toBeInTheDocument();
    expect(analyzeMolecule).toHaveBeenCalledWith("OCC");
  });

  it("requests and displays an RDKit conformer for the submitted SMILES", async () => {
    analyzeMolecule.mockResolvedValue({
      smiles: "CCO",
      descriptors: {
        molecular_weight_da: 46.069,
        crippen_logp: -0.001,
        tpsa_a2: 20.23,
        h_bond_donors: 1,
        h_bond_acceptors: 1,
      },
      depiction_png_base64: "cG5n",
      prediction_model_available: false,
      prediction: null,
    });
    generate3DStructure.mockResolvedValue({
      smiles: "CCO",
      atoms: Array.from({ length: 9 }, (_, index) => ({ index, element: "C" })),
      bonds: Array.from({ length: 8 }, (_, index) => ({ begin: index, end: index + 1 })),
      optimization: { force_field: "MMFF94", converged: true },
    });
    renderAnalyzer();
    fireEvent.change(screen.getByLabelText(/smiles string/i), {
      target: { value: "  OCC  " },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze structure/i }));
    await screen.findByText("Calculated molecular descriptors");
    fireEvent.click(screen.getByRole("button", { name: "3D" }));

    expect(await screen.findByTestId("molecule-3d-canvas")).toHaveTextContent(
      "Rendered 9 actual atoms"
    );
    expect(generate3DStructure).toHaveBeenCalledWith("OCC");
    expect(screen.getByText("MMFF94 geometry optimization converged. Coordinates are generated from the submitted SMILES; a conformer is not evidence of biological activity.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset 3D camera" })).toBeInTheDocument();
  });

  it("shows a clear error and keeps the 2D structure available when 3D generation fails", async () => {
    analyzeMolecule.mockResolvedValue({
      smiles: "CCO",
      descriptors: {
        molecular_weight_da: 46.069,
        crippen_logp: -0.001,
        tpsa_a2: 20.23,
        h_bond_donors: 1,
        h_bond_acceptors: 1,
      },
      depiction_png_base64: "cG5n",
      prediction_model_available: false,
      prediction: null,
    });
    generate3DStructure.mockRejectedValue(new Error("conformer unavailable"));
    renderAnalyzer();
    fireEvent.change(screen.getByLabelText(/smiles string/i), {
      target: { value: "CCO" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze structure/i }));
    await screen.findByText("Calculated molecular descriptors");
    fireEvent.click(screen.getByRole("button", { name: "3D" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not reach the analysis service."
    );
    fireEvent.click(screen.getByRole("button", { name: /return to the accurate 2d depiction/i }));
    expect(screen.getByRole("img", { name: /2d depiction of CCO/i })).toBeInTheDocument();
  });

  it("clears the submitted structure and analysis", async () => {
    analyzeMolecule.mockResolvedValue({
      smiles: "CCO",
      descriptors: {
        molecular_weight_da: 46.069,
        crippen_logp: -0.001,
        tpsa_a2: 20.23,
        h_bond_donors: 1,
        h_bond_acceptors: 1,
      },
      depiction_png_base64: "cG5n",
      prediction_model_available: false,
      prediction: null,
    });
    renderAnalyzer();
    const input = screen.getByLabelText(/smiles string/i);
    fireEvent.change(input, { target: { value: "CCO" } });
    fireEvent.click(screen.getByRole("button", { name: /analyze structure/i }));
    await screen.findByText("Calculated molecular descriptors");
    fireEvent.click(screen.getByRole("button", { name: /clear/i }));

    await waitFor(() => expect(input).toHaveValue(""));
    expect(screen.queryByText("Calculated molecular descriptors")).not.toBeInTheDocument();
  });

  it("shows model provenance, held-out metrics, and uncertainty with a real prediction response", async () => {
    analyzeMolecule.mockResolvedValue({
      smiles: "CCO",
      descriptors: {
        molecular_weight_da: 46.069,
        crippen_logp: -0.001,
        tpsa_a2: 20.23,
        h_bond_donors: 1,
        h_bond_acceptors: 1,
      },
      depiction_png_base64: "cG5n",
      prediction_model_available: true,
      prediction: {
        value: 7.123,
        empirical_interval: { lower: 5.84, upper: 8.41 },
        applicability_domain: {
          status: "borderline",
          nearest_training_similarity: 0.27,
          thresholds: {
            out_of_domain_below: 0.18,
            in_domain_at_or_above: 0.31,
          },
          nearest_neighbors: [
            { smiles: "CCN", tanimoto_similarity: 0.27 },
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
            random_forest: { mae_pIC50: 0.6986 },
            empirical_interval_90: { test_coverage: 0.8389 },
          },
        },
      },
    });
    renderAnalyzer();
    fireEvent.change(screen.getByLabelText(/smiles string/i), {
      target: { value: "CCO" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze structure/i }));

    expect(await screen.findByText("Predicted wild-type EGFR IC50")).toBeInTheDocument();
    expect(screen.getByText("ChEMBL release: ChEMBL_37")).toBeInTheDocument();
    expect(screen.getByText("Held-out scaffold test MAE: 0.70 pIC50")).toBeInTheDocument();
    expect(screen.getByText("Held-out coverage of nominal 90% interval: 83.9%")).toBeInTheDocument();
    expect(screen.getByText("Near the lower calibration similarity range")).toBeInTheDocument();
    expect(screen.getByText("Nearest training similarity: 0.27")).toBeInTheDocument();
    expect(screen.getByText(/Empirical scaffold-calibration interval:/)).toBeInTheDocument();
    expect(screen.getByText(/does not establish EGFR activity or prediction accuracy/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Nearest training neighbors (1)"));
    expect(screen.getByText("CCN")).toBeInTheDocument();
  });

  it("labels a missing domain assessment as unavailable without hiding the prediction", async () => {
    analyzeMolecule.mockResolvedValue({
      smiles: "CCO",
      descriptors: {
        molecular_weight_da: 46.069,
        crippen_logp: -0.001,
        tpsa_a2: 20.23,
        h_bond_donors: 1,
        h_bond_acceptors: 1,
      },
      depiction_png_base64: "cG5n",
      prediction_model_available: true,
      prediction: {
        value: 7.123,
        empirical_interval: { lower: 5.84, upper: 8.41 },
        applicability_domain: {
          status: "unavailable",
          nearest_training_similarity: null,
          thresholds: null,
          nearest_neighbors: [],
          reference_version: null,
          method: "Morgan radius 2 / 2048-bit Tanimoto",
          interpretation:
            "The model prediction is available, but its matching applicability reference is not configured; structural support could not be assessed.",
        },
        model: {
          version: "egfr-wt-ic50-test",
          test_metrics: {},
        },
      },
    });
    renderAnalyzer();
    fireEvent.change(screen.getByLabelText(/smiles string/i), {
      target: { value: "CCO" },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze structure/i }));

    expect(await screen.findByText("Predicted wild-type EGFR IC50")).toBeInTheDocument();
    expect(screen.getByText("Structural support unavailable")).toBeInTheDocument();
    expect(screen.getByText(/matching applicability reference is not configured/)).toBeInTheDocument();
  });
});
