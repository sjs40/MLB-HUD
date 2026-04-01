import { useState } from 'react'
import BlendBadge from './BlendBadge'
import EdgeScore from './EdgeScore'

const PITCH_COLORS = {
  FF: '#60a5fa', SI: '#34d399', SL: '#f59e0b', CU: '#a78bfa',
  CH: '#f87171', KC: '#c084fc', FC: '#38bdf8', FS: '#4ade80',
  ST: '#fb923c', SV: '#e879f9',
}
function pitchColor(pt) { return PITCH_COLORS[pt] || '#a1a1aa' }

function SmallSampleBadge() {
  return (
    <span title="Small sample (<50 pitches)">
      <span className="text-amber-400 text-xs">*</span>
    </span>
  )
}

function BatterRow({ batter, expanded, onToggle }) {
  const matchup = batter.matchup
  const blendMeta = batter.blend_meta

  return (
    <div className="border-b border-zinc-800 last:border-0">
      {/* Summary row */}
      <button
        onClick={onToggle}
        className="w-full text-left px-3 py-2.5 hover:bg-zinc-800/50 transition-colors flex items-center gap-3"
      >
        <span className="text-zinc-500 font-mono text-xs w-5">{batter.batting_order ?? '?'}</span>
        <span className="flex-1 text-sm font-medium text-white">
          {batter.name}
          {batter.projected && (
            <span className="ml-2 text-xs bg-amber-900/60 text-amber-300 border border-amber-700 px-1.5 rounded font-normal">
              PROJECTED
            </span>
          )}
        </span>
        <span className="text-xs text-zinc-500">{batter.bat_side ?? '?'}</span>
        {matchup?.edge_score && (
          <span className={`font-mono text-sm font-bold ${
            matchup.edge_score.score >= 70 ? 'text-red-400' :
            matchup.edge_score.score >= 55 ? 'text-amber-400' :
            matchup.edge_score.score >= 45 ? 'text-zinc-300' : 'text-blue-400'
          }`}>
            {matchup.edge_score.score.toFixed(0)}
          </span>
        )}
        <span className="text-zinc-600 text-xs">{expanded ? '▲' : '▼'}</span>
      </button>

      {/* Expanded detail */}
      {expanded && matchup && (
        <div className="px-3 pb-4 space-y-4 bg-zinc-900/40">
          {blendMeta && <BlendBadge meta={blendMeta} />}

          {/* xwOBA by pitch type */}
          {matchup.xwoba_by_pitch_type?.length > 0 && (
            <div>
              <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wider mb-2">xwOBA vs Pitch Types</p>
              <div className="flex flex-wrap gap-2">
                {matchup.xwoba_by_pitch_type.map((e) => (
                  <div
                    key={e.pitch_type}
                    className={`text-xs px-2 py-1 rounded font-mono ${e.small_sample_flag ? 'border border-amber-700' : 'border border-zinc-700'}`}
                    style={{ color: pitchColor(e.pitch_type) }}
                  >
                    {e.pitch_type}: {e.xwoba ?? '—'}
                    {e.small_sample_flag ? <SmallSampleBadge /> : null}
                    <span className="text-zinc-600 ml-1">n={e.sample_size}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Swing/whiff rates */}
          {matchup.swing_whiff_rates?.length > 0 && (
            <div>
              <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wider mb-2">Swing & Whiff Rate</p>
              <table className="text-xs w-full">
                <thead>
                  <tr className="text-zinc-600">
                    <th className="text-left py-0.5 pr-3">Pitch</th>
                    <th className="text-right py-0.5 pr-3">Swing%</th>
                    <th className="text-right py-0.5">Whiff%</th>
                  </tr>
                </thead>
                <tbody>
                  {matchup.swing_whiff_rates.slice(0, 6).map((e) => (
                    <tr key={e.pitch_type}>
                      <td className="pr-3 py-0.5 font-mono" style={{ color: pitchColor(e.pitch_type) }}>
                        {e.pitch_type}
                      </td>
                      <td className="text-right pr-3 py-0.5 font-mono text-zinc-300">
                        {e.swing_rate != null ? `${(e.swing_rate * 100).toFixed(0)}%` : '—'}
                      </td>
                      <td className="text-right py-0.5 font-mono text-zinc-300">
                        {e.whiff_rate != null ? `${(e.whiff_rate * 100).toFixed(0)}%` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Zone overlap */}
          {matchup.zone_vulnerability && (
            <div>
              <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wider mb-1">Zone Overlap</p>
              {matchup.zone_vulnerability.overlap_zones?.length > 0 ? (
                <p className="text-xs text-amber-300">
                  Overlap zones: {matchup.zone_vulnerability.overlap_zones.join(', ')}
                  {' '}(pitcher primary + batter weak)
                </p>
              ) : (
                <p className="text-xs text-zinc-600">No significant zone overlap.</p>
              )}
            </div>
          )}

          {/* Count leverage */}
          {matchup.count_leverage && (
            <div>
              <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wider mb-1">Count Leverage</p>
              <div className="flex gap-4 text-xs font-mono">
                <span>
                  Hitter counts:{' '}
                  <span className="text-zinc-300">
                    {matchup.count_leverage.hitter_friendly?.xwoba ?? '—'}
                  </span>
                  <span className="text-zinc-600 ml-1">
                    (n={matchup.count_leverage.hitter_friendly?.sample_size ?? 0})
                  </span>
                </span>
                <span>
                  Pitcher counts:{' '}
                  <span className="text-zinc-300">
                    {matchup.count_leverage.pitcher_friendly?.xwoba ?? '—'}
                  </span>
                  <span className="text-zinc-600 ml-1">
                    (n={matchup.count_leverage.pitcher_friendly?.sample_size ?? 0})
                  </span>
                </span>
              </div>
            </div>
          )}

          {/* Edge score */}
          <EdgeScore edgeScore={matchup.edge_score} batterName={batter.name} />
        </div>
      )}
    </div>
  )
}

export default function LineupMatrix({ lineupData, label }) {
  const [expandedIdx, setExpandedIdx] = useState(null)

  if (!lineupData) return <p className="text-zinc-500 text-sm">Lineup not available.</p>

  const { batters, is_projected } = lineupData

  function toggleRow(idx) {
    setExpandedIdx(expandedIdx === idx ? null : idx)
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <h3 className="text-sm font-semibold text-zinc-300">{label ?? 'Lineup'}</h3>
        {is_projected && (
          <span className="text-xs bg-amber-900/60 text-amber-300 border border-amber-700 px-2 py-0.5 rounded">
            PROJECTED LINEUP
          </span>
        )}
      </div>

      {batters?.length > 0 ? (
        <div className="bg-zinc-950 border border-zinc-800 rounded-lg overflow-hidden">
          {batters.map((batter, idx) => (
            <BatterRow
              key={batter.player_id ?? idx}
              batter={batter}
              expanded={expandedIdx === idx}
              onToggle={() => toggleRow(idx)}
            />
          ))}
        </div>
      ) : (
        <p className="text-zinc-500 text-sm">No lineup data.</p>
      )}

      <p className="text-xs text-zinc-600 mt-2">Click a batter to expand full matchup details.</p>
    </div>
  )
}
