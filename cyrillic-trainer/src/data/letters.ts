/**
 * Single source of truth for everything the trainer teaches: the 33 letters,
 * the extra drill words, and (derived from both) the audio clip registry that
 * scripts/generate_audio.py turns into MP3s.
 *
 * Conventions
 * - `id` is an ASCII slug used in URLs, storage keys and clip ids.
 * - Clip ids are ASCII and double as file names: public/audio/<voice>/<clipId>.mp3
 * - `stressed` strings mark the stressed vowel with U+0301 (combining acute).
 *   Ё is always stressed, so it never carries an extra mark.
 */

export type GroupId = 1 | 2 | 3 | 4 | 5
export type LetterKind = 'vowel' | 'consonant' | 'sign'
export type ClipId = string

export interface LetterAudio {
  /** Speaks the letter's Russian name, e.g. "бэ". */
  readonly name: ClipId
  /** A syllable carrying the sound (e.g. "ба"). Absent for Ъ and Ь. */
  readonly syllable?: ClipId
  /** Speaks the example word. */
  readonly word: ClipId
  /** Ъ / Ь only: minimal pair, word without the sign then with it (мат → мать). */
  readonly contrast?: readonly [plain: ClipId, marked: ClipId]
}

export interface ExampleWord {
  readonly word: string
  readonly stressed: string
  readonly en: string
  /** Polish translation or cognate, shown next to the English one. */
  readonly pl: string
}

export interface FalseFriend {
  /** The Latin letter it looks like. */
  readonly looksLike: string
  /** What an English/Polish reader wrongly says, as sound labels. */
  readonly wrongSounds: readonly string[]
}

export interface Letter {
  readonly id: string
  readonly upper: string
  readonly lower: string
  /** Rendered in the cursive font (upper + lower). */
  readonly cursive: string
  /** Where handwritten shape differs from print in a way that trips learners. */
  readonly cursiveNote?: string
  /** Russian letter name, as spoken. */
  readonly name: string
  /** English gloss of the name where it means something (signs, short i). */
  readonly nameGloss?: string
  readonly ipa: string
  /** Short, unique Latin sound label: answer option in Read / False Friends. */
  readonly sound: string
  readonly hintEn: string
  readonly hintPl: string
  readonly group: GroupId
  readonly kind: LetterKind
  /** Text of the syllable clip (absent for Ъ / Ь). */
  readonly syllableText?: string
  /** Ъ / Ь: spelling of the minimal pair, matching audio.contrast. */
  readonly contrastText?: readonly [plain: string, marked: string]
  /** What the TTS says for the name clip, when the bare name can't be synthesized faithfully. */
  readonly nameTts?: string
  /** Shown beside the Name button when nameTts differs from the name. */
  readonly nameAudioNote?: string
  readonly example: ExampleWord
  readonly audio: LetterAudio
  /** Uppercase letters commonly confused with this one, most confusable first. */
  readonly confusables: readonly string[]
  readonly falseFriend?: FalseFriend
}

export interface Word {
  readonly word: string
  readonly stressed: string
  readonly en: string
  readonly pl: string
  readonly audio: ClipId
}

export const GROUPS: Readonly<Record<GroupId, { title: string; blurb: string }>> = {
  1: { title: 'True friends', blurb: 'Look and sound like their Latin twins.' },
  2: { title: 'False friends', blurb: 'Look Latin, sound different. Don’t trust them!' },
  3: { title: 'New shapes, familiar sounds', blurb: 'Strange letters for sounds you already know.' },
  4: { title: 'Sounds English lacks', blurb: 'Polish has most of these. Lucky you.' },
  5: { title: 'Iotated vowels and signs', blurb: 'A built-in “y”, plus two silent signs.' },
}

/** Teaching order inside each group, as specified. */
export const GROUP_ORDER: Readonly<Record<GroupId, readonly string[]>> = {
  1: ['А', 'К', 'М', 'О', 'Т'],
  2: ['В', 'Е', 'Н', 'Р', 'С', 'У', 'Х'],
  3: ['Б', 'Г', 'Д', 'З', 'И', 'Й', 'Л', 'П', 'Ф', 'Э'],
  4: ['Ж', 'Ц', 'Ч', 'Ш', 'Щ', 'Ы'],
  5: ['Ё', 'Ю', 'Я', 'Ъ', 'Ь'],
}

/** All 33 letters in alphabetical order. */
export const LETTERS: readonly Letter[] = [
  {
    id: 'a', upper: 'А', lower: 'а', cursive: 'Аа',
    name: 'а', ipa: 'a', sound: 'a', group: 1, kind: 'vowel',
    hintEn: 'Like “a” in “father”. When unstressed it gets shorter and lazier.',
    hintPl: 'Same as Polish a.',
    syllableText: 'ма',
    example: { word: 'арбуз', stressed: 'арбу́з', en: 'watermelon', pl: 'arbuz' },
    audio: { name: 'name-a', syllable: 'syl-ma', word: 'word-arbuz' },
    confusables: ['Я', 'О', 'Д'],
  },
  {
    id: 'b', upper: 'Б', lower: 'б', cursive: 'Бб',
    cursiveNote: 'Lowercase б looks like the digit 6.',
    name: 'бэ', ipa: 'b ~ bʲ', sound: 'b', group: 3, kind: 'consonant',
    hintEn: 'Like “b” in “bat”. Not to be confused with В, which looks like B but says v.',
    hintPl: 'Polish b.',
    syllableText: 'ба',
    example: { word: 'банан', stressed: 'бана́н', en: 'banana', pl: 'banan' },
    audio: { name: 'name-b', syllable: 'syl-ba', word: 'word-banan' },
    confusables: ['В', 'Ь', 'П'],
  },
  {
    id: 'v', upper: 'В', lower: 'в', cursive: 'Вв',
    name: 'вэ', ipa: 'v ~ vʲ', sound: 'v', group: 2, kind: 'consonant',
    hintEn: 'Looks like B, but sounds like “v” in “van”.',
    hintPl: 'Polish w: вода = woda.',
    syllableText: 'ва',
    example: { word: 'вода', stressed: 'вода́', en: 'water', pl: 'woda' },
    audio: { name: 'name-v', syllable: 'syl-va', word: 'word-voda' },
    confusables: ['Б', 'Ф'],
    falseFriend: { looksLike: 'B', wrongSounds: ['b'] },
  },
  {
    id: 'g', upper: 'Г', lower: 'г', cursive: 'Гг',
    cursiveNote: 'Handwritten г is a small curl, a bit like a backwards s.',
    name: 'гэ', ipa: 'ɡ ~ ɡʲ', sound: 'g', group: 3, kind: 'consonant',
    hintEn: 'Hard “g” as in “go”. One exception: in the ending -ого / -его it is read as v (его ≈ “yevo”).',
    hintPl: 'Polish g — never h as in Ukrainian.',
    syllableText: 'га',
    example: { word: 'гора', stressed: 'гора́', en: 'mountain', pl: 'góra' },
    audio: { name: 'name-g', syllable: 'syl-ga', word: 'word-gora' },
    confusables: ['К', 'Т', 'П'],
  },
  {
    id: 'd', upper: 'Д', lower: 'д', cursive: 'Дд',
    cursiveNote: 'Handwritten д looks like a Latin g.',
    name: 'дэ', ipa: 'd ~ dʲ', sound: 'd', group: 3, kind: 'consonant',
    hintEn: 'Like “d” in “dog”, with the tongue touching the teeth. Shaped like a little house.',
    hintPl: 'Polish d.',
    syllableText: 'да',
    example: { word: 'дом', stressed: 'дом', en: 'house', pl: 'dom' },
    audio: { name: 'name-d', syllable: 'syl-da', word: 'word-dom' },
    confusables: ['Т', 'Л', 'А'],
  },
  {
    id: 'ye', upper: 'Е', lower: 'е', cursive: 'Ее',
    name: 'е', ipa: 'je ~ ʲe', sound: 'ye', group: 2, kind: 'vowel',
    hintEn: 'Looks like E but says “ye” as in “yes”. After a consonant it softens it: нет ≈ “nyet”.',
    hintPl: 'Polish je at the start of a word, ie after a consonant: нет ≈ niet.',
    syllableText: 'ме',
    example: { word: 'ем', stressed: 'ем', en: '(I) eat', pl: 'jem' },
    audio: { name: 'name-ye', syllable: 'syl-mye', word: 'word-yem' },
    confusables: ['Ё', 'Э'],
    falseFriend: { looksLike: 'E', wrongSounds: ['e'] },
  },
  {
    id: 'yo', upper: 'Ё', lower: 'ё', cursive: 'Ёё',
    name: 'ё', ipa: 'jo ~ ʲo', sound: 'yo', group: 5, kind: 'vowel',
    hintEn: '“yo” as in “yogurt”. Always stressed. Books often print it as plain е.',
    hintPl: 'Polish jo / io, always a clear o: ёж ≈ joż (Polish: jeż), мёд ≈ miot (Polish: miód).',
    syllableText: 'мё',
    example: { word: 'ёж', stressed: 'ёж', en: 'hedgehog', pl: 'jeż' },
    audio: { name: 'name-yo', syllable: 'syl-myo', word: 'word-yozh' },
    confusables: ['Е', 'Э', 'Ю'],
  },
  {
    id: 'zh', upper: 'Ж', lower: 'ж', cursive: 'Жж',
    name: 'жэ', ipa: 'ʐ', sound: 'zh', group: 4, kind: 'consonant',
    hintEn: 'Like the “s” in “pleasure”, but with the tongue pulled back. Always hard.',
    hintPl: 'Polish ż / rz: жук = żuk.',
    syllableText: 'жа',
    example: { word: 'жук', stressed: 'жук', en: 'beetle', pl: 'żuk' },
    audio: { name: 'name-zh', syllable: 'syl-zha', word: 'word-zhuk' },
    confusables: ['Х', 'Ш', 'З'],
  },
  {
    id: 'z', upper: 'З', lower: 'з', cursive: 'Зз',
    name: 'зэ', ipa: 'z ~ zʲ', sound: 'z', group: 3, kind: 'consonant',
    hintEn: 'Like “z” in “zoo”. Looks like the digit 3.',
    hintPl: 'Polish z: зима = zima.',
    syllableText: 'за',
    example: { word: 'зима', stressed: 'зима́', en: 'winter', pl: 'zima' },
    audio: { name: 'name-z', syllable: 'syl-za', word: 'word-zima' },
    confusables: ['Э', 'С', 'Ж'],
  },
  {
    id: 'i', upper: 'И', lower: 'и', cursive: 'Ии',
    cursiveNote: 'Handwritten и looks like a Latin u.',
    name: 'и', ipa: 'i', sound: 'i', group: 3, kind: 'vowel',
    hintEn: '“ee” as in “meet”. Looks like a backwards N. Softens the consonant before it.',
    hintPl: 'Polish i — and like Polish it softens the consonant before it: ни ≈ ni.',
    syllableText: 'ми',
    example: { word: 'игра', stressed: 'игра́', en: 'game', pl: 'gra' },
    audio: { name: 'name-i', syllable: 'syl-mi', word: 'word-igra' },
    confusables: ['Й', 'Ы', 'Н'],
  },
  {
    id: 'j', upper: 'Й', lower: 'й', cursive: 'Йй',
    cursiveNote: 'Handwritten й looks like ŭ.',
    name: 'и краткое', nameGloss: 'short i', ipa: 'j', sound: 'j', group: 3, kind: 'consonant',
    hintEn: 'A short glide like the “y” in “boy”. Mostly after vowels: май, мой.',
    hintPl: 'Polish j: май = maj, мой ≈ moj (Polish: mój — but with a clear o).',
    syllableText: 'ай',
    example: { word: 'май', stressed: 'май', en: 'May', pl: 'maj' },
    audio: { name: 'name-j', syllable: 'syl-aj', word: 'word-maj' },
    confusables: ['И', 'Ы'],
  },
  {
    id: 'k', upper: 'К', lower: 'к', cursive: 'Кк',
    name: 'ка', ipa: 'k ~ kʲ', sound: 'k', group: 1, kind: 'consonant',
    hintEn: 'Like “k” in “skin” — without the puff of air English puts after k.',
    hintPl: 'Polish k.',
    syllableText: 'ка',
    example: { word: 'кот', stressed: 'кот', en: 'cat', pl: 'kot' },
    audio: { name: 'name-k', syllable: 'syl-ka', word: 'word-kot' },
    confusables: ['Г', 'Х', 'Ж'],
  },
  {
    id: 'l', upper: 'Л', lower: 'л', cursive: 'Лл',
    name: 'эль', ipa: 'ɫ ~ lʲ', sound: 'l', group: 3, kind: 'consonant',
    hintEn: 'Usually a “dark” l as in “full”. Before е, ё, и, ю, я or ь it is a light l as in “leaf”.',
    hintPl: 'Soft ль ≈ Polish l (лес ≈ les; Polish: las). Hard л is the old “dark ł” — never the modern w-like ł.',
    syllableText: 'ла',
    example: { word: 'лампа', stressed: 'ла́мпа', en: 'lamp', pl: 'lampa' },
    audio: { name: 'name-l', syllable: 'syl-la', word: 'word-lampa' },
    confusables: ['П', 'Д', 'Я'],
  },
  {
    id: 'm', upper: 'М', lower: 'м', cursive: 'Мм',
    cursiveNote: 'Handwritten м starts with a little hook — don’t mix it up with handwritten т, which looks like m.',
    name: 'эм', ipa: 'm ~ mʲ', sound: 'm', group: 1, kind: 'consonant',
    hintEn: 'Like “m”. Lowercase м is a small capital M, not an m-shape.',
    hintPl: 'Polish m.',
    syllableText: 'ма',
    example: { word: 'мама', stressed: 'ма́ма', en: 'mum', pl: 'mama' },
    audio: { name: 'name-m', syllable: 'syl-ma', word: 'word-mama' },
    confusables: ['Т', 'Н', 'Л'],
  },
  {
    id: 'n', upper: 'Н', lower: 'н', cursive: 'Нн',
    name: 'эн', ipa: 'n ~ nʲ', sound: 'n', group: 2, kind: 'consonant',
    hintEn: 'Looks like H, but sounds like “n” in “no”.',
    hintPl: 'Polish n; before е, ё, и, ю, я or ь it turns soft, like ń.',
    syllableText: 'на',
    example: { word: 'нос', stressed: 'нос', en: 'nose', pl: 'nos' },
    audio: { name: 'name-n', syllable: 'syl-na', word: 'word-nos' },
    confusables: ['П', 'И', 'Ч'],
    falseFriend: { looksLike: 'H', wrongSounds: ['h'] },
  },
  {
    id: 'o', upper: 'О', lower: 'о', cursive: 'Оо',
    name: 'о', ipa: 'o (unstressed ɐ, ə)', sound: 'o', group: 1, kind: 'vowel',
    hintEn: 'Stressed: “o” as in “more”. Unstressed it sounds like a: молоко ≈ “malako”.',
    hintPl: 'Stressed = Polish o. Unstressed it sounds like a: окно ≈ akno.',
    syllableText: 'мо',
    example: { word: 'окно', stressed: 'окно́', en: 'window', pl: 'okno' },
    audio: { name: 'name-o', syllable: 'syl-mo', word: 'word-okno' },
    confusables: ['А', 'Ё', 'С'],
  },
  {
    id: 'p', upper: 'П', lower: 'п', cursive: 'Пп',
    cursiveNote: 'Handwritten п looks like a Latin n.',
    name: 'пэ', ipa: 'p ~ pʲ', sound: 'p', group: 3, kind: 'consonant',
    hintEn: 'Like “p” in “spin” (no puff of air). Shaped like the Greek π.',
    hintPl: 'Polish p.',
    syllableText: 'па',
    example: { word: 'папа', stressed: 'па́па', en: 'dad', pl: 'tata (careful: Polish “papa” = bye-bye)' },
    audio: { name: 'name-p', syllable: 'syl-pa', word: 'word-papa' },
    confusables: ['Н', 'Р', 'Л'],
  },
  {
    id: 'r', upper: 'Р', lower: 'р', cursive: 'Рр',
    name: 'эр', ipa: 'r ~ rʲ', sound: 'r', group: 2, kind: 'consonant',
    hintEn: 'Looks like P, but it is a rolled (trilled) r.',
    hintPl: 'Polish r — rolled, exactly like in “rower”.',
    syllableText: 'ра',
    example: { word: 'рука', stressed: 'рука́', en: 'hand, arm', pl: 'ręka' },
    audio: { name: 'name-r', syllable: 'syl-ra', word: 'word-ruka' },
    confusables: ['П', 'Я'],
    falseFriend: { looksLike: 'P', wrongSounds: ['p'] },
  },
  {
    id: 's', upper: 'С', lower: 'с', cursive: 'Сс',
    name: 'эс', ipa: 's ~ sʲ', sound: 's', group: 2, kind: 'consonant',
    hintEn: 'Looks like C, but it is always “s” as in “sun” — never k.',
    hintPl: 'Polish s — never c (ts)! сок = sok.',
    syllableText: 'са',
    example: { word: 'сок', stressed: 'сок', en: 'juice', pl: 'sok' },
    audio: { name: 'name-s', syllable: 'syl-sa', word: 'word-sok' },
    confusables: ['З', 'Ц', 'Э'],
    falseFriend: { looksLike: 'C', wrongSounds: ['k', 'ts'] },
  },
  {
    id: 't', upper: 'Т', lower: 'т', cursive: 'Тт',
    cursiveNote: 'Handwritten т looks like a Latin m — the classic trap.',
    name: 'тэ', ipa: 't ~ tʲ', sound: 't', group: 1, kind: 'consonant',
    hintEn: 'Like “t” in “stop”, with the tongue touching the teeth.',
    hintPl: 'Polish t.',
    syllableText: 'та',
    example: { word: 'торт', stressed: 'торт', en: 'cake', pl: 'tort' },
    audio: { name: 'name-t', syllable: 'syl-ta', word: 'word-tort' },
    confusables: ['Г', 'Д', 'М'],
  },
  {
    id: 'u', upper: 'У', lower: 'у', cursive: 'Уу',
    name: 'у', ipa: 'u', sound: 'u', group: 2, kind: 'vowel',
    hintEn: 'Looks like y, but says “oo” as in “boot”.',
    hintPl: 'Polish u / ó: ухо = ucho.',
    syllableText: 'му',
    example: { word: 'ухо', stressed: 'у́хо', en: 'ear', pl: 'ucho' },
    audio: { name: 'name-u', syllable: 'syl-mu', word: 'word-ukho' },
    confusables: ['Ю', 'Ч', 'О'],
    falseFriend: { looksLike: 'Y', wrongSounds: ['y'] },
  },
  {
    id: 'f', upper: 'Ф', lower: 'ф', cursive: 'Фф',
    name: 'эф', ipa: 'f ~ fʲ', sound: 'f', group: 3, kind: 'consonant',
    hintEn: 'Like “f” in “fun”. A circle on a stick, like the Greek φ.',
    hintPl: 'Polish f.',
    syllableText: 'фа',
    example: { word: 'фото', stressed: 'фо́то', en: 'photo', pl: 'zdjęcie (foto)' },
    audio: { name: 'name-f', syllable: 'syl-fa', word: 'word-foto' },
    confusables: ['В', 'О'],
  },
  {
    id: 'kh', upper: 'Х', lower: 'х', cursive: 'Хх',
    name: 'ха', ipa: 'x ~ xʲ', sound: 'kh', group: 2, kind: 'consonant',
    hintEn: 'Looks like X, but it is a throaty “kh” as in Scottish “loch” — never ks.',
    hintPl: 'Polish ch / h: хлеб = chleb.',
    syllableText: 'ха',
    example: { word: 'хлеб', stressed: 'хлеб', en: 'bread', pl: 'chleb' },
    audio: { name: 'name-kh', syllable: 'syl-kha', word: 'word-khleb' },
    confusables: ['Ж', 'К'],
    falseFriend: { looksLike: 'X', wrongSounds: ['ks'] },
  },
  {
    id: 'ts', upper: 'Ц', lower: 'ц', cursive: 'Цц',
    name: 'цэ', ipa: 't͡s', sound: 'ts', group: 4, kind: 'consonant',
    hintEn: '“ts” as in “cats”, said as one sound. Always hard: ци is never “tsee” — the и comes out like the “i” in “bit”.',
    hintPl: 'Polish c: цирк = cyrk, улица = ulica.',
    syllableText: 'ца',
    example: { word: 'цирк', stressed: 'цирк', en: 'circus', pl: 'cyrk' },
    audio: { name: 'name-ts', syllable: 'syl-tsa', word: 'word-tsirk' },
    confusables: ['Щ', 'Ч', 'С'],
  },
  {
    id: 'ch', upper: 'Ч', lower: 'ч', cursive: 'Чч',
    name: 'че', ipa: 't͡ɕ', sound: 'ch', group: 4, kind: 'consonant',
    // TTS reads a bare "че" as slang "чё" (what?); the phonetic spelling keeps the е.
    nameTts: 'чэ',
    hintEn: '“ch” as in “cheese”, but always soft — the tongue spreads up against the palate.',
    hintPl: '≈ Polish cz, but softer — somewhere between cz and ć: чай ≈ czaj with a ć-like touch.',
    syllableText: 'ча',
    example: { word: 'чай', stressed: 'чай', en: 'tea', pl: 'herbata (dialect: czaj)' },
    audio: { name: 'name-ch', syllable: 'syl-cha', word: 'word-chaj' },
    confusables: ['Щ', 'Ц', 'У'],
  },
  {
    id: 'sh', upper: 'Ш', lower: 'ш', cursive: 'Шш',
    cursiveNote: 'Handwritten ш looks like an upside-down m (ɯ); people sometimes underline it so it isn’t read as т.',
    name: 'ша', ipa: 'ʂ', sound: 'sh', group: 4, kind: 'consonant',
    hintEn: '“sh” as in “shop”, but harder, with the tongue pulled back. Always hard: ши is never “shee” — its vowel is the duller one, like the “i” in “ship”.',
    hintPl: '≈ Polish sz: школа = szkoła, ши ≈ szy.',
    syllableText: 'ша',
    example: { word: 'школа', stressed: 'шко́ла', en: 'school', pl: 'szkoła' },
    audio: { name: 'name-sh', syllable: 'syl-sha', word: 'word-shkola' },
    confusables: ['Щ', 'Ж', 'Ц'],
  },
  {
    id: 'shch', upper: 'Щ', lower: 'щ', cursive: 'Щщ',
    name: 'ща', ipa: 'ɕː', sound: 'shch', group: 4, kind: 'consonant',
    hintEn: 'A long, soft “sh”, like “fresh sheep” run together. Modern Russian says no “ch” in it.',
    hintPl: '≈ a long, soft śś, as in “wieś śpi”. Older Russian said it like the ść in “jeść” — a soft cousin of Polish szcz (борщ = barszcz).',
    syllableText: 'ща',
    example: { word: 'щётка', stressed: 'щётка', en: 'brush', pl: 'szczotka' },
    audio: { name: 'name-shch', syllable: 'syl-shcha', word: 'word-shchyotka' },
    confusables: ['Ш', 'Ч', 'Ц'],
  },
  {
    id: 'hard', upper: 'Ъ', lower: 'ъ', cursive: 'Ъъ',
    name: 'твёрдый знак', nameGloss: 'hard sign', ipa: '∅', sound: 'ʺ separates', group: 5, kind: 'sign',
    hintEn: 'Silent. It separates a consonant from a following е, ё, ю or я, so you hear a clear “y”: съел ≈ “s-yel”.',
    hintPl: 'Like the break in Polish zjeść / objazd: съел ≈ s-jel, and с stays hard.',
    contrastText: ['сел', 'съел'],
    example: { word: 'съел', stressed: 'съел', en: 'ate (up)', pl: 'zjadł' },
    audio: { name: 'name-hard', word: 'word-sel-hard', contrast: ['word-sel', 'word-sel-hard'] },
    confusables: ['Ь', 'Ы', 'Б'],
  },
  {
    id: 'y', upper: 'Ы', lower: 'ы', cursive: 'Ыы',
    name: 'ы', ipa: 'ɨ', sound: 'y', group: 4, kind: 'vowel',
    // Text-to-speech can't say a bare ы (it comes out as и), and Russian never uses it alone.
    nameTts: 'мы', nameAudioNote: 'heard in мы',
    hintEn: 'No English twin: say “ee” with your tongue pulled back, close to the “i” in “bit”. Never starts a word.',
    hintPl: '≈ Polish y, almost exactly (Russian ы is a touch higher, tongue further back): мы = my, вы = wy, ты = ty, рыба = ryba.',
    syllableText: 'вы',
    example: { word: 'рыба', stressed: 'ры́ба', en: 'fish', pl: 'ryba' },
    audio: { name: 'name-y', syllable: 'syl-vy', word: 'word-ryba' },
    confusables: ['И', 'Ь', 'Ъ', 'Й'],
  },
  {
    id: 'soft', upper: 'Ь', lower: 'ь', cursive: 'Ьь',
    name: 'мягкий знак', nameGloss: 'soft sign', ipa: 'ʲ', sound: 'ʹ softens', group: 5, kind: 'sign',
    hintEn: 'Silent. It softens the consonant before it: arch your tongue toward the roof of your mouth as if a “y” were coming, but add no vowel — мать is one syllable, never “ma-tee”. After ж, ш, ч, щ it changes nothing: мышь sounds like мыш.',
    hintPl: 'Works like the Polish kreska: конь ≈ koń. But ть / дь are not ć / dź — the tongue tip stays at the teeth, so мать ends in a soft t. After ж, ш, ч, щ it softens nothing: мышь = mysz.',
    contrastText: ['мат', 'мать'],
    example: { word: 'мать', stressed: 'мать', en: 'mother', pl: 'matka (old: mać)' },
    audio: { name: 'name-soft', word: 'word-mat-soft', contrast: ['word-mat', 'word-mat-soft'] },
    confusables: ['Ъ', 'Ы', 'Б'],
  },
  {
    id: 'e', upper: 'Э', lower: 'э', cursive: 'Ээ',
    name: 'э', ipa: 'ɛ', sound: 'e', group: 3, kind: 'vowel',
    hintEn: '“e” as in “met” — no “y” in front and no softening. Mostly at the start of words: это.',
    hintPl: 'Polish e: это ≈ eto (Polish: to).',
    syllableText: 'мэ',
    example: { word: 'это', stressed: 'э́то', en: 'this (is)', pl: 'to' },
    audio: { name: 'name-e', syllable: 'syl-me', word: 'word-eto' },
    confusables: ['Е', 'Ё', 'З'],
  },
  {
    id: 'yu', upper: 'Ю', lower: 'ю', cursive: 'Юю',
    name: 'ю', ipa: 'ju ~ ʲu', sound: 'yu', group: 5, kind: 'vowel',
    hintEn: '“yu” as in “you”. After a consonant it softens it.',
    hintPl: 'Polish ju / iu: юг ≈ jug, люк ≈ liuk.',
    syllableText: 'мю',
    example: { word: 'юг', stressed: 'юг', en: 'south', pl: 'południe' },
    audio: { name: 'name-yu', syllable: 'syl-myu', word: 'word-yug' },
    confusables: ['У', 'Я', 'Ё'],
  },
  {
    id: 'ya', upper: 'Я', lower: 'я', cursive: 'Яя',
    name: 'я', ipa: 'ja ~ ʲa', sound: 'ya', group: 5, kind: 'vowel',
    hintEn: '“ya” as in “yard”. On its own it is the word “I”. Looks like a backwards R.',
    hintPl: 'Polish ja / ia — and я = ja, both meaning “I”! яблоко = jabłko.',
    syllableText: 'мя',
    example: { word: 'яблоко', stressed: 'я́блоко', en: 'apple', pl: 'jabłko' },
    audio: { name: 'name-ya', syllable: 'syl-mya', word: 'word-yabloko' },
    confusables: ['А', 'Ю', 'Р'],
  },
]

/**
 * Extra words for Read and Word Builder (and the Ъ/Ь contrast partners).
 * Letter example words are added automatically by ALL_WORDS below.
 */
export const EXTRA_WORDS: readonly Word[] = [
  { word: 'там', stressed: 'там', en: 'there', pl: 'tam', audio: 'word-tam' },
  { word: 'кто', stressed: 'кто', en: 'who', pl: 'kto', audio: 'word-kto' },
  { word: 'мак', stressed: 'мак', en: 'poppy', pl: 'mak', audio: 'word-mak' },
  { word: 'как', stressed: 'как', en: 'how', pl: 'jak', audio: 'word-kak' },
  { word: 'атом', stressed: 'а́том', en: 'atom', pl: 'atom', audio: 'word-atom' },
  { word: 'метро', stressed: 'метро́', en: 'metro', pl: 'metro', audio: 'word-metro' },
  { word: 'вот', stressed: 'вот', en: 'here is', pl: 'oto', audio: 'word-vot' },
  { word: 'нет', stressed: 'нет', en: 'no', pl: 'nie', audio: 'word-net' },
  { word: 'сон', stressed: 'сон', en: 'sleep, dream', pl: 'sen', audio: 'word-son' },
  { word: 'хор', stressed: 'хор', en: 'choir', pl: 'chór', audio: 'word-khor' },
  { word: 'суп', stressed: 'суп', en: 'soup', pl: 'zupa', audio: 'word-sup' },
  { word: 'да', stressed: 'да', en: 'yes', pl: 'tak', audio: 'word-da' },
  { word: 'лес', stressed: 'лес', en: 'forest', pl: 'las', audio: 'word-les' },
  { word: 'мы', stressed: 'мы', en: 'we', pl: 'my', audio: 'word-my' },
  { word: 'щи', stressed: 'щи', en: 'cabbage soup', pl: 'kapuśniak', audio: 'word-shchi' },
  { word: 'мышь', stressed: 'мышь', en: 'mouse', pl: 'mysz', audio: 'word-mysh' },
  { word: 'мат', stressed: 'мат', en: 'checkmate', pl: 'mat', audio: 'word-mat' },
  { word: 'сел', stressed: 'сел', en: 'sat down', pl: 'usiadł', audio: 'word-sel' },
]

/** Word Builder targets, as specified. */
export const BUILDER_WORDS: readonly string[] = ['кот', 'дом', 'мама', 'суп', 'чай', 'жук', 'щи', 'мышь']

// ---------------------------------------------------------------------------
// Derived lookups
// ---------------------------------------------------------------------------

export const LETTER_BY_UPPER: ReadonlyMap<string, Letter> = new Map(LETTERS.map((l) => [l.upper, l]))
export const LETTER_BY_ID: ReadonlyMap<string, Letter> = new Map(LETTERS.map((l) => [l.id, l]))

/** Lower or upper case character → letter. */
export function letterOf(char: string): Letter | undefined {
  return LETTER_BY_UPPER.get(char.toUpperCase())
}

/** Letters in teaching order (group 1 first, spec order inside each group). */
export const TEACHING_ORDER: readonly Letter[] = ([1, 2, 3, 4, 5] as const).flatMap((g) =>
  GROUP_ORDER[g].map((u) => LETTER_BY_UPPER.get(u)!),
)

/** Every word that has a clip: letter examples first, then extras (deduped by spelling). */
export const ALL_WORDS: readonly Word[] = (() => {
  const seen = new Map<string, Word>()
  for (const l of LETTERS) {
    const w: Word = { ...l.example, audio: l.audio.word }
    if (!seen.has(w.word)) seen.set(w.word, w)
  }
  for (const w of EXTRA_WORDS) if (!seen.has(w.word)) seen.set(w.word, w)
  return [...seen.values()]
})()

export const WORD_BY_TEXT: ReadonlyMap<string, Word> = new Map(ALL_WORDS.map((w) => [w.word, w]))

/** The letters a word is spelled with (unique, uppercase). */
export function lettersInWord(word: string): Letter[] {
  const out: Letter[] = []
  for (const ch of word) {
    const l = letterOf(ch)
    if (l && !out.includes(l)) out.push(l)
  }
  return out
}

/**
 * Letter-by-letter Latin rendering using each letter's sound label (signs → ʹ / ʺ).
 * Like standard romanizations, е is "ye" at the start of a word or after a
 * vowel or sign, and plain "e" after a consonant (хлеб → khleb).
 * `override` reads one letter with a different sound (used to build decoys).
 */
export function transliterate(word: string, override?: { letter: Letter; sound: string }): string {
  let out = ''
  let prev: Letter | undefined
  for (const ch of word) {
    const l = letterOf(ch)
    if (!l) out += ch
    else if (override && l === override.letter) out += override.sound
    else if (l.kind === 'sign') out += l.id === 'soft' ? 'ʹ' : 'ʺ'
    else if (l.id === 'ye' && prev?.kind === 'consonant') out += 'e'
    else out += l.sound
    prev = l
  }
  return out
}

// ---------------------------------------------------------------------------
// Audio clip registry (consumed by scripts/export-clips.ts → generate_audio.py)
// ---------------------------------------------------------------------------

export type ClipKind = 'name' | 'syllable' | 'word'

export interface ClipSpec {
  readonly id: ClipId
  /** What the clip says, as shown to the learner (and read by the Web Speech fallback). */
  readonly text: string
  /** What is sent to the TTS (see ttsText). */
  readonly tts: string
  readonly kind: ClipKind
}

const VOWELS = 'аеёиоуыэюя'

/**
 * The text actually sent to the neural TTS for a clip.
 *
 * A lone vowel is read as an unstressed function word ("о" comes out as [ɐ],
 * i.e. "а"), so single-vowel texts get a stress mark: "о" → "о́". Nothing else
 * does: next to a consonant the mark splits the token and the TTS spells the
 * consonant out ("мо́" → "эм-о", "ко́т" → "ко-тэ"). Both effects were measured
 * (vowel formants + speech recognition) on ru-RU-SvetlanaNeural / DmitryNeural.
 */
export function ttsText(text: string): string {
  return text.length === 1 && VOWELS.includes(text) && text !== 'ё' ? `${text}\u0301` : text
}

/** Every clip referenced by the data, deduplicated by id, in a stable order. */
export function buildClipRegistry(): ClipSpec[] {
  const byId = new Map<ClipId, ClipSpec>()
  const add = (id: ClipId, text: string, tts: string, kind: ClipKind) => {
    const prev = byId.get(id)
    if (prev && (prev.text !== text || prev.tts !== tts)) {
      throw new Error(`Clip id "${id}" is used for both "${prev.text}" and "${text}"`)
    }
    if (!prev) byId.set(id, { id, text, tts, kind })
  }
  for (const l of LETTERS) {
    add(l.audio.name, l.name, l.nameTts ?? ttsText(l.name), 'name')
    if (l.audio.syllable) add(l.audio.syllable, l.syllableText!, ttsText(l.syllableText!), 'syllable')
  }
  for (const w of ALL_WORDS) add(w.audio, w.word, ttsText(w.word), 'word')
  return [...byId.values()]
}

export const CLIPS: readonly ClipSpec[] = buildClipRegistry()
export const CLIP_TEXT: ReadonlyMap<ClipId, string> = new Map(CLIPS.map((c) => [c.id, c.text]))
/** What speech engines should say for each clip (see ttsText / nameTts). */
export const CLIP_TTS: ReadonlyMap<ClipId, string> = new Map(CLIPS.map((c) => [c.id, c.tts]))
