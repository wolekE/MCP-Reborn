/**
 * Builds drill items and session queues (pure, seeded).
 *
 * Distractors prefer each letter's confusables (Ш/Щ, Е/Ё/Э, И/Й/Ы, …) so the
 * learner practises exactly the distinctions that trip people up. In Listen &
 * Pick, letters audible in the prompt are never offered (the "а" in "ба" must
 * not be a wrong answer).
 */
import {
  ALL_WORDS,
  BUILDER_WORDS,
  CLIP_TEXT,
  GROUP_ORDER,
  LETTERS,
  LETTER_BY_ID,
  LETTER_BY_UPPER,
  WORD_BY_TEXT,
  letterOf,
  lettersInWord,
  transliterate,
  type ClipId,
  type Letter,
  type Word,
} from '../data/letters'
import { isDue, recentAccuracy } from '../srs/scheduler'
import type { SaveData } from '../state/schema'
import { pick, shuffle, type Rng } from './rng'

export type ChoiceKind = 'listen' | 'read-letter' | 'read-word' | 'false-friend'
export type ItemKind = ChoiceKind | 'builder'

export interface Option {
  label: string
  /** Cyrillic options render in the letter font; Latin ones in the UI font. */
  script: 'cyrillic' | 'latin'
  /** The letter this option stands for (feeds the most-confused stats). */
  letterId?: string
}

interface ItemBase {
  /** Unique per occurrence (retries get a new one). */
  uid: string
  /** Times this item has already come back after a miss. */
  retries: number
  /** Response time at or under which an answer counts as fast. */
  fastMs: number
}

export interface ChoiceItem extends ItemBase {
  kind: ChoiceKind
  /** The letter being tested (for read-word: the letter the distractors change). */
  target: Letter
  /** Cyrillic text to show (read-letter, read-word, false-friend). */
  display?: string
  word?: Word
  options: Option[]
  answer: number
  /** Listen: the prompt. Others: played after answering. */
  clips: ClipId[]
}

export interface BuilderItem extends ItemBase {
  kind: 'builder'
  word: Word
  /** The word's letters, in order. */
  letters: Letter[]
  /** Tappable tiles: the word's letters plus confusable decoys, shuffled. */
  tiles: Letter[]
}

export type Item = ChoiceItem | BuilderItem

export const FAST_MS: Record<ItemKind, number> = {
  listen: 3000,
  'read-letter': 2000,
  'read-word': 3500,
  'false-friend': 1500,
  builder: 3000,
}

let uidCounter = 0
const uid = (rng: Rng) => `${++uidCounter}-${Math.floor(rng() * 1e9).toString(36)}`

// ---------------------------------------------------------------------------
// Sounds
// ---------------------------------------------------------------------------

/**
 * The clip(s) that carry a letter's sound: a syllable for consonants (never a
 * bare consonant), the syllable for vowels too (bare one-vowel words are read
 * as reduced function words by TTS — "о" comes out as [ɐ]), and the minimal
 * pair for Ъ / Ь.
 */
export function soundClips(l: Letter): ClipId[] {
  if (l.audio.contrast) return [...l.audio.contrast]
  return [l.audio.syllable ?? l.audio.name]
}

/** Letters you can hear in the given clips, apart from the target itself. */
export function audibleLetters(clips: readonly ClipId[], target: Letter): Set<string> {
  const out = new Set<string>()
  for (const id of clips) for (const l of lettersInWord(CLIP_TEXT.get(id) ?? '')) if (l !== target) out.add(l.id)
  return out
}

// ---------------------------------------------------------------------------
// Distractors
// ---------------------------------------------------------------------------

/**
 * Up to n distractor letters: confusables from the pool first, then the rest
 * of the pool, then (only if the pool is too small) confusables and other
 * letters from the whole alphabet.
 */
export function pickDistractors(
  target: Letter,
  pool: readonly Letter[],
  n: number,
  rng: Rng,
  exclude: ReadonlySet<string> = new Set(),
): Letter[] {
  const ok = (l: Letter, chosen: Letter[]) => l !== target && !exclude.has(l.id) && !chosen.includes(l)
  const chosen: Letter[] = []
  const conf = target.confusables.map((u) => LETTER_BY_UPPER.get(u)!)
  const inPool = new Set(pool)
  const tiers = [conf.filter((l) => inPool.has(l)), shuffle(pool, rng), conf, shuffle(LETTERS, rng)]
  for (const tier of tiers) {
    for (const l of tier) {
      if (chosen.length >= n) return chosen
      if (ok(l, chosen)) chosen.push(l)
    }
  }
  return chosen
}

function finishChoice(
  rng: Rng,
  base: Omit<ChoiceItem, 'options' | 'answer' | 'uid' | 'retries' | 'fastMs'>,
  correct: Option,
  wrong: Option[],
): ChoiceItem {
  const options = shuffle([correct, ...wrong], rng)
  return { ...base, uid: uid(rng), retries: 0, fastMs: FAST_MS[base.kind], options, answer: options.indexOf(correct) }
}

const letterOption = (l: Letter): Option => ({ label: `${l.upper} ${l.lower}`, script: 'cyrillic', letterId: l.id })
const soundOption = (l: Letter): Option => ({ label: l.sound, script: 'latin', letterId: l.id })

// ---------------------------------------------------------------------------
// Item builders
// ---------------------------------------------------------------------------

/** Listen & Pick: hear the sound, pick the letter. */
export function listenItem(target: Letter, pool: readonly Letter[], rng: Rng): ChoiceItem {
  const clips = soundClips(target)
  const wrong = pickDistractors(target, pool, 3, rng, audibleLetters(clips, target))
  return finishChoice(rng, { kind: 'listen', target, clips }, letterOption(target), wrong.map(letterOption))
}

/** Read (letter): see the letter, pick its sound. False-friend misreadings are favourite decoys. */
export function readLetterItem(target: Letter, pool: readonly Letter[], rng: Rng): ChoiceItem {
  const labels = new Set([target.sound])
  const wrong: Option[] = []
  const add = (o: Option) => {
    if (wrong.length < 3 && !labels.has(o.label)) {
      labels.add(o.label)
      wrong.push(o)
    }
  }
  if (target.falseFriend) add({ label: pick(target.falseFriend.wrongSounds, rng), script: 'latin' })
  for (const l of pickDistractors(target, pool, 6, rng)) add(soundOption(l))
  const display = rng() < 0.5 ? target.upper : target.lower
  return finishChoice(rng, { kind: 'read-letter', target, display, clips: soundClips(target) }, soundOption(target), wrong)
}

/**
 * Read (word): see a short word, pick its transliteration. Decoys swap the
 * focus letter (then others) for a confusable's sound or a false-friend misreading.
 */
export function readWordItem(word: Word, focus: Letter, rng: Rng): ChoiceItem {
  const correct = transliterate(word.word)
  const seen = new Set([correct])
  const wrong: Option[] = []
  const swaps = (l: Letter): { sound: string; letterId?: string }[] => [
    ...(l.falseFriend?.wrongSounds.map((s) => ({ sound: s })) ?? []),
    ...l.confusables.map((u) => LETTER_BY_UPPER.get(u)!).filter((c) => c.kind !== 'sign').map((c) => ({ sound: c.sound, letterId: c.id })),
  ]
  const others = shuffle(lettersInWord(word.word).filter((l) => l !== focus && l.kind !== 'sign'), rng)
  for (const l of [focus, ...others]) {
    for (const s of shuffle(swaps(l), rng)) {
      if (wrong.length >= 3) break
      const label = transliterate(word.word, { letter: l, sound: s.sound })
      if (!seen.has(label)) {
        seen.add(label)
        // Only a swap of the focus letter tells us which letter was confused with it.
        wrong.push({ label, script: 'latin', letterId: l === focus ? s.letterId : undefined })
      }
    }
  }
  return finishChoice(
    rng,
    { kind: 'read-word', target: focus, display: word.word, word, clips: [word.audio] },
    { label: correct, script: 'latin', letterId: focus.id },
    wrong,
  )
}

/** False Friends: a group-2 letter; pick its real sound over the Latin look-alike. */
export function falseFriendItem(target: Letter, rng: Rng): ChoiceItem {
  const ff = target.falseFriend!
  const labels = new Set([target.sound])
  const wrong: Option[] = []
  for (const s of shuffle(ff.wrongSounds, rng)) {
    if (labels.has(s)) continue
    labels.add(s)
    const asLetter = LETTERS.find((l) => l.sound === s)
    wrong.push({ label: s, script: 'latin', letterId: asLetter?.id })
  }
  for (const l of shuffle(FALSE_FRIENDS, rng)) {
    if (wrong.length >= 3) break
    if (!labels.has(l.sound)) {
      labels.add(l.sound)
      wrong.push(soundOption(l))
    }
  }
  const display = rng() < 0.5 ? target.upper : target.lower
  return finishChoice(rng, { kind: 'false-friend', target, display, clips: soundClips(target) }, soundOption(target), wrong.slice(0, 3))
}

export const FALSE_FRIENDS: readonly Letter[] = GROUP_ORDER[2].map((u) => LETTER_BY_UPPER.get(u)!)

/** Word Builder: hear a word, tap its letters in order. */
export function builderItem(word: Word, rng: Rng): BuilderItem {
  const letters = [...word.word].map((ch) => letterOf(ch)!)
  const unique = [...new Set(letters)]
  const decoys: Letter[] = []
  for (const l of unique) {
    for (const u of l.confusables) {
      const c = LETTER_BY_UPPER.get(u)!
      if (!unique.includes(c) && !decoys.includes(c)) decoys.push(c)
    }
  }
  const want = Math.max(6, unique.length + 3)
  const extra = shuffle(decoys, rng).slice(0, want - unique.length)
  return { kind: 'builder', uid: uid(rng), retries: 0, fastMs: FAST_MS.builder, word, letters, tiles: shuffle([...unique, ...extra], rng) }
}

/** A fresh variant of an item for its retry (new options order, same target). */
export function retryOf(item: Item, pool: readonly Letter[], rng: Rng): Item {
  const next = remake(item, pool, rng)
  return { ...next, retries: item.retries + 1 }
}

function remake(item: Item, pool: readonly Letter[], rng: Rng): Item {
  switch (item.kind) {
    case 'listen':
      return listenItem(item.target, pool, rng)
    case 'read-letter':
      return readLetterItem(item.target, pool, rng)
    case 'read-word':
      return readWordItem(item.word!, item.target, rng)
    case 'false-friend':
      return falseFriendItem(item.target, rng)
    case 'builder':
      return builderItem(item.word, rng)
  }
}

// ---------------------------------------------------------------------------
// Queues
// ---------------------------------------------------------------------------

/** Letters the learner has been introduced to, in teaching order. */
export function practicePool(save: SaveData): Letter[] {
  return LETTERS.filter((l) => save.letters[l.id]?.introducedAt != null).sort(byTeachingOrder)
}

const TEACH_INDEX = new Map(([1, 2, 3, 4, 5] as const).flatMap((g) => GROUP_ORDER[g]).map((u, i) => [u, i]))
export function byTeachingOrder(a: Letter, b: Letter): number {
  return TEACH_INDEX.get(a.upper)! - TEACH_INDEX.get(b.upper)!
}

/** Practice weight: due, weak and fresh letters come up more often. */
export function weight(save: SaveData, l: Letter, now: number): number {
  const p = save.letters[l.id]
  if (!p) return 1
  const acc = recentAccuracy(p)
  return 1 + (isDue(p, now) ? 2 : 0) + (acc === null ? 2 : (1 - acc) * 3) + (p.attempts < 3 ? 1 : 0)
}

/** n targets by weighted sampling, never the same letter twice in a row. */
export function sampleTargets(save: SaveData, letters: readonly Letter[], n: number, now: number, rng: Rng): Letter[] {
  if (letters.length === 0) return []
  const out: Letter[] = []
  for (let i = 0; i < n; i++) {
    const options = letters.length > 1 ? letters.filter((l) => l !== out[out.length - 1]) : letters
    const weights = options.map((l) => weight(save, l, now))
    let r = rng() * weights.reduce((a, b) => a + b, 0)
    let idx = 0
    while (idx < options.length - 1 && r >= weights[idx]) r -= weights[idx++]
    out.push(options[idx])
  }
  return out
}

export interface QueueOptions {
  save: SaveData
  now: number
  rng: Rng
  /** Restrict to these letters (e.g. just-learned ones); defaults to the whole pool. */
  focus?: readonly Letter[]
}

export const SESSION_LENGTH = { listen: 10, read: 10, builder: 5, review: 20 } as const

export function listenQueue({ save, now, rng, focus }: QueueOptions, n: number = SESSION_LENGTH.listen): ChoiceItem[] {
  const pool = practicePool(save)
  return sampleTargets(save, focus ?? pool, n, now, rng).map((t) => listenItem(t, pool, rng))
}

/** Words whose letters are all known and that contain `focus`. */
export function readableWords(save: SaveData, focus?: Letter): Word[] {
  const known = new Set(practicePool(save))
  return ALL_WORDS.filter((w) => lettersInWord(w.word).every((l) => known.has(l)) && (!focus || lettersInWord(w.word).includes(focus)))
}

export function readQueue({ save, now, rng, focus }: QueueOptions, n: number = SESSION_LENGTH.read): ChoiceItem[] {
  const pool = practicePool(save)
  return sampleTargets(save, focus ?? pool, n, now, rng).map((t, i) => {
    const words = readableWords(save, t)
    // Every other item is a word once there are words to read.
    return i % 2 === 1 && words.length ? readWordItem(pick(words, rng), t, rng) : readLetterItem(t, pool, rng)
  })
}

export function falseFriendRound(rng: Rng): ChoiceItem[] {
  return shuffle(FALSE_FRIENDS, rng).map((l) => falseFriendItem(l, rng))
}

/** Builder words, those spelled only with known letters first. */
export function builderQueue({ save, rng }: QueueOptions, n: number = SESSION_LENGTH.builder): BuilderItem[] {
  const known = new Set(practicePool(save))
  const words = BUILDER_WORDS.map((w) => WORD_BY_TEXT.get(w)!)
  const unknownCount = (w: Word) => lettersInWord(w.word).filter((l) => !known.has(l)).length
  const ordered = shuffle(words, rng).sort((a, b) => unknownCount(a) - unknownCount(b))
  return ordered.slice(0, n).map((w) => builderItem(w, rng))
}

/**
 * Daily review: one item per due letter, rotating through every mode's item
 * type. With nothing due, it practises the weakest letters instead.
 */
export function reviewQueue({ save, now, rng }: QueueOptions, max: number = SESSION_LENGTH.review): { items: Item[]; dueCount: number } {
  const pool = practicePool(save)
  const due = pool
    .filter((l) => isDue(save.letters[l.id], now))
    .sort((a, b) => save.letters[a.id].due - save.letters[b.id].due)
  const targets = due.length ? due.slice(0, max) : sampleTargets(save, pool, Math.min(10, pool.length * 2), now, rng)
  const known = new Set(pool)
  const builderWords = BUILDER_WORDS.map((w) => WORD_BY_TEXT.get(w)!).filter((w) => lettersInWord(w.word).every((l) => known.has(l)))
  const items = shuffle(targets, rng).map((t, i): Item => {
    const kinds: ItemKind[] = ['listen', 'read-letter']
    if (readableWords(save, t).length) kinds.push('read-word')
    if (t.falseFriend) kinds.push('false-friend')
    const bw = builderWords.filter((w) => lettersInWord(w.word).includes(t))
    if (bw.length) kinds.push('builder')
    const kind = kinds[(i + Math.floor(rng() * kinds.length)) % kinds.length]
    switch (kind) {
      case 'read-letter':
        return readLetterItem(t, pool, rng)
      case 'read-word':
        return readWordItem(pick(readableWords(save, t), rng), t, rng)
      case 'false-friend':
        return falseFriendItem(t, rng)
      case 'builder':
        return builderItem(pick(bw, rng), rng)
      default:
        return listenItem(t, pool, rng)
    }
  })
  return { items, dueCount: due.length }
}

/** Unlocked letters that still need their Learn card, in teaching order. */
export function lettersToLearn(save: SaveData, unlocked: readonly string[]): Letter[] {
  return unlocked
    .map((id) => LETTER_BY_ID.get(id)!)
    .filter((l) => save.letters[l.id]?.introducedAt == null)
    .sort(byTeachingOrder)
}
