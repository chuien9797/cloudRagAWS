import { useState, useEffect, useCallback } from 'react'
import { LogOut, Search, Settings, User } from 'lucide-react'

import Sidebar from './components/Sidebar.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import SourcesPanel from './components/SourcesPanel.jsx'
import LoginScreen from './components/LoginScreen.jsx'
import {
  fetchCurrentUser,
  fetchDocuments,
  fetchSessions,
  getStoredUser,
  login,
  logout,
} from './api.js'

export default function App() {
  const [documents, setDocuments] = useState([])
  const [sessions, setSessions] = useState([])
  const [selectedDocId, setSelectedDocId] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [sources, setSources] = useState([])
  const [tokenUsage, setTokenUsage] = useState(null)
  const [highlightedSource, setHighlighted] = useState(null)
  const [loadingDocs, setLoadingDocs] = useState(true)
  const [authChecked, setAuthChecked] = useState(false)
  const [currentUser, setCurrentUser] = useState(getStoredUser())

  const refreshDocuments = useCallback(async () => {
    try {
      const docs = await fetchDocuments()
      setDocuments(docs)
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingDocs(false)
    }
  }, [])

  const refreshSessions = useCallback(async () => {
    try {
      const s = await fetchSessions()
      setSessions(s)
    } catch (e) {
      console.error(e)
    }
  }, [])

  useEffect(() => {
    async function bootstrapAuth() {
      try {
        const user = await fetchCurrentUser()
        setCurrentUser(user)
      } catch {
        setCurrentUser(null)
      } finally {
        setAuthChecked(true)
      }
    }
    bootstrapAuth()
  }, [])

  useEffect(() => {
    if (!currentUser) return
    setLoadingDocs(true)
    refreshDocuments()
    refreshSessions()
  }, [currentUser, refreshDocuments, refreshSessions])

  async function handleLogin(email, password) {
    const user = await login(email, password)
    setCurrentUser(user)
    setSelectedDocId(null)
    setSessionId(null)
    setMessages([])
    setSources([])
    setTokenUsage(null)
  }

  async function handleLogout() {
    await logout()
    setCurrentUser(null)
    setDocuments([])
    setSessions([])
    setSelectedDocId(null)
    setSessionId(null)
    setMessages([])
    setSources([])
    setTokenUsage(null)
  }

  function handleAnswer(data) {
    setSources(data.citations || data.sources || [])
    setTokenUsage(data.token_usage || null)
    if (data.session_id) setSessionId(data.session_id)
    refreshSessions()
  }

  function handleCitationClick(index) {
    if (index < 0 || index >= sources.length) return
    setHighlighted(index)
    setTimeout(() => setHighlighted(null), 2000)
  }

  function handleSessionSelect(sid, msgs) {
    setSessionId(sid)
    setMessages(msgs)
    setSources([])
    setTokenUsage(null)
  }

  function handleNewChat() {
    setSessionId(null)
    setMessages([])
    setSources([])
    setTokenUsage(null)
    setSelectedDocId(null)
  }

  if (!authChecked) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', color: 'var(--text-tertiary)' }}>
        Loading workspace...
      </div>
    )
  }

  if (!currentUser) {
    return <LoginScreen onLogin={handleLogin} />
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)' }}>
      <header style={{
        height: 'var(--navbar-h)',
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        flexShrink: 0,
        boxShadow: 'var(--shadow-sm)',
        zIndex: 10,
      }}>
        <span style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 700,
          fontSize: '17px',
          letterSpacing: '-0.3px',
          color: 'var(--text-primary)',
        }}>
          Cloud<span style={{ color: 'var(--accent)' }}>RAG</span>
        </span>
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          {[Search, Settings].map((Icon, i) => (
            <button
              key={i}
              title={i === 0 ? 'Search' : 'Settings'}
              style={{
                width: 34,
                height: 34,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-secondary)',
                transition: 'background 0.15s, color 0.15s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--surface-2)'
                e.currentTarget.style.color = 'var(--text-primary)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'none'
                e.currentTarget.style.color = 'var(--text-secondary)'
              }}
            >
              <Icon size={16} />
            </button>
          ))}
          <div style={{
            height: 34,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-secondary)',
            padding: '0 8px',
          }}>
            <User size={16} />
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>{currentUser.full_name}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{currentUser.email}</div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            title="Sign out"
            style={{
              height: 34,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '0 10px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--surface-2)',
              color: 'var(--text-secondary)',
              fontSize: '12px',
              fontWeight: 600,
            }}
          >
            <LogOut size={14} />
            Sign out
          </button>
        </div>
      </header>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar
          documents={documents}
          sessions={sessions}
          selectedDocId={selectedDocId}
          onSelectDoc={setSelectedDocId}
          onUploadComplete={refreshDocuments}
          onDeleteDoc={refreshDocuments}
          currentUserId={currentUser.id}
          onSessionSelect={handleSessionSelect}
          onNewChat={handleNewChat}
          onSessionsChange={refreshSessions}
          loading={loadingDocs}
        />
        <ChatPanel
          selectedDocId={selectedDocId}
          sessionId={sessionId}
          messages={messages}
          setMessages={setMessages}
          onAnswer={handleAnswer}
          onCitationClick={handleCitationClick}
        />
        <SourcesPanel
          sources={sources}
          tokenUsage={tokenUsage}
          highlightedIndex={highlightedSource}
        />
      </div>
    </div>
  )
}
