import { useEffect, useRef, useState, type ReactNode } from 'react'
import { player } from '../audio/player'
import type { ClipId } from '../data/letters'

interface Props {
  clips: ClipId | readonly ClipId[]
  children: ReactNode
  className?: string
  title?: string
}

/** A button that plays one clip (or a sequence) and shows when it's playing. */
export function AudioButton({ clips, children, className = '', title }: Props) {
  const [playing, setPlaying] = useState(false)
  const alive = useRef(true)
  useEffect(() => () => void (alive.current = false), [])
  const onClick = async () => {
    setPlaying(true)
    await player.play(clips)
    if (alive.current) setPlaying(false)
  }
  return (
    <button type="button" className={`btn ${playing ? 'playing' : ''} ${className}`} onClick={onClick} title={title}>
      <span aria-hidden="true">🔊</span>
      {children}
    </button>
  )
}
