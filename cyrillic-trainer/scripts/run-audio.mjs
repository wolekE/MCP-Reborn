// Cross-platform launcher for generate_audio.py: finds a Python 3 interpreter
// (python3 on macOS/Linux, python or the py launcher on Windows) and forwards
// any extra arguments, e.g. `npm run audio -- --only syl-ga --force`.
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const script = fileURLToPath(new URL('./generate_audio.py', import.meta.url))
const candidates = [['python3'], ['python'], ['py', '-3']]

for (const [cmd, ...pre] of candidates) {
  const probe = spawnSync(cmd, [...pre, '--version'], { encoding: 'utf8' })
  if (probe.status !== 0 || !/Python 3/.test(probe.stdout + probe.stderr)) continue
  const run = spawnSync(cmd, [...pre, script, ...process.argv.slice(2)], { stdio: 'inherit' })
  process.exit(run.status ?? 1)
}
console.error('Python 3 not found. Install it from https://www.python.org/downloads/ and retry.')
process.exit(1)
