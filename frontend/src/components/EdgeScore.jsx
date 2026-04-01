/**
 * EdgeScore — displays the pitcher edge score with full component transparency.
 * The score alone is never shown without its component inputs.
 */

function ScoreBar({ value, colorClass }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${colorClass}`}
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
      <span className="font-mono text-xs text-zinc-300 w-10 text-right">{value.toFixed(0)}</span>
    </div>
  )
}

const COMPONENT_META = {
  xwoba:          { label: 'xwOBA vs Pitch Types', weight: '40%', color: 'bg-blue-500' },
  whiff:          { label: 'Whiff Rate',            weight: '25%', color: 'bg-amber-500' },
  zone:           { label: 'Zone Overlap',          weight: '20%', color: 'bg-purple-500' },
  count_leverage: { label: 'Count Leverage',        weight: '15%', color: 'bg-green-500' },
}

function scoreColor(score) {
  if (score >= 70) return 'text-red-400'
  if (score >= 55) return 'text-amber-400'
  if (score >= 45) return 'text-zinc-300'
  return 'text-blue-400'
}

export default function EdgeScore({ edgeScore, batterName }) {
  if (!edgeScore) return null
  const { score, components, flags } = edgeScore

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-zinc-500">Pitcher Edge vs {batterName ?? 'Batter'}</span>
        <span className={`text-2xl font-bold font-mono ${scoreColor(score)}`}>
          {score.toFixed(0)}
        </span>
      </div>

      {/* Components — always shown */}
      <div className="space-y-2">
        {Object.entries(COMPONENT_META).map(([key, meta]) => {
          const comp = components?.[key]
          if (!comp) return null
          return (
            <div key={key}>
              <div className="flex justify-between text-xs text-zinc-500 mb-0.5">
                <span>{meta.label}</span>
                <span>{meta.weight} weight</span>
              </div>
              <ScoreBar value={comp.score} colorClass={meta.color} />
            </div>
          )
        })}
      </div>

      {/* Flags */}
      {flags?.length > 0 && (
        <div className="mt-2 space-y-1">
          {flags.map((f, i) => (
            <p key={i} className="text-xs text-amber-400">⚠ {f}</p>
          ))}
        </div>
      )}
    </div>
  )
}
