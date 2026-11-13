import { NavLink } from "react-router-dom";
import { Activity, ArrowUpRight, FlaskConical, Layers3 } from "lucide-react";

const navigation = [
  { to: "/", label: "Overview", icon: Layers3, end: true },
  { to: "/analyzer", label: "Molecule analyzer", icon: FlaskConical },
  { to: "/ranking", label: "Candidate ranking", icon: Activity },
];

export default function AppShell({ children }) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="app-header">
        <div className="header-inner">
          <NavLink className="brand" to="/" aria-label="EGFR Molecular Universe home">
            <span className="brand-mark" aria-hidden="true"><Activity size={19} /></span>
            <span className="brand-copy">
              <span className="brand-name">EGFR<span className="brand-period">.</span></span>
              <span className="brand-caption">MOLECULAR UNIVERSE</span>
            </span>
          </NavLink>
          <nav className="primary-nav" aria-label="Main navigation">
            {navigation.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) => `nav-link${isActive ? " nav-link-active" : ""}`}
              >
                <Icon size={16} aria-hidden="true" />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
          <span className="header-status">
            <span className="status-dot" aria-hidden="true" />
            Research preview
          </span>
        </div>
      </header>
      <main id="main-content" className="main-content">
        {children}
      </main>
      <footer className="app-footer">
        <span>EGFR Molecular Research</span>
        <span className="footer-note">Exploratory research interface · Not for clinical use</span>
        <a href="https://www.chembl.org/" target="_blank" rel="noreferrer">
          ChEMBL <ArrowUpRight size={13} aria-hidden="true" />
        </a>
      </footer>
    </div>
  );
}
