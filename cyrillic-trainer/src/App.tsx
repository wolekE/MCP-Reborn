import { useEffect, type ReactNode } from 'react'
import { sfx } from './audio/sfx'
import { Notices } from './components/Notices'
import { Learn } from './modes/Learn'
import { Play } from './modes/Play'
import { href, useRoute } from './router'
import { Home } from './screens/Home'
import { ModePicker } from './screens/ModePicker'
import { Session } from './screens/Session'
import { Settings } from './screens/Settings'
import { Stats } from './screens/Stats'

const NAV: { path: string; label: string; match: string[] }[] = [
  { path: '', label: 'Home', match: [''] },
  { path: 'modes', label: 'Practice', match: ['modes', 'play', 'session', 'learn'] },
  { path: 'stats', label: 'Stats', match: ['stats'] },
  { path: 'settings', label: 'Settings', match: ['settings'] },
]

export default function App() {
  const route = useRoute()
  const [page = '', ...rest] = route
  const sub = rest[0]

  // Unlock Web Audio on the first gesture so feedback tones are never blocked.
  useEffect(() => {
    const unlock = () => sfx.unlock()
    window.addEventListener('pointerdown', unlock, { once: true })
    window.addEventListener('keydown', unlock, { once: true })
    return () => {
      window.removeEventListener('pointerdown', unlock)
      window.removeEventListener('keydown', unlock)
    }
  }, [])

  // Braces matter: newer browsers return a Promise from scrollTo, which React would treat as a cleanup.
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [page, sub])

  let content: ReactNode
  switch (page) {
    case '':
      content = <Home />
      break
    case 'learn':
      content = <Learn letterId={rest[0]} />
      break
    case 'session':
      content = <Session />
      break
    case 'play':
      content = <Play mode={rest[0]} focus={rest[1]} />
      break
    case 'modes':
      content = <ModePicker />
      break
    case 'settings':
      content = <Settings />
      break
    case 'stats':
      content = <Stats />
      break
    default:
      content = (
        <div className="card">
          <h1>Page not found</h1>
          <a className="btn" href={href('')}>
            Go home
          </a>
        </div>
      )
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href={href('')}>
            <span className="brand-mark" lang="ru" aria-hidden="true">
              Ж
            </span>
            <span className="brand-name">Cyrillic Trainer</span>
          </a>
          <nav className="nav" aria-label="Main">
            {NAV.map((n) => (
              <a key={n.path} href={href(n.path)} aria-current={n.match.includes(page) ? 'page' : undefined}>
                {n.label}
              </a>
            ))}
          </nav>
        </div>
      </header>
      <main key={route.join('/')}>{content}</main>
      <Notices />
    </div>
  )
}
