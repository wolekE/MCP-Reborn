/** Session queue helpers (pure). */

/** How many other items come between a miss and its retry. */
export const RETRY_GAP = 2
/** A single item can come back at most this many times per session. */
export const MAX_RETRIES = 2

/**
 * Returns a new queue with `retry` inserted so that exactly `gap` items sit
 * between position `index` (the item just missed) and the retry. Near the end
 * of the queue the retry simply goes last.
 */
export function insertRetry<T>(queue: readonly T[], index: number, retry: T, gap = RETRY_GAP): T[] {
  const at = Math.min(index + 1 + gap, queue.length)
  return [...queue.slice(0, at), retry, ...queue.slice(at)]
}
