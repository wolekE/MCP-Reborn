import { describe, expect, it } from 'vitest'
import { LETTERS } from '../data/letters'
import { newLetterProgress, type LetterProgress, type SrsState } from '../state/schema'
import {
  BATCHES,
  DAY_MIN,
  FAST_BONUS,
  LADDER_MIN,
  MAX_EASE,
  MINUTE_MS,
  MIN_EASE,
  batchSizes,
  dueLetterIds,
  ladderNext,
  mastery,
  nextDueAt,
  nextEase,
  pushRecent,
  quality,
  review,
  unlockStatus,
  unlockedIds,
} from './scheduler'

const T0 = Date.UTC(2026, 0, 1, 9, 0, 0)
const fresh = (): SrsState => ({ ease: 2.5, intervalMin: 0, reps: 0, lapses: 0, due: T0 })
/** A normal-speed correct answer (quality 4: ease unchanged). */
const ok = { correct: true, responseMs: 4000, fastMs: 2500 }
const fast = { correct: true, responseMs: 900, fastMs: 2500 }
const slow = { correct: true, responseMs: 20_000, fastMs: 2500 }
const miss = { correct: false, responseMs: 1500, fastMs: 2500 }

/** Answer each time the letter falls due, returning the interval after each review. */
function ladder(answers: { correct: boolean; responseMs: number; fastMs: number }[]): number[] {
  let s = fresh()
  const out: number[] = []
  for (const a of answers) {
    s = review(s, a, s.due)
    out.push(s.intervalMin)
  }
  return out
}

describe('quality', () => {
  it('grades fast, normal, slow and wrong answers', () => {
    expect(quality(fast)).toBe(5)
    expect(quality(ok)).toBe(4)
    expect(quality(slow)).toBe(3)
    expect(quality(miss)).toBe(1)
  })
})

describe('nextEase', () => {
  it('follows SM-2: +0.1 for q5, 0 for q4, -0.14 for q3, -0.2 for a miss', () => {
    expect(nextEase(2.5, 5)).toBe(2.6)
    expect(nextEase(2.5, 4)).toBe(2.5)
    expect(nextEase(2.5, 3)).toBe(2.36)
    expect(nextEase(2.5, 1)).toBe(2.3)
  })
  it('clamps to the allowed range', () => {
    expect(nextEase(MIN_EASE, 1)).toBe(MIN_EASE)
    expect(nextEase(MAX_EASE, 5)).toBe(MAX_EASE)
  })
})

describe('review: interval growth', () => {
  it('climbs 10 min → 1 day → 3 days, then multiplies by the ease factor', () => {
    expect(ladder([ok, ok, ok, ok, ok])).toEqual([10, DAY_MIN, 3 * DAY_MIN, 3 * DAY_MIN * 2.5, 3 * DAY_MIN * 2.5 * 2.5])
  })

  it('sets the due time interval minutes after the review', () => {
    const s = review(fresh(), ok, T0)
    expect(s.due).toBe(T0 + 10 * MINUTE_MS)
    expect(s.reps).toBe(1)
  })

  it('makes fast correct answers count more than normal ones', () => {
    const f = ladder([fast, fast, fast, fast])
    const n = ladder([ok, ok, ok, ok])
    for (let i = 0; i < f.length; i++) expect(f[i]).toBeGreaterThan(n[i])
    expect(f[0]).toBe(Math.round(10 * FAST_BONUS))
  })

  it('makes slow correct answers grow more slowly over time (lower ease)', () => {
    const s = ladder([slow, slow, slow, slow])
    const n = ladder([ok, ok, ok, ok])
    expect(s[3]).toBeLessThan(n[3])
  })

  it('does not advance letters that are not due yet', () => {
    const s1 = review(fresh(), ok, T0)
    const s2 = review(s1, fast, T0 + 2 * MINUTE_MS)
    expect(s2).toBe(s1)
  })
})

describe('review: misses', () => {
  it('resets the interval to 10 minutes and lowers the ease', () => {
    let s = fresh()
    for (const a of [ok, ok, ok, ok]) s = review(s, a, s.due)
    expect(s.intervalMin).toBeGreaterThan(3 * DAY_MIN)
    const missed = review(s, miss, s.due)
    expect(missed.intervalMin).toBe(LADDER_MIN[0])
    expect(missed.due).toBe(s.due + 10 * MINUTE_MS)
    expect(missed.ease).toBe(2.3)
    expect(missed.reps).toBe(0)
    expect(missed.lapses).toBe(1)
  })

  it('resets even when the letter was not due', () => {
    const s = review(review(fresh(), ok, T0), miss, T0 + MINUTE_MS)
    expect(s.intervalMin).toBe(10)
    expect(s.due).toBe(T0 + 11 * MINUTE_MS)
  })

  it('climbs back from 10 minutes to 1 day on the next due success', () => {
    let s = fresh()
    for (const a of [ok, ok, ok]) s = review(s, a, s.due)
    s = review(s, miss, s.due)
    s = review(s, ok, s.due)
    expect(s.intervalMin).toBe(DAY_MIN)
  })

  it('only counts a lapse when the letter had reached a day or more', () => {
    const s = review(review(fresh(), ok, T0), miss, T0 + 10 * MINUTE_MS)
    expect(s.lapses).toBe(0)
  })
})

describe('ladderNext', () => {
  it('promotes to the next ladder rung, then multiplies', () => {
    expect(ladderNext(0, 2.5)).toBe(10)
    expect(ladderNext(10, 2.5)).toBe(DAY_MIN)
    expect(ladderNext(13, 2.5)).toBe(DAY_MIN)
    expect(ladderNext(DAY_MIN, 2.5)).toBe(3 * DAY_MIN)
    expect(ladderNext(3 * DAY_MIN, 2)).toBe(6 * DAY_MIN)
  })
})

describe('mastery', () => {
  const p = (over: Partial<LetterProgress>): LetterProgress => ({ ...newLetterProgress(T0), introducedAt: T0, ...over })
  it('maps progress to new / learning / known / mastered', () => {
    expect(mastery(undefined)).toBe('new')
    expect(mastery(newLetterProgress(T0))).toBe('new')
    expect(mastery(p({ intervalMin: 10 }))).toBe('learning')
    expect(mastery(p({ intervalMin: DAY_MIN }))).toBe('known')
    expect(mastery(p({ intervalMin: 7 * DAY_MIN }))).toBe('mastered')
  })
})

describe('due letters', () => {
  it('lists introduced, due letters most overdue first', () => {
    const letters: Record<string, LetterProgress> = {
      a: { ...newLetterProgress(T0), introducedAt: T0, due: T0 - 5000 },
      k: { ...newLetterProgress(T0), introducedAt: T0, due: T0 - 9000 },
      m: { ...newLetterProgress(T0), introducedAt: T0, due: T0 + 60_000 },
      o: { ...newLetterProgress(T0), introducedAt: null, due: T0 - 99_999 },
    }
    expect(dueLetterIds(letters, T0)).toEqual(['k', 'a'])
    expect(nextDueAt(letters, T0)).toBe(T0 + 60_000)
  })
})

describe('batches', () => {
  it('splits groups into batches of 3–5', () => {
    expect(batchSizes(5)).toEqual([5])
    expect(batchSizes(7)).toEqual([4, 3])
    expect(batchSizes(10)).toEqual([5, 5])
    expect(batchSizes(6)).toEqual([3, 3])
    for (const b of BATCHES) {
      expect(b.ids.length).toBeGreaterThanOrEqual(3)
      expect(b.ids.length).toBeLessThanOrEqual(5)
    }
  })

  it('covers all 33 letters exactly once, in group order', () => {
    const all = BATCHES.flatMap((b) => b.ids)
    expect(all).toHaveLength(33)
    expect(new Set(all).size).toBe(33)
    expect(new Set(all)).toEqual(new Set(LETTERS.map((l) => l.id)))
    expect(BATCHES.map((b) => b.group)).toEqual([...BATCHES.map((b) => b.group)].sort())
    expect(unlockedIds(1)).toEqual(['a', 'k', 'm', 'o', 't'])
  })
})

describe('unlockStatus', () => {
  const trained = (results: boolean[]): LetterProgress => ({
    ...newLetterProgress(T0),
    introducedAt: T0,
    recent: results.reduce<boolean[]>((r, x) => pushRecent(r, x), []),
  })
  const group1 = (results: boolean[]) => Object.fromEntries(unlockedIds(1).map((id) => [id, trained(results)]))

  it('opens the next batch when the current group averages 80%+', () => {
    expect(unlockStatus(group1([true, true, true, true, false]), 1).ready).toBe(true)
  })

  it('stays closed below 80%', () => {
    const s = unlockStatus(group1([true, true, false, true, false]), 1)
    expect(s.ready).toBe(false)
    expect(s.groupAccuracy).toBeCloseTo(0.6)
  })

  it('requires every letter to be introduced and answered at least 3 times', () => {
    const letters = group1([true, true, true])
    letters.t = trained([true, true])
    expect(unlockStatus(letters, 1)).toMatchObject({ ready: false, pending: ['t'] })
    delete letters.t
    expect(unlockStatus(letters, 1)).toMatchObject({ ready: false, pending: ['t'] })
  })

  it('judges only the current group, across all of its open batches', () => {
    const letters = { ...group1([false, false, false]) }
    for (const id of unlockedIds(2).slice(5)) letters[id] = trained([true, true, true])
    // Group 1 is weak, but batch 2 belongs to group 2, which is what counts now.
    expect(unlockStatus(letters, 2)).toMatchObject({ ready: true, group: 2 })
  })

  it('reports completion once every batch is open', () => {
    expect(unlockStatus({}, BATCHES.length)).toMatchObject({ ready: false, complete: true })
  })
})
