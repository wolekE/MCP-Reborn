/**
 * Plays clips by id from public/audio/<voice>/<id>.mp3.
 *
 * Fallback chain for each clip:
 *   1. the selected voice's MP3
 *   2. the other voice's MP3 (a real recording beats robotic speech)
 *   3. the Web Speech API with a ru-RU voice
 *   4. nothing — plus a one-time notice explaining how to install a Russian voice
 *
 * Missing files are detected from media errors rather than HTTP status: Vite's
 * dev server answers unknown paths with index.html (200), which the <audio>
 * element rejects as an unsupported source.
 */
import { CLIP_TTS, type ClipId } from '../data/letters'

export type VoiceKey = 'svetlana' | 'dmitry'
export type SpeechRate = 1 | 0.75

export interface PlayerSettings {
  voice: VoiceKey
  rate: SpeechRate
}

/** How a play request ended. `blocked` = the browser refused autoplay (needs a tap). */
export type PlayOutcome = 'played' | 'spoken' | 'silent' | 'blocked' | 'interrupted'

export interface PlayerNotice {
  kind: 'no-russian-voice'
}

const VOICE_KEYS: readonly VoiceKey[] = ['svetlana', 'dmitry']
const NOTICE_KEY = 'cyrillic-trainer:notice:no-russian-voice'
const GAP_MS = 350

type Availability = Record<VoiceKey, Set<ClipId>>

function audioUrl(voice: VoiceKey, id: ClipId): string {
  return `${import.meta.env.BASE_URL}audio/${voice}/${encodeURIComponent(id)}.mp3`
}

function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

export class AudioPlayer {
  private settings: PlayerSettings = { voice: 'svetlana', rate: 1 }
  private el: HTMLAudioElement | null = null
  private generation = 0
  private last: readonly ClipId[] = []
  private availability: Promise<Availability | null> | null = null
  private listeners = new Set<(n: PlayerNotice) => void>()

  configure(settings: Partial<PlayerSettings>): void {
    this.settings = { ...this.settings, ...settings }
  }

  getSettings(): PlayerSettings {
    return this.settings
  }

  /** Subscribe to user-facing notices (e.g. no Russian TTS voice). Returns an unsubscribe fn. */
  onNotice(listener: (n: PlayerNotice) => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  /** The clip(s) most recently requested, for Space-to-replay. */
  get lastPlayed(): readonly ClipId[] {
    return this.last
  }

  /**
   * Play one clip, or several in sequence with a short gap (Ъ/Ь contrast pairs).
   * Resolves when playback finishes, so callers can chain sounds.
   * A newer play() or stop() interrupts this one.
   */
  async play(ids: ClipId | readonly ClipId[]): Promise<PlayOutcome> {
    const list = typeof ids === 'string' ? [ids] : ids
    if (list.length === 0) return 'silent'
    this.last = list
    const gen = this.stopInternal()
    let outcome: PlayOutcome = 'silent'
    for (let i = 0; i < list.length; i++) {
      if (i > 0) {
        await sleep(GAP_MS)
        if (gen !== this.generation) return 'interrupted'
      }
      const result = await this.playOne(list[i], gen)
      if (result === 'interrupted' || result === 'blocked') return result
      if (result === 'played' || outcome === 'silent') outcome = result
    }
    return outcome
  }

  /** Replay whatever was played last (Space bar). */
  replay(): Promise<PlayOutcome> {
    return this.last.length ? this.play(this.last) : Promise.resolve('silent')
  }

  stop(): void {
    this.stopInternal()
  }

  /** Clears the remembered clip so Space does nothing until something new plays. */
  forget(): void {
    this.last = []
  }

  // -------------------------------------------------------------------------

  private stopInternal(): number {
    this.generation++
    if (this.el) {
      this.el.pause()
      this.el.removeAttribute('src')
      this.el.load()
    }
    if (typeof speechSynthesis !== 'undefined') speechSynthesis.cancel()
    return this.generation
  }

  private async playOne(id: ClipId, gen: number): Promise<PlayOutcome> {
    const avail = await this.loadAvailability()
    if (gen !== this.generation) return 'interrupted'
    const preferred = this.settings.voice
    const voices = [preferred, ...VOICE_KEYS.filter((v) => v !== preferred)]
    // With an index we only try voices that have the clip; without one we try them all.
    const candidates = avail ? voices.filter((v) => avail[v].has(id)) : voices
    for (const voice of candidates) {
      const r = await this.playFile(audioUrl(voice, id), gen)
      if (r !== 'error') return r
    }
    return this.speak(id, gen)
  }

  private playFile(url: string, gen: number): Promise<PlayOutcome | 'error'> {
    const el = (this.el ??= new Audio())
    el.preload = 'auto'
    el.src = url
    el.playbackRate = this.settings.rate
    el.preservesPitch = true
    return new Promise((resolve) => {
      let settled = false
      const done = (r: PlayOutcome | 'error') => {
        if (settled) return
        settled = true
        el.removeEventListener('ended', onEnded)
        el.removeEventListener('error', onError)
        clearInterval(watch)
        resolve(r)
      }
      const onEnded = () => done(gen === this.generation ? 'played' : 'interrupted')
      const onError = () => done(gen === this.generation ? 'error' : 'interrupted')
      // stop() swaps the source without firing 'ended'; notice that here.
      const watch = setInterval(() => {
        if (gen !== this.generation) done('interrupted')
      }, 100)
      el.addEventListener('ended', onEnded)
      el.addEventListener('error', onError)
      el.play().catch((err: unknown) => {
        const name = err instanceof DOMException ? err.name : ''
        if (gen !== this.generation || name === 'AbortError') done('interrupted')
        else if (name === 'NotAllowedError') done('blocked')
        else done('error')
      })
    })
  }

  private async speak(id: ClipId, gen: number): Promise<PlayOutcome> {
    // The TTS spelling, e.g. Ы's name is demonstrated in "мы" and a lone "о" carries a stress mark.
    const text = CLIP_TTS.get(id)
    if (!text || typeof speechSynthesis === 'undefined') {
      this.notifyNoVoice()
      return 'silent'
    }
    const voice = await pickRussianVoice(this.settings.voice)
    if (gen !== this.generation) return 'interrupted'
    if (!voice) {
      this.notifyNoVoice()
      return 'silent'
    }
    return new Promise((resolve) => {
      const u = new SpeechSynthesisUtterance(text)
      u.voice = voice
      u.lang = voice.lang
      u.rate = this.settings.rate
      u.onend = () => resolve(gen === this.generation ? 'spoken' : 'interrupted')
      u.onerror = (e) => resolve(e.error === 'not-allowed' ? 'blocked' : gen === this.generation ? 'silent' : 'interrupted')
      speechSynthesis.speak(u)
    })
  }

  private notifyNoVoice(): void {
    try {
      if (localStorage.getItem(NOTICE_KEY)) return
      localStorage.setItem(NOTICE_KEY, '1')
    } catch {
      // Storage unavailable: still tell the user, at most once per page load.
      if (this.noticeShown) return
    }
    this.noticeShown = true
    for (const l of this.listeners) l({ kind: 'no-russian-voice' })
  }

  private noticeShown = false

  private loadAvailability(): Promise<Availability | null> {
    this.availability ??= fetch(`${import.meta.env.BASE_URL}audio/index.json`)
      .then((r) => (r.ok ? r.json() : null))
      .then((json: unknown) => {
        const voices = (json as { voices?: Record<string, { clips?: Record<string, string> }> } | null)?.voices
        if (!voices) return null
        const out = {} as Availability
        for (const v of VOICE_KEYS) out[v] = new Set(Object.keys(voices[v]?.clips ?? {}))
        return out
      })
      .catch(() => null)
    return this.availability
  }
}

// ---------------------------------------------------------------------------
// Web Speech helpers
// ---------------------------------------------------------------------------

/** Name fragments of common system voices, used to honour the male/female setting. */
const MALE_HINTS = ['yuri', 'pavel', 'dmitr', 'maxim', 'male']
const FEMALE_HINTS = ['milena', 'katya', 'irina', 'svetlana', 'anna', 'elena', 'female', 'ekaterina', 'dariya']

function loadVoices(): Promise<SpeechSynthesisVoice[]> {
  const now = speechSynthesis.getVoices()
  if (now.length) return Promise.resolve(now)
  // Chrome fills the list asynchronously.
  return new Promise((resolve) => {
    const finish = () => {
      speechSynthesis.removeEventListener('voiceschanged', finish)
      clearTimeout(timer)
      resolve(speechSynthesis.getVoices())
    }
    const timer = setTimeout(finish, 1500)
    speechSynthesis.addEventListener('voiceschanged', finish)
  })
}

export async function pickRussianVoice(pref: VoiceKey): Promise<SpeechSynthesisVoice | null> {
  if (typeof speechSynthesis === 'undefined') return null
  const ru = (await loadVoices()).filter((v) => v.lang.toLowerCase().replace('_', '-').startsWith('ru'))
  if (!ru.length) return null
  const hints = pref === 'dmitry' ? MALE_HINTS : FEMALE_HINTS
  return ru.find((v) => hints.some((h) => v.name.toLowerCase().includes(h))) ?? ru.find((v) => v.localService) ?? ru[0]
}

export const player = new AudioPlayer()
