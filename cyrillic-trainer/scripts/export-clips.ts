/**
 * Writes scripts/clips.json — the clip list generate_audio.py synthesizes.
 * Derived from src/data/letters.ts (the single source of truth); a unit test
 * fails if the committed JSON drifts from the data, and the Python script
 * warns if letters.ts changed since (it compares the recorded source hash).
 */
import { createHash } from 'node:crypto'
import { readFileSync, realpathSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { CLIPS } from '../src/data/letters.ts'

const LETTERS_TS = new URL('../src/data/letters.ts', import.meta.url)

/** sha256 of letters.ts with line endings normalized, so Windows checkouts hash the same. */
export function lettersHash(): string {
  const text = readFileSync(LETTERS_TS, 'utf8').replace(/\r\n/g, '\n')
  return createHash('sha256').update(text, 'utf8').digest('hex')
}

export function clipsJson(): string {
  return JSON.stringify({ source: { file: 'src/data/letters.ts', sha256: lettersHash() }, clips: CLIPS }, null, 2) + '\n'
}

function isMain(): boolean {
  try {
    // realpath both sides: symlinks / Windows junctions make the raw paths differ.
    return !!process.argv[1] && realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url))
  } catch {
    return false
  }
}

if (isMain()) {
  const out = new URL('./clips.json', import.meta.url)
  writeFileSync(out, clipsJson(), 'utf8')
  console.log(`Wrote ${CLIPS.length} clips to ${fileURLToPath(out)}`)
}
