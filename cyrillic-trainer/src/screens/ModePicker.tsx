import './modepicker.css'
import { Fragment, useEffect, useState, type ReactNode } from 'react'
import { useKeys } from '../hooks/useKeys'
import { MODES } from '../modes/modes'
import { href, navigate } from '../router'
import { lettersToLearn, practicePool } from '../session/items'
import { BATCHES, dueLetterIds, nextDueAt, unlockedIds } from '../srs/scheduler'
import { useStore } from '../state/store'

type ModeKey = 'learn' | 'listen' | 'read' | 'false-friends' | 'builder' | 'review'
type Tone = 'accent' | 'good' | 'bad' | 'warn' | 'neutral'

interface ModeCard {
  key: ModeKey
  path: string
  title: string
  blurb: string
  tone: Tone
  icon: ReactNode
  /** Status line under the blurb (letters waiting, due count, …). */
  meta?: ReactNode
}

const LEARN_BLURB = 'One big letter card at a time: shapes, sounds, hints'
/** Letters listed on the Learn card before collapsing into "+N". */
const MAX_SHOWN = 5

/** Re-renders every `ms` (and when the tab becomes visible) so due counts stay fresh. */
function useNow(ms: number): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const tick = () => setNow(Date.now())
    const t = window.setInterval(tick, ms)
    const onVisible = () => {
      if (document.visibilityState === 'visible') tick()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.clearInterval(t)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [ms])
  return now
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

/** "in 5 min", "in 3 h", "in 2 days". */
function fromNow(ms: number): string {
  const min = Math.max(1, Math.round(ms / 60_000))
  if (min < 60) return `in ${min} min`
  const h = Math.round(min / 60)
  if (h < 24) return `in ${h} h`
  return `in ${plural(Math.round(h / 24), 'day')}`
}

/** Wraps runs of Cyrillic in lang="ru" so they get the letter font. */
function withRu(text: string): ReactNode {
  return text.split(/([Ѐ-ӿ]+(?:[\s,]+[Ѐ-ӿ]+)*)/).map((part, i) =>
    i % 2 === 1 ? (
      <span key={i} lang="ru">
        {part}
      </span>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    ),
  )
}

/**
 * Status line under a card's blurb: a short pill plus optional extra text.
 * The two wrap as separate pieces, so a pill never breaks into a two-line box.
 */
function Meta({ hot = false, note = false, extra, children }: { hot?: boolean; note?: boolean; extra?: ReactNode; children: ReactNode }) {
  return (
    <span className="mode-meta-row">
      <span className={`mode-meta${hot ? ' is-hot' : ''}${note ? ' mode-note' : ''}`}>
        {note && (
          <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
            <circle cx="8" cy="8" r="6.6" fill="none" stroke="currentColor" strokeWidth="1.6" />
            <path d="M8 7.2v4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            <circle cx="8" cy="4.8" r="1" fill="currentColor" />
          </svg>
        )}
        {children}
      </span>
      {extra && (
        <>
          {/* Keeps the link's accessible name from running the two pieces together. */}
          <span className="sr-only">, </span>
          {extra}
        </>
      )}
    </span>
  )
}

function SpeakerIcon() {
  return (
    <svg className="mi-speaker" viewBox="0 0 32 32" aria-hidden="true">
      <path d="M5 12.5h4.5L16 7v18l-6.5-5.5H5z" fill="currentColor" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M20.5 11.5a6.4 6.4 0 0 1 0 9" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M24.2 7.8a11.6 11.6 0 0 1 0 16.4" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  )
}

export function ModePicker() {
  const { save } = useStore()
  const now = useNow(30_000)

  const pool = practicePool(save)
  const hasLetters = pool.length > 0
  const toLearn = lettersToLearn(save, unlockedIds(save.unlockedBatches))
  const due = dueLetterIds(save.letters, now).length
  const nextDue = nextDueAt(save.letters, now)
  const allOpen = save.unlockedBatches >= BATCHES.length

  const needLetters = <Meta note>Learn a few letters first</Meta>
  const poolMeta = hasLetters ? <Meta>Uses your {plural(pool.length, 'letter')}</Meta> : needLetters

  const learnMeta =
    toLearn.length > 0 ? (
      <Meta
        hot
        extra={
          <span className="mode-meta-extra">
            <span className="mode-meta-letters glyph-print" lang="ru">
              {toLearn
                .slice(0, MAX_SHOWN)
                .map((l) => l.upper)
                .join(' ')}
            </span>
            {toLearn.length > MAX_SHOWN ? ` +${toLearn.length - MAX_SHOWN}` : ''}
          </span>
        }
      >
        {plural(toLearn.length, 'new letter')}
      </Meta>
    ) : allOpen && hasLetters ? (
      <Meta>All 33 letters met</Meta>
    ) : hasLetters ? (
      <Meta>Practise to unlock more</Meta>
    ) : null

  const reviewMeta = !hasLetters ? (
    needLetters
  ) : due > 0 ? (
    <Meta hot>{plural(due, 'letter')} due now</Meta>
  ) : (
    <Meta extra={nextDue !== null ? <span className="mode-meta-extra">next due {fromNow(nextDue - now)}</span> : undefined}>
      All caught up
    </Meta>
  )

  const cards: ModeCard[] = [
    {
      key: 'learn',
      path: 'learn',
      title: 'Learn',
      blurb: LEARN_BLURB,
      tone: 'accent',
      icon: (
        <span className="mi-learn glyph-print" lang="ru">
          А<span className="mi-lower">а</span>
        </span>
      ),
      meta: learnMeta,
    },
    {
      key: 'listen',
      path: 'play/listen',
      title: MODES.listen.title,
      blurb: MODES.listen.blurb,
      tone: 'good',
      icon: <SpeakerIcon />,
      meta: poolMeta,
    },
    {
      key: 'read',
      path: 'play/read',
      title: MODES.read.title,
      blurb: MODES.read.blurb,
      tone: 'accent',
      icon: (
        <span className="mi-read">
          <span className="glyph-print" lang="ru">
            Ж
          </span>
          <span className="mi-arrow">→</span>
          <span className="mi-latin">zh</span>
        </span>
      ),
      meta: poolMeta,
    },
    {
      key: 'false-friends',
      path: 'play/false-friends',
      title: MODES['false-friends'].title,
      blurb: MODES['false-friends'].blurb,
      tone: 'bad',
      icon: (
        <span className="mi-ff">
          <span className="glyph-print" lang="ru">
            Р
          </span>
          <span className="mi-neq">≠</span>
          <span className="mi-latin">P</span>
        </span>
      ),
    },
    {
      key: 'builder',
      path: 'play/builder',
      title: MODES.builder.title,
      blurb: MODES.builder.blurb,
      tone: 'warn',
      icon: (
        <span className="mi-tiles" lang="ru">
          <span>к</span>
          <span>о</span>
          <span>т</span>
        </span>
      ),
    },
    {
      key: 'review',
      path: 'play/review',
      title: MODES.review.title,
      blurb: MODES.review.blurb,
      tone: hasLetters && due > 0 ? 'accent' : 'neutral',
      icon: (
        <span className="mi-review">
          <span className="mi-count">{hasLetters ? due : '–'}</span>
          <span className="mi-count-label">due</span>
        </span>
      ),
      meta: reviewMeta,
    },
  ]

  useKeys(Object.fromEntries(cards.map((c, i) => [String(i + 1), () => navigate(c.path)])))

  return (
    <div className="modes">
      <header className="modes-head">
        <h1>Practice</h1>
        <p className="muted">
          Pick a way to practise, or press its number. Not sure? <a href={href('session')}>Start today’s session</a>.
        </p>
      </header>

      <ul className="modes-grid" aria-label="Practice modes">
        {cards.map((c, i) => (
          <li key={c.key}>
            <a
              className="mode-card"
              href={href(c.path)}
              data-testid={`mode-${c.key}`}
              data-tone={c.tone}
              aria-keyshortcuts={String(i + 1)}
            >
              <span className="mode-icon" aria-hidden="true">
                {c.icon}
              </span>
              <div className="mode-body">
                <h2 className="mode-title">{c.title}</h2>
                <p className="mode-blurb">{withRu(c.blurb)}</p>
                {c.meta}
              </div>
              <kbd className="mode-key" aria-hidden="true">
                {i + 1}
              </kbd>
            </a>
          </li>
        ))}
      </ul>

      <p className="modes-help muted small">
        <span>Keyboard:</span>{' '}
        <span>
          <kbd>1</kbd>–<kbd>4</kbd> answer ·
        </span>{' '}
        <span>
          <kbd>Space</kbd> replays audio ·
        </span>{' '}
        <span>
          <kbd>Enter</kbd> continues
        </span>
      </p>
    </div>
  )
}
