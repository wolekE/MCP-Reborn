import { useEffect, useState } from 'react'
import { player, type PlayOutcome } from '../audio/player'
import type { ClipId } from '../data/letters'

/**
 * Plays clips whenever `key` changes (auto-play). If the browser blocks autoplay,
 * returns `blocked: true` so the caller can show a "tap to play" prompt.
 */
export function useAutoPlay(clips: readonly ClipId[] | null, key: string): { blocked: boolean; replay: () => void } {
  const [blocked, setBlocked] = useState(false)
  useEffect(() => {
    if (!clips) return
    let live = true
    setBlocked(false)
    player.play(clips).then((r: PlayOutcome) => {
      if (live && r === 'blocked') setBlocked(true)
    })
    return () => {
      live = false
    }
    // `key` identifies the item; clips are derived from it.
  }, [key])
  return {
    blocked,
    replay: () => {
      setBlocked(false)
      if (clips) void player.play(clips)
    },
  }
}
