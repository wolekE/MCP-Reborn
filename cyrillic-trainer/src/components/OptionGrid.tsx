import type { Option } from '../session/items'

interface Props {
  options: readonly Option[]
  /** Index the learner picked, once answered. */
  chosen: number | null
  /** The right answer's index; revealed after answering. */
  answer: number
  onPick: (index: number) => void
}

/** Four big answer buttons with 1–4 key hints; colours show right/wrong after answering. */
export function OptionGrid({ options, chosen, answer, onPick }: Props) {
  const answered = chosen !== null
  return (
    <div className={`options ${options.length === 4 ? 'options-4' : ''}`} role="group" aria-label="Answers">
      {options.map((o, i) => {
        let state = ''
        if (answered) state = i === answer ? 'correct' : i === chosen ? 'wrong' : 'dim'
        return (
          <button
            key={i}
            type="button"
            className={`option ${o.script === 'cyrillic' ? 'cyrillic' : ''} ${state}`}
            lang={o.script === 'cyrillic' ? 'ru' : undefined}
            disabled={answered}
            aria-keyshortcuts={String(i + 1)}
            data-testid={`option-${i + 1}`}
            data-correct={answered && i === answer ? 'true' : undefined}
            onClick={() => onPick(i)}
          >
            <span className="key" aria-hidden="true">
              {i + 1}
            </span>
            {o.label}
          </button>
        )
      })}
    </div>
  )
}
