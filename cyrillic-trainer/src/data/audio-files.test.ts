/**
 * Checks the generated audio against the data: every clip id referenced by
 * src/data/letters.ts must exist (non-empty) for both voices in public/audio,
 * and scripts/clips.json (what generate_audio.py reads) must match the data.
 * If this fails, run `npm run audio`.
 */
import { existsSync, readFileSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { clipsJson } from '../../scripts/export-clips'
import { CLIPS, LETTERS, WORD_BY_TEXT, BUILDER_WORDS } from './letters'

const root = fileURLToPath(new URL('../../', import.meta.url))
const VOICES = ['svetlana', 'dmitry'] as const

/** Every clip id the data references. */
function referencedClipIds(): Set<string> {
  const ids = new Set<string>()
  for (const l of LETTERS) {
    ids.add(l.audio.name)
    ids.add(l.audio.word)
    if (l.audio.syllable) ids.add(l.audio.syllable)
    for (const c of l.audio.contrast ?? []) ids.add(c)
  }
  for (const w of BUILDER_WORDS) ids.add(WORD_BY_TEXT.get(w)!.audio)
  for (const c of CLIPS) ids.add(c.id)
  return ids
}

describe('generated audio', () => {
  const ids = [...referencedClipIds()]

  it.each(VOICES)('has a non-empty MP3 for every referenced clip (%s)', (voice) => {
    const missing = ids.filter((id) => {
      const file = `${root}public/audio/${voice}/${id}.mp3`
      return !existsSync(file) || statSync(file).size === 0
    })
    expect(missing, `missing in public/audio/${voice}: run npm run audio`).toEqual([])
  })

  it('lists every clip in public/audio/index.json, generated from the current text', () => {
    const index = JSON.parse(readFileSync(`${root}public/audio/index.json`, 'utf8'))
    for (const voice of VOICES) {
      const clips: Record<string, string> = index.voices[voice].clips
      for (const c of CLIPS) expect(clips[c.id], `${voice}/${c.id}`).toBe(c.tts)
    }
  })

  it('has a review page', () => {
    expect(existsSync(`${root}public/audio/review.html`)).toBe(true)
  })

  it('keeps scripts/clips.json in sync with the data (run npm run audio:manifest)', () => {
    expect(readFileSync(`${root}scripts/clips.json`, 'utf8')).toBe(clipsJson())
  })
})
