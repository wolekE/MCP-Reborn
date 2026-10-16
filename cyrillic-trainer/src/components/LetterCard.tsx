import { useEffect, type ReactNode } from 'react'
import { player } from '../audio/player'
import { GROUPS, transliterate, type Letter } from '../data/letters'
import { useKeys, useSpaceReplay } from '../hooks/useKeys'
import { AudioButton } from './AudioButton'

interface Props {
  letter: Letter
  /** e.g. "2 / 5" in a Learn session. */
  position?: string
  /** Shown above the card (e.g. a preview banner). */
  banner?: ReactNode
  primaryLabel: string
  onPrimary: () => void
  onBack?: () => void
}

/** The big Learn card: shapes, name, sound hints and the three audio buttons. */
export function LetterCard({ letter: l, position, banner, primaryLabel, onPrimary, onBack }: Props) {
  const group = GROUPS[l.group]
  const soundClips = l.audio.contrast ?? (l.audio.syllable ? [l.audio.syllable] : [])
  const soundLabel = l.audio.contrast ? `${l.contrastText![0]} → ${l.contrastText![1]}` : l.syllableText

  // Say the letter's name when the card appears; Space replays it.
  useEffect(() => {
    void player.play(l.audio.name)
    return () => player.stop()
  }, [l])
  useSpaceReplay()
  useKeys({
    '1': () => void player.play(l.audio.name),
    '2': () => soundClips.length && void player.play(soundClips),
    '3': () => void player.play(l.audio.word),
    Enter: onPrimary,
    ArrowLeft: () => onBack?.(),
  })

  return (
    <article className="card learn-card" aria-labelledby={`letter-${l.id}`}>
      {banner}
      <div className="spread">
        <span className="pill">
          Group {l.group} · {group.title}
        </span>
        {position && <span className="muted small">{position}</span>}
      </div>

      <div className="learn-glyphs">
        <div className="glyph-print learn-print" lang="ru" id={`letter-${l.id}`}>
          {l.upper}
          <span className="learn-lower">{l.lower}</span>
        </div>
        <figure className="learn-cursive">
          <div className="glyph-cursive" lang="ru">
            {l.cursive}
          </div>
          <figcaption className="small muted">handwritten</figcaption>
        </figure>
      </div>

      <div className="learn-meta">
        <div>
          <span className="muted small">Name </span>
          <strong lang="ru" className="learn-name">
            {l.name}
          </strong>
          {l.nameGloss && <span className="muted"> ({l.nameGloss})</span>}
        </div>
        <div>
          <span className="muted small">IPA </span>
          <span className="ipa">[{l.ipa}]</span>
        </div>
      </div>

      {l.falseFriend && (
        <p className="learn-warn">
          ⚠ Looks like Latin <strong>{l.falseFriend.looksLike}</strong>, but it isn’t “{l.falseFriend.wrongSounds.join('” or “')}”.
        </p>
      )}

      <dl className="hints">
        <div>
          <dt>EN</dt>
          <dd>{l.hintEn}</dd>
        </div>
        <div>
          <dt>PL</dt>
          <dd>{l.hintPl}</dd>
        </div>
        {l.cursiveNote && (
          <div>
            <dt aria-label="Handwriting">✍</dt>
            <dd>{l.cursiveNote}</dd>
          </div>
        )}
      </dl>

      <div className="learn-example">
        <span lang="ru" className="learn-word">
          {l.example.stressed}
        </span>
        <span className="muted"> {transliterate(l.example.word)}</span>
        <div>
          {l.example.en} <span className="muted">· PL: {l.example.pl}</span>
        </div>
      </div>

      <div className="row learn-audio" role="group" aria-label="Listen">
        <AudioButton clips={l.audio.name} title="Play the letter’s name (1)">
          Name {l.nameAudioNote && <span className="small muted">({l.nameAudioNote})</span>} <kbd>1</kbd>
        </AudioButton>
        {soundClips.length > 0 && (
          <AudioButton clips={soundClips} title="Play the sound in a syllable (2)">
            <span lang="ru">{soundLabel}</span> <kbd>2</kbd>
          </AudioButton>
        )}
        <AudioButton clips={l.audio.word} title="Play the example word (3)">
          <span lang="ru">{l.example.word}</span> <kbd>3</kbd>
        </AudioButton>
      </div>
      <p className="small muted" style={{ margin: 0 }}>
        <kbd>Space</kbd> replays the last sound.
      </p>

      <div className="spread">
        {onBack ? (
          <button className="btn btn-ghost" onClick={onBack}>
            ← Back
          </button>
        ) : (
          <span />
        )}
        <button className="btn btn-primary btn-big" onClick={onPrimary} autoFocus>
          {primaryLabel} <kbd>Enter</kbd>
        </button>
      </div>
    </article>
  )
}
