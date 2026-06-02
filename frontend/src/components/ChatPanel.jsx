import { useState, useRef, useEffect } from 'react'
import { Send, Loader, FileText, Square } from 'lucide-react'
import MessageBubble from './MessageBubble.jsx'
import { askQuestion } from '../api.js'

export default function ChatPanel({
  selectedDocId, sessionId, messages, setMessages,
  onAnswer, onCitationClick,
}) {
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)
  const bottomRef = useRef()
  const textareaRef = useRef()
  const requestRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function handleSend() {
    const q = input.trim()
    if (!q || loading) return

    setInput('')
    setError(null)
    setMessages(prev => [...prev, { role: 'user', content: q }])
    setLoading(true)
    const controller = new AbortController()
    requestRef.current = controller

    try {
      const data = await askQuestion(q, selectedDocId, sessionId, { signal: controller.signal })
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer }])
      onAnswer(data)
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Response stopped.')
      } else {
        setError(err.message)
      }
      setMessages(prev => prev.slice(0, -1))
    } finally {
      requestRef.current = null
      setLoading(false)
    }
  }

  function handleStop() {
    requestRef.current?.abort()
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <main style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      background: 'var(--bg)',
    }}>

      {/* Active doc indicator */}
      {selectedDocId && (
        <div style={{
          padding: '8px 24px',
          background: 'var(--accent-light)',
          borderBottom: '1px solid #bfdbfe',
          display: 'flex', alignItems: 'center', gap: '6px',
          fontSize: '12px', color: 'var(--accent)',
        }}>
          <FileText size={12} />
          Filtering to selected document
        </div>
      )}

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 32px' }}>
        {messages.length === 0 && (
          <div style={{
            height: '100%', display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            color: 'var(--text-tertiary)', gap: '10px',
            userSelect: 'none',
          }}>
            <div style={{
              fontFamily: 'var(--font-display)',
              fontSize: '22px', fontWeight: 600,
              color: 'var(--text-secondary)',
              letterSpacing: '-0.3px',
            }}>
              Ask anything
            </div>
            <div style={{ fontSize: '13px' }}>
              Upload a document and start a conversation
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            message={msg}
            onCitationClick={onCitationClick}
          />
        ))}

        {loading && (
          <div style={{
            display: 'flex', gap: '10px', alignItems: 'flex-start',
            marginBottom: '20px', animation: 'fadeIn 0.2s ease',
          }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%',
              background: 'var(--surface-2)',
              border: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Loader size={13} color="var(--text-secondary)" className="spinning" />
            </div>
            <div style={{
              background: 'var(--surface)',
              border: '1px solid var(--border-light)',
              borderRadius: '4px 14px 14px 14px',
              padding: '10px 14px',
              fontSize: '13px', color: 'var(--text-tertiary)',
              boxShadow: 'var(--shadow-sm)',
            }}>
              Thinking...
            </div>
          </div>
        )}

        {error && (
          <div style={{
            background: '#fef2f2', border: '1px solid #fecaca',
            borderRadius: 'var(--radius-md)',
            padding: '10px 14px',
            fontSize: '12px', color: 'var(--error)',
            marginBottom: '16px',
          }}>
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '16px 24px 20px',
        background: 'var(--surface)',
        borderTop: '1px solid var(--border)',
      }}>
        <div style={{
          display: 'flex', gap: '10px', alignItems: 'flex-end',
          background: 'var(--bg)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          padding: '10px 14px',
          transition: 'border-color 0.15s, box-shadow 0.15s',
          boxShadow: 'var(--shadow-sm)',
        }}
        onFocusCapture={e => {
          e.currentTarget.style.borderColor = 'var(--accent)'
          e.currentTarget.style.boxShadow = '0 0 0 3px rgba(37,99,235,0.1)'
        }}
        onBlurCapture={e => {
          e.currentTarget.style.borderColor = 'var(--border)'
          e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
        }}
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question... (Enter to send, Shift+Enter for newline)"
            rows={1}
            style={{
              flex: 1, resize: 'none', border: 'none', background: 'none',
              outline: 'none', fontSize: '13.5px', color: 'var(--text-primary)',
              lineHeight: '1.5', maxHeight: '120px', overflowY: 'auto',
            }}
          />
          <button
            onClick={loading ? handleStop : handleSend}
            disabled={!loading && !input.trim()}
            style={{
              width: 28, height: 28, borderRadius: '5px',
              background: input.trim() && !loading ? 'var(--accent)' : 'var(--surface-2)',
              color: loading || input.trim() ? '#fff' : 'var(--text-tertiary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, transition: 'background 0.15s, color 0.15s',
              backgroundColor: loading ? '#171717' : (input.trim() ? 'var(--accent)' : 'var(--surface-2)'),
            }}
            title={loading ? 'Stop generating' : 'Send message'}
          >
            {loading
              ? <Square size={10} fill="currentColor" />
              : <Send size={14} />
            }
          </button>
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '6px', textAlign: 'center' }}>
          {loading
            ? 'Generating answer. Press stop to cancel.'
            : (selectedDocId ? 'Asking about selected document' : 'Asking across all documents')
          }
        </div>
      </div>
    </main>
  )
}
