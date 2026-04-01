import { useEffect, useState } from 'react'

export default function PostgameView({ apiBase, gameId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    fetch(`${apiBase}/game/${gameId}/postgame`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((d) => { setData(d); setLoading(false) })
      .catch((err) => { setError(err.message); setLoading(false) })
  }, [apiBase, gameId])

  if (loading) return <div className="text-zinc-500 py-10">Loading post-game analysis…</div>
  if (error) return <div className="text-red-400 py-10">Failed to load post-game analysis: {error}</div>
  if (!data) return null

  return (
    <div className="space-y-6">
      <div className="text-sm text-zinc-400">
        Status: <span className="text-zinc-200">{data.status}</span> · Total pitches tracked: {data.total_pitches}
      </div>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
        <h3 className="font-semibold text-white mb-3">Pitcher progression + deviations</h3>
        <div className="space-y-3">
          {data.pitchers?.map((p) => (
            <div key={p.pitcher_id} className="border border-zinc-800 rounded-lg p-3">
              <p className="text-sm font-medium text-white">{p.pitcher_name}</p>
              <p className="text-xs text-zinc-400 mt-1">
                Velo delta vs norm: {p.deviations?.velo_delta ?? 'N/A'} mph · Whiff delta: {p.deviations?.whiff_delta ?? 'N/A'}
              </p>
              <div className="mt-2 text-xs text-zinc-300">
                Biggest pitch-mix changes:{' '}
                {p.deviations?.pitch_mix?.slice(0, 3).map((d) => `${d.pitch_type} ${d.delta > 0 ? '+' : ''}${d.delta}pp`).join(', ') || 'N/A'}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
        <h3 className="font-semibold text-white mb-3">Hitter success/failure vs personal norms</h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {data.hitters?.map((h) => (
            <div key={h.batter_id} className="border border-zinc-800 rounded-lg p-3">
              <p className="text-sm font-medium text-white">{h.batter_name}</p>
              <p className="text-xs text-zinc-400 mt-1">{h.summary?.join(' · ') || 'No strong deviations captured.'}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
