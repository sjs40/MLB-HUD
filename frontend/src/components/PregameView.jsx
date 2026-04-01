import { useState, useEffect } from 'react'
import PitcherProfile from './PitcherProfile'
import LineupMatrix from './LineupMatrix'
import NarrativeSection from './NarrativeSection'
import LiveTracker from './LiveTracker'
import PostgameView from './PostgameView'

export default function PregameView({ apiBase, game, onBack }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('pregame') // 'pregame' | 'live' | 'postgame'
  const [activeSide, setActiveSide] = useState('away')  // 'away' | 'home'

  useEffect(() => {
    setLoading(true)
    fetch(`${apiBase}/game/${game.game_id}/pregame`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((d) => { setData(d); setLoading(false) })
      .catch((err) => { setError(err.message); setLoading(false) })
  }, [apiBase, game.game_id])

  const gameTime = game.game_time
    ? new Date(game.game_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : 'TBD'

  return (
    <div>
      {/* Breadcrumb */}
      <button onClick={onBack} className="text-sm text-zinc-500 hover:text-white mb-4 transition-colors">
        ← Back to Slate
      </button>

      {/* Game header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">
          {game.away_team} @ {game.home_team}
        </h1>
        <p className="text-zinc-500 text-sm mt-1">{game.game_date} · {gameTime}</p>
      </div>

      {/* Mode tabs */}
      <div className="flex gap-2 mb-6">
        {['pregame', 'live', 'postgame'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              activeTab === tab ? 'bg-blue-600 text-white' : 'bg-zinc-800 text-zinc-400 hover:text-white'
            }`}
          >
            {tab === 'pregame' ? 'Pre-Game Analysis' : tab === 'live' ? '🔴 Live Tracker' : 'Post-Game Analysis'}
          </button>
        ))}
      </div>

      {/* Live tracker */}
      {activeTab === 'live' && (
        <LiveTracker apiBase={apiBase} gameId={game.game_id} />
      )}


      {activeTab === 'postgame' && (
        <PostgameView apiBase={apiBase} gameId={game.game_id} />
      )}

      {/* Pre-game analysis */}
      {activeTab === 'pregame' && (
        <>
          {loading && (
            <div className="text-zinc-500 text-center py-16">
              Loading pre-game analysis — this may take a moment on first run
              (Statcast data is being fetched and cached)…
            </div>
          )}

          {error && (
            <div className="text-red-400 text-center py-16">
              Failed to load analysis: {error}
            </div>
          )}

          {data && (
            <div className="space-y-8">
              {/* Narratives */}
              {data.narratives && (
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                  {['away', 'home'].map((side) => {
                    const stories = data.narratives[side]
                    const name = data[`${side}_pitcher`]?.pitcher_name ?? side
                    return stories?.length ? (
                      <div key={side}>
                        <p className="text-xs text-zinc-500 mb-1">{name}</p>
                        <NarrativeSection narratives={stories} />
                      </div>
                    ) : null
                  })}
                </div>
              )}

              {/* Side selector */}
              <div className="flex gap-2 border-b border-zinc-800 pb-4">
                {['away', 'home'].map((side) => (
                  <button
                    key={side}
                    onClick={() => setActiveSide(side)}
                    className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
                      activeSide === side ? 'bg-zinc-700 text-white' : 'bg-zinc-900 text-zinc-400 hover:text-white'
                    }`}
                  >
                    {side === 'away' ? game.away_team : game.home_team}
                    {' '}SP
                  </button>
                ))}
              </div>

              {/* Pitcher profile */}
              <PitcherProfile pitcherData={data[`${activeSide}_pitcher`]} />

              {/* Opposing lineup */}
              <LineupMatrix
                lineupData={data[`${activeSide === 'away' ? 'home' : 'away'}_lineup`]}
                label={`${activeSide === 'away' ? game.home_team : game.away_team} Lineup vs ${data[`${activeSide}_pitcher`]?.pitcher_name ?? 'SP'}`}
              />
            </div>
          )}
        </>
      )}
    </div>
  )
}
