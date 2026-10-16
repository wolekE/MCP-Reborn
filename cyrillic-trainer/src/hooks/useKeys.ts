import { useEffect, useLayoutEffect, useRef } from 'react'
import { player } from '../audio/player'

/** Return `false` when the key did nothing, so the browser's default isn't suppressed. */
type KeyMap = Partial<Record<string, (e: KeyboardEvent) => unknown>>

const INTERACTIVE = 'a[href], button, summary, select, textarea, input, [role="button"], [role="link"], [role="radio"], [role="switch"]'

function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null
  if (!el) return false
  const tag = el.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable
}

/**
 * Global keyboard shortcuts while a component is mounted. Keys are matched on
 * `event.key` ('1'…'4', 'Enter', ' ' …). The latest handlers are always used,
 * so callers can pass inline closures.
 *
 * Enter on a focused link or button keeps its native meaning (activate *that*
 * control); the shortcut only applies when focus is elsewhere. Primary buttons
 * that should answer to Enter are auto-focused instead.
 */
export function useKeys(map: KeyMap, enabled = true): void {
  const ref = useRef(map)
  useLayoutEffect(() => {
    ref.current = map
  })
  useEffect(() => {
    if (!enabled) return
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || e.repeat || e.defaultPrevented || isTyping(e.target)) return
      if (e.key === 'Enter' && (e.target as Element | null)?.closest?.(INTERACTIVE)) return
      const fn = ref.current[e.key]
      if (fn && fn(e) !== false) e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [enabled])
}

/** Space replays the last sound (instead of pressing the focused button). */
export function useSpaceReplay(enabled = true): void {
  useKeys({ ' ': () => void player.replay() }, enabled)
}
