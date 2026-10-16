import { describe, expect, it } from 'vitest'
import { SCHEMA_VERSION, STORAGE_KEY, defaultSave } from './schema'
import { loadSave, normalize, parseSave, resetProgress, writeSave, type Migration, type StorageLike } from './storage'

const NOW = Date.UTC(2026, 3, 1, 12)

function memoryStorage(initial: Record<string, string> = {}): StorageLike & { data: Record<string, string> } {
  const data = { ...initial }
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => void (data[k] = v),
    removeItem: (k) => void delete data[k],
  }
}

describe('parseSave', () => {
  it('starts fresh when nothing is stored', () => {
    expect(parseSave(null, NOW)).toEqual({ data: defaultSave(NOW), problem: null })
  })

  it('round-trips a saved document', () => {
    const save = defaultSave(NOW)
    save.settings.voice = 'dmitry'
    save.unlockedBatches = 3
    save.letters.zh = { ease: 2.2, intervalMin: 1440, reps: 2, lapses: 1, due: NOW + 5, introducedAt: NOW - 9, attempts: 7, correct: 5, recent: [true, false], lastSeen: NOW }
    save.confusions['sh>shch'] = 2
    expect(parseSave(JSON.stringify(save), NOW).data).toEqual(save)
  })

  it('flags corrupt JSON and documents without a version', () => {
    expect(parseSave('{not json', NOW).problem).toBe('corrupt')
    expect(parseSave('{"letters":{}}', NOW).problem).toBe('corrupt')
    expect(parseSave('[1,2]', NOW).problem).toBe('corrupt')
  })

  it('refuses data written by a newer version', () => {
    const r = parseSave(JSON.stringify({ version: SCHEMA_VERSION + 1 }), NOW)
    expect(r.problem).toBe('future-version')
    expect(r.data).toEqual(defaultSave(NOW))
  })

  it('runs migrations step by step up to the current version', () => {
    const migrations: Record<number, Migration> = {
      [-1]: (d) => ({ ...d, version: 0, streak: { current: d.days, best: d.days, lastDay: null } }),
      0: (d) => ({ ...d, version: 1, unlockedBatches: d.level }),
    }
    const old = JSON.stringify({ version: -1, days: 4, level: 2 })
    const r = parseSave(old, NOW, migrations)
    expect(r.problem).toBeNull()
    expect(r.data.streak.current).toBe(4)
    expect(r.data.unlockedBatches).toBe(2)
  })

  it('reports a missing migration instead of guessing', () => {
    expect(parseSave(JSON.stringify({ version: 0 }), NOW, {}).problem).toBe('no-migration')
  })
})

describe('normalize', () => {
  it('fills gaps, clamps values and drops unknown letters and confusions', () => {
    const data = normalize(
      {
        version: 1,
        settings: { voice: 'robot', rate: 2, sfxMuted: 'yes', theme: 'dark' },
        letters: {
          a: { ease: 99, attempts: 3, correct: 10, recent: [true, 'x', false] },
          zz: { ease: 2 },
        },
        unlockedBatches: 999,
        confusions: { 'a>k': 2, 'a>zz': 5, 'k>m': -1 },
        streak: { current: 2, lastDay: 'yesterday' },
      },
      NOW,
    )
    expect(data.settings).toEqual({ voice: 'svetlana', rate: 1, sfxMuted: false, theme: 'dark' })
    expect(Object.keys(data.letters)).toEqual(['a'])
    expect(data.letters.a.ease).toBe(5)
    expect(data.letters.a.correct).toBe(3)
    expect(data.letters.a.recent).toEqual([true, false])
    expect(data.letters.a.introducedAt).toBeNull()
    expect(data.unlockedBatches).toBe(8)
    expect(data.confusions).toEqual({ 'a>k': 2 })
    expect(data.streak).toEqual({ current: 2, best: 0, lastDay: null })
  })
})

describe('loadSave / writeSave', () => {
  it('persists under the versioned key', () => {
    const storage = memoryStorage()
    const save = defaultSave(NOW)
    save.sessionsCompleted = 3
    expect(writeSave(storage, save)).toBe(true)
    expect(JSON.parse(storage.data[STORAGE_KEY]).version).toBe(SCHEMA_VERSION)
    expect(loadSave(storage, NOW).data.sessionsCompleted).toBe(3)
  })

  it('backs up unreadable data before starting fresh', () => {
    const storage = memoryStorage({ [STORAGE_KEY]: '{oops' })
    const r = loadSave(storage, NOW)
    expect(r.problem).toBe('corrupt')
    expect(storage.data[`${STORAGE_KEY}:backup:${NOW}`]).toBe('{oops')
  })

  it('survives storage that throws (private mode, quota)', () => {
    const broken: StorageLike = {
      getItem: () => {
        throw new Error('denied')
      },
      setItem: () => {
        throw new Error('quota')
      },
      removeItem: () => {},
    }
    expect(loadSave(broken, NOW).data).toEqual(defaultSave(NOW))
    expect(writeSave(broken, defaultSave(NOW))).toBe(false)
  })
})

describe('resetProgress', () => {
  it('erases progress but keeps settings', () => {
    const save = defaultSave(NOW)
    save.settings = { voice: 'dmitry', rate: 0.75, sfxMuted: true, theme: 'light' }
    save.sessionsCompleted = 9
    save.unlockedBatches = 4
    const fresh = resetProgress(save, NOW + 1)
    expect(fresh.settings).toEqual(save.settings)
    expect(fresh.sessionsCompleted).toBe(0)
    expect(fresh.unlockedBatches).toBe(1)
    expect(fresh.letters).toEqual({})
  })
})
