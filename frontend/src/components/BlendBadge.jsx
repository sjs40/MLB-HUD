/**
 * BlendBadge — displays the 2025/2026 data blend source label.
 * Every analysis view must render this to show data provenance.
 */
export default function BlendBadge({ meta }) {
  if (!meta) return null
  return (
    <span className="inline-block text-xs bg-zinc-800 text-zinc-400 border border-zinc-700 rounded px-2 py-0.5">
      {meta.label}
    </span>
  )
}
