import { useState } from 'react'
import PitcherProfile from './PitcherProfile'
import EdgeScore from './EdgeScore'
import NarrativeSection from './NarrativeSection'
import BlendBadge from './BlendBadge'

function PlayerSearch({ label, onSelect }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [selected, setSelected] = useState(null)

  function search() {
    if (query.length < 2) return
    setSearching(true)
    fetch(`/api/players/search?q=${encodeURIComponent(query)}`)
      .then((r) => r.json())
      .then((data) => { setResults(data); setSearching(false) })
      .catch(() => setSearching(false))
  }

  function pick(player) {
    setSelected(player)
    setResults([])
    setQuery(player.name)
    onSelect(player)
  }

  return (
    <div className="relative">
      <label className="block text-xs text-zinc-400 mb-1">{label}</label>
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
          placeholder="Player name..."
          className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-1.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-blue-500"
        />
        <button
          onClick={search}
          disabled={searching}
          className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm rounded transition-colors disabled:opacity-50"
        >
          {searching ? '…' : 'Search'}
        </button>
      </div>
      {results.length > 0 && (
        <div className="absolute z-10 top-full left-0 right-0 mt-1 bg-zinc-900 border border-zinc-700 rounded-lg overflow-hidden shadow-xl">
          {results.slice(0, 8).map((p) => (
            <button
              key={p.player_id}
              onClick={() => pick(p)}
              className="w-full text-left px-3 py-2 text-sm hover:bg-zinc-800 transition-colors"
            >
              <span className="text-white">{p.name}</span>
              <span className="text-zinc-500 ml-2 text-xs">
                {p.position} · {p.pitch_hand ?? p.bat_side ?? '?'} · {p.team ?? 'FA'}
              </span>
            </button>
          ))}
        </div>
      )}
      {selected && (
        <p className="text-xs text-green-400 mt-1">✓ {selected.name} (id={selected.player_id})</p>
      )}
    </div>
  )
}

export default function AdHocAnalyzer({ apiBase }) {
  const [pitcher, setPitcher] = useState(null)
  const [batter, setBatter] = useState(null)
  const [batterHand, setBatterHand] = useState('R')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  function analyze() {
    if (!pitcher || !batter) return
    setLoading(true)
    setError(null)
    const params = new URLSearchParams({
      pitcher_id: pitcher.player_id,
      batter_id: batter.player_id,
      pitcher_name: pitcher.name,
      batter_name: batter.name,
      batter_hand: batter.bat_side ?? batterHand,
    })
    fetch(`${apiBase}/adhoc?${params}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((d) => { setResult(d); setLoading(false) })
      .catch((err) => { setError(err.message); setLoading(false) })
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2 text-white">Ad Hoc Analyzer</h1>
      <p className="text-zinc-500 text-sm mb-6">
        Analyze any pitcher vs. any batter — relievers, non-today matchups, prop research.
      </p>

      {/* Inputs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 max-w-2xl">
        <PlayerSearch label="Pitcher" onSelect={setPitcher} />
        <PlayerSearch label="Batter" onSelect={setBatter} />
      </div>

      <div className="flex items-center gap-4 mb-6">
        <div>
          <label className="text-xs text-zinc-400 mr-2">Batter hand (if unknown):</label>
          {['L', 'R'].map((h) => (
            <button
              key={h}
              onClick={() => setBatterHand(h)}
              className={`mr-1 px-2 py-0.5 text-xs rounded transition-colors ${batterHand === h ? 'bg-zinc-600 text-white' : 'bg-zinc-800 text-zinc-400'}`}
            >
              {h}
            </button>
          ))}
        </div>
        <button
          onClick={analyze}
          disabled={!pitcher || !batter || loading}
          className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded transition-colors disabled:opacity-40"
        >
          {loading ? 'Analyzing…' : 'Analyze Matchup'}
        </button>
      </div>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {loading && (
        <p className="text-zinc-500 text-sm">
          Fetching Statcast data — may take a moment on first run…
        </p>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-8">
          {/* Narratives */}
          {result.narratives?.length > 0 && (
            <NarrativeSection narratives={result.narratives} />
          )}

          {/* Batter summary */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <h2 className="font-semibold text-white">{result.batter?.batter_name}</h2>
              {result.batter?.blend_meta && <BlendBadge meta={result.batter.blend_meta} />}
            </div>
            <EdgeScore edgeScore={result.batter?.matchup?.edge_score} batterName={result.batter?.batter_name} />
          </div>

          {/* Pitcher profile */}
          <PitcherProfile pitcherData={result.pitcher} />
        </div>
      )}
    </div>
  )
}
