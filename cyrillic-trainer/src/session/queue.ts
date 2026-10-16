/** Session queue helpers (pure). */

/** How many other items come between a miss and its retry. */
export const RETRY_GAP = 2
/** A single item can come back at most this many times per session. */
export const MAX_RETRIES = 2

/**
 * Returns a new queue with `retry` inserted so that `gap` items sit between
 * position `index` (the item just missed) and the retry. If fewer than `gap`
 * items follow, the retry simply goes last — use `fillersFor` first to top up.
 */
export function insertRetry<T>(queue: readonly T[], index: number, retry: T, gap = RETRY_GAP): T[] {
  const at = Math.min(index + 1 + gap, queue.length)
  return [...queue.slice(0, at), retry, ...queue.slice(at)]
}

/**
 * Items to append before inserting a retry near the end of a round, so the
 * retry still comes exactly `gap` items later. Picks from `candidates` in
 * order, skipping anything about the same subject as the missed item or as
 * the item it would follow (no back-to-back repeats).
 */
export function fillersFor<T>(
  queue: readonly T[],
  index: number,
  candidates: readonly T[],
  subject: (item: T) => string,
  gap = RETRY_GAP,
): T[] {
  const needed = gap - (queue.length - index - 1)
  if (needed <= 0) return []
  const missed = subject(queue[index])
  const out: T[] = []
  let prev = subject(queue[queue.length - 1])
  for (const c of candidates) {
    if (out.length >= needed) break
    const s = subject(c)
    if (s !== missed && s !== prev) {
      out.push(c)
      prev = s
    }
  }
  return out
}
