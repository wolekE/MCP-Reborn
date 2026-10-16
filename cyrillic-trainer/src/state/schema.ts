/**
 * Persisted data model. Everything the app remembers lives in one versioned
 * JSON document in localStorage (see storage.ts for load/save/migrations).
 *
 * Bump SCHEMA_VERSION whenever the shape changes incompatibly and add a
 * migration from the previous version in storage.ts.
 */
import type { SpeechRate, VoiceKey } from '../audio/player'

export const SCHEMA_VERSION = 1
export const STORAGE_KEY = 'cyrillic-trainer'

/** Spaced-repetition state for one letter (see srs/scheduler.ts). */
export interface SrsState {
  /** SM-2 ease factor (≥ 1.3). */
  ease: number
  /** Current interval in minutes; 0 until the first successful review. */
  intervalMin: number
  /** Consecutive successful spaced reviews. */
  reps: number
  /** Times the letter was forgotten after having been learned. */
  lapses: number
  /** Next review time (epoch ms). */
  due: number
}

export interface LetterProgress extends SrsState {
  /** When the Learn card was completed ("Got it"); null = not introduced yet. */
  introducedAt: number | null
  attempts: number
  correct: number
  /** Most recent results, oldest first (capped at RECENT_WINDOW). */
  recent: boolean[]
  lastSeen: number | null
}

export type ThemePref = 'system' | 'light' | 'dark'

export interface Settings {
  voice: VoiceKey
  rate: SpeechRate
  /** Mutes the synthesized correct/wrong/streak/level-up tones only (not speech). */
  sfxMuted: boolean
  theme: ThemePref
}

export interface Streak {
  current: number
  best: number
  /** Local calendar day (YYYY-MM-DD) of the last completed session. */
  lastDay: string | null
}

export interface SaveData {
  version: typeof SCHEMA_VERSION
  settings: Settings
  /** Keyed by letter id (see data/letters.ts). */
  letters: Record<string, LetterProgress>
  /** How many unlock batches are open (≥ 1). */
  unlockedBatches: number
  /** Wrong answers: "<targetId>><chosenId>" → count. */
  confusions: Record<string, number>
  streak: Streak
  sessionsCompleted: number
  createdAt: number
}

export const RECENT_WINDOW = 10

export const DEFAULT_SETTINGS: Settings = {
  voice: 'svetlana',
  rate: 1,
  sfxMuted: false,
  theme: 'system',
}

export function newLetterProgress(now: number): LetterProgress {
  return {
    ease: 2.5,
    intervalMin: 0,
    reps: 0,
    lapses: 0,
    due: now,
    introducedAt: null,
    attempts: 0,
    correct: 0,
    recent: [],
    lastSeen: null,
  }
}

export function defaultSave(now: number): SaveData {
  return {
    version: SCHEMA_VERSION,
    settings: { ...DEFAULT_SETTINGS },
    letters: {},
    unlockedBatches: 1,
    confusions: {},
    streak: { current: 0, best: 0, lastDay: null },
    sessionsCompleted: 0,
    createdAt: now,
  }
}
