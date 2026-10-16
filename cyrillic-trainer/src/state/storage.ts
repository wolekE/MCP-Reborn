/**
 * Loading, saving and migrating the versioned save document.
 *
 * Pure functions take a StorageLike so they can be unit-tested without a
 * browser. Anything unreadable (corrupt JSON, a version from a newer build, a
 * version with no migration path) is backed up under its own key before the
 * app starts fresh, so progress is never silently destroyed.
 */
import { LETTER_BY_ID } from '../data/letters'
import {
  DEFAULT_SETTINGS,
  RECENT_WINDOW,
  SCHEMA_VERSION,
  STORAGE_KEY,
  defaultSave,
  newLetterProgress,
  type LetterProgress,
  type SaveData,
  type Settings,
} from './schema'
import { BATCHES } from '../srs/scheduler'

export interface StorageLike {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

/** Upgrades a document from version N to N + 1. */
export type Migration = (doc: Record<string, unknown>) => Record<string, unknown>

/**
 * Migrations keyed by the version they upgrade FROM.
 * Example for a future v2: `1: (doc) => ({ ...doc, version: 2, newField: … })`.
 */
export const MIGRATIONS: Readonly<Record<number, Migration>> = {}

export type LoadProblem = 'corrupt' | 'future-version' | 'no-migration'

export interface LoadResult {
  data: SaveData
  problem: LoadProblem | null
}

type Obj = Record<string, unknown>
const isObj = (v: unknown): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v)
const num = (v: unknown, fallback: number, min = -Infinity, max = Infinity) =>
  typeof v === 'number' && Number.isFinite(v) ? Math.min(max, Math.max(min, v)) : fallback

/** Parses and upgrades a raw stored string. Never throws. */
export function parseSave(raw: string | null, now: number, migrations = MIGRATIONS): LoadResult {
  if (raw === null) return { data: defaultSave(now), problem: null }
  let doc: unknown
  try {
    doc = JSON.parse(raw)
  } catch {
    return { data: defaultSave(now), problem: 'corrupt' }
  }
  if (!isObj(doc) || typeof doc.version !== 'number') return { data: defaultSave(now), problem: 'corrupt' }
  if (doc.version > SCHEMA_VERSION) return { data: defaultSave(now), problem: 'future-version' }
  let current: Obj = doc
  while ((current.version as number) < SCHEMA_VERSION) {
    const step = migrations[current.version as number]
    if (!step) return { data: defaultSave(now), problem: 'no-migration' }
    current = step(current)
  }
  return { data: normalize(current, now), problem: null }
}

/**
 * Coerces a current-version document into a valid SaveData: fills missing
 * fields with defaults, clamps numbers, and drops unknown letter ids.
 */
export function normalize(doc: Obj, now: number): SaveData {
  const base = defaultSave(now)
  const s = isObj(doc.settings) ? doc.settings : {}
  const settings: Settings = {
    voice: s.voice === 'dmitry' ? 'dmitry' : DEFAULT_SETTINGS.voice,
    rate: s.rate === 0.75 ? 0.75 : 1,
    sfxMuted: s.sfxMuted === true,
    theme: s.theme === 'light' || s.theme === 'dark' ? s.theme : 'system',
  }
  const letters: Record<string, LetterProgress> = {}
  if (isObj(doc.letters)) {
    for (const [id, v] of Object.entries(doc.letters)) {
      if (!LETTER_BY_ID.has(id) || !isObj(v)) continue
      const d = newLetterProgress(now)
      letters[id] = {
        ease: num(v.ease, d.ease, 1.3, 5),
        intervalMin: num(v.intervalMin, d.intervalMin, 0),
        reps: Math.round(num(v.reps, 0, 0)),
        lapses: Math.round(num(v.lapses, 0, 0)),
        due: num(v.due, d.due),
        introducedAt: typeof v.introducedAt === 'number' ? v.introducedAt : null,
        attempts: Math.round(num(v.attempts, 0, 0)),
        correct: Math.round(num(v.correct, 0, 0)),
        recent: Array.isArray(v.recent) ? v.recent.filter((x) => typeof x === 'boolean').slice(-RECENT_WINDOW) : [],
        lastSeen: typeof v.lastSeen === 'number' ? v.lastSeen : null,
      }
      letters[id].correct = Math.min(letters[id].correct, letters[id].attempts)
    }
  }
  const confusions: Record<string, number> = {}
  if (isObj(doc.confusions)) {
    for (const [k, v] of Object.entries(doc.confusions)) {
      const [a, b] = k.split('>')
      if (LETTER_BY_ID.has(a) && LETTER_BY_ID.has(b) && typeof v === 'number' && v > 0) confusions[k] = Math.round(v)
    }
  }
  const st = isObj(doc.streak) ? doc.streak : {}
  return {
    version: SCHEMA_VERSION,
    settings,
    letters,
    unlockedBatches: Math.round(num(doc.unlockedBatches, 1, 1, BATCHES.length)),
    confusions,
    streak: {
      current: Math.round(num(st.current, 0, 0)),
      best: Math.round(num(st.best, 0, 0)),
      lastDay: typeof st.lastDay === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(st.lastDay) ? st.lastDay : null,
    },
    sessionsCompleted: Math.round(num(doc.sessionsCompleted, 0, 0)),
    createdAt: num(doc.createdAt, base.createdAt),
  }
}

/** Reads the save; unreadable data is backed up under `<key>:backup:<time>` first. */
export function loadSave(storage: StorageLike, now: number): LoadResult {
  let raw: string | null = null
  try {
    raw = storage.getItem(STORAGE_KEY)
  } catch {
    return { data: defaultSave(now), problem: null }
  }
  const result = parseSave(raw, now)
  if (result.problem && raw !== null) {
    try {
      storage.setItem(`${STORAGE_KEY}:backup:${now}`, raw)
    } catch {
      // Quota or privacy mode: nothing more we can do.
    }
  }
  return result
}

/** Returns false when the browser refuses to store (private mode, quota). */
export function writeSave(storage: StorageLike, data: SaveData): boolean {
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(data))
    return true
  } catch {
    return false
  }
}

/** Fresh progress that keeps the user's settings. */
export function resetProgress(data: SaveData, now: number): SaveData {
  return { ...defaultSave(now), settings: { ...data.settings } }
}
