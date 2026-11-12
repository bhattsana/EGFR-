const statusLabels = {
  in_domain: "Within calibration similarity range",
  borderline: "Near the lower calibration similarity range",
  out_of_domain: "Below calibration similarity range",
  unavailable: "Structural support unavailable",
};

const statusClasses = {
  in_domain: "domain-status-supported",
  borderline: "domain-status-borderline",
  out_of_domain: "domain-status-outside",
  unavailable: "domain-status-unavailable",
};

export default function ApplicabilityDomain({ assessment }) {
  if (!assessment) {
    return (
      <div className="applicability-domain domain-status-unavailable" role="status">
        <strong>Structural support unavailable</strong>
        <p>No applicability-domain result was included with this prediction.</p>
      </div>
    );
  }

  const status = statusLabels[assessment.status] ? assessment.status : "unavailable";
  const neighbors = assessment.nearest_neighbors || [];

  return (
    <section
      className={`applicability-domain ${statusClasses[status]}`}
      aria-label="Applicability-domain screening"
    >
      <div className="applicability-domain-heading">
        <strong>{statusLabels[status]}</strong>
        {assessment.nearest_training_similarity != null && (
          <span>
            Nearest training similarity:{" "}
            {assessment.nearest_training_similarity.toFixed(2)}
          </span>
        )}
      </div>
      <p>{assessment.interpretation}</p>
      {neighbors.length > 0 && (
        <details>
          <summary>Nearest training neighbors ({neighbors.length})</summary>
          <ol>
            {neighbors.map((neighbor) => (
              <li key={`${neighbor.smiles}-${neighbor.tanimoto_similarity}`}>
                <code>{neighbor.smiles}</code>
                <span>{neighbor.tanimoto_similarity.toFixed(2)}</span>
              </li>
            ))}
          </ol>
        </details>
      )}
    </section>
  );
}
