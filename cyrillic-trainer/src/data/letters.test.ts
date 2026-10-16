import { describe, expect, it } from 'vitest'
import {
  ALL_WORDS,
  BUILDER_WORDS,
  CLIPS,
  GROUP_ORDER,
  LETTERS,
  LETTER_BY_UPPER,
  TEACHING_ORDER,
  WORD_BY_TEXT,
  buildClipRegistry,
  lettersInWord,
  transliterate,
  ttsText,
} from './letters'

const ALPHABET = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
const NAMES = [
  'а', 'бэ', 'вэ', 'гэ', 'дэ', 'е', 'ё', 'жэ', 'зэ', 'и', 'и краткое', 'ка', 'эль', 'эм', 'эн', 'о', 'пэ',
  'эр', 'эс', 'тэ', 'у', 'эф', 'ха', 'цэ', 'че', 'ша', 'ща', 'твёрдый знак', 'ы', 'мягкий знак', 'э', 'ю', 'я',
]

describe('the 33 letters', () => {
  it('are all present, unique and in alphabetical order', () => {
    expect(LETTERS).toHaveLength(33)
    expect(LETTERS.map((l) => l.upper).join('')).toBe(ALPHABET)
    expect(new Set(LETTERS.map((l) => l.upper)).size).toBe(33)
    expect(new Set(LETTERS.map((l) => l.lower)).size).toBe(33)
    expect(new Set(LETTERS.map((l) => l.id)).size).toBe(33)
    expect(new Set(LETTERS.map((l) => l.sound)).size).toBe(33)
  })

  it('pair each uppercase letter with its lowercase form', () => {
    for (const l of LETTERS) {
      expect(l.upper.toLowerCase()).toBe(l.lower)
      expect(l.cursive).toBe(l.upper + l.lower)
    }
  })

  it('use the specified Russian names', () => {
    expect(LETTERS.map((l) => l.name)).toEqual(NAMES)
  })

  it('have every field a learner sees', () => {
    for (const l of LETTERS) {
      expect(l.ipa, l.upper).not.toBe('')
      expect(l.hintEn, l.upper).not.toBe('')
      expect(l.hintPl, l.upper).not.toBe('')
      expect(l.example.word, l.upper).not.toBe('')
      expect(l.example.en, l.upper).not.toBe('')
      expect(l.example.stressed.replace(/́/g, ''), l.upper).toBe(l.example.word)
      expect(l.id, 'ids are URL/file safe').toMatch(/^[a-z]+$/)
    }
  })
})

describe('groups', () => {
  it('match the teaching plan exactly', () => {
    expect(GROUP_ORDER).toEqual({
      1: ['А', 'К', 'М', 'О', 'Т'],
      2: ['В', 'Е', 'Н', 'Р', 'С', 'У', 'Х'],
      3: ['Б', 'Г', 'Д', 'З', 'И', 'Й', 'Л', 'П', 'Ф', 'Э'],
      4: ['Ж', 'Ц', 'Ч', 'Ш', 'Щ', 'Ы'],
      5: ['Ё', 'Ю', 'Я', 'Ъ', 'Ь'],
    })
    for (const l of LETTERS) expect(GROUP_ORDER[l.group]).toContain(l.upper)
    expect(TEACHING_ORDER).toHaveLength(33)
  })

  it('give every false friend (group 2) its Latin look-alike', () => {
    for (const u of GROUP_ORDER[2]) expect(LETTER_BY_UPPER.get(u)!.falseFriend, u).toBeDefined()
    expect(LETTER_BY_UPPER.get('Р')!.falseFriend).toEqual({ looksLike: 'P', wrongSounds: ['p'] })
  })
})

describe('confusables', () => {
  it('only reference real letters, never the letter itself', () => {
    for (const l of LETTERS) {
      for (const c of l.confusables) {
        expect(LETTER_BY_UPPER.has(c), `${l.upper} → ${c}`).toBe(true)
        expect(c).not.toBe(l.upper)
      }
    }
  })

  it('include every specified pair, in both directions', () => {
    const sets = [['Ш', 'Щ'], ['Е', 'Ё', 'Э'], ['И', 'Й', 'Ы'], ['Б', 'В'], ['П', 'Н'], ['Ь', 'Ъ', 'Ы'], ['Х', 'Ж']]
    for (const set of sets) {
      for (const a of set) {
        for (const b of set) {
          if (a !== b) expect(LETTER_BY_UPPER.get(a)!.confusables, `${a} should list ${b}`).toContain(b)
        }
      }
    }
  })
})

describe('audio data', () => {
  it('gives every letter a name, a syllable and a word clip — or a contrast pair for Ъ and Ь', () => {
    for (const l of LETTERS) {
      expect(l.audio.name).toMatch(/^name-/)
      expect(l.audio.word).toMatch(/^word-/)
      if (l.kind === 'sign') {
        expect(l.audio.syllable, l.upper).toBeUndefined()
        expect(l.audio.contrast, l.upper).toHaveLength(2)
      } else {
        expect(l.audio.syllable, l.upper).toMatch(/^syl-/)
        expect(l.syllableText, l.upper).toBeTruthy()
      }
    }
  })

  it('never plays a consonant on its own: every syllable has a vowel', () => {
    for (const l of LETTERS) {
      if (l.syllableText) expect(l.syllableText, l.upper).toMatch(/[аеёиоуыэюя]/)
    }
  })

  it('builds consonant syllables as consonant + а', () => {
    for (const l of LETTERS) {
      if (l.kind === 'consonant' && l.id !== 'j') expect(l.syllableText).toBe(`${l.lower}а`)
    }
  })

  it('uses the specified contrast pairs for Ъ and Ь', () => {
    const hard = LETTER_BY_UPPER.get('Ъ')!
    const soft = LETTER_BY_UPPER.get('Ь')!
    expect(hard.contrastText).toEqual(['сел', 'съел'])
    expect(soft.contrastText).toEqual(['мат', 'мать'])
    for (const l of [hard, soft]) {
      const [plain, marked] = l.audio.contrast!
      expect(WORD_BY_TEXT.get(l.contrastText![0])!.audio).toBe(plain)
      expect(WORD_BY_TEXT.get(l.contrastText![1])!.audio).toBe(marked)
    }
  })

  it('has a consistent clip registry (one text per id, ASCII ids)', () => {
    expect(() => buildClipRegistry()).not.toThrow()
    expect(new Set(CLIPS.map((c) => c.id)).size).toBe(CLIPS.length)
    for (const c of CLIPS) expect(c.id).toMatch(/^[a-z]+-[a-z-]+$/)
  })

  it('has clips for every Word Builder word', () => {
    expect(BUILDER_WORDS).toEqual(['кот', 'дом', 'мама', 'суп', 'чай', 'жук', 'щи', 'мышь'])
    for (const w of BUILDER_WORDS) expect(WORD_BY_TEXT.get(w), w).toBeDefined()
  })

  it('spells every word with real letters', () => {
    for (const w of ALL_WORDS) expect(lettersInWord(w.word).length, w.word).toBeGreaterThan(0)
  })
})

describe('ttsText', () => {
  it('stress-marks a lone vowel so TTS does not read it as an unstressed word', () => {
    expect(ttsText('о')).toBe('о\u0301')
    expect(ttsText('а')).toBe('а\u0301')
  })
  it('leaves everything else alone (a mark next to a consonant makes TTS spell it out)', () => {
    for (const t of ['ба', 'мо', 'эль', 'кот', 'мама', 'ё', 'ай']) expect(ttsText(t)).toBe(t)
  })
  it('sends only a few clips with a different spelling, each for a measured reason', () => {
    const changed = CLIPS.filter((c) => c.tts !== c.text).map((c) => c.id)
    expect(changed.sort()).toEqual(['name-a', 'name-ch', 'name-e', 'name-i', 'name-o', 'name-u', 'name-y', 'name-ya', 'name-ye', 'name-yu'])
  })
})

describe('transliterate', () => {
  it('romanizes letter by letter', () => {
    expect(transliterate('кот')).toBe('kot')
    expect(transliterate('щётка')).toBe('shchyotka')
    expect(transliterate('мышь')).toBe('myshʹ')
    expect(transliterate('съел')).toBe('sʺyel')
  })
  it('writes е as ye at the start and e after a consonant', () => {
    expect(transliterate('ем')).toBe('yem')
    expect(transliterate('хлеб')).toBe('khleb')
  })
  it('can read one letter differently (for decoys)', () => {
    expect(transliterate('рука', { letter: LETTER_BY_UPPER.get('Р')!, sound: 'p' })).toBe('puka')
  })
})
