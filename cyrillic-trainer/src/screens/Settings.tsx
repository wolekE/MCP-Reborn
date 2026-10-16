import './settings.css'
import { Fragment, useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { player, type PlayOutcome, type SpeechRate, type VoiceKey } from '../audio/player'
import { sfx } from '../audio/sfx'
import { VoiceHelp } from '../components/Notices'
import { LETTER_BY_ID } from '../data/letters'
import { currentStreak } from '../state/actions'
import type { SaveData, ThemePref } from '../state/schema'
import { useStore } from '../state/store'

// The sample word everybody meets first: мама (from the М card).
const SAMPLE = LETTER_BY_ID.get('m')?.example ?? { word: 'мама', stressed: 'ма́ма', en: 'mum', pl: 'mama' }
const SAMPLE_CLIP = LETTER_BY_ID.get('m')?.audio.word ?? 'word-mama'

const REVIEW_URL = `${import.meta.env.BASE_URL}audio/review.html`

interface Choice<T> {
  value: T
  label: string
  sub?: string
  /** Accessible name when it should differ from the visible label + sub. */
  name?: string
  icon?: ReactNode
}

const VOICES: readonly Choice<VoiceKey>[] = [
  { value: 'svetlana', label: 'Female', sub: 'Svetlana', name: 'Female (Svetlana)' },
  { value: 'dmitry', label: 'Male', sub: 'Dmitry', name: 'Male (Dmitry)' },
]

const RATES: readonly Choice<SpeechRate>[] = [
  { value: 1, label: '1×', sub: 'normal', name: '1× normal' },
  { value: 0.75, label: '0.75×', sub: 'slower', name: '0.75× slower' },
]

const icon = (path: ReactNode) => (
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {path}
  </svg>
)

const THEMES: readonly Choice<ThemePref>[] = [
  {
    value: 'system',
    label: 'System',
    icon: icon(
      <>
        <rect x="3" y="4" width="18" height="12" rx="2" />
        <path d="M8 20h8M12 16v4" />
      </>,
    ),
  },
  {
    value: 'light',
    label: 'Light',
    icon: icon(
      <>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
      </>,
    ),
  },
  {
    value: 'dark',
    label: 'Dark',
    icon: icon(<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />),
  },
]

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

/** Message shown under the voice controls after a sample plays (null = nothing to say). */
function outcomeNote(outcome: PlayOutcome): string | null {
  switch (outcome) {
    case 'spoken':
      return 'No recorded clip was found, so your system’s Russian text-to-speech voice read it instead.'
    case 'silent':
      return 'No sound: the recorded clip is missing and this browser has no Russian voice. See “Audio not working?” below.'
    case 'blocked':
      return 'Your browser blocked the sound. Press “Test voice” to try again.'
    default:
      return null
  }
}

export function Settings() {
  const { save, updateSettings, resetProgress } = useStore()
  const { voice, rate, sfxMuted, theme } = save.settings

  const [playing, setPlaying] = useState<'voice' | 'tones' | null>(null)
  const [voiceNote, setVoiceNote] = useState<string | null>(null)
  const [helpOpen, setHelpOpen] = useState(false)

  // Leaving the page stops a sample that is still playing.
  useEffect(() => () => player.stop(), [])

  async function playSample(patch?: { voice?: VoiceKey; rate?: SpeechRate }) {
    // The store pushes settings into the player after it re-renders; apply the
    // change right away so this sample already uses the new voice/speed.
    if (patch) player.configure(patch)
    setVoiceNote(null)
    setPlaying('voice')
    const outcome = await player.play(SAMPLE_CLIP)
    if (outcome === 'interrupted') return // a newer sample took over
    setPlaying((p) => (p === 'voice' ? null : p))
    setVoiceNote(outcomeNote(outcome))
    if (outcome === 'silent') setHelpOpen(true)
  }

  function chooseVoice(v: VoiceKey) {
    updateSettings({ voice: v })
    void playSample({ voice: v })
  }

  function chooseRate(r: SpeechRate) {
    updateSettings({ rate: r })
    void playSample({ rate: r })
  }

  function setTones(on: boolean) {
    updateSettings({ sfxMuted: !on })
    if (on) {
      // Same as the store will do after re-rendering; done now so the confirmation chime is audible.
      sfx.setMuted(false)
      void sfx.correct()
    }
  }

  async function testTones() {
    setPlaying('tones')
    await sfx.correct()
    await sleep(250)
    await sfx.wrong()
    setPlaying((p) => (p === 'tones' ? null : p))
  }

  const tonesHintId = useId()

  return (
    <div className="stack settings">
      <header className="settings-head">
        <h1>Settings</h1>
        <p className="muted">Changes are saved on this device straight away.</p>
      </header>

      <section className="card settings-section" aria-labelledby="settings-sound">
        <h2 id="settings-sound">Sound</h2>

        <Segmented legend="Voice" hint="Who reads the letters and words." name="voice" choices={VOICES} value={voice} onChange={chooseVoice} />

        <Segmented legend="Speech speed" hint="Slower speech keeps the natural pitch." name="rate" choices={RATES} value={rate} onChange={chooseRate} />

        <div className="settings-sample">
          <button
            type="button"
            className={`btn ${playing === 'voice' ? 'playing' : ''}`}
            onClick={() => void playSample()}
            aria-describedby="settings-sample-word"
          >
            <span aria-hidden="true">🔊</span> Test voice
          </button>
          <p id="settings-sample-word" className="settings-sample-word">
            <span lang="ru">{SAMPLE.stressed}</span>
            <span className="muted small">
              “{SAMPLE.en}” · pl. <em>{SAMPLE.pl}</em>
            </span>
          </p>
        </div>
        {/* The live region stays in the DOM so screen readers announce the note when it appears. */}
        <div role="status" className="settings-live">
          {voiceNote && <p className="settings-note small">{voiceNote}</p>}
        </div>

        <div className="settings-field settings-tones">
          <label className="switch">
            <input type="checkbox" role="switch" checked={!sfxMuted} onChange={(e) => setTones(e.currentTarget.checked)} aria-describedby={tonesHintId} />
            <span className="switch-track" aria-hidden="true">
              <span className="switch-thumb" />
            </span>
            <span className="switch-label">
              Play feedback tones <span className="muted">(correct / wrong / streak / level-up)</span>
            </span>
          </label>
          <p id={tonesHintId} className="muted small settings-hint">
            Only the little chimes and buzzes. Russian speech always plays.
          </p>
          <div className="row">
            <button type="button" className={`btn ${playing === 'tones' ? 'playing' : ''}`} onClick={() => void testTones()} disabled={sfxMuted}>
              <span aria-hidden="true">🔔</span> Test tones
            </button>
            {sfxMuted && <span className="muted small">Tones are off.</span>}
          </div>
        </div>
      </section>

      <section className="card settings-section" aria-labelledby="settings-look">
        <h2 id="settings-look">Appearance</h2>
        <Segmented legend="Theme" hint="System follows your device’s light or dark mode." name="theme" choices={THEMES} value={theme} onChange={(t) => updateSettings({ theme: t })} />
      </section>

      <details className="card settings-help" open={helpOpen} onToggle={(e) => setHelpOpen(e.currentTarget.open)}>
        <summary>
          <span>Audio not working?</span>
          <span className="settings-chevron" aria-hidden="true" />
        </summary>
        <div className="settings-help-body">
          <VoiceHelp />
          <p className="small" style={{ margin: 0 }}>
            <a href={REVIEW_URL} target="_blank" rel="noopener noreferrer">
              Listen to every recorded clip
            </a>{' '}
            <span className="muted">(opens in a new tab) to check which ones are present.</span>
          </p>
        </div>
      </details>

      <section className="card settings-section" aria-labelledby="settings-keys">
        <h2 id="settings-keys">Keyboard shortcuts</h2>
        <dl className="settings-keys">
          <Shortcut keys={<><kbd>1</kbd>–<kbd>4</kbd></>}>Pick an answer</Shortcut>
          <Shortcut keys={<kbd>Space</kbd>}>Replay the current audio</Shortcut>
          <Shortcut keys={<kbd>Enter</kbd>}>Continue / Got it</Shortcut>
          <Shortcut keys={<><kbd>1</kbd>–<kbd>3</kbd></>}>
            On a Learn card: play the letter’s name / syllable / word
          </Shortcut>
          <Shortcut keys={<kbd>←</kbd>}>On a Learn card: go back to the previous letter</Shortcut>
          <Shortcut keys={<><kbd>1</kbd>–<kbd>9</kbd></>}>
            Word builder: pick a tile (or type the letter on a Russian keyboard layout)
          </Shortcut>
        </dl>
      </section>

      <DangerZone save={save} onReset={resetProgress} />
    </div>
  )
}

// ---------------------------------------------------------------------------

function Segmented<T extends string | number>({
  legend,
  hint,
  name,
  choices,
  value,
  onChange,
}: {
  legend: string
  hint?: string
  name: string
  choices: readonly Choice<T>[]
  value: T
  onChange: (v: T) => void
}) {
  const hintId = useId()
  return (
    <fieldset className="settings-field" aria-describedby={hint ? hintId : undefined}>
      <legend>{legend}</legend>
      {hint && (
        <p id={hintId} className="muted small settings-hint">
          {hint}
        </p>
      )}
      <div className="segmented">
        {choices.map((c) => (
          <label key={String(c.value)} className="segment">
            <input type="radio" name={`settings-${name}`} value={String(c.value)} checked={c.value === value} onChange={() => onChange(c.value)} aria-label={c.name} />
            <span className="segment-face">
              {c.icon}
              <span className="segment-text">
                <span className="segment-label">{c.label}</span>
                {c.sub && <span className="segment-sub">{c.sub}</span>}
              </span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}

function Shortcut({ keys, children }: { keys: ReactNode; children: ReactNode }) {
  return (
    <div>
      <dt>{keys}</dt>
      <dd>{children}</dd>
    </div>
  )
}

// ---------------------------------------------------------------------------

function DangerZone({ save, onReset }: { save: SaveData; onReset: () => void }) {
  const [step, setStep] = useState<'idle' | 'confirm' | 'done'>('idle')
  const resetRef = useRef<HTMLButtonElement>(null)
  const cancelRef = useRef<HTMLButtonElement>(null)
  // Only move focus after the user acted here, not on first render.
  const acted = useRef(false)

  useEffect(() => {
    if (!acted.current) return
    if (step === 'confirm') cancelRef.current?.focus()
    else resetRef.current?.focus()
  }, [step])

  // A letter counts as started once it was introduced or answered (False Friends / Word Builder previews).
  const met = Object.values(save.letters).filter((p) => p.introducedAt !== null || p.attempts > 0).length
  const streak = currentStreak(save, Date.now())
  const sessions = save.sessionsCompleted
  const found = [
    met > 0 ? `${met} ${met === 1 ? 'letter' : 'letters'} started` : '',
    sessions > 0 ? `${sessions} ${sessions === 1 ? 'session' : 'sessions'}` : '',
    streak > 0 ? `${streak}-day streak` : '',
  ].filter(Boolean)
  const parts = found.length ? found : ['no progress yet.']
  // Each part stays on one line; lines may break only at the separators.
  const summary = parts.map((p, i) => (
    <Fragment key={p}>
      {i > 0 && ' · '}
      <span className="settings-nowrap">
        {i === 0 && 'Now: '}
        {p}
      </span>
    </Fragment>
  ))

  const go = (s: typeof step) => {
    acted.current = true
    setStep(s)
  }

  function onConfirmKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.stopPropagation()
      go('idle')
    }
  }

  return (
    <section className="card settings-section settings-danger" aria-labelledby="settings-danger">
      <h2 id="settings-danger">Danger zone</h2>
      <div className="settings-danger-row">
        <div>
          <h3>Reset progress</h3>
          <p className="muted small" style={{ margin: 0 }}>
            Start over from the first letters. Your settings above are kept.
            <br />
            {summary}
          </p>
        </div>
        {step !== 'confirm' && (
          <button ref={resetRef} type="button" className="btn btn-danger" data-testid="reset-progress" onClick={() => go('confirm')}>
            Reset progress
          </button>
        )}
      </div>

      {step === 'confirm' && (
        <div className="settings-confirm" role="group" aria-labelledby="settings-confirm-text" onKeyDown={onConfirmKey}>
          <p id="settings-confirm-text">
            <strong>This erases all letter progress, stats and your streak.</strong> It can’t be undone.
          </p>
          <div className="row">
            <button
              type="button"
              className="btn btn-danger-solid"
              data-testid="confirm-reset"
              onClick={() => {
                onReset()
                go('done')
              }}
            >
              Yes, reset
            </button>
            <button ref={cancelRef} type="button" className="btn" onClick={() => go('idle')}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div role="status" className="settings-live">
        {step === 'done' && (
          <p className="settings-done">
            <span aria-hidden="true">✓</span> Progress reset. You’re back at the start with your settings unchanged.
          </p>
        )}
      </div>
    </section>
  )
}
