import { useState } from 'react'
import { LetterCard } from '../components/LetterCard'
import { GROUPS, LETTER_BY_ID, type Letter } from '../data/letters'
import { href, navigate } from '../router'
import { lettersToLearn } from '../session/items'
import { unlockedIds } from '../srs/scheduler'
import { useStore } from '../state/store'

/** Learn: one big card at a time. With a letter id, shows just that letter (from the progress map). */
export function Learn({ letterId }: { letterId?: string }) {
  return letterId ? <SingleCard id={letterId} /> : <LearnSession />
}

function LearnSession() {
  const store = useStore()
  // Snapshot at start so introducing letters doesn't change the list mid-session.
  const [letters] = useState(() => lettersToLearn(store.save, unlockedIds(store.save.unlockedBatches)))
  const [index, setIndex] = useState(0)
  const [done, setDone] = useState(false)

  if (letters.length === 0) return <NothingNew />
  if (done) return <LearnDone letters={letters} />

  const letter = letters[index]
  const gotIt = () => {
    store.introduce([letter.id])
    if (index + 1 < letters.length) setIndex(index + 1)
    else {
      store.completeSession()
      setDone(true)
    }
  }
  return (
    <div className="stack">
      <div className="progress" aria-hidden="true">
        <span style={{ width: `${(index / letters.length) * 100}%` }} />
      </div>
      <LetterCard
        key={letter.id}
        letter={letter}
        position={`${index + 1} / ${letters.length}`}
        primaryLabel={index + 1 < letters.length ? 'Got it' : 'Finish'}
        onPrimary={gotIt}
        onBack={index > 0 ? () => setIndex(index - 1) : undefined}
      />
    </div>
  )
}

function LearnDone({ letters }: { letters: Letter[] }) {
  return (
    <div className="card stack" style={{ textAlign: 'center' }} data-testid="learn-done">
      <h1>Nice work!</h1>
      <p>
        You met{' '}
        <span className="glyph-print" lang="ru" style={{ fontSize: '1.6rem' }}>
          {letters.map((l) => l.upper).join(' ')}
        </span>
      </p>
      <p className="muted">Now lock them in: hear a sound, pick the letter.</p>
      <div className="row" style={{ justifyContent: 'center' }}>
        <a className="btn btn-primary btn-big" href={href(`play/listen/${letters.map((l) => l.id).join(',')}`)}>
          Practise them now
        </a>
        <a className="btn" href={href('')}>
          Home
        </a>
      </div>
    </div>
  )
}

function NothingNew() {
  return (
    <div className="card stack" style={{ textAlign: 'center' }}>
      <h1>All caught up</h1>
      <p className="muted">
        You’ve met every unlocked letter. New ones unlock when your current group averages 80% or better — keep practising!
      </p>
      <div className="row" style={{ justifyContent: 'center' }}>
        <a className="btn btn-primary" href={href('session')}>
          Practise
        </a>
        <a className="btn" href={href('')}>
          Progress map
        </a>
      </div>
    </div>
  )
}

function SingleCard({ id }: { id: string }) {
  const store = useStore()
  const letter = LETTER_BY_ID.get(id)
  if (!letter) {
    return (
      <div className="card">
        <h1>Unknown letter</h1>
        <a className="btn" href={href('')}>
          Home
        </a>
      </div>
    )
  }
  const unlocked = unlockedIds(store.save.unlockedBatches).includes(id)
  const introduced = store.save.letters[id]?.introducedAt != null
  const onPrimary = () => {
    if (unlocked && !introduced) store.introduce([id])
    navigate('')
  }
  const banner = !unlocked ? (
    <p className="learn-banner">
      Preview — this letter unlocks with group {letter.group} ({GROUPS[letter.group].title}). Keep practising to open it.
    </p>
  ) : null
  return (
    <LetterCard
      letter={letter}
      banner={banner}
      primaryLabel={unlocked && !introduced ? 'Got it' : 'Back to map'}
      onPrimary={onPrimary}
    />
  )
}
