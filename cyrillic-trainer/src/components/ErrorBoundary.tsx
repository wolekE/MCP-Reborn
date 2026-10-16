import { Component, type ErrorInfo, type ReactNode } from 'react'
import { STORAGE_KEY } from '../state/schema'

interface State {
  error: Error | null
}

/** Shows what went wrong (instead of a blank page) and offers a way out. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Cyrillic Trainer crashed:', error, info.componentStack)
  }

  private resetProgress = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) localStorage.setItem(`${STORAGE_KEY}:backup:${Date.now()}`, raw)
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      // storage unavailable: a reload is all we can do
    }
    window.location.reload()
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children
    const translated = /removeChild|insertBefore|not a child of this node/i.test(error.message)
    return (
      <main style={{ maxWidth: 640, margin: '2rem auto', padding: '0 16px' }}>
        <div className="card stack">
          <h1>Something went wrong</h1>
          {translated && (
            <p>
              <strong>This is usually caused by the browser translating the page.</strong> If Chrome shows a translate icon in the
              address bar, choose <em>Never translate this site</em> (or <em>Show original</em>), then reload.
            </p>
          )}
          <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', margin: 0 }} className="small">
            {error.name}: {error.message}
          </pre>
          <div className="row">
            <button className="btn btn-primary" onClick={() => window.location.reload()}>
              Reload
            </button>
            <button className="btn btn-danger" onClick={this.resetProgress}>
              Reset progress and reload
            </button>
          </div>
          <p className="small muted" style={{ margin: 0 }}>
            Reset keeps a backup of your progress in this browser.
          </p>
        </div>
      </main>
    )
  }
}
