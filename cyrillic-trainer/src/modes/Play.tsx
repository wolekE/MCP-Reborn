import { useEffect, useRef } from 'react'
import { Drill } from '../components/Drill'
import { LETTER_BY_ID, type Letter } from '../data/letters'
import { href } from '../router'
import {
  FALSE_FRIENDS,
  builderQueue,
  falseFriendRound,
  listenQueue,
  practicePool,
  readQueue,
  reviewQueue,
} from '../session/items'
import type { Rng } from '../session/rng'
import { useStore } from '../state/store'

export const MODES = {
  listen: { title: 'Listen & Pick', blurb: 'Hear a syllable, pick the letter.' },
  read: { title: 'Read', blurb: 'See a letter or word, pick how it sounds.' },
  'false-friends': { title: 'False Friends', blurb: '45 seconds, rapid fire: В Е Н Р С У Х — what do they really say?' },
  builder: { title: 'Word Builder', blurb: 'Hear a word, tap its letters in order.' },
  review: { title: 'Daily review', blurb: 'Everything that’s due, across all modes.' },
} as const

export type PlayMode = keyof typeof MODES

const FALSE_FRIENDS_SECONDS = 45

/** Routes #/play/<mode>[/<letter ids>] to a drill round. */
export function Play({ mode, focus }: { mode?: string; focus?: string }) {
  const { save } = useStore()
  // Queues are built from the latest progress each time a round (re)starts.
  const saveRef = useRef(save)
  useEffect(() => {
    saveRef.current = save
  })
  const pool = practicePool(save)
  const focusLetters = focus
    ?.split(',')
    .map((id) => LETTER_BY_ID.get(id))
    .filter((l): l is Letter => !!l)
  const opts = (rng: Rng) => ({ save: saveRef.current, now: Date.now(), rng, focus: focusLetters?.length ? focusLetters : undefined })

  if (!(mode && mode in MODES)) {
    return (
      <div className="card">
        <h1>Unknown mode</h1>
        <a className="btn" href={href('modes')}>
          Choose a mode
        </a>
      </div>
    )
  }
  const m = mode as PlayMode
  const needsLetters = m !== 'false-friends' && m !== 'builder'
  if (needsLetters && pool.length === 0) return <NeedLetters />

  switch (m) {
    case 'listen':
      return <Drill title={MODES.listen.title} pool={pool} start={(rng) => listenQueue(opts(rng))} />
    case 'read':
      return <Drill title={MODES.read.title} pool={pool} start={(rng) => readQueue(opts(rng))} />
    case 'false-friends':
      return (
        <Drill
          title={MODES['false-friends'].title}
          pool={FALSE_FRIENDS}
          timeLimitSec={FALSE_FRIENDS_SECONDS}
          start={falseFriendRound}
          more={falseFriendRound}
        />
      )
    case 'builder':
      return <Drill title={MODES.builder.title} pool={pool} start={(rng) => builderQueue(opts(rng))} />
    case 'review':
      return <Drill title={MODES.review.title} pool={pool} start={(rng) => reviewQueue(opts(rng)).items} />
  }
}

function NeedLetters() {
  return (
    <div className="card stack" style={{ textAlign: 'center' }}>
      <h1>Meet some letters first</h1>
      <p className="muted">This mode practises letters you’ve already seen on a Learn card.</p>
      <div className="row" style={{ justifyContent: 'center' }}>
        <a className="btn btn-primary btn-big" href={href('learn')}>
          Start learning
        </a>
      </div>
    </div>
  )
}
