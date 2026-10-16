import { useRef, useState } from 'react'
import { player } from '../audio/player'
import { sfx } from '../audio/sfx'
import { useKeys } from '../hooks/useKeys'
import { soundClips, type BuilderItem } from '../session/items'
import { useAutoPlay } from '../hooks/useAutoPlay'

interface Props {
  item: BuilderItem
  /** Records one slot; returns the running streak. */
  record: (letterId: string, correct: boolean, fastMs: number, chosenId?: string) => number
  onDone: (missed: boolean, streak: number) => void
  feedback: { correct: boolean } | null
}

/** Word Builder: hear the word, tap its letters in order. */
export function BuilderBoard({ item, record, onDone, feedback }: Props) {
  const [filled, setFilled] = useState(0)
  const [missedSlots, setMissedSlots] = useState<number[]>([])
  const [shake, setShake] = useState<number | null>(null)
  const missed = useRef(false)
  const { blocked, replay } = useAutoPlay([item.word.audio], item.uid)
  const complete = filled >= item.letters.length

  const tap = (tileIndex: number) => {
    if (complete || feedback) return
    const tapped = item.tiles[tileIndex]
    const expected = item.letters[filled]
    const ok = tapped === expected
    const streak = record(expected.id, ok, item.fastMs, ok ? undefined : tapped.id)
    if (!ok) {
      missed.current = true
      setMissedSlots((m) => [...m, filled])
      setShake(tileIndex)
      // Show the right letter in its slot and play its sound.
      void sfx.wrong().then(() => player.play(soundClips(expected)))
    }
    const nextFilled = filled + 1
    setFilled(nextFilled)
    if (nextFilled >= item.letters.length) onDone(missed.current, streak)
  }

  const keys: Record<string, () => void> = {}
  item.tiles.forEach((t, i) => {
    keys[String(i + 1)] = () => tap(i)
    keys[t.lower] = () => tap(i) // a Russian keyboard layout types the letter directly
  })
  useKeys(keys, !complete && !feedback)

  return (
    <div className="stack">
      <div className="card prompt">
        <button type="button" className={`btn btn-big listen-btn ${blocked ? 'btn-primary' : ''}`} onClick={replay}>
          🔊 {blocked ? 'Tap to listen' : 'Play again'} <kbd>Space</kbd>
        </button>
        <p className="muted" style={{ margin: 0 }}>
          Spell the word you hear.
        </p>
        <div className="slots" lang="ru" aria-label="Your spelling">
          {item.letters.map((l, i) => (
            <span
              key={i}
              className={`slot ${i < filled ? 'filled' : ''} ${i === filled && !complete ? 'current' : ''} ${missedSlots.includes(i) ? 'missed' : ''}`}
              data-testid={`slot-${i}`}
            >
              {i < filled ? l.lower : ''}
            </span>
          ))}
        </div>
      </div>
      <div className="tiles" role="group" aria-label="Letters">
        {item.tiles.map((t, i) => (
          <button
            key={t.id}
            type="button"
            lang="ru"
            className={`option cyrillic tile ${shake === i ? 'wrong' : ''}`}
            onClick={() => tap(i)}
            onAnimationEnd={() => setShake(null)}
            disabled={complete || !!feedback}
            data-testid={`tile-${t.lower}`}
            aria-label={`${t.lower} (${i + 1})`}
          >
            <span className="key" aria-hidden="true">
              {i + 1}
            </span>
            {t.lower}
          </button>
        ))}
      </div>
    </div>
  )
}
