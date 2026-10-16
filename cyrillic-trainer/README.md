# Cyrillic Trainer

A local web app that teaches the 33 letters of the Russian alphabet with real audio, spaced repetition and Polish comparisons where they help (В = *w*, Ж = *ż*, Ы ≈ *y*, Ь works like the Polish *kreska*…).

No backend and no account. Everything runs in your browser and progress is saved in `localStorage`.

- **Learn**: one big letter card at a time, showing print and handwritten forms, the Russian name, IPA, English and Polish hints and an example word, with buttons for the name, a syllable and the word.
- **Listen & Pick**: hear a syllable and pick the letter.
- **Read**: see a letter or short word and pick how it sounds.
- **False Friends**: 45-second rapid fire on В Е Н Р С У Х, the letters that look Latin but aren't.
- **Word Builder**: hear a word (кот, дом, мама, суп, чай, жук, щи, мышь) and tap its letters in order.
- **Daily review**: everything that's due, mixed across all the modes above.

Letters unlock in batches of 3–5, group by group, once your current group averages 80%+.

## Setup

You need **Node.js 20.19+ or 22.12+** (check with `node --version`). It works the same on macOS and Windows:

```sh
cd cyrillic-trainer
npm install
npm run dev
```

Then open the address it prints (normally <http://localhost:5173>).

The recorded audio is already in `public/audio/`, so the app works straight away. You only need Python to *regenerate* the clips (see below).

To build a static copy instead: `npm run build`, then `npm run preview` (or open `dist/` from any static web server).

## Keyboard

| Key | Does |
| --- | --- |
| <kbd>1</kbd>–<kbd>4</kbd> | Answer (in Word Builder, number keys tap tiles; a Russian keyboard layout types letters directly) |
| <kbd>Space</kbd> | Replay the current audio |
| <kbd>Enter</kbd> | Got it / Continue / Play again |
| <kbd>1</kbd> <kbd>2</kbd> <kbd>3</kbd> on a Learn card | Play the name, syllable or word |
| <kbd>1</kbd>–<kbd>6</kbd> on the Practice screen | Pick a mode |

## Audio

Every letter has three clips: its **name**, a **syllable** and its **example word**. A consonant is never played alone: the syllable is consonant + а (ба, ва, га…), and vowels are heard after м (ма, мо, му…). Ъ and Ь play contrast pairs instead: **сел → съел** and **мат → мать**.

Clips are synthesized with Microsoft's neural voices through [`edge-tts`](https://github.com/rany2/edge-tts): **ru-RU-SvetlanaNeural** (female, the default) and **ru-RU-DmitryNeural** (male). Pick the voice and speed (1× or 0.75×) in **Settings**.

### Regenerating audio

1. Install Python 3.9+ and the one dependency:

   ```sh
   pip install -r scripts/requirements.txt
   ```

   On Windows use `py -m pip install -r scripts/requirements.txt` if `pip` isn't on your PATH.

2. Run:

   ```sh
   npm run audio
   ```

   This exports the clip list from `src/data/letters.ts` (the single source of truth) to `scripts/clips.json`. It then runs `scripts/generate_audio.py`, which writes `public/audio/<voice>/<clip>.mp3` for both voices.

The script is **idempotent**. Clips that already exist are skipped, so re-running only fills gaps. `public/audio/index.json` records the text each file was made from, so if you change a word or syllable in `letters.ts`, just that clip is regenerated. Extra options go after `--`:

```sh
npm run audio -- --only syl-ga word-mat --force   # redo specific clips
npm run audio -- --voice dmitry                   # one voice only
npm run audio -- --prune                          # delete clips no longer in the data
```

You can also run the Python script directly: `python scripts/generate_audio.py --help`.

**Spot-check pronunciation** on the generated review page, which lists every clip with play buttons and a "Play all" mode. Open <http://localhost:5173/audio/review.html> while `npm run dev` is running, or open `public/audio/review.html` straight from disk.

Notes on the generated audio:

- Text sent to the speech engine carries stress marks (о́, ба́, арбу́з). Without them a bare "о" is read as the unstressed preposition and comes out sounding like "а". This was confirmed by measuring vowel formants and transcribing every clip.
- Ы never stands on its own in Russian, and the voices can't say a bare [ɨ] (it comes out as и), so its name is demonstrated in **мы** and its syllable is **вы**. The review page notes "spoken as …" wherever the spoken text differs from the label.
- Behind a corporate proxy that inspects TLS, point `SSL_CERT_FILE` at the proxy's CA bundle before running the script.

### When a clip is missing

If an MP3 can't be loaded, the app falls back to the browser's speech synthesis with a Russian voice. If your system has no Russian voice, it shows a one-time notice explaining how to add one:

- **macOS:** System Settings → Accessibility → Spoken Content → System voice → Manage Voices… → Russian (*Milena* or *Yuri*).
- **Windows 10/11:** Settings → Time & language → Speech → Manage voices → Add voices → Russian (*Irina* / *Pavel*). Restart the browser afterwards.

The same help is in **Settings → Audio not working?**

## How it schedules practice

Spaced repetition is a light version of SM-2 (`src/srs/scheduler.ts`, pure functions):

- Each letter has an **ease factor** (starts at 2.5, minimum 1.3) and an **interval**.
- A correct answer on a due letter climbs **10 min → 1 day → 3 days**, then multiplies the interval by the ease.
- A **miss resets to 10 minutes** and lowers the ease.
- **Fast answers count more**: they raise the ease and stretch the interval ×1.3. Slow but correct answers lower the ease a little.
- Answering a letter that isn't due yet doesn't move its schedule (misses still do), so cramming can't fake long-term memory.
- Mastery colours on the home map:
  - **new**: not met yet
  - **learning**: interval under 1 day
  - **known**: 1 day or more
  - **mastered**: 7 days or more

Within a session, anything you miss comes back **two items later**. Each wrong answer shows the right letter and plays its sound.

## Resetting progress

- In the app: **Settings → Reset progress**. This keeps your settings (voice, speed, theme).
- By hand: open your browser's developer tools on the app's page and run `localStorage.removeItem('cyrillic-trainer')`, then reload.

Progress lives under the `cyrillic-trainer` key as a versioned JSON document (`src/state/schema.ts`, `SCHEMA_VERSION`). If saved data can't be read, for example because it's corrupt or came from a newer version, it's copied to `cyrillic-trainer:backup:<timestamp>` before the app starts fresh, so nothing is silently lost. Note that `localStorage` is per browser and per address: `localhost:5173` and `localhost:4173` (preview) keep separate progress.

## Tests

```sh
npm test                       # Vitest unit tests
npx playwright install chromium   # once, downloads the test browser
npm run test:e2e               # Playwright: a Learn session, a Listen & Pick round, the audio fallback
```

The unit tests cover:

- **Letter data:** all 33 letters present and unique; names, groups and confusables match the plan.
- **Audio files:** every audio id referenced by the data exists in `public/audio` for both voices.
- **Scheduler maths:** intervals, misses, fast answers, unlocking.
- **Session engine:** storage and migrations, streaks, the missed-items-return-2-later queue, and distractor rules.

## Project layout

```
src/
  data/letters.ts      the 33 letters, extra words and the derived clip registry (single source of truth)
  audio/player.ts      plays clips by id; falls back to the other voice, then Web Speech
  audio/sfx.ts         correct / wrong / streak / level-up tones synthesized with Web Audio
  srs/scheduler.ts     spaced repetition, mastery and unlocking (pure)
  session/             item generators, distractors, queues (pure, seeded)
  state/               versioned save format, storage + migrations, React store
  modes/               Learn and the drill router
  screens/             Home + progress map, mode picker, settings, stats
  components/          letter card, drill engine, word builder board, notices
scripts/
  export-clips.ts      letters.ts → clips.json
  generate_audio.py    clips.json → public/audio (edge-tts), index.json, review.html
  run-audio.mjs        finds python3 / python / py on macOS and Windows
tests/e2e/             Playwright tests
```

Fonts are bundled locally (no CDN), so the app also works offline: [Bad Script](https://fonts.google.com/specimen/Bad+Script) for handwritten letters, PT Sans for print and Nunito for the interface, all Google Fonts via Fontsource.
