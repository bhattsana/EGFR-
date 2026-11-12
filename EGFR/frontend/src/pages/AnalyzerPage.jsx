import { useEffect, useState } from "react";
import { AlertCircle, ArrowRight, CheckCircle2, FlaskConical, RotateCcw } from "lucide-react";
import { Link } from "react-router-dom";
import ApplicabilityDomain from "../components/ApplicabilityDomain";
import { analyzeMolecule, getApiErrorMessage, getApiStatus } from "../lib/api";

const descriptorFields = [
  { key: "molecular_weight_da", label: "Molecular weight", unit: "Da" },
  { key: "crippen_logp", label: "Crippen LogP", unit: "" },
  { key: "tpsa_a2", label: "TPSA", unit: "Å²" },
  { key: "h_bond_donors", label: "H-bond donors", unit: "" },
  { key: "h_bond_acceptors", label: "H-bond acceptors", unit: "" },
];

function StructureResults({ result }) {
  const testMetrics = result.prediction?.model?.test_metrics?.random_forest;
  const intervalTestCoverage = result.prediction?.model?.test_metrics?.empirical_interval_90?.test_coverage;

  return (
    <>
      <div className="structure-result-grid">
        <div className="structure-preview">
          <img
            src={`data:image/png;base64,${result.depiction_png_base64}`}
            alt={`2D depiction of ${result.smiles}`}
          />
          <span>2D structure generated from the submitted SMILES</span>
        </div>
        <div className="descriptor-panel">
          <h3>Calculated molecular descriptors</h3>
          <dl className="descriptor-grid">
            {descriptorFields.map(({ key, label, unit }) => (
              <div className="descriptor-item" key={key}>
                <dt>{label}</dt>
                <dd>{result.descriptors[key]}{unit && <span> {unit}</span>}</dd>
              </div>
            ))}
          </dl>
          <p>Descriptors are calculated from the parsed structure; they are not experimental assay results.</p>
        </div>
      </div>
      {result.prediction ? (
        <div className="prediction-result" aria-label="EGFR prediction">
          <div className="prediction-result-heading">
            <div><span>MODEL OUTPUT · EXPLORATORY</span><h3>Predicted wild-type EGFR IC50</h3></div>
            <span className="model-version">{result.prediction.model.version}</span>
          </div>
          <div className="prediction-value">
            <strong>{result.prediction.value.toFixed(2)}</strong>
            <span>pIC50</span>
          </div>
          <p>
            Empirical scaffold-calibration interval: {result.prediction.empirical_interval.lower.toFixed(2)}–{result.prediction.empirical_interval.upper.toFixed(2)} pIC50.
            This is a separate estimate of model uncertainty, not a clinical confidence interval.
          </p>
          <ApplicabilityDomain assessment={result.prediction.applicability_domain} />
          <small>Exploratory in-vitro endpoint estimate only. Not clinically validated; not a treatment recommendation.</small>
          <div className="prediction-provenance">
            {result.prediction.model.dataset_release && (
              <span>ChEMBL release: {result.prediction.model.dataset_release}</span>
            )}
            {testMetrics?.mae_pIC50 != null && (
              <span>Held-out scaffold test MAE: {testMetrics.mae_pIC50.toFixed(2)} pIC50</span>
            )}
            {intervalTestCoverage != null && (
              <span>Held-out coverage of nominal 90% interval: {(intervalTestCoverage * 100).toFixed(1)}%</span>
            )}
          </div>
        </div>
      ) : (
        <div className="notice notice-info" role="status">
          <AlertCircle size={18} aria-hidden="true" />
          <div><strong>Model prediction unavailable</strong><p>The structure and descriptors were calculated, but no trained, eligible model artifact is configured. No prediction value has been generated.</p></div>
        </div>
      )}
    </>
  );
}

export default function AnalyzerPage() {
  const [smiles, setSmiles] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [modelAvailable, setModelAvailable] = useState(null);

  useEffect(() => {
    let active = true;
    getApiStatus()
      .then((status) => {
        if (active) setModelAvailable(status.prediction_model_available === true);
      })
      .catch(() => {
        if (active) setModelAvailable(null);
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    const normalizedSmiles = smiles.trim();
    if (!normalizedSmiles) {
      setError("Enter a SMILES string before starting an analysis.");
      return;
    }

    setError("");
    setResult(null);
    setIsLoading(true);
    try {
      setResult(await analyzeMolecule(normalizedSmiles));
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }

  function clearForm() {
    setSmiles("");
    setError("");
    setResult(null);
  }

  return (
    <div className="page-wrap content-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-rule" /> ANALYSIS WORKSPACE</div>
          <h1>Molecule analyzer</h1>
          <p>Inspect a molecular structure, calculate descriptors, and review model output when available.</p>
        </div>
        <span className={`status-pill ${modelAvailable ? "status-pill-success" : "status-pill-warning"}`}>
          <span className="status-dot" /> {modelAvailable === null ? "Checking model status" : modelAvailable ? "Model available" : "Model unavailable"}
        </span>
      </div>

      <div className="analyzer-layout">
        <section className="panel analyzer-panel" aria-labelledby="structure-title">
          <div className="panel-heading">
            <span className="panel-icon"><FlaskConical size={18} aria-hidden="true" /></span>
            <div><h2 id="structure-title">Molecular structure</h2><p>Enter the structure using SMILES notation.</p></div>
          </div>
          <form onSubmit={handleSubmit} noValidate>
            <label className="field-label" htmlFor="smiles-input">SMILES string <span className="required-label">Required</span></label>
            <textarea
              id="smiles-input"
              name="smiles"
              value={smiles}
              onChange={(event) => {
                setSmiles(event.target.value);
                if (error) setError("");
              }}
              maxLength={10000}
              placeholder="Paste or type a molecular SMILES string"
              aria-describedby={error ? "smiles-help smiles-count smiles-error" : "smiles-help smiles-count"}
              aria-invalid={Boolean(error)}
              className="smiles-input"
              spellCheck="false"
              autoComplete="off"
            />
            <div className="field-meta">
              <span id="smiles-help">Whitespace around the input is ignored.</span>
              <span id="smiles-count">{smiles.length.toLocaleString()} / 10,000</span>
            </div>
            {error && <div id="smiles-error" className="notice notice-error" role="alert"><AlertCircle size={17} aria-hidden="true" /><span>{error}</span></div>}
            <div className="form-actions">
              <button className="button button-primary" type="submit" disabled={isLoading || !smiles.trim()}>
                {isLoading ? <><span className="spinner" aria-hidden="true" /> Analyzing structure…</> : <>Analyze structure <ArrowRight size={16} aria-hidden="true" /></>}
              </button>
              <button className="button button-secondary" type="button" onClick={clearForm} disabled={isLoading || (!smiles && !result && !error)}>
                <RotateCcw size={15} aria-hidden="true" /> Clear
              </button>
            </div>
          </form>
          <div className="panel-divider" />
          <p className="disclaimer">
            Structural validation, visualization, and descriptors do not require a prediction model.
            Model-based potency estimates are shown only when an eligible trained artifact is configured.
          </p>
        </section>

        <aside className="panel status-panel" aria-labelledby="status-title">
          <div className="status-panel-mark"><AlertCircle size={19} aria-hidden="true" /></div>
          <div className="eyebrow"><span className="eyebrow-rule" /> SYSTEM STATUS</div>
          <h2 id="status-title">{modelAvailable ? "A research model is configured" : modelAvailable === null ? "Model status unavailable" : "Scoring is not enabled"}</h2>
          <p>{modelAvailable
            ? "Predictions are exploratory, endpoint-specific estimates with limitations and uncertainty shown alongside the result."
            : "Structure validation and descriptors can still run. Model predictions remain unavailable until an eligible artifact is configured."}</p>
          <div className="status-list">
            <div><span className="status-list-icon status-ok"><CheckCircle2 size={15} /></span><span>Structure analysis</span><strong>Ready</strong></div>
            <div><span className={`status-list-icon ${modelAvailable ? "status-ok" : "status-pending"}`}>{modelAvailable ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />}</span><span>Model-based potency estimate</span><strong>{modelAvailable ? "Available" : "Unavailable"}</strong></div>
          </div>
          <Link className="status-link" to="/ranking">About candidate ranking <ArrowRight size={14} aria-hidden="true" /></Link>
        </aside>
      </div>

      {result && (
        <section className="results-section" aria-live="polite">
          <div className="results-heading">
            <div><div className="eyebrow"><span className="eyebrow-rule" /> ANALYSIS RESPONSE</div><h2>Submitted structure</h2></div>
            <span className="status-pill status-pill-success"><CheckCircle2 size={14} /> Request received</span>
          </div>
          <div className="submitted-structure"><span>CANONICAL ISOMERIC SMILES</span><code>{result.smiles}</code></div>
          <StructureResults result={result} />
        </section>
      )}
    </div>
  );
}
