/**
 * StrikeZoneHeatmap — SVG 9-zone strike zone grid.
 *
 * Zone layout (catcher's view):
 *   1 | 2 | 3
 *   4 | 5 | 6
 *   7 | 8 | 9
 *
 * Color intensity driven by a selected metric (whiff_rate or xwoba).
 */

// Zone positions in a 3x3 grid (col, row) — 0-indexed
const ZONE_GRID = {
  1: [0, 0], 2: [1, 0], 3: [2, 0],
  4: [0, 1], 5: [1, 1], 6: [2, 1],
  7: [0, 2], 8: [1, 2], 9: [2, 2],
}

const CELL = 60    // px per cell
const PAD = 24     // padding around grid

function zoneColor(value, metric) {
  if (value == null) return '#27272a' // zinc-800

  if (metric === 'whiff_rate') {
    // Higher = more orange (pitcher advantage)
    const t = Math.min(1, value / 0.40)
    return interpolateColor('#27272a', '#f97316', t)
  } else {
    // xwoba: higher = more red (hitter advantage)
    const t = Math.min(1, Math.max(0, (value - 0.200) / 0.300))
    return interpolateColor('#27272a', '#ef4444', t)
  }
}

function interpolateColor(hex1, hex2, t) {
  const parse = (h) => [
    parseInt(h.slice(1, 3), 16),
    parseInt(h.slice(3, 5), 16),
    parseInt(h.slice(5, 7), 16),
  ]
  const [r1, g1, b1] = parse(hex1)
  const [r2, g2, b2] = parse(hex2)
  const r = Math.round(r1 + (r2 - r1) * t)
  const g = Math.round(g1 + (g2 - g1) * t)
  const b = Math.round(b1 + (b2 - b1) * t)
  return `rgb(${r},${g},${b})`
}

const W = CELL * 3 + PAD * 2
const H = CELL * 3 + PAD * 2

export default function StrikeZoneHeatmap({ zones = [], metric = 'whiff_rate', label }) {
  const zoneMap = Object.fromEntries(zones.map((z) => [z.zone_id, z]))

  return (
    <div>
      {label && <p className="text-xs text-zinc-500 mb-1">{label}</p>}
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        className="rounded overflow-hidden"
        role="img"
        aria-label={`Strike zone heatmap — ${metric}`}
      >
        {/* Background */}
        <rect width={W} height={H} fill="#18181b" rx="4" />

        {/* Zone cells */}
        {Object.entries(ZONE_GRID).map(([zoneId, [col, row]]) => {
          const id = Number(zoneId)
          const z = zoneMap[id]
          const value = z ? z[metric] : null
          const fill = zoneColor(value, metric)
          const x = PAD + col * CELL
          const y = PAD + row * CELL
          const displayVal = value != null
            ? (metric === 'whiff_rate' ? `${(value * 100).toFixed(0)}%` : value.toFixed(3))
            : '—'

          return (
            <g key={id}>
              <rect
                x={x} y={y}
                width={CELL - 2} height={CELL - 2}
                fill={fill}
                rx="2"
              />
              <text
                x={x + CELL / 2 - 1}
                y={y + CELL / 2 - 6}
                textAnchor="middle"
                fill="#e4e4e7"
                fontSize="11"
                fontFamily="ui-monospace, monospace"
              >
                {displayVal}
              </text>
              <text
                x={x + CELL / 2 - 1}
                y={y + CELL / 2 + 8}
                textAnchor="middle"
                fill="#71717a"
                fontSize="9"
              >
                {z ? `n=${z.count}` : ''}
              </text>
            </g>
          )
        })}

        {/* Strike zone border */}
        <rect
          x={PAD} y={PAD}
          width={CELL * 3} height={CELL * 3}
          fill="none"
          stroke="#3f3f46"
          strokeWidth="1"
          rx="1"
        />

        {/* Grid lines */}
        {[1, 2].map((i) => (
          <g key={i}>
            <line
              x1={PAD + i * CELL} y1={PAD}
              x2={PAD + i * CELL} y2={PAD + CELL * 3}
              stroke="#3f3f46" strokeWidth="1"
            />
            <line
              x1={PAD} y1={PAD + i * CELL}
              x2={PAD + CELL * 3} y2={PAD + i * CELL}
              stroke="#3f3f46" strokeWidth="1"
            />
          </g>
        ))}
      </svg>
    </div>
  )
}
