import { createContext, useContext, useEffect, useMemo, useReducer, useRef, useState, type ReactNode } from 'react'
import { player } from '../audio/player'
import { sfx } from '../audio/sfx'
import * as A from './actions'
import { STORAGE_KEY, defaultSave, type SaveData, type Settings } from './schema'
import { loadSave, parseSave, resetProgress, writeSave, type LoadProblem, type StorageLike } from './storage'

type Action =
  | { type: 'introduce'; ids: readonly string[]; now: number }
  | { type: 'answer'; event: A.AnswerEvent; now: number }
  | { type: 'completeSession'; now: number }
  | { type: 'settings'; patch: Partial<Settings> }
  | { type: 'reset'; now: number }
  | { type: 'dismissUnlock' }
  | { type: 'replace'; save: SaveData }

interface State {
  save: SaveData
  /** Letters that just unlocked, shown as a celebration until dismissed. */
  justUnlocked: string[] | null
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'introduce':
      return { ...state, save: A.introduce(state.save, action.ids, action.now) }
    case 'answer': {
      const { save, unlocked } = A.maybeUnlock(A.recordAnswer(state.save, action.event, action.now))
      return { save, justUnlocked: unlocked.length ? unlocked : state.justUnlocked }
    }
    case 'completeSession': {
      const { save, unlocked } = A.maybeUnlock(A.completeSession(state.save, action.now))
      return { save, justUnlocked: unlocked.length ? unlocked : state.justUnlocked }
    }
    case 'settings':
      return { ...state, save: { ...state.save, settings: { ...state.save.settings, ...action.patch } } }
    case 'reset':
      return { save: resetProgress(state.save, action.now), justUnlocked: null }
    case 'dismissUnlock':
      return { ...state, justUnlocked: null }
    case 'replace':
      return { ...state, save: action.save }
  }
}

export interface Store {
  save: SaveData
  justUnlocked: string[] | null
  /** Set when the stored progress could not be read (it was backed up first). */
  loadProblem: LoadProblem | null
  introduce(ids: readonly string[]): void
  answer(event: A.AnswerEvent): void
  completeSession(): void
  updateSettings(patch: Partial<Settings>): void
  resetProgress(): void
  dismissUnlock(): void
}

const StoreContext = createContext<Store | null>(null)

function browserStorage(): StorageLike | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

export function StoreProvider({ children, storage = browserStorage() }: { children: ReactNode; storage?: StorageLike | null }) {
  const [initial] = useState(() => (storage ? loadSave(storage, Date.now()) : { data: defaultSave(Date.now()), problem: null }))
  const [state, dispatch] = useReducer(reducer, { save: initial.data, justUnlocked: null })

  // Another tab saved: adopt its progress instead of overwriting it with ours later.
  const fromOtherTab = useRef(false)
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key !== STORAGE_KEY || e.newValue === null) return
      const { data, problem } = parseSave(e.newValue, Date.now())
      if (problem) return
      fromOtherTab.current = true
      dispatch({ type: 'replace', save: data })
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  useEffect(() => {
    if (fromOtherTab.current) {
      fromOtherTab.current = false // already stored by the other tab
      return
    }
    if (storage) writeSave(storage, state.save)
  }, [storage, state.save])

  const { voice, rate, sfxMuted, theme } = state.save.settings
  useEffect(() => {
    player.configure({ voice, rate })
    sfx.setMuted(sfxMuted)
    const root = document.documentElement
    if (theme === 'system') delete root.dataset.theme
    else root.dataset.theme = theme
  }, [voice, rate, sfxMuted, theme])

  const store = useMemo<Store>(
    () => ({
      save: state.save,
      justUnlocked: state.justUnlocked,
      loadProblem: initial.problem,
      introduce: (ids) => dispatch({ type: 'introduce', ids, now: Date.now() }),
      answer: (event) => dispatch({ type: 'answer', event, now: Date.now() }),
      completeSession: () => dispatch({ type: 'completeSession', now: Date.now() }),
      updateSettings: (patch) => dispatch({ type: 'settings', patch }),
      resetProgress: () => dispatch({ type: 'reset', now: Date.now() }),
      dismissUnlock: () => dispatch({ type: 'dismissUnlock' }),
    }),
    [state, initial.problem],
  )
  return <StoreContext.Provider value={store}>{children}</StoreContext.Provider>
}

export function useStore(): Store {
  const s = useContext(StoreContext)
  if (!s) throw new Error('useStore must be used inside <StoreProvider>')
  return s
}
