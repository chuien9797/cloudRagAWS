import { User, Bot } from 'lucide-react'

function renderInlineCitations(text, onCitationClick, keyPrefix) {
  const parts = text.split(/(\[\d+(?:\s*,\s*\d+)*\])/g)
  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+(?:\s*,\s*\d+)*)\]$/)
    if (match) {
      return match[1].split(/\s*,\s*/).map((label, j) => {
        const num = parseInt(label, 10) - 1
        return (
          <sup
            key={`${keyPrefix}-${i}-${j}`}
            onClick={() => onCitationClick(num)}
            style={{
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              minWidth: '16px', height: '16px',
              borderRadius: '50%',
              background: 'var(--accent)',
              color: '#fff',
              fontSize: '9px', fontWeight: 700,
              cursor: 'pointer',
              marginLeft: '2px',
              verticalAlign: 'super',
              transition: 'background 0.15s',
              userSelect: 'none',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--accent-hover)'}
            onMouseLeave={e => e.currentTarget.style.background = 'var(--accent)'}
          >
            {label}
          </sup>
        )
      })
    }

    const boldParts = part.split(/(\*\*.*?\*\*)/g)
    return boldParts.map((boldPart, k) => {
      const boldMatch = boldPart.match(/^\*\*(.*?)\*\*$/)
      if (boldMatch) {
        return <strong key={`${keyPrefix}-${i}-${k}`}>{boldMatch[1]}</strong>
      }
      return <span key={`${keyPrefix}-${i}-${k}`}>{boldPart}</span>
    })
  })
}

function renderAssistantContent(text, onCitationClick) {
  const lines = text.split('\n').filter(line => line.trim() !== '')

  return lines.map((line, index) => {
    const trimmed = line.trim()

    if (/^\*\*.*?:\*\*$/.test(trimmed)) {
      const title = trimmed.replace(/^\*\*(.*):\*\*$/, '$1')
      return (
        <div
          key={`heading-${index}`}
          style={{
            fontSize: '14px',
            fontWeight: 700,
            color: 'var(--text-primary)',
            marginTop: index === 0 ? 0 : '14px',
            marginBottom: '6px',
          }}
        >
          {title}
        </div>
      )
    }

    if (/^\d+\.\s/.test(trimmed)) {
      const label = trimmed.match(/^(\d+\.)\s/)?.[1] || ''
      const body = trimmed.replace(/^\d+\.\s/, '')
      return (
        <div key={`ordered-${index}`} style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
          <div style={{ minWidth: '20px', fontWeight: 700, color: 'var(--text-secondary)' }}>{label}</div>
          <div style={{ flex: 1 }}>{renderInlineCitations(body, onCitationClick, `ordered-${index}`)}</div>
        </div>
      )
    }

    if (/^[-*]\s/.test(trimmed)) {
      const body = trimmed.replace(/^[-*]\s/, '')
      return (
        <div key={`bullet-${index}`} style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
          <div style={{ minWidth: '12px', fontWeight: 700, color: 'var(--text-secondary)' }}>•</div>
          <div style={{ flex: 1 }}>{renderInlineCitations(body, onCitationClick, `bullet-${index}`)}</div>
        </div>
      )
    }

    return (
      <p
        key={`para-${index}`}
        style={{
          margin: 0,
          marginTop: index === 0 ? 0 : '10px',
          lineHeight: '1.75',
        }}
      >
        {renderInlineCitations(trimmed, onCitationClick, `para-${index}`)}
      </p>
    )
  })
}

export default function MessageBubble({ message, onCitationClick }) {
  const isUser = message.role === 'user'

  return (
    <div style={{
      display: 'flex',
      flexDirection: isUser ? 'row-reverse' : 'row',
      gap: '10px',
      alignItems: 'flex-start',
      marginBottom: '20px',
      animation: 'fadeIn 0.2s ease',
    }}>
      <div style={{
        width: 28, height: 28, borderRadius: '50%',
        background: isUser ? 'var(--accent)' : 'var(--surface-2)',
        border: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>
        {isUser
          ? <User size={13} color="#fff" />
          : <Bot size={13} color="var(--text-secondary)" />
        }
      </div>

      <div style={{
        maxWidth: '75%',
        background: isUser ? 'var(--accent)' : 'var(--surface)',
        color: isUser ? '#fff' : 'var(--text-primary)',
        borderRadius: isUser ? '14px 4px 14px 14px' : '4px 14px 14px 14px',
        padding: isUser ? '10px 14px' : '14px 16px',
        fontSize: '13.5px',
        lineHeight: '1.7',
        boxShadow: 'var(--shadow-sm)',
        border: isUser ? 'none' : '1px solid var(--border-light)',
      }}>
        {isUser
          ? message.content
          : renderAssistantContent(message.content, onCitationClick)
        }
      </div>
    </div>
  )
}
