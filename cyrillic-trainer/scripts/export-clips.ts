/**
 * Writes scripts/clips.json — the clip list generate_audio.py synthesizes.
 * Derived from src/data/letters.ts (the single source of truth); a unit test
 * fails if the committed JSON drifts from the data.
 */
import { writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { CLIPS } from '../src/data/letters.ts'

export function clipsJson(): string {
  return JSON.stringify({ clips: CLIPS }, null, 2) + '\n'
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const out = new URL('./clips.json', import.meta.url)
  writeFileSync(out, clipsJson(), 'utf8')
  console.log(`Wrote ${CLIPS.length} clips to ${fileURLToPath(out)}`)
}
