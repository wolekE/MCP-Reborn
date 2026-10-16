/** The drill modes: titles and one-line blurbs shared by the mode picker and the drills. */
export const MODES = {
  listen: { title: 'Listen & Pick', blurb: 'Hear a syllable, pick the letter.' },
  read: { title: 'Read', blurb: 'See a letter or word, pick how it sounds.' },
  'false-friends': { title: 'False Friends', blurb: '45 seconds, rapid fire: В Е Н Р С У Х — what do they really say?' },
  builder: { title: 'Word Builder', blurb: 'Hear a word, tap its letters in order.' },
  review: { title: 'Daily review', blurb: 'Everything that’s due, across all modes.' },
} as const

export type PlayMode = keyof typeof MODES
