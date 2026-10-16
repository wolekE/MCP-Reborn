#!/usr/bin/env python3
"""Generate the trainer's MP3 clips with Microsoft Edge neural TTS (edge-tts).

Reads the clip list from scripts/clips.json (exported from src/data/letters.ts
by `npm run audio:manifest`) and writes:

  public/audio/<voice>/<clip-id>.mp3   one file per clip per voice
  public/audio/index.json              which clips exist, read by the app's player
  public/audio/review.html             every clip with play buttons, for spot-checks

Each clip is trimmed to the speech (edge-tts pads short utterances with about
1.5 s of silence, which made rapid-fire drills sluggish). Trimming cuts whole
MP3 frames using edge-tts's word-boundary timings: no ffmpeg, no re-encoding.

Idempotent: clips that already exist are skipped, so re-running only fills gaps.
index.json remembers the text each file was made from, so a clip whose text
changed in letters.ts is regenerated automatically. Use --force to regenerate
everything (e.g. after an edge-tts voice update), or --only for specific clips.

Usage:
  python -m pip install -r scripts/requirements.txt   (inside a virtual environment, see README)
  npm run audio                                       # export clips.json, then run this script
  python3 scripts/generate_audio.py                   # both voices (Windows: py scripts/generate_audio.py)
  python3 scripts/generate_audio.py --voice svetlana  # just one
  python3 scripts/generate_audio.py --only syl-ga word-mat --force
  python3 scripts/generate_audio.py --prune           # delete clips no longer in the data

Behind a TLS-inspecting proxy, point SSL_CERT_FILE at the proxy's CA bundle.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import os
import ssl
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "scripts" / "clips.json"
LETTERS_TS = ROOT / "src" / "data" / "letters.ts"
AUDIO_DIR = ROOT / "public" / "audio"

# Folder name -> edge-tts voice. Svetlana (female) is the app's default voice.
VOICES = {
    "svetlana": "ru-RU-SvetlanaNeural",
    "dmitry": "ru-RU-DmitryNeural",
}

CONCURRENCY = 4
RETRIES = 4
# Bump when the way clips are produced changes; older clips are then regenerated.
FORMAT = 2  # 2 = trimmed to speech
# Silence kept around the speech when trimming (seconds).
LEAD_IN = 0.0  # word boundaries already start ~0.12 s before the voice
TAIL = 0.12


def load_clips() -> list[dict]:
    if not MANIFEST.exists():
        sys.exit(f"Missing {MANIFEST.relative_to(ROOT)}. Run `npm run audio:manifest` first.")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    recorded = manifest.get("source", {}).get("sha256")
    if LETTERS_TS.exists() and recorded:
        text = LETTERS_TS.read_text(encoding="utf-8").replace("\r\n", "\n")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != recorded:
            print(
                "warning: src/data/letters.ts changed since scripts/clips.json was exported; "
                "run `npm run audio:manifest` (or `npm run audio`) to refresh it.",
                file=sys.stderr,
            )
    clips = manifest["clips"]
    ids = [c["id"] for c in clips]
    if len(ids) != len(set(ids)):
        sys.exit("scripts/clips.json contains duplicate clip ids")
    return clips


def trust_extra_ca() -> None:
    """edge-tts pins certifi's CA bundle; add SSL_CERT_FILE on top for corporate proxies."""
    cafile = os.environ.get("SSL_CERT_FILE")
    if not cafile:
        return
    from edge_tts import communicate

    ctx = getattr(communicate, "_SSL_CTX", None)
    if isinstance(ctx, ssl.SSLContext):
        ctx.load_verify_locations(cafile=cafile)


# MPEG audio header tables (Layer III only — what edge-tts produces).
_BITRATES = {
    "1": [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
    "2": [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
}
_SAMPLE_RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def mp3_frames(data: bytes) -> list[tuple[int, int, float]]:
    """(offset, length, seconds) of each MPEG Layer III frame; [] if the data isn't plain frames."""
    frames = []
    pos = 0
    while pos + 4 <= len(data):
        b1, b2 = data[pos + 1], data[pos + 2]
        version = (b1 >> 3) & 3
        if data[pos] != 0xFF or (b1 & 0xE0) != 0xE0 or version == 1 or ((b1 >> 1) & 3) != 1:
            return []
        bitrate = _BITRATES["1" if version == 3 else "2"][(b2 >> 4) & 0xF] * 1000
        rate_index = (b2 >> 2) & 3
        if bitrate == 0 or rate_index == 3:
            return []
        rate = _SAMPLE_RATES[version][rate_index]
        samples = 1152 if version == 3 else 576
        length = samples // 8 * bitrate // rate + ((b2 >> 1) & 1)
        frames.append((pos, length, samples / rate))
        pos += length
    return frames if pos == len(data) else []


def trim_to_speech(data: bytes, start: float, end: float) -> bytes:
    """Keeps the frames overlapping [start, end] seconds; returns data unchanged if it can't parse it."""
    frames = mp3_frames(data)
    if not frames or end <= start:
        return data
    kept = bytearray()
    t = 0.0
    for offset, length, seconds in frames:
        if t + seconds > start and t < end:
            kept += data[offset : offset + length]
        t += seconds
    return bytes(kept) or data


async def synthesize(text: str, voice: str, dest: Path) -> None:
    import edge_tts

    tmp = dest.with_name(dest.name + ".part")
    delay = 2.0
    for attempt in range(1, RETRIES + 1):
        try:
            audio = bytearray()
            spans: list[tuple[float, float]] = []
            async for chunk in edge_tts.Communicate(text, voice, boundary="WordBoundary").stream():
                if chunk["type"] == "audio":
                    audio += chunk["data"]
                elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                    start = chunk["offset"] / 1e7  # 100-ns units
                    spans.append((start, start + chunk["duration"] / 1e7))
            if not audio:
                raise RuntimeError("empty audio")
            data = bytes(audio)
            if spans:
                data = trim_to_speech(data, min(s for s, _ in spans) - LEAD_IN, max(e for _, e in spans) + TAIL)
            tmp.write_bytes(data)
            tmp.replace(dest)  # atomic: an interrupted run never leaves a half-written clip
            return
        except Exception as exc:  # network hiccups, throttling
            tmp.unlink(missing_ok=True)
            if attempt == RETRIES:
                raise RuntimeError(f"{dest.name}: {exc}") from exc
            await asyncio.sleep(delay)
            delay *= 2


def recorded_texts() -> dict[str, dict[str, str]]:
    """voice -> {clip id -> text it was generated from}, from the previous index.json.

    Empty when the index is missing or was written by an older FORMAT, so those
    clips are regenerated.
    """
    try:
        index = json.loads((AUDIO_DIR / "index.json").read_text(encoding="utf-8"))
        if index.get("format") != FORMAT:
            return {}
        return {k: dict(v.get("clips", {})) for k, v in index.get("voices", {}).items()}
    except (OSError, ValueError, AttributeError):
        return {}


async def generate(
    clips: list[dict], voices: list[str], force: bool, recorded: dict[str, dict[str, str]]
) -> tuple[int, int, list[str]]:
    sem = asyncio.Semaphore(CONCURRENCY)
    made = skipped = 0
    failures: list[str] = []

    async def one(clip: dict, voice_key: str) -> None:
        nonlocal made, skipped
        dest = AUDIO_DIR / voice_key / f"{clip['id']}.mp3"
        was = recorded.get(voice_key, {}).get(clip["id"])
        up_to_date = dest.exists() and dest.stat().st_size > 0 and was == clip["tts"]
        if up_to_date and not force:
            skipped += 1
            return
        async with sem:
            try:
                await synthesize(clip["tts"], VOICES[voice_key], dest)
                recorded.setdefault(voice_key, {})[clip["id"]] = clip["tts"]
                made += 1
                print(f"  {voice_key:9} {clip['id']:20} {clip['tts']}")
            except Exception as exc:
                failures.append(f"{voice_key}/{clip['id']}: {exc}")

    for v in voices:
        (AUDIO_DIR / v).mkdir(parents=True, exist_ok=True)
    await asyncio.gather(*(one(c, v) for v in voices for c in clips))
    return made, skipped, failures


def existing(voice_key: str) -> set[str]:
    folder = AUDIO_DIR / voice_key
    if not folder.is_dir():
        return set()
    return {p.stem for p in folder.glob("*.mp3") if p.stat().st_size > 0}


def write_index(clips: list[dict], recorded: dict[str, dict[str, str]]) -> None:
    """Lists the clips present per voice (read by the app) with the TTS text each was made from."""
    index: dict = {"format": FORMAT, "voices": {}}
    for key, name in VOICES.items():
        have = existing(key)
        texts = recorded.get(key, {})
        index["voices"][key] = {
            "voice": name,
            "clips": {c["id"]: texts[c["id"]] for c in clips if c["id"] in have and c["id"] in texts},
        }
    (AUDIO_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def write_review(clips: list[dict]) -> None:
    have = {key: existing(key) for key in VOICES}
    sections = []
    for kind, title in (("name", "Letter names"), ("syllable", "Syllables"), ("word", "Words")):
        rows = []
        for c in (c for c in clips if c["kind"] == kind):
            cells = []
            for key in VOICES:
                if c["id"] in have[key]:
                    cells.append(f'<td><button data-src="{key}/{c["id"]}.mp3">▶ {key}</button></td>')
                else:
                    cells.append('<td class="missing">missing</td>')
            spoken = c["tts"].replace("\u0301", "")
            note = f'<div class="said">spoken as “{html.escape(c["tts"])}”</div>' if spoken != c["text"] else ""
            rows.append(
                f'<tr><td class="ru" lang="ru">{html.escape(c["text"])}{note}</td>'
                f'<td><code>{html.escape(c["id"])}</code></td>{"".join(cells)}</tr>'
            )
        sections.append(f"<h2>{title} ({len(rows)})</h2><table>{''.join(rows)}</table>")

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cyrillic Trainer — audio review</title>
<style>
  :root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
  body {{ max-width: 760px; margin: 2rem auto; padding: 0 1rem; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td {{ padding: .35rem .5rem; border-bottom: 1px solid #8884; }}
  .ru {{ font-size: 1.5rem; width: 40%; }}
  .missing {{ color: #c33; }}
  .said {{ font-size: .8rem; opacity: .7; }}
  button {{ font: inherit; padding: .3rem .7rem; cursor: pointer; }}
  button.playing {{ outline: 2px solid #3a7; }}
  .bar {{ position: sticky; top: 0; padding: .5rem 0; background: Canvas; display: flex; gap: .5rem; flex-wrap: wrap; }}
</style></head><body>
<h1>Audio review</h1>
<p>{len(clips)} clips × {len(VOICES)} voices. Click ▶ to hear a clip, or play a whole voice in order.
Regenerate a bad clip with <code>npm run audio -- --only &lt;id&gt; --force</code>.</p>
<div class="bar">{''.join(f'<button data-all="{k}">Play all: {k}</button>' for k in VOICES)}<button data-stop>Stop</button></div>
{''.join(sections)}
<script>
  const audio = new Audio();
  let queue = [];
  function play(btn) {{
    document.querySelectorAll('.playing').forEach(b => b.classList.remove('playing'));
    btn.classList.add('playing');
    btn.scrollIntoView({{ block: 'nearest' }});
    audio.src = btn.dataset.src;
    audio.play();
  }}
  audio.onended = () => {{ const next = queue.shift(); if (next) setTimeout(() => play(next), 250); }};
  document.addEventListener('click', e => {{
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.src) {{ queue = []; play(b); }}
    else if (b.dataset.all) {{ queue = [...document.querySelectorAll(`button[data-src^="${{b.dataset.all}}/"]`)]; play(queue.shift()); }}
    else if ('stop' in b.dataset) {{ queue = []; audio.pause(); }}
  }});
</script>
</body></html>
"""
    (AUDIO_DIR / "review.html").write_text(page, encoding="utf-8")


def prune(clips: list[dict]) -> int:
    wanted = {c["id"] for c in clips}
    removed = 0
    for key in VOICES:
        for p in (AUDIO_DIR / key).glob("*.mp3") if (AUDIO_DIR / key).is_dir() else []:
            if p.stem not in wanted:
                p.unlink()
                removed += 1
    return removed


def main() -> int:
    # Windows consoles/redirects may use cp1252, which can't encode Cyrillic: never crash on a print.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--voice", choices=sorted(VOICES), action="append", help="only this voice (repeatable)")
    parser.add_argument("--only", nargs="+", metavar="CLIP_ID", help="only these clip ids")
    parser.add_argument("--force", action="store_true", help="regenerate even if the file exists")
    parser.add_argument("--prune", action="store_true", help="delete MP3s whose clip id is no longer in the data")
    args = parser.parse_args()

    clips = load_clips()
    voices = args.voice or list(VOICES)
    todo = clips
    if args.only:
        unknown = set(args.only) - {c["id"] for c in clips}
        if unknown:
            sys.exit(f"Unknown clip id(s): {', '.join(sorted(unknown))}")
        todo = [c for c in clips if c["id"] in args.only]

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        sys.exit(
            f"edge-tts is not installed for {sys.executable}.\n"
            "Create the project's virtual environment once and install it there:\n"
            "  macOS/Linux: python3 -m venv .venv && .venv/bin/python -m pip install -r scripts/requirements.txt\n"
            "  Windows:     py -m venv .venv && .venv\\Scripts\\python -m pip install -r scripts/requirements.txt\n"
            "Then run `npm run audio` again (it uses .venv automatically)."
        )
    trust_extra_ca()

    print(f"{len(todo)} clips × {len(voices)} voice(s) → {AUDIO_DIR.relative_to(ROOT)}")
    recorded = recorded_texts()
    made, skipped, failures = asyncio.run(generate(todo, voices, args.force, recorded))
    if args.prune:
        print(f"Pruned {prune(clips)} stale file(s).")
    write_index(clips, recorded)
    write_review(clips)

    print(f"Done: {made} generated, {skipped} already present, {len(failures)} failed.")
    print(f"Spot-check pronunciation: {(AUDIO_DIR / 'review.html').relative_to(ROOT)} (or /audio/review.html in the dev server)")
    for f in failures:
        print(f"  FAILED {f}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
