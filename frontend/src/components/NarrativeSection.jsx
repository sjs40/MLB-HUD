export default function NarrativeSection({ narratives }) {
  if (!narratives?.length) return null

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-zinc-300 mb-3">📋 Key Pre-Game Storylines</h3>
      <ul className="space-y-2">
        {narratives.map((story, i) => (
          <li key={i} className="text-sm text-zinc-300 flex gap-2">
            <span className="text-zinc-600 shrink-0">·</span>
            <span>{story}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
