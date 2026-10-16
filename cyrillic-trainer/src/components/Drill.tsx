import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { player } from '../audio/player'
import { sfx } from '../audio/sfx'
import { LETTER_BY_ID, type Letter } from '../data/letters'
import { useKeys, useSpaceReplay } from '../hooks/useKeys'
import { href } from '../router'
import { retryOf, soundClips, type BuilderItem, type ChoiceItem, type Item } from '../session/items'
import { MAX_RETRIES, insertRetry } from '../session/queue'
import { seededRng, type Rng } from '../session/rng'
import { useStore } from '../state/store'
import { useAutoPlay } from '../hooks/useAutoPlay'
import { BuilderBoard } from './BuilderBoard'
import { OptionGrid } from './OptionGrid'

export interface DrillProps {
  title: string
  /** Builds the round's opening queue (called again for "Play again"). */
  start: (rng: Rng) => Item[]
  /** Endless modes: more items when the queue runs out. */
  more?: (rng: Rng) => Item[]
  /** Timed modes: round length in seconds. */
  timeLimitSec?: number
  /** Letters available as distractors when an item is retried. */
  pool: readonly Letter[]
  /** Shown instead of the drill when there's nothing to practise. */
  empty?: ReactNode
}

/** Runs a drill round; "Play again" remounts a fresh round. */
export function Drill(props: DrillProps) {
  const [round, setRound] = useState(0)
  return <DrillRound key={round} {...props} onAgain={() => setRound((r) => r + 1)} />
}

interface Stats {
  answered: number
  correct: number
  streak: number
  best: number
  /** Letter ids missed at least once, in order of first miss. */
  missed: string[]
}

interface Feedback {
  correct: boolean
  /** Option index picked (choice items). */
  chosen: number | null
}

const STREAK_EVERY = 5
const ADVANCE_MS = 650

function DrillRound({ title, start, more, timeLimitSec, pool, empty, onAgain }: DrillProps & { onAgain: () => void }) {
  const store = useStore()
  const [rng] = useState(() => seededRng(Date.now() >>> 0))
  const [queue, setQueue] = useState<Item[]>(() => start(rng))
  const [index, setIndex] = useState(0)
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [stats, setStats] = useState<Stats>({ answered: 0, correct: 0, streak: 0, best: 0, missed: [] })
  const [done, setDone] = useState(false)
  const [timeLeft, setTimeLeft] = useState(timeLimitSec ?? 0)
  const shownAt = useRef(0)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const finished = useRef(false)
  const streakRef = useRef(0)
  /** Uids already answered / advanced past: guards against double key presses and late timers. */
  const answered = useRef<string | null>(null)
  const advanced = useRef<string | null>(null)

  const item = queue[index] as Item | undefined
  const itemRef = useRef(item)
  useLayoutEffect(() => {
    itemRef.current = item
  })

  const finish = useCallback(() => {
    if (finished.current) return
    finished.current = true
    if (timer.current) clearTimeout(timer.current)
    player.stop()
    setDone(true)
    store.completeSession()
  }, [store])

  // Out of items: top up endless modes, otherwise end the round.
  useEffect(() => {
    if (done || queue.length === 0 || index < queue.length) return
    if (more) {
      const extra = more(rng)
      setQueue((q) => [...q, ...extra])
    } else finish()
  }, [index, queue.length, more, rng, done, finish])

  useEffect(() => {
    shownAt.current = performance.now()
  }, [item?.uid])

  // Countdown for timed rounds.
  useEffect(() => {
    if (!timeLimitSec || done) return
    const t = setInterval(() => setTimeLeft((s) => Math.max(0, s - 1)), 1000)
    return () => clearInterval(t)
  }, [timeLimitSec, done])
  useEffect(() => {
    if (timeLimitSec && timeLeft === 0) finish()
  }, [timeLeft, timeLimitSec, finish])

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current)
      player.stop()
    },
    [],
  )

  /** Moves past item `uid` — once, and only if it is still the current item. */
  const advance = useCallback((uid: string) => {
    if (itemRef.current?.uid !== uid || advanced.current === uid) return
    advanced.current = uid
    if (timer.current) clearTimeout(timer.current)
    timer.current = null
    setFeedback(null)
    setIndex((i) => i + 1)
  }, [])
  const next = () => item && advance(item.uid)

  /** Records one answer for one letter (choice items: one per item; builder: one per slot). */
  const record = useCallback(
    (letterId: string, correct: boolean, fastMs: number, chosenId?: string) => {
      const responseMs = performance.now() - shownAt.current
      shownAt.current = performance.now()
      store.answer({ letterId, correct, responseMs, fastMs, chosenId })
      const streak = correct ? streakRef.current + 1 : 0
      streakRef.current = streak
      setStats((s) => ({
        answered: s.answered + 1,
        correct: s.correct + (correct ? 1 : 0),
        streak,
        best: Math.max(s.best, streak),
        missed: correct || s.missed.includes(letterId) ? s.missed : [...s.missed, letterId],
      }))
      return streak
    },
    [store],
  )

  /** Finishes the current item: misses come back 2 items later. */
  const settle = useCallback(
    (missed: boolean, clipsAfter: readonly string[], streak: number, playTone = true) => {
      if (!item) return
      if (missed && item.retries < MAX_RETRIES) {
        const retry = retryOf(item, pool, rng)
        setQueue((q) => insertRetry(q, index, retry))
      }
      const tone = !playTone
        ? Promise.resolve()
        : missed
          ? sfx.wrong()
          : streak > 0 && streak % STREAK_EVERY === 0
            ? sfx.correct().then(sfx.streak)
            : sfx.correct()
      // Wrong answers: after the buzz, play the right letter's clip. Read modes play the audio after any answer.
      const playAfter = missed || item.kind !== 'listen' ? clipsAfter : []
      const audio = tone.then(() => (playAfter.length && !finished.current ? player.play(playAfter) : undefined))
      if (!missed || timeLimitSec) {
        const uid = item.uid
        void audio.then(() => {
          if (!finished.current && itemRef.current?.uid === uid) {
            timer.current = setTimeout(() => advance(uid), missed ? ADVANCE_MS * 2 : ADVANCE_MS)
          }
        })
      }
    },
    [item, index, pool, rng, advance, timeLimitSec],
  )

  const pick = (choice: number) => {
    if (!item || item.kind === 'builder' || feedback || done || answered.current === item.uid) return
    if (choice >= item.options.length) return
    answered.current = item.uid
    const correct = choice === item.answer
    const streak = record(item.target.id, correct, item.fastMs, item.options[choice].letterId)
    setFeedback({ correct, chosen: choice })
    settle(!correct, item.kind === 'read-word' ? item.clips : soundClips(item.target), streak)
  }

  const builderDone = (missed: boolean, streak: number) => {
    if (!item || item.kind !== 'builder' || answered.current === item.uid) return
    answered.current = item.uid
    setFeedback({ correct: !missed, chosen: null })
    // Wrong taps already buzzed; a missed word just replays the word.
    settle(missed, [item.word.audio], streak, !missed)
  }

  useSpaceReplay(!done)
  useKeys(
    {
      '1': () => pick(0),
      '2': () => pick(1),
      '3': () => pick(2),
      '4': () => pick(3),
      Enter: () => feedback && !feedback.correct && next(),
    },
    !done && item?.kind !== 'builder',
  )
  useKeys({ Enter: () => feedback && next() }, !done && item?.kind === 'builder' && feedback !== null)

  if (queue.length === 0) return <>{empty}</>
  if (done) return <Summary title={title} stats={stats} onAgain={onAgain} timed={!!timeLimitSec} />
  if (!item) return null

  const total = timeLimitSec ? null : queue.length
  return (
    <div className="stack drill" data-testid="drill">
      <div className="spread">
        <h1 style={{ margin: 0, fontSize: '1.3rem' }}>{title}</h1>
        <div className="row">
          {timeLimitSec ? (
            <span className={`pill ${timeLeft <= 5 ? 'pill-hot' : ''}`} aria-label={`${timeLeft} seconds left`}>
              ⏱ {timeLeft}s
            </span>
          ) : null}
          <span className="pill" aria-label={`Streak ${stats.streak}`}>
            🔥 {stats.streak}
          </span>
          <span className="pill" data-testid="score">
            {stats.correct}/{stats.answered}
          </span>
        </div>
      </div>
      {total !== null && (
        <div className="progress" aria-hidden="true">
          <span style={{ width: `${(index / total) * 100}%` }} />
        </div>
      )}
      {item.kind === 'builder' ? (
        <BuilderBoard key={item.uid} item={item} record={record} onDone={builderDone} feedback={feedback} />
      ) : (
        <ChoiceView key={item.uid} item={item} feedback={feedback} onPick={pick} />
      )}
      {feedback && <FeedbackPanel item={item} feedback={feedback} onNext={next} timed={!!timeLimitSec} />}
    </div>
  )
}

// ---------------------------------------------------------------------------

const QUESTION: Record<ChoiceItem['kind'], string> = {
  listen: 'Which letter do you hear?',
  'read-letter': 'How does it sound?',
  'read-word': 'How do you read it?',
  'false-friend': 'What sound is it really?',
}

function ChoiceView({ item, feedback, onPick }: { item: ChoiceItem; feedback: Feedback | null; onPick: (i: number) => void }) {
  const isListen = item.kind === 'listen'
  const { blocked, replay } = useAutoPlay(isListen ? item.clips : null, item.uid)
  const question =
    isListen && item.target.contrastText
      ? `Which letter turns ${item.target.contrastText[0]} into ${item.target.contrastText[1]}?`
      : QUESTION[item.kind]
  return (
    <div className="stack">
      <div className="card prompt" data-kind={item.kind} data-clips={item.clips.join(' ')} data-testid="prompt-card">
        {isListen ? (
          <button type="button" className={`btn btn-big listen-btn ${blocked ? 'btn-primary' : ''}`} onClick={replay}>
            🔊 {blocked ? 'Tap to listen' : 'Play again'} <kbd>Space</kbd>
          </button>
        ) : (
          <div className={`glyph-print prompt-glyph ${item.kind === 'read-word' ? 'is-word' : ''}`} lang="ru" data-testid="prompt">
            {item.display}
          </div>
        )}
        <p className="muted" style={{ margin: 0 }}>
          {question}
        </p>
      </div>
      <OptionGrid options={item.options} chosen={feedback?.chosen ?? null} answer={item.answer} onPick={onPick} />
    </div>
  )
}

function FeedbackPanel({ item, feedback, onNext, timed }: { item: Item; feedback: Feedback; onNext: () => void; timed: boolean }) {
  if (item.kind === 'builder') {
    const w = item.word
    return (
      <div className={`feedback ${feedback.correct ? 'good' : 'bad'}`} role="status">
        <div className="big" lang="ru">
          {w.stressed}
        </div>
        <div style={{ flex: 1 }}>
          <strong>{feedback.correct ? 'Spelled it!' : 'Almost — this word comes back soon.'}</strong>
          <div>
            {w.en} <span className="muted">· PL: {w.pl}</span>
          </div>
        </div>
        {!feedback.correct && <NextButton onNext={onNext} />}
      </div>
    )
  }
  const l = item.target
  if (feedback.correct) {
    return (
      <div className="feedback good" role="status">
        <strong>✓ Correct</strong>
        {item.word && (
          <span>
            <span lang="ru">{item.word.stressed}</span> — {item.word.en}
          </span>
        )}
      </div>
    )
  }
  return (
    <div className="feedback bad" role="status" data-testid="feedback-wrong">
      <div className="big" lang="ru">
        {item.word ? item.word.stressed : `${l.upper}${l.lower}`}
      </div>
      <div style={{ flex: 1 }}>
        <strong>It was {item.options[item.answer].label}</strong>
        <div className="small">
          {item.word ? (
            <>
              {item.word.en} · <span lang="ru">{l.upper}</span> reads “{l.sound}”
            </>
          ) : (
            <>
              <span lang="ru">{l.name}</span> · sounds like “{l.sound}” · {l.hintEn}
            </>
          )}
        </div>
      </div>
      {!timed && <NextButton onNext={onNext} />}
    </div>
  )
}

function NextButton({ onNext }: { onNext: () => void }) {
  return (
    <button className="btn btn-primary" onClick={onNext} autoFocus data-testid="continue">
      Continue <kbd>Enter</kbd>
    </button>
  )
}

function Summary({ title, stats, onAgain, timed }: { title: string; stats: Stats; onAgain: () => void; timed: boolean }) {
  const pct = stats.answered ? Math.round((stats.correct / stats.answered) * 100) : 0
  useKeys({ Enter: onAgain })
  return (
    <div className="card stack" data-testid="summary" style={{ textAlign: 'center' }}>
      <h1>{timed ? 'Time!' : 'Round complete'}</h1>
      <p style={{ fontSize: '1.3rem', margin: 0 }}>
        <strong>{stats.correct}</strong> / {stats.answered} correct ({pct}%) · best streak {stats.best}
      </p>
      <p className="muted" style={{ margin: 0 }}>
        {title}
      </p>
      {stats.missed.length > 0 && (
        <div>
          <p className="small muted">Worth another look:</p>
          <div className="row" style={{ justifyContent: 'center' }}>
            {stats.missed.map((id) => {
              const l = LETTER_BY_ID.get(id)!
              return (
                <a key={id} className="btn" href={href(`learn/${id}`)} lang="ru">
                  {l.upper} {l.lower}
                </a>
              )
            })}
          </div>
        </div>
      )}
      <div className="row" style={{ justifyContent: 'center' }}>
        <button className="btn btn-primary btn-big" onClick={onAgain} autoFocus>
          Play again <kbd>Enter</kbd>
        </button>
        <a className="btn" href={href('modes')}>
          Other modes
        </a>
        <a className="btn" href={href('')}>
          Home
        </a>
      </div>
    </div>
  )
}

export type { BuilderItem }
