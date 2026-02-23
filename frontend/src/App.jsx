import { useState, useEffect, useCallback } from 'react'
import { chatApi } from './api/client'
import Chat from './pages/Chat'
import Templates from './pages/Templates'
import Rules from './pages/Rules'
import './App.css'

const USER_ID = 'web-user'
const SESSIONS_KEY = 'elma365_chat_sessions'

function toLocal(s) {
  return { id: s.session_id, title: s.title || 'Новый чат' }
}

function loadSessionsFallback() {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    if (!raw) return [{ id: 'default-session', title: 'Новый чат' }]
    const list = JSON.parse(raw)
    return Array.isArray(list) && list.length ? list : [{ id: 'default-session', title: 'Новый чат' }]
  } catch {
    return [{ id: 'default-session', title: 'Новый чат' }]
  }
}

function App() {
  const [sessions, setSessions] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [page, setPage] = useState('chat')
  const [sessionsLoaded, setSessionsLoaded] = useState(false)

  useEffect(() => {
    let cancelled = false
    chatApi
      .listSessions(USER_ID)
      .then((data) => {
        if (cancelled) return
        const list = (data.sessions || []).map(toLocal)
        if (list.length) {
          setSessions(list)
          setCurrentSessionId((id) => id || list[0].id)
        } else {
          const fallback = loadSessionsFallback()
          setSessions(fallback)
          setCurrentSessionId((id) => id || fallback[0].id)
        }
      })
      .catch(() => {
        if (cancelled) return
        const fallback = loadSessionsFallback()
        setSessions(fallback)
        setCurrentSessionId((id) => id || fallback[0].id)
      })
      .finally(() => {
        if (!cancelled) setSessionsLoaded(true)
      })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (sessions.length) {
      try {
        localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
      } catch (_) {}
    }
  }, [sessions])

  const handleNewChat = useCallback(() => {
    chatApi
      .createSession({ user_id: USER_ID })
      .then((res) => {
        const id = res.session_id
        const title = res.title || 'Новый чат'
        setSessions((s) => [{ id, title }, ...s])
        setCurrentSessionId(id)
        setPage('chat')
      })
      .catch(() => {
        const id = `session-${Date.now()}`
        setSessions((s) => [{ id, title: 'Новый чат' }, ...s])
        setCurrentSessionId(id)
        setPage('chat')
      })
  }, [])

  const handleSelectSession = useCallback((id) => {
    setCurrentSessionId(id)
    setPage('chat')
  }, [])

  const handleRenameSession = useCallback((sessionId, title) => {
    setSessions((s) =>
      s.map((x) => (x.id === sessionId ? { ...x, title: title || x.title } : x))
    )
    chatApi.updateSessionTitle(sessionId, USER_ID, title || 'Новый чат').catch(() => {})
  }, [])

  if (!sessionsLoaded) {
    return (
      <div className="app">
        <aside className="sidebar">
          <div className="sidebar-header">
            <h1 className="sidebar-logo">ELMA365 Chat</h1>
          </div>
          <p className="placeholder" style={{ padding: '1rem' }}>Загрузка…</p>
        </aside>
        <main className="main" />
      </div>
    )
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1 className="sidebar-logo">ELMA365 Chat</h1>
        </div>
        <button type="button" className="sidebar-new-chat" onClick={handleNewChat}>
          + Новый чат
        </button>
        <div className="sidebar-chats">
          {sessions.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`sidebar-chat ${currentSessionId === s.id ? 'active' : ''}`}
              onClick={() => handleSelectSession(s.id)}
            >
              {s.title}
            </button>
          ))}
        </div>
        <div className="sidebar-footer">
          <button
            type="button"
            className="sidebar-footer-btn"
            onClick={() => setPage('templates')}
          >
            Шаблоны
          </button>
          <button
            type="button"
            className="sidebar-footer-btn"
            onClick={() => setPage('rules')}
          >
            Правила
          </button>
        </div>
      </aside>
      <main className="main">
        {page === 'chat' && currentSessionId && (
          <Chat
            sessionId={currentSessionId}
            userId={USER_ID}
            onSessionTitle={handleRenameSession}
          />
        )}
        {page === 'templates' && (
          <div className="page-content">
            <Templates />
          </div>
        )}
        {page === 'rules' && (
          <div className="page-content">
            <Rules />
          </div>
        )}
      </main>
    </div>
  )
}

export default App
