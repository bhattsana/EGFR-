import { useEffect, useState } from "react";
import {
  ArrowDownRight,
  ArrowRight,
  Atom,
  BarChart3,
  Check,
  FlaskConical,
  HelpCircle,
  Layers3,
  Pause,
  Play,
  ScanLine,
} from "lucide-react";
import { Link } from "react-router-dom";
import { getApiStatus } from "../lib/api";

const workflow = [
  { number: "01", title: "Provide a molecule", description: "Enter a molecular structure as a SMILES string." },
  { number: "02", title: "Validate the input", description: "The service checks whether the structure can be parsed." },
  { number: "03", title: "Review available evidence", description: "Scores appear only when an eligible trained model is configured." },
];

const features = [
  {
    title: "Molecular analysis",
    description: "Validate a structure and inspect calculated molecular descriptors.",
    icon: FlaskConical,
    to: "/analyzer",
    action: "Analyze a structure",
  },
  {
    title: "3D exploration",
    description: "Inspect accurate 2D depictions today; real 3D exploration needs conformer coordinates.",
    icon: ScanLine,
    to: "/analyzer",
    action: "Explore structure tools",
  },
  {
    title: "Candidate ranking",
    description: "Compare submitted structures when eligible model predictions are available.",
    icon: BarChart3,
    to: "/ranking",
    action: "Compare candidates",
  },
];

export default function LandingPage() {
  const [modelAvailable, setModelAvailable] = useState(null);
  const [visualizationPaused, setVisualizationPaused] = useState(false);

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
          <div className="eyebrow"><span className="eyebrow-rule" /> EGFR RESEARCH <span className="eyebrow-divider">/</span> NSCLC CONTEXT</div>
          <h1 id="hero-title">Explore the Molecular <span>Universe.</span></h1>
          <p className="hero-description">
            Discover EGFR inhibitor candidates through molecular analysis, structural insights and model-driven research.
          </p>
          <div className="hero-actions">
            <Link className="button button-primary" to="/analyzer">
              <FlaskConical size={16} aria-hidden="true" /> Analyze Molecule <ArrowRight size={16} aria-hidden="true" />
            </Link>
            <Link className="button button-secondary" to="/ranking">
              Candidate Ranking <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
          <a className="hero-workflow-link" href="#workflow">
            Explore the workflow <ArrowDownRight size={15} aria-hidden="true" />
          </a>
          <div className="hero-footnote">
            <HelpCircle size={15} aria-hidden="true" />
            <span>Exploratory research only. This interface is not for clinical use.</span>
          </div>
        </div>

        <div className="hero-visual" aria-label="Research workspace status and illustrative molecular-universe visualization">
          <div className="universe-starfield" aria-hidden="true" />
          <div className="visual-topline">
            <span>EGFR RESEARCH / LIVE STATUS</span>
            <span className={`status-pill ${modelAvailable === null ? "status-pill-muted" : modelAvailable ? "status-pill-success" : "status-pill-warning"}`}>
              <span className="status-dot" />
              {modelAvailable === null ? "Checking" : modelAvailable ? "Model ready" : "No model"}
            </span>
          </div>
          <div className={`molecule-art${visualizationPaused ? " molecule-art-paused" : ""}`} aria-hidden="true">
            <div className="visual-grid" />
            <div className="universe-core-glow" />
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="orbit orbit-three" />
            <span className="atom atom-center"><Atom size={25} /></span>
            <span className="atom atom-a" />
            <span className="atom atom-b" />
            <span className="atom atom-c" />
            <span className="atom atom-d" />
            <span className="bond bond-a" />
            <span className="bond bond-b" />
            <span className="bond bond-c" />
            <span className="bond bond-d" />
            <span className="visual-particle visual-particle-a" />
            <span className="visual-particle visual-particle-b" />
            <span className="visual-particle visual-particle-c" />
            <span className="visual-particle visual-particle-d" />
          </div>
          <div className="visual-floating-note" aria-label="Illustrative visualization, not molecular coordinates">
            <span className="floating-note-icon"><Atom size={15} aria-hidden="true" /></span>
            <span><strong>Conceptual field</strong><small>Illustrative · not molecular coordinates</small></span>
          </div>
          <div className="visual-caption">
            <div>
              <span>MOLECULAR UNIVERSE · CONCEPT VISUAL</span>
              <strong>Explore the science behind every structure.</strong>
              <small>Decorative visualization · not a specific molecule or experimental result</small>
            </div>
            <button
              className="visualization-control"
              type="button"
              onClick={() => setVisualizationPaused((paused) => !paused)}
              aria-label={visualizationPaused ? "Resume orbital animation" : "Pause orbital animation"}
              aria-pressed={visualizationPaused}
            >
              {visualizationPaused ? <Play size={15} aria-hidden="true" /> : <Pause size={15} aria-hidden="true" />}
            </button>
          </div>
          <div className="model-note">
            <span className="model-note-icon"><FlaskConical size={17} aria-hidden="true" /></span>
            <span>
              <strong>
                {modelAvailable === null
                  ? "Prediction service status unavailable"
                  : modelAvailable
                    ? "Research model configured"
                    : "Prediction model not configured"}
              </strong>
              <small>
                {modelAvailable
                  ? "Exploratory endpoint estimates; not clinically validated."
                  : "Molecular descriptors remain available without a model."}
              </small>
            </span>
          </div>
        </div>
      </section>

      <section className="feature-section" aria-labelledby="feature-title">
        <div className="section-heading">
          <div>
            <div className="eyebrow"><span className="eyebrow-rule" /> RESEARCH CAPABILITIES</div>
            <h2 id="feature-title">A closer look at every structure.</h2>
          </div>
          <p>Purpose-built tools make the analysis and its limits easy to understand.</p>
        </div>
        <div className="feature-grid">
          {features.map(({ title, description, icon: Icon, to, action }) => (
            <Link className="feature-card" to={to} key={title}>
              <span className="feature-icon"><Icon size={19} aria-hidden="true" /></span>
              <h3>{title}</h3>
              <p>{description}</p>
              <span className="feature-action">{action}<ArrowRight size={14} aria-hidden="true" /></span>
            </Link>
          ))}
        </div>
      </section>

      <section id="workflow" className="workflow-section" aria-labelledby="workflow-title">
        <div className="section-heading">
          <div>
            <div className="eyebrow"><span className="eyebrow-rule" /> A TRANSPARENT WORKFLOW</div>
            <h2 id="workflow-title">Research, grounded in the molecule.</h2>
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
          <p>Candidate scoring and ranking require an eligible prediction model and real candidate structures. Model estimates are exploratory, not clinically validated.</p>
        </div>
        <Link to="/ranking" className="text-link">Explore candidate ranking <ArrowRight size={15} aria-hidden="true" /></Link>
      </section>
    </div>
  );
}
