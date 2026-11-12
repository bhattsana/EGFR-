import { useEffect, useState } from "react";
import { ArrowDownRight, ArrowRight, Atom, Check, FlaskConical, HelpCircle, Layers3 } from "lucide-react";
import { Link } from "react-router-dom";
import { getApiStatus } from "../lib/api";

const workflow = [
  { number: "01", title: "Provide a molecule", description: "Enter a molecular structure as a SMILES string." },
  { number: "02", title: "Validate the input", description: "The service checks whether the structure can be parsed." },
  { number: "03", title: "Review available evidence", description: "Scores will appear when a trained model is configured." },
];

export default function LandingPage() {
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

  return (
    <div className="page-wrap landing-page">
      <section className="hero-section" aria-labelledby="hero-title">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-rule" /> EGFR INHIBITOR EXPLORATION</div>
          <h1 id="hero-title">A clearer view of the <span>molecules</span> behind the science.</h1>
          <p className="hero-description">
            A research interface for exploring EGFR inhibitor candidates in the NSCLC
            context. Start with a molecular structure and inspect the analysis workflow.
          </p>
          <div className="hero-actions">
            <Link className="button button-primary" to="/analyzer">
              Open molecule analyzer <ArrowRight size={17} aria-hidden="true" />
            </Link>
            <a className="text-link" href="#workflow">
              See how it works <ArrowDownRight size={16} aria-hidden="true" />
            </a>
          </div>
          <div className="hero-footnote">
            <HelpCircle size={15} aria-hidden="true" />
            <span>Exploratory research only. This interface is not for clinical use.</span>
          </div>
        </div>
        <div className="hero-visual" aria-label="Molecular research status">
          <div className="visual-topline">
            <span>WORKSPACE STATUS</span>
            <span className="status-pill status-pill-muted"><span className="status-dot" /> {modelAvailable === null ? "Checking" : modelAvailable ? "Model ready" : "No model"}</span>
          </div>
          <div className="molecule-art" aria-hidden="true">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="orbit orbit-three" />
            <span className="atom atom-center"><Atom size={28} /></span>
            <span className="atom atom-a" />
            <span className="atom atom-b" />
            <span className="atom atom-c" />
            <span className="atom atom-d" />
            <span className="bond bond-a" />
            <span className="bond bond-b" />
            <span className="bond bond-c" />
            <span className="bond bond-d" />
          </div>
          <div className="visual-caption">
            <span>MOLECULAR WORKFLOW</span>
            <strong>Structure in. Evidence out.</strong>
          </div>
          <div className="model-note">
            <span className="model-note-icon"><FlaskConical size={17} /></span>
            <span>
              <strong>{modelAvailable === null ? "Prediction service status unavailable" : modelAvailable ? "Research model configured" : "Prediction model not configured"}</strong>
              <small>{modelAvailable ? "Exploratory endpoint estimates; not clinically validated." : "Molecular descriptors remain available without a model."}</small>
            </span>
          </div>
        </div>
      </section>

      <section id="workflow" className="workflow-section" aria-labelledby="workflow-title">
        <div className="section-heading">
          <div>
            <div className="eyebrow"><span className="eyebrow-rule" /> A TRANSPARENT WORKFLOW</div>
            <h2 id="workflow-title">Designed around the molecule.</h2>
          </div>
          <p>Each step is explicit about what the current system can—and cannot—do.</p>
        </div>
        <div className="workflow-grid">
          {workflow.map((step) => (
            <article className="workflow-card" key={step.number}>
              <span className="workflow-number">{step.number}</span>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
              <Check className="workflow-check" size={17} aria-hidden="true" />
            </article>
          ))}
        </div>
      </section>

      <section className="scope-banner" aria-label="Project scope">
        <div className="scope-icon"><Layers3 size={20} aria-hidden="true" /></div>
        <div>
          <strong>A research prototype, with its limits in plain sight.</strong>
          <p>Candidate scoring and ranking require a validated prediction model and a real candidate dataset.</p>
        </div>
        <Link to="/ranking" className="text-link">View ranking workspace <ArrowRight size={15} aria-hidden="true" /></Link>
      </section>
    </div>
  );
}
