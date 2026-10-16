/**
 * Spaced repetition and unlocking — pure functions only (no clocks, no storage).
 *
 * Light SM-2:
 * - Each letter has an ease factor (starts 2.5, floor 1.3) and an interval.
 * - A correct answer on a due letter grows the interval along a fixed ladder,
 *   10 min → 1 day → 3 days, then multiplies by the ease factor.
 * - A miss resets the interval to 10 minutes (and lowers the ease).
 * - Fast correct answers count more: they raise the ease and stretch the
 *   interval by FAST_BONUS; slow ones lower the ease.
 * - Correct answers on letters that are not due yet don't move the schedule,
 *   so drilling one letter five times in a session can't fake long-term memory.
 */
import { GROUP_ORDER, LETTER_BY_UPPER, type GroupId } from '../data/letters'
import { RECENT_WINDOW, type LetterProgress, type SrsState } from '../state/schema'

export const MINUTE_MS = 60_000
export const DAY_MIN = 24 * 60
/** Interval ladder (minutes) before ease-based growth takes over. */
export const LADDER_MIN = [10, DAY_MIN, 3 * DAY_MIN] as const
export const MIN_EASE = 1.3
export const MAX_EASE = 3.0
/** Interval multiplier for a fast correct answer. */
export const FAST_BONUS = 1.3
/** Default "fast" threshold for a response. Modes pass their own. */
export const DEFAULT_FAST_MS = 2500

export type Quality = 1 | 3 | 4 | 5

export interface Answer {
  correct: boolean
  responseMs: number
  /** At or under this many ms counts as fast. */
  fastMs?: number
}

/** SM-2 style grade: 5 fast, 4 normal, 3 slow but correct, 1 wrong. */
export function quality({ correct, responseMs, fastMs = DEFAULT_FAST_MS }: Answer): Quality {
  if (!correct) return 1
  if (responseMs <= fastMs) return 5
  if (responseMs <= fastMs * 2.5) return 4
  return 3
}

/** SM-2 ease update for a passing grade (q ≥ 3), clamped to [MIN_EASE, MAX_EASE]. */
export function nextEase(ease: number, q: Quality): number {
  const raw = q < 3 ? ease - 0.2 : ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
  return Math.min(MAX_EASE, Math.max(MIN_EASE, round2(raw)))
}

/** The interval (minutes) a successful review promotes `currentMin` to, before bonuses. */
export function ladderNext(currentMin: number, ease: number): number {
  for (const step of LADDER_MIN) if (currentMin < step) return step
  return currentMin * ease
}

export function isDue(s: Pick<SrsState, 'due'>, now: number): boolean {
  return s.due <= now
}

/** Applies one answer to a letter's schedule. */
export function review(s: SrsState, answer: Answer, now: number): SrsState {
  const q = quality(answer)
  if (!answer.correct) {
    return {
      ease: nextEase(s.ease, q),
      intervalMin: LADDER_MIN[0],
      reps: 0,
      lapses: s.intervalMin >= DAY_MIN ? s.lapses + 1 : s.lapses,
      due: now + LADDER_MIN[0] * MINUTE_MS,
    }
  }
  if (!isDue(s, now)) return s
  const ease = nextEase(s.ease, q)
  let interval = ladderNext(s.intervalMin, ease)
  if (q === 5) interval *= FAST_BONUS
  interval = Math.round(interval)
  return { ease, intervalMin: interval, reps: s.reps + 1, lapses: s.lapses, due: now + interval * MINUTE_MS }
}

// ---------------------------------------------------------------------------
// Mastery
// ---------------------------------------------------------------------------

export type Mastery = 'new' | 'learning' | 'known' | 'mastered'
export const MASTERED_MIN = 7 * DAY_MIN

export function mastery(p: LetterProgress | undefined): Mastery {
  if (!p || p.introducedAt === null) return 'new'
  if (p.intervalMin >= MASTERED_MIN) return 'mastered'
  if (p.intervalMin >= DAY_MIN) return 'known'
  return 'learning'
}

/** Share of recent answers that were correct, or null with no answers yet. */
export function recentAccuracy(p: LetterProgress | undefined): number | null {
  if (!p || p.recent.length === 0) return null
  return p.recent.filter(Boolean).length / p.recent.length
}

/** Appends a result to the rolling window. */
export function pushRecent(recent: readonly boolean[], ok: boolean): boolean[] {
  return [...recent, ok].slice(-RECENT_WINDOW)
}

/** Introduced letters due for review, most overdue first. */
export function dueLetterIds(letters: Readonly<Record<string, LetterProgress>>, now: number): string[] {
  return Object.entries(letters)
    .filter(([, p]) => p.introducedAt !== null && isDue(p, now))
    .sort(([, a], [, b]) => a.due - b.due)
    .map(([id]) => id)
}

/** When the next not-yet-due letter becomes due, or null. */
export function nextDueAt(letters: Readonly<Record<string, LetterProgress>>, now: number): number | null {
  let next: number | null = null
  for (const p of Object.values(letters)) {
    if (p.introducedAt !== null && p.due > now && (next === null || p.due < next)) next = p.due
  }
  return next
}

// ---------------------------------------------------------------------------
// Unlocking: letters open in batches of 3–5, group by group
// ---------------------------------------------------------------------------

export const UNLOCK_THRESHOLD = 0.8
/** Each letter needs this many answers before its accuracy counts. */
export const MIN_ANSWERS_FOR_UNLOCK = 3
export const MIN_BATCH = 3
export const MAX_BATCH = 5

/** Splits n into the fewest batches of MIN_BATCH..MAX_BATCH, as even as possible, larger first. */
export function batchSizes(n: number): number[] {
  if (n <= MAX_BATCH) return [n]
  const k = Math.ceil(n / MAX_BATCH)
  const base = Math.floor(n / k)
  const extra = n % k
  return Array.from({ length: k }, (_, i) => base + (i < extra ? 1 : 0))
}

export interface Batch {
  group: GroupId
  /** Letter ids in teaching order. */
  ids: readonly string[]
}

export const BATCHES: readonly Batch[] = ([1, 2, 3, 4, 5] as const).flatMap((group) => {
  const ids = GROUP_ORDER[group].map((u) => LETTER_BY_UPPER.get(u)!.id)
  let at = 0
  return batchSizes(ids.length).map((size) => {
    const batch = { group, ids: ids.slice(at, at + size) }
    at += size
    return batch
  })
})

/** Letter ids open for learning given how many batches are unlocked. */
export function unlockedIds(unlockedBatches: number): string[] {
  return BATCHES.slice(0, unlockedBatches).flatMap((b) => b.ids)
}

export interface UnlockStatus {
  /** True when the next batch should open now. */
  ready: boolean
  /** All batches are already open. */
  complete: boolean
  group: GroupId
  /** Average recent accuracy across the current group's unlocked letters (null if none answered). */
  groupAccuracy: number | null
  /** Unlocked letters of the current group that are not introduced or have too few answers. */
  pending: string[]
}

/**
 * The next batch opens once every unlocked letter of the current group has
 * been introduced and answered MIN_ANSWERS_FOR_UNLOCK times, and their recent
 * accuracy averages at least UNLOCK_THRESHOLD.
 */
export function unlockStatus(letters: Readonly<Record<string, LetterProgress>>, unlockedBatches: number): UnlockStatus {
  const open = Math.min(Math.max(1, unlockedBatches), BATCHES.length)
  const group = BATCHES[open - 1].group
  const ids = BATCHES.slice(0, open).filter((b) => b.group === group).flatMap((b) => b.ids)
  const pending = ids.filter((id) => {
    const p = letters[id]
    return !p || p.introducedAt === null || p.recent.length < MIN_ANSWERS_FOR_UNLOCK
  })
  const accs = ids.map((id) => recentAccuracy(letters[id])).filter((a): a is number => a !== null)
  const groupAccuracy = accs.length ? accs.reduce((a, b) => a + b, 0) / accs.length : null
  const complete = open >= BATCHES.length
  const ready = !complete && pending.length === 0 && groupAccuracy !== null && groupAccuracy >= UNLOCK_THRESHOLD
  return { ready, complete, group, groupAccuracy, pending }
}

function round2(n: number): number {
  return Math.round(n * 100) / 100
}
