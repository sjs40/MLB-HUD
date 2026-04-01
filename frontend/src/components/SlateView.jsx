import { useState, useEffect } from 'react'

function GameCard({ game, onSelect }) {
  const gameTime = game.game_time
    ? new Date(game.game_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : 'TBD'

  return (
    <button
      onClick={() => onSelect(game)}
      className="w-full text-left bg-zinc-900 border border-zinc-800 rounded-lg p-4 hover:border-blue-500 hover:bg-zinc-800 transition-all group"
    >
      <div className="flex justify-between items-start mb-3">
        <span className="text-xs text-zinc-500 font-mono">{game.game_date} · {gameTime}</span>
        <span className="text-xs text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity">
          Pre-Game Analysis →
        </span>
      </div>

      <div className="flex items-center justify-between gap-4">
        <div className="flex-1">
          <p className="font-semibold text-white">{game.away_team}</p>
          <p className="text-xs text-zinc-500 mt-0.5">
            SP: {game.away_probable_pitcher ?? <span className="text-zinc-600">TBD</span>}
          </p>
        </div>

        <div className="text-zinc-600 font-mono text-sm">@</div>

        <div className="flex-1 text-right">
          <p className="font-semibold text-white">{game.home_team}</p>
          <p className="text-xs text-zinc-500 mt-0.5">
            SP: {game.home_probable_pitcher ?? <span className="text-zinc-600">TBD</span>}
          </p>
        </div>
      </div>
    </button>
  )
}

export default function SlateView({ apiBase, onGameSelect }) {
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    fetch(`${apiBase}/schedule`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data) => {
        setGames(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [apiBase])

  if (loading) {
    return (
      <div className="text-zinc-500 text-center py-16">Loading today&apos;s slate...</div>
    )
  }

  if (error) {
    return (
      <div className="text-red-400 text-center py-16">
        Failed to load schedule: {error}
      </div>
    )
  }

  const today = new Date().toISOString().slice(0, 10)
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10)
  const todayGames = games.filter((g) => g.game_date === today)
  const tomorrowGames = games.filter((g) => g.game_date === tomorrow)

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-white">Today&apos;s Slate</h1>

      {todayGames.length > 0 ? (
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Today</h2>
          <div className="grid gap-3 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
            {todayGames.map((g) => (
              <GameCard key={g.game_id} game={g} onSelect={onGameSelect} />
            ))}
          </div>
        </section>
      ) : (
        <p className="text-zinc-500 mb-8">No games scheduled today.</p>
      )}

      {tomorrowGames.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Tomorrow</h2>
          <div className="grid gap-3 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
            {tomorrowGames.map((g) => (
              <GameCard key={g.game_id} game={g} onSelect={onGameSelect} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
