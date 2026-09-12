import { useState } from "react";
import axios from "axios";

export default function AnalyzerPage() {

  const [smiles, setSmiles] = useState("");
  const [result, setResult] = useState(null);

  const analyze = async () => {
    const res = await axios.post(
      "http://127.0.0.1:8000/predict",
      { smiles }
    );

    setResult(res.data);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-10">

      <h1 className="text-5xl font-bold mb-10">
        Molecular Analyzer
      </h1>

      <textarea
        value={smiles}
        onChange={(e) => setSmiles(e.target.value)}
        placeholder="Paste SMILES string..."
        className="w-full h-40 bg-zinc-900 rounded-2xl p-6 text-lg"
      />

      <button
        onClick={analyze}
        className="mt-6 px-8 py-4 bg-emerald-500 rounded-2xl font-bold"
      >
        Analyze Molecule
      </button>

      {result && (
        <div className="grid grid-cols-2 gap-6 mt-10">

          <div className="bg-zinc-900 rounded-2xl p-6">
            <h2 className="text-xl font-bold">Efficacy</h2>
            <p className="text-4xl mt-4">{result.efficacy}</p>
          </div>

          <div className="bg-zinc-900 rounded-2xl p-6">
            <h2 className="text-xl font-bold">Safety</h2>
            <p className="text-4xl mt-4">{result.safety}</p>
          </div>

          <div className="bg-zinc-900 rounded-2xl p-6">
            <h2 className="text-xl font-bold">Synthetic Accessibility</h2>
            <p className="text-4xl mt-4">{result.synthetic_accessibility}</p>
          </div>

          <div className="bg-zinc-900 rounded-2xl p-6">
            <h2 className="text-xl font-bold">Final Score</h2>
            <p className="text-4xl mt-4">{result.final_score}</p>
          </div>

        </div>
      )}

    </div>
  );
}