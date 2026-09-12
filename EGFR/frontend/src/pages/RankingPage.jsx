export default function RankingPage() {

  const data = [
    { name: "Erlotinib Analog", score: 0.92 },
    { name: "Gefitinib Analog", score: 0.87 },
    { name: "Osimertinib Analog", score: 0.84 }
  ];

  return (
    <div className="min-h-screen bg-black text-white p-10">

      <h1 className="text-5xl font-bold mb-10">
        Candidate Leaderboard
      </h1>

      <div className="bg-zinc-900 rounded-2xl p-6">

        <table className="w-full">
          <thead>
            <tr className="border-b border-zinc-700 text-left">
              <th className="pb-4">Rank</th>
              <th className="pb-4">Molecule</th>
              <th className="pb-4">Score</th>
            </tr>
          </thead>

          <tbody>
            {data.map((molecule, idx) => (
              <tr key={idx} className="border-b border-zinc-800">
                <td className="py-4">{idx + 1}</td>
                <td>{molecule.name}</td>
                <td>{molecule.score}</td>
              </tr>
            ))}
          </tbody>
        </table>

      </div>
    </div>
  );
}