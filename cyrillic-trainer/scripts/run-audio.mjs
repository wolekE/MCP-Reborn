// Cross-platform launcher for generate_audio.py: finds a Python 3 interpreter
// (the active virtual environment first, then python3 on macOS/Linux, python or
// the py launcher on Windows) and forwards extra arguments, e.g.
// `npm run audio -- --only syl-ga --force`.
import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const script = fileURLToPath(new URL('./generate_audio.py', import.meta.url))
const projectVenv = fileURLToPath(new URL('../.venv', import.meta.url))
const venvPython = (dir) => (process.platform === 'win32' ? join(dir, 'Scripts', 'python.exe') : join(dir, 'bin', 'python'))
const candidates = []
// The active virtual environment, else the project's .venv (works without activating it).
// On Windows, `python3` inside a venv can resolve to a global (Store) Python without edge-tts.
for (const dir of [process.env.VIRTUAL_ENV, projectVenv]) {
  if (dir && existsSync(venvPython(dir))) candidates.push([venvPython(dir)])
}
// Windows: the py launcher knows the real installs; `python3` is often the Microsoft Store stub.
if (process.platform === 'win32') candidates.push(['py', '-3'], ['python'], ['python3'])
else candidates.push(['python3'], ['python'])

for (const [cmd, ...pre] of candidates) {
  const probe = spawnSync(cmd, [...pre, '--version'], { encoding: 'utf8' })
  if (probe.status !== 0 || !/Python 3/.test(probe.stdout + probe.stderr)) continue
  console.log(`Using ${[cmd, ...pre].join(' ')} (${(probe.stdout + probe.stderr).trim()})`)
  const run = spawnSync(cmd, [...pre, script, ...process.argv.slice(2)], { stdio: 'inherit' })
  process.exit(run.status ?? 1)
}
console.error('Python 3 not found. Install it from https://www.python.org/downloads/ and retry.')
process.exit(1)
