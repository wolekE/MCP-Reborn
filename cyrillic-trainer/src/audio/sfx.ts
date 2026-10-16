/**
 * Feedback tones synthesized with the Web Audio API — no sound files.
 * Each function resolves when its tone has finished, so a "wrong" buzz can be
 * followed by the correct letter's clip without the two overlapping.
 */

type Wave = OscillatorType

interface Note {
  /** Frequency in Hz (or [from, to] for a glide). */
  freq: number | readonly [number, number]
  /** Start offset in seconds. */
  at: number
  /** Duration in seconds. */
  dur: number
  wave?: Wave
  gain?: number
}

let ctx: AudioContext | null = null
let muted = false
const MASTER = 0.22

function context(): AudioContext | null {
  if (typeof window === 'undefined') return null
  const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!Ctor) return null
  ctx ??= new Ctor()
  if (ctx.state === 'suspended') void ctx.resume()
  return ctx
}

function play(notes: readonly Note[]): Promise<void> {
  const ac = muted ? null : context()
  const end = Math.max(...notes.map((n) => n.at + n.dur))
  if (!ac) return Promise.resolve()
  const t0 = ac.currentTime + 0.01
  const out = ac.createGain()
  out.gain.value = MASTER
  out.connect(ac.destination)
  for (const n of notes) {
    const osc = ac.createOscillator()
    const env = ac.createGain()
    osc.type = n.wave ?? 'sine'
    const start = t0 + n.at
    const stop = start + n.dur
    if (typeof n.freq === 'number') {
      osc.frequency.setValueAtTime(n.freq, start)
    } else {
      osc.frequency.setValueAtTime(n.freq[0], start)
      osc.frequency.exponentialRampToValueAtTime(n.freq[1], stop)
    }
    // Short attack and exponential release: no clicks.
    const peak = n.gain ?? 1
    env.gain.setValueAtTime(0.0001, start)
    env.gain.exponentialRampToValueAtTime(peak, start + 0.012)
    env.gain.exponentialRampToValueAtTime(0.0001, stop)
    osc.connect(env).connect(out)
    osc.start(start)
    osc.stop(stop + 0.02)
  }
  return new Promise((resolve) =>
    setTimeout(() => {
      out.disconnect()
      resolve()
    }, (end + 0.05) * 1000),
  )
}

// Note frequencies (equal temperament).
const C5 = 523.25, E5 = 659.25, G5 = 783.99, A5 = 880, C6 = 1046.5, E6 = 1318.51, G6 = 1567.98, C7 = 2093

export const sfx = {
  /** Bright two-note chime, rising a fourth. */
  correct: () =>
    play([
      { freq: E5, at: 0, dur: 0.12, wave: 'triangle' },
      { freq: A5, at: 0.09, dur: 0.22, wave: 'triangle' },
      { freq: A5 * 2, at: 0.09, dur: 0.16, gain: 0.15 },
    ]),

  /** Soft low "bonk" sliding down — clearly wrong, never harsh. */
  wrong: () =>
    play([
      { freq: [220, 150], at: 0, dur: 0.28, wave: 'triangle', gain: 0.9 },
      { freq: [110, 80], at: 0, dur: 0.3, wave: 'sine', gain: 0.6 },
    ]),

  /** Quick sparkling arpeggio for an answer streak. */
  streak: () =>
    play([
      { freq: C6, at: 0, dur: 0.1 },
      { freq: E6, at: 0.06, dur: 0.1 },
      { freq: G6, at: 0.12, dur: 0.1 },
      { freq: C7, at: 0.18, dur: 0.25, gain: 0.7 },
    ]),

  /** Little fanfare plus a held major chord when new letters unlock. */
  levelUp: () =>
    play([
      { freq: G5, at: 0, dur: 0.12, wave: 'square', gain: 0.25 },
      { freq: C6, at: 0.12, dur: 0.12, wave: 'square', gain: 0.25 },
      { freq: E6, at: 0.24, dur: 0.12, wave: 'square', gain: 0.25 },
      { freq: C5, at: 0.38, dur: 0.6, wave: 'triangle' },
      { freq: E5, at: 0.38, dur: 0.6, wave: 'triangle', gain: 0.8 },
      { freq: G5, at: 0.38, dur: 0.6, wave: 'triangle', gain: 0.7 },
      { freq: C6, at: 0.38, dur: 0.7, gain: 0.5 },
    ]),

  setMuted(value: boolean) {
    muted = value
  },

  get muted() {
    return muted
  },

  /** Call from a user gesture so later tones aren't blocked by autoplay rules. */
  unlock() {
    if (!muted) context()
  },
}

export type SfxName = 'correct' | 'wrong' | 'streak' | 'levelUp'
