import './home.css'
import { useEffect, useState } from 'react'
import { GROUPS, GROUP_ORDER, LETTERS, LETTER_BY_ID, LETTER_BY_UPPER, type GroupId, type Letter } from '../data/letters'
import { href } from '../router'
import { SESSION_LENGTH, lettersToLearn, practicePool } from '../session/items'
import {
  BATCHES,
  MIN_ANSWERS_FOR_UNLOCK,
  UNLOCK_THRESHOLD,
  dueLetterIds,
  mastery,
  nextDueAt,
  recentAccuracy,
  unlockStatus,
  unlockedIds,
  type Mastery,
} from '../srs/scheduler'
import { currentStreak, localDay } from '../state/actions'
import type { LetterProgress, SaveData } from '../state/schema'
import { useStore } from '../state/store'

const MINUTE = 60_000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR
const GROUP_IDS: readonly GroupId[] = [1, 2, 3, 4, 5]
const MASTERY_ORDER: readonly Mastery[] = ['new', 'learning', 'known', 'mastered']
const MASTERY_LABEL: Record<Mastery, string> = { new: 'New', learning: 'Learning', known: 'Known', mastered: 'Mastered' }
/** Most letters listed inline in the hero before collapsing into "+N". */
const MAX_HERO_CHIPS = 10

/** The current time, refreshed every 30 s (and when the tab becomes visible) so due counts stay fresh. */
function useNow(everyMs = 30_000): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const tick = () => setNow(Date.now())
    const id = window.setInterval(tick, everyMs)
    const onVisible = () => {
      if (document.visibilityState === 'visible') tick()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.clearInterval(id)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [everyMs])
  return now
}

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`
const percent = (x: number) => Math.round(x * 100)

/** "under a minute", "25 min", "3 h", "2 days". */
function formatWait(ms: number): string {
  if (ms < MINUTE) return 'under a minute'
  if (ms < HOUR) return `${Math.ceil(ms / MINUTE)} min`
  if (ms < DAY) return `${Math.round(ms / HOUR)} h`
  return plural(Math.round(ms / DAY), 'day')
}

function greeting(now: number): { ru: string; en: string } {
  const h = new Date(now).getHours()
  if (h >= 5 && h < 12) return { ru: 'Доброе утро!', en: 'Good morning' }
  if (h >= 12 && h < 18) return { ru: 'Добрый день!', en: 'Good afternoon' }
  if (h >= 18 && h < 23) return { ru: 'Добрый вечер!', en: 'Good evening' }
  return { ru: 'Привет!', en: 'Hi there' }
}

function endOfDay(now: number): number {
  const d = new Date(now)
  d.setHours(24, 0, 0, 0)
  return d.getTime()
}

const letterOf = (id: string) => LETTER_BY_ID.get(id)!
const uppers = (ids: readonly string[]) => ids.map((id) => letterOf(id).upper).join(' ')

export function Home() {
  const { save } = useStore()
  const now = useNow()

  const unlocked = unlockedIds(save.unlockedBatches)
  const toLearn = lettersToLearn(save, unlocked)
  const metCount = practicePool(save).length
  const due = dueLetterIds(save.letters, now)

  return (
    <div className="stack home">
      <Hero save={save} now={now} toLearn={toLearn} due={due} metCount={metCount} />
      <StatTiles save={save} now={now} due={due} metCount={metCount} />
      <UnlockCard save={save} />
      <LetterMap save={save} unlocked={new Set(unlocked)} due={new Set(due)} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Hero: what "Start session" will do right now
// ---------------------------------------------------------------------------

function Hero({
  save,
  now,
  toLearn,
  due,
  metCount,
}: {
  save: SaveData
  now: number
  toLearn: readonly Letter[]
  due: readonly string[]
  metCount: number
}) {
  const hello = greeting(now)
  let title: string
  let plan: string
  let chips: { letter: Letter; mastery?: Mastery }[] = []

  if (toLearn.length > 0) {
    title = metCount === 0 ? 'Let’s meet your first letters' : `${plural(toLearn.length, 'new letter')} to meet`
    plan = `Start session introduces ${toLearn.length === 1 ? 'it' : `these ${toLearn.length}`}, one card at a time, with audio:`
    chips = toLearn.map((letter) => ({ letter }))
  } else if (due.length > 0) {
    title = 'Time for a quick review'
    // The review round takes at most SESSION_LENGTH.review letters, most overdue first.
    plan =
      due.length > SESSION_LENGTH.review
        ? `Start session reviews the ${SESSION_LENGTH.review} most overdue of your ${due.length} due letters, across all modes:`
        : `Start session reviews your ${plural(due.length, 'due letter')} across all modes:`
    chips = due.map((id) => ({ letter: letterOf(id), mastery: mastery(save.letters[id]) }))
  } else {
    title = 'You’re all caught up'
    const next = nextDueAt(save.letters, now)
    plan = `Nothing is due${next !== null ? ` for ${formatWait(next - now)}` : ''} — Start session practises your weakest letters.`
  }

  const shown = chips.slice(0, MAX_HERO_CHIPS)
  const watermark = chips[0]?.letter.upper ?? 'Я'

  return (
    <section className="card home-hero" aria-labelledby="home-title">
      <span className="home-hero-glyph glyph-print" lang="ru" aria-hidden="true">
        {watermark}
      </span>
      <p className="home-greeting">
        <span lang="ru">{hello.ru}</span> <span className="muted">{hello.en}.</span>
      </p>
      <h1 id="home-title">{title}</h1>
      <p className="home-plan">{plan}</p>
      {shown.length > 0 && (
        <ul className="home-chips" aria-label="Letters in this session">
          {shown.map(({ letter, mastery: m }) => (
            <li key={letter.id} className={`home-chip glyph-print ${m ? `m-${m}` : 'home-chip-plain'}`} lang="ru">
              {letter.upper}
            </li>
          ))}
          {chips.length > shown.length && <li className="home-chip home-chip-more">+{chips.length - shown.length}</li>}
        </ul>
      )}
      <div className="row home-actions">
        <a className="btn btn-primary btn-big" href={href('session')} data-testid="start-session">
          Start session
          <svg className="home-arrow" viewBox="0 0 20 20" width="20" height="20" aria-hidden="true">
            <path d="M4 10h11m-4.5-4.5L15 10l-4.5 4.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </a>
        {metCount > 0 && (
          <a className="btn btn-big" href={href('play/review')} data-testid="daily-review">
            Daily review
            <span className="home-count">{due.length} due</span>
          </a>
        )}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Stat tiles: due, streak, letters learned
// ---------------------------------------------------------------------------

function StatTiles({ save, now, due, metCount }: { save: SaveData; now: number; due: readonly string[]; metCount: number }) {
  // Due
  let dueSub: string
  if (metCount === 0) dueSub = 'Meet letters first'
  else if (due.length > 0) {
    const eod = endOfDay(now)
    const later = Object.values(save.letters).filter((p) => p.introducedAt !== null && p.due > now && p.due < eod).length
    dueSub = later > 0 ? `+${later} more later today` : 'Ready to review'
  } else {
    const next = nextDueAt(save.letters, now)
    dueSub = next !== null ? `Next in ${formatWait(next - now)}` : 'Nothing scheduled'
  }

  // Streak
  const streak = currentStreak(save, now)
  const best = Math.max(save.streak.best, streak)
  const doneToday = save.streak.lastDay === localDay(now)
  const streakStatus = doneToday ? 'Done today' : streak > 0 ? 'Practise today' : best > 0 ? null : 'Finish a session'

  // Learned
  const mastered = LETTERS.filter((l) => mastery(save.letters[l.id]) === 'mastered').length
  const total = LETTERS.length

  return (
    <section className="home-stats" aria-label="Today">
      <div className={`card home-stat${due.length > 0 ? ' is-hot' : ''}`} data-testid="stat-due">
        <h2 className="home-stat-label">Due now</h2>
        <p className="home-stat-value">{due.length}</p>
        <p className="home-stat-sub">{dueSub}</p>
      </div>
      <div className="card home-stat" data-testid="stat-streak">
        <h2 className="home-stat-label">Day streak</h2>
        <p className="home-stat-value">
          {streak}
          <small className="home-stat-unit"> {streak === 1 ? 'day' : 'days'}</small>
        </p>
        <p className="home-stat-sub home-stat-sub-split">
          {streakStatus && <span>{streakStatus}</span>}
          {streakStatus && best > 0 && (
            <span className="home-stat-sep" aria-hidden="true">
              {' · '}
            </span>
          )}
          {best > 0 && <span>{streakStatus ? 'best' : 'Best'} {best}</span>}
        </p>
      </div>
      <div className="card home-stat" data-testid="stat-learned">
        <h2 className="home-stat-label">Learned</h2>
        <p className="home-stat-value">
          {metCount}
          <small>/{total}</small>
        </p>
        <div
          className="progress home-stat-bar"
          role="progressbar"
          aria-label="Letters learned"
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={metCount}
        >
          <span style={{ width: `${(metCount / total) * 100}%` }} />
        </div>
        <p className="home-stat-sub">{mastered} mastered</p>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Unlock progress
// ---------------------------------------------------------------------------

function InlineLetters({ ids }: { ids: readonly string[] }) {
  return (
    <b className="home-inline-letters" lang="ru">
      {uppers(ids)}
    </b>
  )
}

function UnlockCard({ save }: { save: SaveData }) {
  const status = unlockStatus(save.letters, save.unlockedBatches)
  const group = GROUPS[status.group]

  if (status.complete) {
    return (
      <section className="card home-unlock" aria-labelledby="home-unlock-title" data-testid="unlock">
        <p className="home-eyebrow">All 5 groups open</p>
        <h2 id="home-unlock-title">Every letter is unlocked</h2>
        <p className="muted home-unlock-text">Keep reviewing until the whole map turns green.</p>
      </section>
    )
  }

  const nextBatch = BATCHES[Math.max(1, save.unlockedBatches)]
  const acc = status.groupAccuracy
  const target = percent(UNLOCK_THRESHOLD)
  const passing = acc !== null && acc >= UNLOCK_THRESHOLD
  // Rounding must never contradict the threshold check: 79.6% shows as 79%, not "80% … lift it to 80%".
  const pct = acc === null ? 0 : passing ? Math.max(target, percent(acc)) : Math.min(target - 1, percent(acc))
  const notMet = status.pending.filter((id) => save.letters[id]?.introducedAt == null)
  const fewAnswers = status.pending.filter((id) => save.letters[id]?.introducedAt != null)

  return (
    <section className="card home-unlock" aria-labelledby="home-unlock-title" data-testid="unlock">
      <div className="home-unlock-head">
        <div>
          <p className="home-eyebrow">Group {status.group} of 5 · unlock progress</p>
          <h2 id="home-unlock-title">{group.title}</h2>
          <p className="muted small home-unlock-text">{group.blurb}</p>
        </div>
        <div className="home-next" data-testid="unlock-next">
          <span className="small muted">{status.ready ? 'Unlocking next' : 'Next to unlock'}</span>
          <ul className="home-chips home-chips-small" aria-label="Letters that unlock next">
            {nextBatch.ids.map((id) => (
              <li key={id} className="home-chip home-chip-locked glyph-print" lang="ru">
                {letterOf(id).upper}
              </li>
            ))}
          </ul>
          {nextBatch.group !== status.group && (
            <span className="small muted">opens group {nextBatch.group}</span>
          )}
        </div>
      </div>

      <div
        className="home-meter"
        role="meter"
        aria-label={`Group ${status.group} recent accuracy`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        aria-valuetext={acc === null ? 'No answers yet' : `${pct}%, target ${target}%`}
      >
        <div className="progress">
          <span className={passing ? 'is-good' : undefined} style={{ width: `${pct}%` }} />
        </div>
        <span className="home-meter-target" style={{ left: `${target}%` }} aria-hidden="true" />
      </div>
      <div className="spread small home-meter-legend">
        <span>
          {acc === null ? (
            'No answers yet'
          ) : (
            <>
              <strong>{pct}%</strong> recent accuracy
            </>
          )}
        </span>
        <span className="muted">Target {target}%</span>
      </div>

      {status.ready ? (
        <p className="home-unlock-note">
          Target reached — <InlineLetters ids={nextBatch.ids} /> open with your next answer.
        </p>
      ) : (
        (notMet.length > 0 || fewAnswers.length > 0 || (acc !== null && !passing)) && (
          <ul className="home-todo small">
            {notMet.length > 0 && (
              <li>
                Meet <InlineLetters ids={notMet} /> first — Start session introduces {notMet.length === 1 ? 'it' : 'them'}.
              </li>
            )}
            {fewAnswers.length > 0 && (
              <li>
                Answer <InlineLetters ids={fewAnswers} /> a few more times — each letter needs {MIN_ANSWERS_FOR_UNLOCK} answers to
                count.
              </li>
            )}
            {acc !== null && !passing && (
              <li>
                Keep practising to lift the group average from {pct}% to {target}%.
              </li>
            )}
          </ul>
        )
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------
// Progress map
// ---------------------------------------------------------------------------

type MapOrder = 'alphabet' | 'groups'

function LockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <rect x="3" y="7" width="10" height="7.5" rx="1.6" fill="currentColor" />
      <path d="M5.2 7V5.1a2.8 2.8 0 0 1 5.6 0V7" fill="none" stroke="currentColor" strokeWidth="1.7" />
    </svg>
  )
}

function tileLabel(letter: Letter, p: LetterProgress | undefined, isUnlocked: boolean, isDue: boolean): string {
  if (!isUnlocked) return `${letter.upper} — locked, opens with group ${letter.group} (${GROUPS[letter.group].title}); tap for a preview`
  const m = mastery(p)
  const acc = recentAccuracy(p)
  const detail = acc !== null ? `${percent(acc)}% recent accuracy` : m === 'new' ? 'not met yet' : 'no answers yet'
  return `${letter.upper} — ${MASTERY_LABEL[m].toLowerCase()}, ${detail}${isDue ? ', due for review' : ''}`
}

function TileGrid({
  letters,
  save,
  unlocked,
  due,
}: {
  letters: readonly Letter[]
  save: SaveData
  unlocked: ReadonlySet<string>
  due: ReadonlySet<string>
}) {
  return (
    <ul className="home-grid">
      {letters.map((l) => {
        const p = save.letters[l.id]
        const isUnlocked = unlocked.has(l.id)
        const isDue = due.has(l.id)
        const label = tileLabel(l, p, isUnlocked, isDue)
        return (
          <li key={l.id}>
            <a
              className={`home-tile ${isUnlocked ? `m-${mastery(p)}` : 'is-locked'}`}
              href={href(`learn/${l.id}`)}
              aria-label={label}
              title={label}
              data-testid={`map-${l.id}`}
            >
              <span className="home-tile-up glyph-print" lang="ru">
                {l.upper}
              </span>
              <span className="home-tile-lo glyph-print" lang="ru">
                {l.lower}
              </span>
              {!isUnlocked && <LockIcon className="home-tile-lock" />}
              {isDue && <span className="home-tile-due" />}
            </a>
          </li>
        )
      })}
    </ul>
  )
}

function LetterMap({ save, unlocked, due }: { save: SaveData; unlocked: ReadonlySet<string>; due: ReadonlySet<string> }) {
  const [order, setOrder] = useState<MapOrder>('alphabet')

  const counts: Record<Mastery | 'locked', number> = { new: 0, learning: 0, known: 0, mastered: 0, locked: 0 }
  for (const l of LETTERS) counts[unlocked.has(l.id) ? mastery(save.letters[l.id]) : 'locked']++

  const grid = (letters: readonly Letter[]) => <TileGrid letters={letters} save={save} unlocked={unlocked} due={due} />

  return (
    <section className="card home-map" aria-labelledby="home-map-title" data-testid="map">
      <div className="spread home-map-head">
        <div>
          <h2 id="home-map-title">Your alphabet</h2>
          <p className="muted small home-map-hint">Tap a letter to open its Learn card.</p>
        </div>
        <div className="home-seg" role="group" aria-label="Order the letters">
          <button type="button" aria-pressed={order === 'alphabet'} onClick={() => setOrder('alphabet')}>
            <span lang="ru">А–Я</span>
            <span className="sr-only"> alphabetical</span>
          </button>
          <button type="button" aria-pressed={order === 'groups'} onClick={() => setOrder('groups')}>
            By group
          </button>
        </div>
      </div>

      {order === 'alphabet'
        ? grid(LETTERS)
        : GROUP_IDS.map((g) => {
            const letters = GROUP_ORDER[g].map((u) => LETTER_BY_UPPER.get(u)!)
            const met = letters.filter((l) => save.letters[l.id]?.introducedAt != null).length
            const anyOpen = letters.some((l) => unlocked.has(l.id))
            return (
              <div key={g} className="home-map-group">
                <h3>
                  <span className="home-map-group-num">{g}</span>
                  {GROUPS[g].title}
                  <span className="muted small home-map-group-count">
                    {anyOpen ? `${met}/${letters.length} met` : 'locked'}
                  </span>
                </h3>
                {grid(letters)}
              </div>
            )
          })}

      <ul className="home-legend" aria-label="Legend">
        {MASTERY_ORDER.map((m) => (
          <li key={m}>
            <span className={`home-swatch m-${m}`} aria-hidden="true" />
            {MASTERY_LABEL[m]}
            <span className="home-legend-count">{counts[m]}</span>
          </li>
        ))}
        <li>
          <span className="home-swatch is-locked" aria-hidden="true">
            <LockIcon />
          </span>
          Locked
          <span className="home-legend-count">{counts.locked}</span>
        </li>
        <li>
          <span className="home-swatch-dot" aria-hidden="true" />
          Due now
          <span className="home-legend-count">{due.size}</span>
        </li>
      </ul>
    </section>
  )
}
