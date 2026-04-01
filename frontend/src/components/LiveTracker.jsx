import { useLiveGame } from '../hooks/useLiveGame'

const PITCH_COLORS = {
  FF: '#60a5fa', SI: '#34d399', SL: '#f59e0b', CU: '#a78bfa',
  CH: '#f87171', KC: '#c084fc', FC: '#38bdf8', FS: '#4ade80',
  ST: '#fb923c', SV: '#e879f9',
}
function pitchColor(pt) { return PITCH_COLORS[pt] || '#a1a1aa' }

function DeviationFlag({ flag }) {
  const up = flag.delta > 0
  return (
    <div className={`text-xs px-2 py-1 rounded border font-mono ${
      up ? 'border-amber-700 bg-amber-950/40 text-amber-300'
         : 'border-blue-800 bg-blue-950/40 text-blue-300'
    }`}>
      <span style={{ color: pitchColor(flag.pitch_type) }}>{flag.pitch_type}</span>
      {' '}{up ? '↑' : '↓'} {Math.abs(flag.delta).toFixed(1)}pp
      {' '}({flag.live_pct}% vs {flag.norm_pct}% norm)
    </div>
  )
}

function VeloDevFlag({ flag }) {
  if (!flag) return null
  const up = flag.delta > 0
  return (
    <div className={`text-xs px-2 py-1 rounded border font-mono ${
      up ? 'border-green-700 bg-green-950/40 text-green-300'
         : 'border-red-800 bg-red-950/40 text-red-300'
    }`}>
      Velo {up ? '↑' : '↓'} {Math.abs(flag.delta).toFixed(1)} mph
      {' '}({flag.live_avg_velo} tonight vs {flag.norm_avg_velo} norm)
      {' · n='}{flag.pitch_count}
    </div>
  )
}

export default function LiveTracker({ apiBase, gameId }) {
  const { data, loading, error, lastUpdated, refresh } = useLiveGame(apiBase, gameId)

  if (loading && !data) {
    return <div className="text-zinc-500 text-center py-8">Loading live feed…</div>
  }

  if (error && !data) {
    return <div className="text-red-400 text-center py-8">Live feed error: {error}</div>
  }

  if (!data) return null

  const isActive = data.status === 'Live'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <span className={`inline-block w-2 h-2 rounded-full mr-2 ${isActive ? 'bg-red-500 animate-pulse' : 'bg-zinc-600'}`} />
          <span className="text-sm font-semibold text-white">
            {data.detailed_status ?? data.status}
          </span>
          {data.inning && (
            <span className="text-zinc-500 text-sm ml-2">
              {data.inning_half} {data.inning} · {data.outs} out{data.outs !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        {data.home_score != null && (
          <span className="text-zinc-300 font-mono text-sm">
            {data.away_score} – {data.home_score}
          </span>
        )}
        {lastUpdated && (
          <span className="text-xs text-zinc-600">
            Updated {lastUpdated.toLocaleTimeString()}
          </span>
        )}
        <button
          onClick={refresh}
          className="text-xs text-zinc-500 hover:text-white border border-zinc-700 rounded px-2 py-0.5 transition-colors"
        >
          ↻ Refresh
        </button>
      </div>

      {error && (
        <p className="text-xs text-amber-400">⚠ Last poll failed: {error} — showing last known data</p>
      )}

      {/* Current pitcher */}
      {data.current_pitcher_name && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
          <p className="text-xs text-zinc-500 mb-1">On the mound</p>
          <p className="font-semibold text-white">{data.current_pitcher_name}</p>
          <p className="text-xs text-zinc-500 mt-0.5">{data.total_pitches_tonight} pitches tonight</p>
        </div>
      )}

      {/* Deviation flags */}
      {(data.pitch_mix_deviations?.length > 0 || data.velo_deviation) && (
        <div>
          <p className="text-xs text-zinc-400 font-semibold uppercase tracking-wider mb-2">
            Deviation Flags vs Blended Norms
          </p>
          <div className="flex flex-wrap gap-2">
            {data.velo_deviation && <VeloDevFlag flag={data.velo_deviation} />}
            {data.pitch_mix_deviations?.map((f) => (
              <DeviationFlag key={f.pitch_type} flag={f} />
            ))}
          </div>
        </div>
      )}

      {/* Tonight's pitch mix */}
      {data.live_pitch_mix?.length > 0 && (
        <div>
          <p className="text-xs text-zinc-400 font-semibold uppercase tracking-wider mb-2">
            Tonight&apos;s Pitch Mix ({data.total_pitches_tonight} pitches)
          </p>
          <div className="space-y-1.5">
            {data.live_pitch_mix.map((p) => {
              const norm = data.norm_pitch_mix?.find((n) => n.pitch_type === p.pitch_type)
              return (
                <div key={p.pitch_type} className="flex items-center gap-2 text-sm">
                  <span className="font-mono w-8" style={{ color: pitchColor(p.pitch_type) }}>
                    {p.pitch_type}
                  </span>
                  <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${p.pct}%`, background: pitchColor(p.pitch_type) }}
                    />
                  </div>
                  <span className="font-mono text-xs text-zinc-300 w-10 text-right">{p.pct}%</span>
                  {norm && (
                    <span className="text-zinc-600 text-xs w-16">
                      norm {norm.pct}%
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Inning-by-inning velo */}
      {data.inning_progression?.length > 0 && (
        <div>
          <p className="text-xs text-zinc-400 font-semibold uppercase tracking-wider mb-2">
            Velocity by Inning (Tonight)
          </p>
          <div className="flex flex-wrap gap-2">
            {data.inning_progression.map((inn) => (
              <div key={inn.inning} className="text-xs font-mono bg-zinc-900 border border-zinc-800 rounded px-2 py-1">
                <span className="text-zinc-500">Inn {inn.inning}:</span>
                {' '}<span className="text-white">{inn.avg_velo}</span>
                {' '}<span className="text-zinc-600">({inn.pitch_count}p)</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-zinc-700">Auto-refreshes every 60 seconds during live games.</p>
    </div>
  )
}
