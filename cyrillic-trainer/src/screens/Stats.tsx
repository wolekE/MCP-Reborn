import './stats.css'
import { useMemo, useState } from 'react'
import { LETTERS, LETTER_BY_ID, type Letter } from '../data/letters'
import { href } from '../router'
import { mastery, recentAccuracy, type Mastery } from '../srs/scheduler'
import { currentStreak } from '../state/actions'
import type { LetterProgress, SaveData } from '../state/schema'
import { useStore } from '../state/store'

type SortKey = 'alpha' | 'weakest' | 'practised'
type Band = 'good' | 'warn' | 'bad'

const MASTERY_LABEL: Record<Mastery, string> = { new: 'New', learning: 'Learning', known: 'Known', mastered: 'Mastered' }
const SORTS: { key: SortKey; label: string; short: string; shortLang?: 'ru' }[] = [
  { key: 'alpha', label: 'Alphabet', short: 'А–Я', shortLang: 'ru' },
  { key: 'weakest', label: 'Weakest first', short: 'Weakest' },
  { key: 'practised', label: 'Most practised', short: 'Most practised' },
]
const SORT_PHRASE: Record<SortKey, string> = {
  alpha: 'alphabetically',
  weakest: 'weakest first',
  practised: 'most practised first',
}
/** How many confused pairs to list. */
const TOP_PAIRS = 8

const ALPHA_INDEX: ReadonlyMap<string, number> = new Map(LETTERS.map((l, i) => [l.id, i]))
const alpha = (l: Letter) => ALPHA_INDEX.get(l.id) ?? 0
/**
 * Whole-number percentage that never overstates or understates: 250/251 shows
 * 99%, not 100%, and 1/300 shows 1%, not 0%.
 */
function percent(x: number): number {
  const p = Math.round(x * 100)
  if (p >= 100 && x < 1) return 99
  if (p <= 0 && x > 0) return 1
  return p
}
const plural = (n: number, one: string, many = `${one}s`) => `${n.toLocaleString()} ${n === 1 ? one : many}`

/** Bar colour band; always paired with the printed number. */
function band(pct: number): Band {
  if (pct >= 80) return 'good'
  if (pct >= 50) return 'warn'
  return 'bad'
}

// ---------------------------------------------------------------------------
// Derived data
// ---------------------------------------------------------------------------

interface LetterRow {
  letter: Letter
  attempts: number
  correct: number
  /** Exact all-time accuracy (0..1), null with no answers. */
  ratio: number | null
  /** Rounded all-time accuracy in %, null with no answers. */
  pct: number | null
  /** Rounded recent accuracy in %, null with no answers. */
  recentPct: number | null
  recentN: number
  mastery: Mastery
}

function letterRow(letter: Letter, p: LetterProgress | undefined): LetterRow {
  const attempts = p?.attempts ?? 0
  const correct = p?.correct ?? 0
  const ratio = attempts > 0 ? correct / attempts : null
  const recent = recentAccuracy(p)
  return {
    letter,
    attempts,
    correct,
    ratio,
    pct: ratio === null ? null : percent(ratio),
    recentPct: recent === null ? null : percent(recent),
    recentN: p?.recent.length ?? 0,
    mastery: mastery(p),
  }
}

function sortRows(rows: readonly LetterRow[], key: SortKey): LetterRow[] {
  const out = [...rows]
  if (key === 'alpha') return out.sort((a, b) => alpha(a.letter) - alpha(b.letter))
  if (key === 'practised') {
    return out.sort((a, b) => b.attempts - a.attempts || alpha(a.letter) - alpha(b.letter))
  }
  // Weakest first: answered letters by accuracy (then more answers first); unanswered last.
  return out.sort((a, b) => {
    if (a.ratio === null || b.ratio === null) {
      if (a.ratio !== b.ratio) return a.ratio === null ? 1 : -1
      return alpha(a.letter) - alpha(b.letter)
    }
    return a.ratio - b.ratio || b.attempts - a.attempts || alpha(a.letter) - alpha(b.letter)
  })
}

interface ConfusedPair {
  /** Stable id: the two letter ids in alphabetical order. */
  key: string
  /** Shown first: the letter that was mistaken more often. */
  first: Letter
  second: Letter
  /** Times `first` was mistaken for `second`. */
  firstAsSecond: number
  secondAsFirst: number
  total: number
}

/** Folds "target>chosen" counts into unordered pairs, most confused first. */
function confusedPairs(confusions: Readonly<Record<string, number>>): ConfusedPair[] {
  const pairs = new Map<string, ConfusedPair>()
  for (const [k, count] of Object.entries(confusions)) {
    const [targetId, chosenId] = k.split('>')
    const target = LETTER_BY_ID.get(targetId)
    const chosen = LETTER_BY_ID.get(chosenId)
    if (!target || !chosen || target === chosen || !(count > 0)) continue
    const [a, b] = alpha(target) <= alpha(chosen) ? [target, chosen] : [chosen, target]
    const key = `${a.id}-${b.id}`
    const pair = pairs.get(key) ?? { key, first: a, second: b, firstAsSecond: 0, secondAsFirst: 0, total: 0 }
    if (target === a) pair.firstAsSecond += count
    else pair.secondAsFirst += count
    pair.total += count
    pairs.set(key, pair)
  }
  return [...pairs.values()]
    .map((p) =>
      p.secondAsFirst > p.firstAsSecond
        ? { ...p, first: p.second, second: p.first, firstAsSecond: p.secondAsFirst, secondAsFirst: p.firstAsSecond }
        : p,
    )
    .sort((x, y) => y.total - x.total || alpha(x.first) - alpha(y.first) || alpha(x.second) - alpha(y.second))
}

interface Summary {
  attempts: number
  correct: number
  recentN: number
  recentCorrect: number
  learned: number
  counts: Record<Mastery, number>
}

function summarize(save: SaveData): Summary {
  const s: Summary = {
    attempts: 0,
    correct: 0,
    recentN: 0,
    recentCorrect: 0,
    learned: 0,
    counts: { new: 0, learning: 0, known: 0, mastered: 0 },
  }
  for (const l of LETTERS) {
    const p = save.letters[l.id]
    s.counts[mastery(p)]++
    if (!p) continue
    s.attempts += p.attempts
    s.correct += p.correct
    s.recentN += p.recent.length
    s.recentCorrect += p.recent.filter(Boolean).length
    if (p.introducedAt !== null) s.learned++
  }
  return s
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

export function Stats() {
  const { save } = useStore()
  const [now] = useState(() => Date.now())
  const summary = useMemo(() => summarize(save), [save])

  if (summary.attempts === 0) {
    return (
      <div className="stack stats">
        <header className="stats-head">
          <h1>Stats</h1>
        </header>
        <section className="card stats-empty" aria-labelledby="stats-empty-title" data-testid="stats-empty">
          <div className="stats-empty-art" aria-hidden="true">
            {[72, 45, 88].map((w, i) => (
              <span key={i} className="stats-track">
                <span className="stats-fill stats-fill-ghost" style={{ width: `${w}%` }} />
              </span>
            ))}
          </div>
          <h2 id="stats-empty-title">Your stats appear after your first practice round</h2>
          <p className="muted">
            Answer a few letters and this page fills in: how accurate you are on each of the 33 letters, and which pairs you
            mix up most.
          </p>
          <div className="row">
            <a className="btn btn-primary btn-big" href={href('session')}>
              Start a session
            </a>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className="stack stats">
      <header className="stats-head">
        <h1>Stats</h1>
        <p className="muted">How you’re doing on every letter, and where the mix-ups are.</p>
      </header>
      <SummaryTiles save={save} summary={summary} now={now} />
      <LetterAccuracy save={save} />
      <Confusions save={save} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Summary tiles
// ---------------------------------------------------------------------------

function SummaryTiles({ save, summary, now }: { save: SaveData; summary: Summary; now: number }) {
  const total = LETTERS.length
  const accPct = percent(summary.correct / summary.attempts)
  const recentPct = summary.recentN > 0 ? percent(summary.recentCorrect / summary.recentN) : null
  const streakNow = currentStreak(save, now)
  const best = Math.max(save.streak.best, streakNow)
  const { known, learning, mastered } = summary.counts

  return (
    <section aria-labelledby="stats-summary-title">
      <h2 id="stats-summary-title" className="sr-only">
        Summary
      </h2>
      <dl className="stats-tiles" data-testid="stats-summary">
        <div className="card stats-tile" data-testid="summary-answers">
          <dt>Total answers</dt>
          <dd className="stats-tile-value">{summary.attempts.toLocaleString()}</dd>
          <dd className="stats-tile-sub">{summary.correct.toLocaleString()} correct</dd>
        </div>
        <div className="card stats-tile" data-testid="summary-accuracy">
          <dt>Overall accuracy</dt>
          <dd className="stats-tile-value">
            {accPct}
            <small>%</small>
          </dd>
          <dd className="stats-tile-bar-wrap" aria-hidden="true">
            <span className="stats-track stats-tile-bar">
              <span className={`stats-fill is-${band(accPct)}`} style={{ width: `${accPct}%` }} />
            </span>
          </dd>
          {recentPct !== null && <dd className="stats-tile-sub">Recent answers: {recentPct}%</dd>}
        </div>
        <div className="card stats-tile" data-testid="summary-learned">
          <dt>Letters learned</dt>
          <dd className="stats-tile-value">
            {summary.learned}
            <small>/{total}</small>
          </dd>
          <dd className="stats-tile-bar-wrap">
            <span
              className="progress stats-tile-bar"
              role="progressbar"
              aria-label="Letters learned"
              aria-valuemin={0}
              aria-valuemax={total}
              aria-valuenow={summary.learned}
            >
              <span style={{ width: `${(summary.learned / total) * 100}%` }} />
            </span>
          </dd>
          <dd className="stats-tile-sub">{total - summary.learned} still to meet</dd>
        </div>
        <div className="card stats-tile" data-testid="summary-mastered">
          <dt>Mastered</dt>
          <dd className="stats-tile-value">
            {mastered}
            <small>/{total}</small>
          </dd>
          <dd className="stats-tile-sub">
            {known} known · {learning} learning
          </dd>
        </div>
        <div className="card stats-tile" data-testid="summary-sessions">
          <dt>Sessions completed</dt>
          <dd className="stats-tile-value">{save.sessionsCompleted.toLocaleString()}</dd>
          <dd className="stats-tile-sub">
            {save.sessionsCompleted > 0
              ? `About ${plural(Math.round(summary.attempts / save.sessionsCompleted), 'answer')} each`
              : 'Finish a round to count it'}
          </dd>
        </div>
        <div className="card stats-tile" data-testid="summary-streak">
          <dt>Best day streak</dt>
          <dd className="stats-tile-value">
            {best}
            <small> {best === 1 ? 'day' : 'days'}</small>
          </dd>
          <dd className="stats-tile-sub">{streakNow > 0 ? `Current: ${plural(streakNow, 'day')}` : 'No streak running'}</dd>
        </div>
      </dl>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Accuracy per letter
// ---------------------------------------------------------------------------

function rowLabel(r: LetterRow): string {
  const m = MASTERY_LABEL[r.mastery].toLowerCase()
  // The sound label gives screen readers something pronounceable next to the bare Cyrillic glyph.
  const who = `${r.letter.upper} (${r.letter.sound})`
  if (r.pct === null) return `${who}: no answers yet, ${m}. Open Learn card.`
  const recent = r.recentPct !== null && r.recentPct !== r.pct ? `, last ${r.recentN}: ${r.recentPct}%` : ''
  return `${who}: ${r.pct}% correct over ${plural(r.attempts, 'answer')}${recent}, ${m}. Open Learn card.`
}

function LetterAccuracy({ save }: { save: SaveData }) {
  const [sort, setSort] = useState<SortKey>('alpha')
  const rows = useMemo(() => LETTERS.map((l) => letterRow(l, save.letters[l.id])), [save])
  const sorted = useMemo(() => sortRows(rows, sort), [rows, sort])

  return (
    <section className="card stats-letters" aria-labelledby="stats-letters-title" data-testid="stats-letters">
      <div className="spread stats-section-head">
        <div>
          <h2 id="stats-letters-title">Accuracy per letter</h2>
          <p className="muted small stats-hint">All-time share of correct answers. Tap a letter to open its Learn card.</p>
        </div>
        <fieldset className="stats-seg">
          <legend className="sr-only">Sort letters</legend>
          {SORTS.map((s) => (
            <label key={s.key} className="stats-seg-option">
              <input
                type="radio"
                name="stats-sort"
                value={s.key}
                checked={sort === s.key}
                onChange={() => setSort(s.key)}
                aria-label={s.label}
                data-testid={`sort-${s.key}`}
              />
              <span className="stats-seg-long" aria-hidden="true">
                {s.label}
              </span>
              <span className="stats-seg-short" lang={s.shortLang} aria-hidden="true">
                {s.short}
              </span>
            </label>
          ))}
        </fieldset>
      </div>

      <ul className="stats-key small" aria-label="Bar colours">
        <li>
          <span className="stats-swatch is-good" aria-hidden="true" />
          80% and up
        </li>
        <li>
          <span className="stats-swatch is-warn" aria-hidden="true" />
          50–79%
        </li>
        <li>
          <span className="stats-swatch is-bad" aria-hidden="true" />
          under 50%
        </li>
        <li className="stats-key-note">“last N” = that letter’s N most recent answers</li>
      </ul>

      <ol className="stats-list" aria-label={`Letters, ${SORT_PHRASE[sort]}`}>
        {sorted.map((r) => (
          <li key={r.letter.id}>
            <LetterStatRow row={r} />
          </li>
        ))}
      </ol>
    </section>
  )
}

function LetterStatRow({ row: r }: { row: LetterRow }) {
  const quiet = r.pct === null
  const showRecent = r.recentPct !== null && r.pct !== null && r.recentPct !== r.pct
  const up = showRecent && r.recentPct! > r.pct!
  return (
    <a
      className={`stats-row${quiet ? ' is-quiet' : ''}`}
      href={href(`learn/${r.letter.id}`)}
      aria-label={rowLabel(r)}
      data-testid={`stat-${r.letter.id}`}
    >
      <span className="stats-row-glyph" lang="ru">
        <span className="glyph-print stats-row-upper">{r.letter.upper}</span>
        <span className="glyph-print stats-row-lower">{r.letter.lower}</span>
      </span>
      <span className="stats-track stats-row-bar">
        {r.pct !== null && <span className={`stats-fill is-${band(r.pct)}`} style={{ width: `${r.pct}%` }} />}
      </span>
      <span className="stats-row-pct">{r.pct === null ? '—' : `${r.pct}%`}</span>
      <span className="stats-row-meta">
        <span>{r.attempts > 0 ? plural(r.attempts, 'answer') : 'No answers yet'}</span>
        {showRecent && (
          <span className="stats-recent">
            last {r.recentN}: {r.recentPct}%
            <span className={`stats-trend ${up ? 'is-up' : 'is-down'}`}>{up ? '▲' : '▼'}</span>
          </span>
        )}
      </span>
      <span className={`stats-chip m-${r.mastery}`}>{MASTERY_LABEL[r.mastery]}</span>
    </a>
  )
}

// ---------------------------------------------------------------------------
// Most-confused pairs
// ---------------------------------------------------------------------------

function Confusions({ save }: { save: SaveData }) {
  const pairs = useMemo(() => confusedPairs(save.confusions), [save.confusions])
  const top = pairs.slice(0, TOP_PAIRS)
  const max = top[0]?.total ?? 1

  return (
    <section className="card stats-confusions" aria-labelledby="stats-confusions-title" data-testid="stats-confusions">
      <div className="stats-section-head">
        <h2 id="stats-confusions-title">Most-confused pairs</h2>
        {pairs.length > 0 && (
          <p className="muted small stats-hint">
            {pairs.length > TOP_PAIRS
              ? `Your top ${TOP_PAIRS} of ${pairs.length} mixed-up pairs, both directions combined.`
              : 'Letters you picked in place of each other, both directions combined.'}
          </p>
        )}
      </div>

      {top.length === 0 ? (
        <p className="stats-none" data-testid="confusions-empty">
          No mix-ups yet — they’ll show up here as you practise.
        </p>
      ) : (
        <ol className="stats-pairs">
          {top.map((p) => (
            <li key={p.key} className="stats-pair" data-testid={`pair-${p.key}`}>
              <div className="stats-pair-glyphs">
                <PairLetter letter={p.first} />
                <span className="stats-pair-arrow" aria-hidden="true">
                  ⇄
                </span>
                <PairLetter letter={p.second} />
              </div>
              <p className="stats-pair-total">
                <strong>{p.total}</strong> {p.total === 1 ? 'mix-up' : 'mix-ups'}
              </p>
              <span className="stats-track stats-pair-bar" aria-hidden="true">
                <span className="stats-fill is-accent" style={{ width: `${(p.total / max) * 100}%` }} />
              </span>
              <ul className="stats-pair-detail small">
                {p.firstAsSecond > 0 && <Direction from={p.first} to={p.second} count={p.firstAsSecond} />}
                {p.secondAsFirst > 0 && <Direction from={p.second} to={p.first} count={p.secondAsFirst} />}
              </ul>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

function PairLetter({ letter }: { letter: Letter }) {
  return (
    <a className="stats-pair-letter" href={href(`learn/${letter.id}`)} aria-label={`${letter.upper} (${letter.sound}): open Learn card`}>
      <span className="glyph-print" lang="ru">
        {letter.upper}
      </span>
      <span className="stats-pair-sound">{letter.sound}</span>
    </a>
  )
}

function Direction({ from, to, count }: { from: Letter; to: Letter; count: number }) {
  return (
    <li>
      <b lang="ru">{from.upper}</b> mistaken for <b lang="ru">{to.upper}</b> <span className="stats-times">×{count}</span>
    </li>
  )
}
