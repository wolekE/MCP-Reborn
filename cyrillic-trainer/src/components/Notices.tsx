import { useEffect, useState } from 'react'
import { player } from '../audio/player'
import { sfx } from '../audio/sfx'
import { LETTER_BY_ID } from '../data/letters'
import { href } from '../router'
import { useStore } from '../state/store'

/** How to get a Russian system voice — shown once when one is needed, and in Settings. */
export function VoiceHelp() {
  return (
    <div className="stack small" style={{ gap: '0.5rem' }}>
      <p>
        <strong>Best fix:</strong> generate the recorded clips with <code>npm run audio</code> (see the README). Until then, the app
        falls back to your system’s text-to-speech, which needs a Russian voice:
      </p>
      <p>
        <strong>macOS:</strong> System Settings → Accessibility → Spoken Content → System voice → Manage Voices… → Russian → tick
        <em> Milena</em> or <em>Yuri</em>. Then reload this page.
      </p>
      <p>
        <strong>Windows 10/11:</strong> Settings → Time &amp; language → Speech → Manage voices → Add voices → Russian (
        <em>Irina</em> / <em>Pavel</em>). Restart the browser afterwards.
      </p>
      <p className="muted">Chrome and Edge may also offer online Russian voices when you’re connected to the internet.</p>
    </div>
  )
}

/** Global notices: missing Russian voice, letters unlocked, unreadable save. */
export function Notices() {
  const { justUnlocked, dismissUnlock, loadProblem } = useStore()
  const [noVoice, setNoVoice] = useState(false)
  const [showLoadProblem, setShowLoadProblem] = useState(loadProblem !== null)

  useEffect(() => player.onNotice((n) => n.kind === 'no-russian-voice' && setNoVoice(true)), [])

  const unlockKey = justUnlocked?.join(',')
  useEffect(() => {
    if (unlockKey) void sfx.levelUp()
  }, [unlockKey])

  return (
    <div className="toast-layer" aria-live="polite">
      {justUnlocked && (
        <div className="toast" role="status">
          <div className="spread">
            <div>
              <h3 style={{ marginBottom: '0.2rem' }}>New letters unlocked!</h3>
              <div className="glyph-print" style={{ fontSize: '2rem' }} lang="ru">
                {justUnlocked.map((id) => LETTER_BY_ID.get(id)!.upper).join(' ')}
              </div>
            </div>
            <div className="row">
              <a className="btn btn-primary" href={href('learn')} onClick={dismissUnlock}>
                Learn them
              </a>
              <button className="btn btn-ghost" onClick={dismissUnlock}>
                Later
              </button>
            </div>
          </div>
        </div>
      )}
      {noVoice && (
        <div className="toast" role="alertdialog" aria-labelledby="novoice-title">
          <h3 id="novoice-title">No Russian voice found</h3>
          <p className="small">Some audio files are missing, and this browser has no Russian text-to-speech voice to read them instead.</p>
          <VoiceHelp />
          <button className="btn" onClick={() => setNoVoice(false)}>
            Got it
          </button>
        </div>
      )}
      {showLoadProblem && (
        <div className="toast" role="status">
          <p className="small" style={{ margin: 0 }}>
            Your saved progress couldn’t be read (it was backed up in localStorage), so you’re starting fresh.
          </p>
          <button className="btn btn-ghost" onClick={() => setShowLoadProblem(false)}>
            OK
          </button>
        </div>
      )}
    </div>
  )
}
