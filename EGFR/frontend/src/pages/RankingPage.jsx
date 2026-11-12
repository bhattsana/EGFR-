import { useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  Database,
  FlaskConical,
  RotateCcw,
} from "lucide-react";
import { Link } from "react-router-dom";
import ApplicabilityDomain from "../components/ApplicabilityDomain";
import { analyzeMolecule, getApiErrorMessage, getApiStatus } from "../lib/api";

const MAX_CANDIDATES = 10;

export default function RankingPage() {
  const [smilesInput, setSmilesInput] = useState("");
  const [candidates, setCandidates] = useState([]);
  const [modelAvailable, setModelAvailable] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

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
    const inputs = smilesInput.split(/\r?\n/).map((smiles) => smiles.trim()).filter(Boolean);
    if (inputs.length === 0) {
      setError("Enter at least one SMILES string to analyze.");
      return;
    }
    if (inputs.length > MAX_CANDIDATES) {
      setError(`Analyze no more than ${MAX_CANDIDATES} structures at a time.`);
      return;
    }

    setError("");
    setCandidates([]);
    setIsLoading(true);
    try {
      const results = await Promise.all(
        inputs.map(async (inputSmiles, index) => {
          try {
            return { inputSmiles, candidateNumber: index + 1, result: await analyzeMolecule(inputSmiles) };
          } catch (requestError) {
            return {
              inputSmiles,
              candidateNumber: index + 1,
              error: getApiErrorMessage(requestError),
            };
          }
        })
      );

      const seenStructures = new Set();
      setCandidates(results.map((candidate) => {
        if (!candidate.result) return candidate;
        if (seenStructures.has(candidate.result.smiles)) {
          return {
            inputSmiles: candidate.inputSmiles,
            candidateNumber: candidate.candidateNumber,
            error: "This structure duplicates an earlier candidate after canonicalization.",
          };
        }
        seenStructures.add(candidate.result.smiles);
        return candidate;
      }));

      if (results.some((candidate) => candidate.result?.prediction_model_available === false)) {
        setModelAvailable(false);
      }
    } finally {
      setIsLoading(false);
    }
  }

  function clearCandidates() {
    setSmilesInput("");
    setCandidates([]);
    setError("");
  }

  const scoredCandidates = candidates
    .filter((candidate) => candidate.result?.prediction)
    .sort((left, right) => right.result.prediction.value - left.result.prediction.value);
  const unscoredCandidates = candidates.filter((candidate) => !candidate.result?.prediction);
  const hasPredictions = scoredCandidates.length > 0;
  const modelMetadata = scoredCandidates[0]?.result.prediction.model;
  const testMetrics = modelMetadata?.test_metrics?.random_forest;
  const intervalTestCoverage = modelMetadata?.test_metrics?.empirical_interval_90?.test_coverage;
  const displayedCandidates = hasPredictions
    ? [...scoredCandidates, ...unscoredCandidates]
    : candidates;

  return (
    <div className="page-wrap content-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-rule" /> CANDIDATE WORKSPACE</div>
          <h1>Candidate comparison</h1>
          <p>Analyze structures you provide and rank them only when eligible model outputs are available.</p>
        </div>
        <span className={`status-pill ${modelAvailable ? "status-pill-success" : "status-pill-warning"}`}>
          <span className="status-dot" />
          {modelAvailable === null ? "Model status unavailable" : modelAvailable ? "Model available" : "No eligible model"}
        </span>
      </div>

      <section className="panel ranking-input" aria-labelledby="candidate-input-title">
        <div className="panel-heading">
          <span className="panel-icon"><FlaskConical size={18} aria-hidden="true" /></span>
          <div>
            <h2 id="candidate-input-title">Your candidate structures</h2>
            <p>Enter one SMILES string per line. Up to {MAX_CANDIDATES} structures are analyzed per request.</p>
          </div>
        </div>
        <form onSubmit={handleSubmit} noValidate>
          <label className="field-label" htmlFor="candidate-smiles-input">Candidate SMILES</label>
          <textarea
            id="candidate-smiles-input"
            value={smilesInput}
            onChange={(event) => {
              setSmilesInput(event.target.value);
              if (error) setError("");
            }}
            maxLength={100000}
            placeholder="One molecular SMILES string per line"
            aria-describedby={error ? "candidate-smiles-help candidate-smiles-error" : "candidate-smiles-help"}
            aria-invalid={Boolean(error)}
            className="smiles-input ranking-smiles-input"
            spellCheck="false"
            autoComplete="off"
          />
          <div className="field-meta">
            <span id="candidate-smiles-help">Only actual API analyses are shown; no sample compounds or scores are added.</span>
            <span>{smilesInput.split(/\r?\n/).filter((line) => line.trim()).length} / {MAX_CANDIDATES}</span>
          </div>
          {error && (
            <div id="candidate-smiles-error" className="notice notice-error" role="alert">
              <AlertCircle size={17} aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}
          <div className="form-actions">
            <button className="button button-primary" type="submit" disabled={isLoading || !smilesInput.trim()}>
              {isLoading
                ? <><span className="spinner" aria-hidden="true" /> Analyzing candidates…</>
                : <>Analyze candidates <ArrowRight size={16} aria-hidden="true" /></>}
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={clearCandidates}
              disabled={isLoading || (!smilesInput && candidates.length === 0 && !error)}
            >
              <RotateCcw size={15} aria-hidden="true" /> Clear
            </button>
          </div>
        </form>
      </section>

      {modelAvailable !== true && (
        <div className="notice notice-info ranking-model-notice" role="status">
          <AlertCircle size={18} aria-hidden="true" />
          <div>
            <strong>{modelAvailable === null ? "Model status unavailable" : "Potency ranking is unavailable"}</strong>
            <p>
              Structure validation and descriptors can still run. A ranked potency comparison requires a trained,
              eligible model artifact; no scores will be substituted.
            </p>
          </div>
        </div>
      )}

      {isLoading && <p className="ranking-loading" role="status">Analyzing submitted structures with the API…</p>}

      {candidates.length > 0 && (
        <section className="panel ranking-results" aria-labelledby="comparison-results-title">
          <div className="ranking-results-heading">
            <div>
              <div className="eyebrow"><span className="eyebrow-rule" /> ANALYSIS RESPONSE</div>
              <h2 id="comparison-results-title">{hasPredictions ? "Model-based comparison" : "Structure analysis results"}</h2>
            </div>
            {hasPredictions && <span className="ranking-sort-label">Sorted by predicted pIC50 · higher implies lower IC50</span>}
          </div>
          {hasPredictions && (
            <>
              <p className="ranking-disclaimer">
                Estimates are exploratory human wild-type EGFR IC50 outputs, not clinical evidence or treatment guidance.
                Intervals are empirical, not clinical confidence intervals. Structural similarity screening describes
                resemblance to training compounds only and does not establish biological activity. Ordering is based on
                point estimates; overlapping intervals do not establish a meaningful potency difference.
              </p>
              <p className="ranking-model-provenance">
                Model {modelMetadata.version}
                {modelMetadata.dataset_release && ` · ChEMBL release: ${modelMetadata.dataset_release}`}
                {testMetrics?.mae_pIC50 != null && ` · Held-out scaffold test MAE: ${testMetrics.mae_pIC50.toFixed(2)} pIC50`}
                {intervalTestCoverage != null && ` · Held-out coverage of nominal 90% interval: ${(intervalTestCoverage * 100).toFixed(1)}%`}
              </p>
            </>
          )}
          <ol className="candidate-list">
            {displayedCandidates.map((candidate, index) => (
              <li className="candidate-card" key={`${candidate.inputSmiles}-${candidate.candidateNumber}`}>
                <div className="candidate-card-heading">
                  <span className="candidate-rank">
                    {candidate.result?.prediction ? `Rank ${index + 1}` : `Candidate ${candidate.candidateNumber}`}
                  </span>
                  {candidate.result?.prediction && <strong>{candidate.result.prediction.value.toFixed(2)} pIC50</strong>}
                </div>
                {candidate.error ? (
                  <p className="candidate-error" role="alert">{candidate.error}</p>
                ) : (
                  <>
                    <code className="candidate-smiles">{candidate.result.smiles}</code>
                    {candidate.result.prediction ? (
                      <>
                        <p className="candidate-interval">
                          Empirical interval: {candidate.result.prediction.empirical_interval.lower.toFixed(2)}–{candidate.result.prediction.empirical_interval.upper.toFixed(2)} pIC50
                          <span>Model {candidate.result.prediction.model.version}</span>
                        </p>
                        <ApplicabilityDomain
                          assessment={candidate.result.prediction.applicability_domain}
                        />
                      </>
                    ) : (
                      <p className="candidate-interval">Structure validated; no model prediction was generated.</p>
                    )}
                    <div className="candidate-descriptors">
                      <span>MW {candidate.result.descriptors.molecular_weight_da} Da</span>
                      <span>LogP {candidate.result.descriptors.crippen_logp}</span>
                      <span>TPSA {candidate.result.descriptors.tpsa_a2} Å²</span>
                    </div>
                  </>
                )}
              </li>
            ))}
          </ol>
        </section>
      )}

      {candidates.length === 0 && (
        <section className="panel ranking-empty" aria-labelledby="empty-title">
          <div className="empty-illustration" aria-hidden="true">
            <span><Database size={25} /></span>
            <i /><i /><i />
          </div>
          <div className="eyebrow"><span className="eyebrow-rule" /> NOTHING TO COMPARE YET</div>
          <h2 id="empty-title">Add structures to begin.</h2>
          <p>
            Submit molecular structures from a sourced dataset or your own research. Candidates are never populated
            with example molecules; potency sorting appears only when the configured model returns real outputs.
          </p>
          <Link className="button button-secondary" to="/analyzer">
            Open molecule analyzer <ArrowRight size={16} aria-hidden="true" />
          </Link>
          <div className="ranking-requirements">
            <div><FlaskConical size={16} aria-hidden="true" /><span>RDKit-validated structures</span></div>
            <div><BarChart3 size={16} aria-hidden="true" /><span>Eligible model for potency rank</span></div>
            <div><Database size={16} aria-hidden="true" /><span>Session-only comparison</span></div>
          </div>
        </section>
      )}
    </div>
  );
}
