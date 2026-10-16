/**
 * Pure state transitions on SaveData. The React store (store.tsx) is a thin
 * wrapper that calls these with the current time and persists the result.
 */
import { BATCHES, pushRecent, review, unlockStatus, type Answer } from '../srs/scheduler'
import { newLetterProgress, type LetterProgress, type SaveData } from './schema'

export interface AnswerEvent extends Answer {
  letterId: string
  /** The letter the learner picked instead, for the most-confused stats. */
  chosenId?: string
}

function progressOf(save: SaveData, id: string, now: number): LetterProgress {
  return save.letters[id] ?? newLetterProgress(now)
}

/** Marks letters as introduced (Learn → "Got it"); they become due for practice right away. */
export function introduce(save: SaveData, ids: readonly string[], now: number): SaveData {
  const letters = { ...save.letters }
  for (const id of ids) {
    const p = progressOf(save, id, now)
    if (p.introducedAt === null) letters[id] = { ...p, introducedAt: now, due: now }
  }
  return { ...save, letters }
}

/**
 * Records one answer: rolling stats always; the schedule only for letters
 * that have been introduced (previews in False Friends / Word Builder don't
 * schedule unseen letters).
 */
export function recordAnswer(save: SaveData, e: AnswerEvent, now: number): SaveData {
  const p = progressOf(save, e.letterId, now)
  const schedule = p.introducedAt !== null ? review(p, e, now) : p
  const next: LetterProgress = {
    ...p,
    ...schedule,
    attempts: p.attempts + 1,
    correct: p.correct + (e.correct ? 1 : 0),
    recent: pushRecent(p.recent, e.correct),
    lastSeen: now,
  }
  let confusions = save.confusions
  if (!e.correct && e.chosenId && e.chosenId !== e.letterId) {
    const key = `${e.letterId}>${e.chosenId}`
    confusions = { ...confusions, [key]: (confusions[key] ?? 0) + 1 }
  }
  return { ...save, letters: { ...save.letters, [e.letterId]: next }, confusions }
}

/** Opens the next batch if the current group qualifies. Returns the new letter ids. */
export function maybeUnlock(save: SaveData): { save: SaveData; unlocked: string[] } {
  if (!unlockStatus(save.letters, save.unlockedBatches).ready) return { save, unlocked: [] }
  const batch = BATCHES[save.unlockedBatches]
  return { save: { ...save, unlockedBatches: save.unlockedBatches + 1 }, unlocked: [...batch.ids] }
}

/** Local calendar day as YYYY-MM-DD. */
export function localDay(ms: number): string {
  const d = new Date(ms)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function dayBefore(day: string): string {
  const [y, m, d] = day.split('-').map(Number)
  return localDay(new Date(y, m - 1, d - 1, 12).getTime())
}

/** The streak as it stands today: a streak whose last day is before yesterday is broken. */
export function currentStreak(save: SaveData, now: number): number {
  const today = localDay(now)
  const { lastDay, current } = save.streak
  return lastDay === today || lastDay === dayBefore(today) ? current : 0
}

/** Counts a finished session and extends the daily streak. */
export function completeSession(save: SaveData, now: number): SaveData {
  const today = localDay(now)
  const { lastDay, current, best } = save.streak
  const nextCurrent = lastDay === today ? current : lastDay === dayBefore(today) ? current + 1 : 1
  return {
    ...save,
    sessionsCompleted: save.sessionsCompleted + 1,
    streak: { current: nextCurrent, best: Math.max(best, nextCurrent), lastDay: today },
  }
}
