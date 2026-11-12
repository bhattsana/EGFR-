import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section className="page-wrap content-page not-found-page">
      <div className="eyebrow"><span className="eyebrow-rule" /> PAGE NOT FOUND</div>
      <h1>This page isn't in the workspace.</h1>
      <p>The address may be outdated, or the page may have moved.</p>
      <div className="hero-actions">
        <Link className="button button-secondary" to="/analyzer">Open molecule analyzer</Link>
        <Link className="button button-primary" to="/">Return to overview <ArrowRight size={15} /></Link>
      </div>
    </section>
  );
}
