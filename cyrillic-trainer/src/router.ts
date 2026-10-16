import { useSyncExternalStore } from 'react'

/** Hash routing (#/learn/zh): works from any static host or folder with no server config. */
function subscribe(cb: () => void) {
  window.addEventListener('hashchange', cb)
  return () => window.removeEventListener('hashchange', cb)
}

const current = () => window.location.hash.replace(/^#\/?/, '')

/** Current route as path segments, e.g. ['learn', 'zh']. */
export function useRoute(): string[] {
  const path = useSyncExternalStore(subscribe, current, () => '')
  return path.split('/').filter(Boolean).map(decodeURIComponent)
}

export const href = (path: string) => `#/${path}`

/** Go to a route. `replace` swaps the current history entry (for redirects, so Back doesn't bounce). */
export function navigate(path: string, { replace = false } = {}) {
  if (replace) window.location.replace(`#/${path}`)
  else window.location.hash = `/${path}`
}
