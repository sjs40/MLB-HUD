import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import BlendBadge from './BlendBadge'
import StrikeZoneHeatmap from './StrikeZoneHeatmap'

const PITCH_COLORS = {
  FF: '#60a5fa', SI: '#34d399', SL: '#f59e0b', CU: '#a78bfa',
  CH: '#f87171', KC: '#c084fc', FC: '#38bdf8', FS: '#4ade80',
  ST: '#fb923c', SV: '#e879f9', CS: '#94a3b8',
}

function pitchColor(pt) {
  return PITCH_COLORS[pt] || '#a1a1aa'
}

function PitchMixTable({ pitchMix }) {
  if (!pitchMix?.length) return <p className="text-zinc-500 text-sm">No pitch mix data.</p>
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-zinc-500 text-xs border-b border-zinc-800">
          <th className="text-left py-1.5 pr-3">Pitch</th>
          <th className="text-right py-1.5 pr-3">Usage</th>
          <th className="text-right py-1.5 pr-3">Velo</th>
          <th className="text-right py-1.5 pr-3">Spin</th>
          <th className="text-right py-1.5 pr-3">H-Brk</th>
          <th className="text-right py-1.5">V-Brk</th>
        </tr>
      </thead>
      <tbody>
        {pitchMix.map((p) => (
          <tr key={p.pitch_type} className="border-b border-zinc-900">
            <td className="py-1.5 pr-3">
              <span
                className="inline-block w-2 h-2 rounded-full mr-2"
                style={{ background: pitchColor(p.pitch_type) }}
              />
              <span className="font-mono">{p.pitch_type}</span>
            </td>
            <td className="text-right py-1.5 pr-3 font-mono">{p.pct}%</td>
            <td className="text-right py-1.5 pr-3 font-mono">{p.avg_velo ?? '—'}</td>
            <td className="text-right py-1.5 pr-3 font-mono">{p.spin_rate ?? '—'}</td>
            <td className="text-right py-1.5 pr-3 font-mono">{p.h_break ?? '—'}</td>
            <td className="text-right py-1.5 font-mono">{p.v_break ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function GameProgressionChart({ data }) {
  if (!data?.length) return null
  const chartData = data.map((d) => ({
    name: `Inn ${d.inning_band}`,
    velo: d.avg_velo,
    whiff: d.whiff_rate != null ? +(d.whiff_rate * 100).toFixed(1) : null,
    veloFlag: d.velo_flag,
  }))
  return (
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
          <XAxis dataKey="name" tick={{ fill: '#71717a', fontSize: 11 }} />
          <YAxis yAxisId="velo" tick={{ fill: '#71717a', fontSize: 11 }} domain={['auto', 'auto']} />
          <YAxis yAxisId="whiff" orientation="right" tick={{ fill: '#71717a', fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 6 }}
            labelStyle={{ color: '#e4e4e7' }}
          />
          <Legend wrapperStyle={{ fontSize: 11, color: '#a1a1aa' }} />
          <Line yAxisId="velo" dataKey="velo" stroke="#60a5fa" name="Avg Velo" dot={{ r: 3 }} strokeWidth={2} />
          <Line yAxisId="whiff" dataKey="whiff" stroke="#f59e0b" name="Whiff %" dot={{ r: 3 }} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function WeaponsVulns({ data }) {
  if (!data) return null
  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <p className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-2">⚔ Weapons</p>
        {data.weapons?.map((w) => (
          <div key={w.pitch_type} className="text-sm mb-1">
            <span className="font-mono" style={{ color: pitchColor(w.pitch_type) }}>{w.pitch_type}</span>
            <span className="text-zinc-400 ml-2">
              {w.whiff_rate != null ? `${(w.whiff_rate * 100).toFixed(0)}% whiff` : ''}
              {w.xwoba != null ? ` · ${w.xwoba} xwOBA` : ''}
            </span>
          </div>
        ))}
      </div>
      <div>
        <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">⚠ Vulnerabilities</p>
        {data.vulnerabilities?.map((v) => (
          <div key={v.pitch_type} className="text-sm mb-1">
            <span className="font-mono" style={{ color: pitchColor(v.pitch_type) }}>{v.pitch_type}</span>
            <span className="text-zinc-400 ml-2">
              {v.xwoba != null ? `${v.xwoba} xwOBA` : ''}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function PitcherProfile({ pitcherData }) {
  const [heatmapPitch, setHeatmapPitch] = useState(null)
  const [heatmapHand, setHeatmapHand] = useState('R')
  const [heatmapMetric, setHeatmapMetric] = useState('whiff_rate')

  if (!pitcherData?.profile) {
    return (
      <div className="text-zinc-500 text-sm p-4">
        {pitcherData?.pitcher_name ?? 'Pitcher'} — no profile data available.
      </div>
    )
  }

  const { profile, blend_meta, profile_change_alerts, pitcher_name } = pitcherData
  const pitchTypes = profile.pitch_mix?.map((p) => p.pitch_type) ?? []
  const activePitch = heatmapPitch ?? pitchTypes[0]

  const heatmapData = activePitch
    ? profile.location_heatmaps?.[activePitch]?.[heatmapHand === 'L' ? 'vs_LHH' : 'vs_RHH'] ?? []
    : []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-xl font-bold text-white">{pitcher_name}</h2>
        {blend_meta && <BlendBadge meta={blend_meta} />}
      </div>

      {/* Profile change alerts */}
      {profile_change_alerts?.length > 0 && (
        <div className="bg-amber-950/40 border border-amber-700 rounded-lg p-3">
          <p className="text-xs font-semibold text-amber-400 mb-1">⚡ Profile Change Alert</p>
          {profile_change_alerts.map((a) => (
            <p key={a.pitch_type} className="text-sm text-amber-300">
              <span className="font-mono">{a.pitch_type}</span>
              {' '}usage {a.direction === 'up' ? '↑' : '↓'} {Math.abs(a.delta)}pp
              {' '}({a.pct_2025}% → {a.pct_2026}%)
            </p>
          ))}
        </div>
      )}

      {/* Pitch mix */}
      <section>
        <h3 className="text-sm font-semibold text-zinc-300 mb-2">Pitch Mix</h3>
        <PitchMixTable pitchMix={profile.pitch_mix} />
      </section>

      {/* Location heatmaps */}
      <section>
        <div className="flex flex-wrap items-center gap-3 mb-3">
          <h3 className="text-sm font-semibold text-zinc-300">Location Heatmap</h3>
          {/* Pitch selector */}
          <div className="flex gap-1">
            {pitchTypes.map((pt) => (
              <button
                key={pt}
                onClick={() => setHeatmapPitch(pt)}
                className={`text-xs px-2 py-0.5 rounded font-mono transition-colors ${activePitch === pt ? 'bg-blue-600 text-white' : 'bg-zinc-800 text-zinc-400 hover:text-white'}`}
              >
                {pt}
              </button>
            ))}
          </div>
          {/* Hand selector */}
          <div className="flex gap-1">
            {['L', 'R'].map((h) => (
              <button
                key={h}
                onClick={() => setHeatmapHand(h)}
                className={`text-xs px-2 py-0.5 rounded transition-colors ${heatmapHand === h ? 'bg-zinc-600 text-white' : 'bg-zinc-800 text-zinc-400 hover:text-white'}`}
              >
                vs {h}HH
              </button>
            ))}
          </div>
          {/* Metric selector */}
          <div className="flex gap-1">
            {[['whiff_rate', 'Whiff%'], ['xwoba', 'xwOBA']].map(([val, lbl]) => (
              <button
                key={val}
                onClick={() => setHeatmapMetric(val)}
                className={`text-xs px-2 py-0.5 rounded transition-colors ${heatmapMetric === val ? 'bg-zinc-600 text-white' : 'bg-zinc-800 text-zinc-400 hover:text-white'}`}
              >
                {lbl}
              </button>
            ))}
          </div>
        </div>
        <StrikeZoneHeatmap
          zones={heatmapData}
          metric={heatmapMetric}
          label={`${activePitch} vs ${heatmapHand}HH — ${heatmapMetric === 'whiff_rate' ? 'Whiff Rate' : 'xwOBA'}`}
        />
      </section>

      {/* Count tendencies */}
      <section>
        <h3 className="text-sm font-semibold text-zinc-300 mb-2">Count Tendencies</h3>
        <div className="grid grid-cols-2 gap-4">
          {['hitter_friendly', 'pitcher_friendly'].map((type) => {
            const dist = profile.count_tendencies?.[type] ?? {}
            const counts = profile.count_tendencies?.[`${type}_counts`] ?? []
            return (
              <div key={type} className="bg-zinc-900 rounded-lg p-3">
                <p className="text-xs text-zinc-500 mb-2">
                  {type === 'hitter_friendly' ? '🟢 Hitter counts' : '🔴 Pitcher counts'}
                  {' '}({counts.join(', ')})
                </p>
                {Object.entries(dist).sort(([, a], [, b]) => b - a).map(([pt, pct]) => (
                  <div key={pt} className="flex items-center gap-2 text-sm mb-1">
                    <span className="font-mono w-8" style={{ color: pitchColor(pt) }}>{pt}</span>
                    <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${pct}%`, background: pitchColor(pt) }}
                      />
                    </div>
                    <span className="text-zinc-400 font-mono text-xs w-10 text-right">{pct}%</span>
                  </div>
                ))}
              </div>
            )
          })}
        </div>
      </section>

      {/* Platoon splits */}
      <section>
        <h3 className="text-sm font-semibold text-zinc-300 mb-2">Platoon Splits (xwOBA allowed)</h3>
        <div className="grid grid-cols-2 gap-4">
          {['vs_LHH', 'vs_RHH'].map((side) => {
            const splits = profile.platoon_splits?.[side] ?? []
            return (
              <div key={side} className="bg-zinc-900 rounded-lg p-3">
                <p className="text-xs text-zinc-500 mb-2">{side.replace('_', ' ')}</p>
                {splits.map((s) => (
                  <div key={s.pitch_type} className="flex justify-between text-sm mb-1">
                    <span className="font-mono" style={{ color: pitchColor(s.pitch_type) }}>
                      {s.pitch_type}
                    </span>
                    <span className={`font-mono ${s.small_sample ? 'text-amber-400' : 'text-zinc-300'}`}>
                      {s.xwoba ?? '—'}
                      {s.small_sample ? ' *' : ''}
                    </span>
                    <span className="text-zinc-600 text-xs">n={s.count}</span>
                  </div>
                ))}
              </div>
            )
          })}
        </div>
        <p className="text-xs text-amber-400 mt-1">* Small sample (&lt;50 pitches)</p>
      </section>

      {/* Game progression */}
      <section>
        <h3 className="text-sm font-semibold text-zinc-300 mb-2">Game Progression</h3>
        {profile.game_progression?.some((p) => p.velo_flag) && (
          <p className="text-xs text-amber-400 mb-2">
            ⚠ Velocity decline detected between inning bands
          </p>
        )}
        <GameProgressionChart data={profile.game_progression} />
      </section>

      {/* Weapons & vulnerabilities */}
      <section>
        <h3 className="text-sm font-semibold text-zinc-300 mb-2">Weapons & Vulnerabilities</h3>
        <WeaponsVulns data={profile.weapons_vulnerabilities} />
      </section>
    </div>
  )
}
