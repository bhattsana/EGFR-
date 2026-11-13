import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Atom, Info, RotateCcw } from "lucide-react";

const Molecule3DCanvas = lazy(() => import("./Molecule3DCanvas"));

export default function StructureViewer({
  result,
  conformer,
  isGenerating3D,
  generationError,
  onGenerate3D,
}) {
  const [mode, setMode] = useState("2d");
  const [showAtomLabels, setShowAtomLabels] = useState(false);
  const [hoveredAtom, setHoveredAtom] = useState(null);
  const [renderError, setRenderError] = useState("");
  const canvasRef = useRef(null);
  const imageAvailable = Boolean(result?.depiction_png_base64);

  useEffect(() => {
    setMode("2d");
    setShowAtomLabels(false);
    setHoveredAtom(null);
    setRenderError("");
  }, [result?.smiles]);

  function selectMode(nextMode) {
    setMode(nextMode);
    setHoveredAtom(null);
    if (nextMode === "3d" && !conformer && !isGenerating3D) onGenerate3D();
  }

  const optimization = conformer?.optimization;
  const optimizationSummary = optimization?.force_field === "none"
    ? "No supported force field was available; coordinates are from the RDKit conformer."
    : optimization
      ? `${optimization.force_field} geometry optimization ${optimization.converged ? "converged" : "did not converge within the iteration limit"}.`
      : "";

  return (
    <section className="panel structure-viewer-panel" aria-label="Molecular visualization">
      <div className="viewer-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-rule" /> STRUCTURE VIEW</div>
          <h2>{imageAvailable ? "Analyzed molecule" : "Visualization workspace"}</h2>
        </div>
        <div className="viewer-heading-controls">
          <div className="viewer-controls" role="group" aria-label="Visualization mode">
            <button
              type="button"
              className={`viewer-mode${mode === "2d" ? " viewer-mode-active" : ""}`}
              aria-pressed={mode === "2d"}
              onClick={() => selectMode("2d")}
            >
              2D
            </button>
            <button
              type="button"
              className={`viewer-mode${mode === "3d" ? " viewer-mode-active" : ""}`}
              aria-pressed={mode === "3d"}
              disabled={!imageAvailable || isGenerating3D}
              onClick={() => selectMode("3d")}
              aria-describedby="viewer-3d-unavailable"
              title={imageAvailable ? "Generate and inspect an RDKit 3D conformer." : "Analyze a structure first."}
            >
              3D
            </button>
          </div>
          {mode === "3d" && conformer && (
            <button
              type="button"
              className="viewer-reset"
              onClick={() => canvasRef.current?.reset()}
              aria-label="Reset 3D camera"
            >
              <RotateCcw size={15} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      <div className={`structure-viewer-canvas${imageAvailable ? " structure-viewer-populated" : ""}`}>
        {mode === "2d" ? (
          imageAvailable ? (
            <img
              src={`data:image/png;base64,${result.depiction_png_base64}`}
              alt={`RDKit-generated 2D depiction of ${result.smiles}`}
            />
          ) : (
            <div className="viewer-empty-state">
              <span className="viewer-empty-icon"><Atom size={28} aria-hidden="true" /></span>
              <strong>Awaiting a validated structure</strong>
              <span>Submit a SMILES string to display its 2D depiction.</span>
            </div>
          )
        ) : isGenerating3D ? (
          <div className="viewer-empty-state" role="status">
            <span className="spinner viewer-spinner" aria-hidden="true" />
            <strong>Generating 3D conformer</strong>
            <span>RDKit is embedding and optimizing the submitted structure.</span>
          </div>
        ) : generationError ? (
          <div className="viewer-empty-state" role="alert">
            <strong>3D conformer unavailable</strong>
            <span>{generationError}</span>
            <button type="button" className="button button-secondary viewer-retry" onClick={onGenerate3D}>
              Retry 3D generation
            </button>
            <button type="button" className="viewer-fallback-link" onClick={() => selectMode("2d")}>
              Return to the accurate 2D depiction
            </button>
          </div>
        ) : conformer ? (
          <Suspense fallback={
            <div className="viewer-empty-state" role="status">
              <span className="spinner viewer-spinner" aria-hidden="true" />
              <strong>Loading interactive 3D viewer</strong>
            </div>
          }>
            <Molecule3DCanvas
              ref={canvasRef}
              structure={conformer}
              showAtomLabels={showAtomLabels}
              onAtomHover={setHoveredAtom}
              onRenderError={setRenderError}
            />
          </Suspense>
        ) : (
          <div className="viewer-empty-state" role="status">
            <span className="spinner viewer-spinner" aria-hidden="true" />
            <strong>Preparing 3D conformer</strong>
          </div>
        )}
      </div>

      {mode === "3d" && conformer && (
        <div className="viewer-3d-toolbar">
          <label className="atom-label-toggle">
            <input
              type="checkbox"
              checked={showAtomLabels}
              onChange={(event) => setShowAtomLabels(event.target.checked)}
            />
            <span>Show atom labels</span>
          </label>
          <span className="viewer-atom-count">
            {conformer.atoms.length} atoms · {conformer.bonds.length} bonds
          </span>
        </div>
      )}

      {mode === "3d" && hoveredAtom && (
        <div className="viewer-hover-info" role="status" aria-live="polite">
          Atom {hoveredAtom.index + 1} · {hoveredAtom.element}
          {hoveredAtom.formal_charge ? ` · charge ${hoveredAtom.formal_charge}` : ""}
          {" · "}
          {hoveredAtom.coordinates.x.toFixed(2)}, {hoveredAtom.coordinates.y.toFixed(2)}, {hoveredAtom.coordinates.z.toFixed(2)} Å
        </div>
      )}
      {mode === "3d" && renderError && (
        <div className="viewer-render-error" role="status">
          3D rendering is unavailable in this browser: {renderError} Switch to 2D to see the RDKit depiction.
        </div>
      )}

      <div className="viewer-footnote">
        <Info size={15} aria-hidden="true" />
        <p id="viewer-3d-unavailable">
          {mode === "3d" && conformer
            ? `${optimizationSummary} Coordinates are generated from the submitted SMILES; a conformer is not evidence of biological activity.`
            : imageAvailable
              ? "2D depiction generated by RDKit. Request 3D to generate and inspect an actual RDKit conformer."
              : "3D coordinates are generated from the submitted structure after analysis."}
        </p>
      </div>
    </section>
  );
}
