import { describe, expect, it } from 'vitest'
import { BUILDER_WORDS, CLIP_TEXT, LETTERS, LETTER_BY_ID, LETTER_BY_UPPER, WORD_BY_TEXT, transliterate } from '../data/letters'
import { introduce, recordAnswer } from '../state/actions'
import { defaultSave } from '../state/schema'
import { MINUTE_MS, unlockedIds } from '../srs/scheduler'
import {
  FALSE_FRIENDS,
  audibleLetters,
  builderItem,
  builderQueue,
  falseFriendItem,
  listenItem,
  listenQueue,
  pickDistractors,
  readLetterItem,
  readWordItem,
  retryOf,
  reviewQueue,
  sampleTargets,
  soundClips,
  type ChoiceItem,
} from './items'
import { MAX_RETRIES, RETRY_GAP, fillersFor, insertRetry } from './queue'
import { seededRng, shuffle } from './rng'

const T0 = Date.UTC(2026, 5, 1, 8)
const L = (u: string) => LETTER_BY_UPPER.get(u)!
const ALL = [...LETTERS]

function checkChoice(item: ChoiceItem) {
  expect(item.options).toHaveLength(4)
  expect(new Set(item.options.map((o) => o.label)).size).toBe(4)
  expect(item.answer).toBeGreaterThanOrEqual(0)
  expect(item.answer).toBeLessThan(4)
}

describe('insertRetry: missed items return 2 items later', () => {
  it('puts exactly two other items between the miss and its retry', () => {
    const q = ['A', 'B', 'C', 'D', 'E']
    const out = insertRetry(q, 0, "A'")
    expect(out).toEqual(['A', 'B', 'C', "A'", 'D', 'E'])
    expect(out.indexOf("A'") - 0 - 1).toBe(RETRY_GAP)
  })
  it('appends at the end when fewer than two items remain', () => {
    expect(insertRetry(['A', 'B', 'C'], 2, "C'")).toEqual(['A', 'B', 'C', "C'"])
    expect(insertRetry(['A', 'B', 'C'], 1, "B'")).toEqual(['A', 'B', 'C', "B'"])
  })
  it('tops up the queue so a miss near the end still comes back 2 items later', () => {
    const key = (s: string) => s[0]
    for (const missAt of [3, 4]) {
      const q = ['A1', 'B1', 'C1', 'D1', 'E1']
      const fill = fillersFor(q, missAt, ['E2', 'A2', 'F1', 'G1', 'H1'], key)
      const out = insertRetry([...q, ...fill], missAt, `${q[missAt]}'`)
      expect(out.indexOf(`${q[missAt]}'`) - missAt - 1).toBe(RETRY_GAP)
      // No filler repeats the missed item or sits next to the same subject.
      for (let i = 1; i < out.length; i++) expect(key(out[i])).not.toBe(key(out[i - 1]))
    }
    expect(fillersFor(['A', 'B', 'C', 'D'], 0, ['X'], (s) => s)).toEqual([])
  })

  it('limits how often an item can come back', () => {
    expect(MAX_RETRIES).toBeGreaterThan(0)
    const rng = seededRng(1)
    const first = listenItem(L('Ш'), ALL, rng)
    const second = retryOf(retryOf(first, ALL, rng), ALL, rng)
    expect(second.retries).toBe(2)
    expect(second.uid).not.toBe(first.uid)
  })
})

describe('sounds', () => {
  it('never plays a bare consonant: consonants and vowels use syllables, Ъ/Ь their pair', () => {
    for (const l of LETTERS) {
      const clips = soundClips(l)
      if (l.kind === 'sign') expect(clips).toEqual(l.audio.contrast)
      else expect(clips).toEqual([l.audio.syllable])
    }
  })
  it('knows which other letters are audible in a prompt', () => {
    expect([...audibleLetters(soundClips(L('Б')), L('Б'))]).toEqual(['a'])
    expect(audibleLetters(soundClips(L('Ь')), L('Ь'))).toEqual(new Set(['m', 'a', 't']))
  })
})

describe('pickDistractors', () => {
  it('prefers confusables that the learner knows', () => {
    const out = pickDistractors(L('Ш'), ALL, 3, seededRng(3))
    expect(out.map((l) => l.upper)).toEqual(['Щ', 'Ж', 'Ц'])
  })
  it('falls back to the pool, then the alphabet, never repeating or including the target', () => {
    const pool = ['А', 'К', 'М', 'О', 'Т'].map(L)
    for (let seed = 0; seed < 50; seed++) {
      const out = pickDistractors(L('К'), pool, 3, seededRng(seed))
      expect(out).toHaveLength(3)
      expect(new Set(out).size).toBe(3)
      expect(out).not.toContain(L('К'))
    }
  })
  it('honours exclusions', () => {
    const out = pickDistractors(L('Б'), ALL, 3, seededRng(9), new Set(['a', 'v']))
    expect(out.map((l) => l.id)).not.toContain('a')
    expect(out.map((l) => l.id)).not.toContain('v')
  })
})

describe('item builders', () => {
  it('Listen & Pick: 4 distinct letters, the right one included, none audible in the prompt', () => {
    for (const target of LETTERS) {
      for (let seed = 0; seed < 5; seed++) {
        const item = listenItem(target, ALL, seededRng(seed))
        checkChoice(item)
        expect(item.options[item.answer].letterId).toBe(target.id)
        const heard = item.clips.map((c) => CLIP_TEXT.get(c)!).join(' ')
        for (const o of item.options) {
          if (o.letterId === target.id) continue
          const l = LETTER_BY_ID.get(o.letterId!)!
          expect(heard.includes(l.lower), `${target.upper}: "${heard}" contains option ${l.upper}`).toBe(false)
        }
      }
    }
  })

  it('Read (letter): answer is the letter’s sound; false friends offer their misreading', () => {
    for (const target of LETTERS) {
      const item = readLetterItem(target, ALL, seededRng(4))
      checkChoice(item)
      expect(item.options[item.answer].label).toBe(target.sound)
      expect([target.upper, target.lower]).toContain(item.display)
    }
    const r = readLetterItem(L('Р'), ALL, seededRng(5))
    expect(r.options.map((o) => o.label)).toContain('p')
  })

  it('Read (word): answer is the transliteration, decoys differ', () => {
    for (const w of ['кот', 'мама', 'рука', 'хлеб', 'щётка', 'мышь']) {
      const word = WORD_BY_TEXT.get(w)!
      const item = readWordItem(word, LETTER_BY_UPPER.get(w[0].toUpperCase())!, seededRng(6))
      checkChoice(item)
      expect(item.options[item.answer].label).toBe(transliterate(w))
      expect(item.clips).toEqual([word.audio])
    }
  })

  it('False Friends: the real sound beats the Latin look-alike', () => {
    for (const target of FALSE_FRIENDS) {
      const item = falseFriendItem(target, seededRng(7))
      checkChoice(item)
      expect(item.options[item.answer].label).toBe(target.sound)
      expect(item.options.map((o) => o.label)).toEqual(expect.arrayContaining([target.falseFriend!.wrongSounds[0]]))
    }
  })

  it('Word Builder: tiles contain every letter of the word plus decoys', () => {
    for (const w of BUILDER_WORDS) {
      const item = builderItem(WORD_BY_TEXT.get(w)!, seededRng(8))
      expect(item.letters.map((l) => l.lower).join('')).toBe(w)
      for (const l of item.letters) expect(item.tiles).toContain(l)
      expect(new Set(item.tiles).size).toBe(item.tiles.length)
      expect(item.tiles.length).toBeGreaterThanOrEqual(6)
    }
  })
})

describe('queues', () => {
  const group1 = () => introduce(defaultSave(T0), unlockedIds(1), T0)

  it('never asks about the same letter twice in a row', () => {
    const s = group1()
    const pool = unlockedIds(1).map((id) => LETTER_BY_ID.get(id)!)
    for (let seed = 0; seed < 20; seed++) {
      const t = sampleTargets(s, pool, 30, T0, seededRng(seed))
      for (let i = 1; i < t.length; i++) expect(t[i]).not.toBe(t[i - 1])
    }
  })

  it('builds Listen & Pick rounds from introduced letters only', () => {
    const q = listenQueue({ save: group1(), now: T0, rng: seededRng(2) })
    expect(q).toHaveLength(10)
    for (const item of q) expect(unlockedIds(1)).toContain(item.target.id)
  })

  it('Daily review covers every due letter and mixes item types', () => {
    let s = introduce(defaultSave(T0), [...unlockedIds(2), 'b', 'g', 'd', 'z', 'i', 'sh'], T0)
    // One letter answered recently is not due.
    s = recordAnswer(s, { letterId: 'a', correct: true, responseMs: 3000, fastMs: 2500 }, T0)
    const { items, dueCount } = reviewQueue({ save: s, now: T0 + MINUTE_MS, rng: seededRng(11) })
    expect(dueCount).toBe(14)
    const targets = items.map((i) => (i.kind === 'builder' ? null : i.target.id))
    expect(targets).not.toContain('a')
    expect(new Set(items.map((i) => i.kind)).size).toBeGreaterThan(2)
  })

  it('falls back to practising the weakest letters when nothing is due', () => {
    let s = group1()
    for (const id of unlockedIds(1)) s = recordAnswer(s, { letterId: id, correct: true, responseMs: 3000, fastMs: 2500 }, T0)
    const { items, dueCount } = reviewQueue({ save: s, now: T0 + MINUTE_MS, rng: seededRng(12) })
    expect(dueCount).toBe(0)
    expect(items.length).toBeGreaterThan(0)
  })

  it('Word Builder prefers words spelled with known letters', () => {
    const q = builderQueue({ save: group1(), now: T0, rng: seededRng(13) }, 2)
    expect(q.map((i) => i.word.word).sort()).toEqual(['кот', 'мама'])
  })
})

describe('rng', () => {
  it('is deterministic per seed and shuffles without losing items', () => {
    expect(shuffle([1, 2, 3, 4, 5], seededRng(42))).toEqual(shuffle([1, 2, 3, 4, 5], seededRng(42)))
    expect(shuffle([1, 2, 3, 4, 5], seededRng(42)).sort()).toEqual([1, 2, 3, 4, 5])
  })
})
