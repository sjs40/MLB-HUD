import { useState } from 'react'
import SlateView from './components/SlateView'
import PregameView from './components/PregameView'
import AdHocAnalyzer from './components/AdHocAnalyzer'

const API = '/api'

export default function App() {
  const [mode, setMode] = useState('slate') // 'slate' | 'pregame' | 'adhoc'
  const [selectedGame, setSelectedGame] = useState(null)

  function openPregame(game) {
    setSelectedGame(game)
    setMode('pregame')
  }

  function goBack() {
    setMode('slate')
    setSelectedGame(null)
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Nav */}
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center gap-6">
        <button
          onClick={goBack}
          className="text-lg font-bold tracking-tight text-white hover:text-blue-400 transition-colors"
        >
          ⚾ MLB-HUD
        </button>
        <nav className="flex gap-4 text-sm">
          <button
            onClick={() => setMode('slate')}
            className={`px-3 py-1 rounded transition-colors ${mode === 'slate' ? 'bg-blue-600 text-white' : 'text-zinc-400 hover:text-white'}`}
          >
            Today&apos;s Slate
          </button>
          <button
            onClick={() => setMode('adhoc')}
            className={`px-3 py-1 rounded transition-colors ${mode === 'adhoc' ? 'bg-blue-600 text-white' : 'text-zinc-400 hover:text-white'}`}
          >
            Ad Hoc Analyzer
          </button>
        </nav>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {mode === 'slate' && (
          <SlateView apiBase={API} onGameSelect={openPregame} />
        )}
        {mode === 'pregame' && selectedGame && (
          <PregameView apiBase={API} game={selectedGame} onBack={goBack} />
        )}
        {mode === 'adhoc' && (
          <AdHocAnalyzer apiBase={API} />
        )}
      </main>
    </div>
  )
}
