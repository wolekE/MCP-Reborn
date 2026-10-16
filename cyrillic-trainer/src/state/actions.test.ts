import { describe, expect, it } from 'vitest'
import { DAY_MIN, MINUTE_MS, unlockedIds } from '../srs/scheduler'
import { completeSession, currentStreak, introduce, localDay, maybeUnlock, recordAnswer } from './actions'
import { defaultSave } from './schema'

const T0 = new Date(2026, 4, 10, 9, 0).getTime()
const DAY_MS = 24 * 60 * MINUTE_MS
const answer = (letterId: string, correct: boolean, chosenId?: string) => ({ letterId, correct, responseMs: 4000, fastMs: 2500, chosenId })

describe('introduce', () => {
  it('marks letters as introduced and due right away', () => {
    const s = introduce(defaultSave(T0), ['a', 'k'], T0)
    expect(s.letters.a.introducedAt).toBe(T0)
    expect(s.letters.a.due).toBe(T0)
    expect(s.letters.k.introducedAt).toBe(T0)
  })

  it('does not reset a letter that was already introduced', () => {
    let s = introduce(defaultSave(T0), ['a'], T0)
    s = recordAnswer(s, answer('a', true), T0)
    const again = introduce(s, ['a'], T0 + 5000)
    expect(again.letters.a).toEqual(s.letters.a)
  })
})

describe('recordAnswer', () => {
  it('updates stats and the schedule of introduced letters', () => {
    let s = introduce(defaultSave(T0), ['a'], T0)
    s = recordAnswer(s, answer('a', true), T0)
    expect(s.letters.a).toMatchObject({ attempts: 1, correct: 1, recent: [true], intervalMin: 10, lastSeen: T0 })
  })

  it('records stats but no schedule for letters not introduced yet', () => {
    const s = recordAnswer(defaultSave(T0), answer('v', true), T0)
    expect(s.letters.v).toMatchObject({ attempts: 1, correct: 1, introducedAt: null, intervalMin: 0 })
  })

  it('counts confusions by target and chosen letter', () => {
    let s = introduce(defaultSave(T0), ['sh'], T0)
    s = recordAnswer(s, answer('sh', false, 'shch'), T0)
    s = recordAnswer(s, answer('sh', false, 'shch'), T0)
    s = recordAnswer(s, answer('sh', false), T0)
    expect(s.confusions).toEqual({ 'sh>shch': 2 })
  })

  it('keeps only the last 10 results', () => {
    let s = introduce(defaultSave(T0), ['a'], T0)
    for (let i = 0; i < 12; i++) s = recordAnswer(s, answer('a', i >= 2), T0)
    expect(s.letters.a.recent).toHaveLength(10)
    expect(s.letters.a.recent.every(Boolean)).toBe(true)
    expect(s.letters.a.attempts).toBe(12)
  })
})

describe('maybeUnlock', () => {
  it('opens the next batch once the current group averages 80%+', () => {
    let s = introduce(defaultSave(T0), unlockedIds(1), T0)
    for (const id of unlockedIds(1)) for (let i = 0; i < 3; i++) s = recordAnswer(s, answer(id, true), T0)
    const r = maybeUnlock(s)
    expect(r.unlocked).toEqual(['v', 'ye', 'n', 'r'])
    expect(r.save.unlockedBatches).toBe(2)
    // Nothing more until the new letters are learned and practised.
    expect(maybeUnlock(r.save).unlocked).toEqual([])
  })

  it('stays closed while the group is below 80%', () => {
    let s = introduce(defaultSave(T0), unlockedIds(1), T0)
    for (const id of unlockedIds(1)) for (let i = 0; i < 3; i++) s = recordAnswer(s, answer(id, i !== 0), T0)
    expect(maybeUnlock(s).unlocked).toEqual([])
  })
})

describe('daily streak', () => {
  it('starts at 1, grows on consecutive days and ignores repeat sessions on one day', () => {
    let s = completeSession(defaultSave(T0), T0)
    expect(s.streak).toEqual({ current: 1, best: 1, lastDay: localDay(T0) })
    s = completeSession(s, T0 + 3 * 60 * MINUTE_MS)
    expect(s.streak.current).toBe(1)
    s = completeSession(s, T0 + DAY_MS)
    s = completeSession(s, T0 + 2 * DAY_MS)
    expect(s.streak).toMatchObject({ current: 3, best: 3 })
    expect(s.sessionsCompleted).toBe(4)
  })

  it('resets after a missed day but keeps the best', () => {
    let s = defaultSave(T0)
    for (let d = 0; d < 3; d++) s = completeSession(s, T0 + d * DAY_MS)
    s = completeSession(s, T0 + 5 * DAY_MS)
    expect(s.streak).toMatchObject({ current: 1, best: 3 })
  })

  it('shows a broken streak as 0 until the next session', () => {
    let s = completeSession(defaultSave(T0), T0)
    expect(currentStreak(s, T0 + DAY_MS)).toBe(1)
    expect(currentStreak(s, T0 + 2 * DAY_MS)).toBe(0)
    s = completeSession(s, T0 + DAY_MIN * MINUTE_MS)
    expect(currentStreak(s, T0 + DAY_MS)).toBe(2)
  })
})
