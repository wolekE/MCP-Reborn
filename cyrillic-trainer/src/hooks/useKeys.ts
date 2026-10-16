import { useEffect, useLayoutEffect, useRef } from 'react'
import { player } from '../audio/player'

type KeyMap = Partial<Record<string, (e: KeyboardEvent) => void>>

function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null
  if (!el) return false
  const tag = el.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable
}

/**
 * Global keyboard shortcuts while a component is mounted. Keys are matched on
 * `event.key` ('1'…'4', 'Enter', 'Escape', ' ' …). The latest handlers are
 * always used, so callers can pass inline closures.
 */
export function useKeys(map: KeyMap, enabled = true): void {
  const ref = useRef(map)
  useLayoutEffect(() => {
    ref.current = map
  })
  useEffect(() => {
    if (!enabled) return
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || e.repeat || isTyping(e.target)) return
      const fn = ref.current[e.key]
      if (fn) {
        e.preventDefault()
        fn(e)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [enabled])
}

/** Space replays the current audio (instead of pressing the focused button). */
export function useSpaceReplay(enabled = true): void {
  useKeys({ ' ': () => void player.replay() }, enabled)
}
