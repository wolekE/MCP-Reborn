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

export function navigate(path: string) {
  window.location.hash = `/${path}`
}
