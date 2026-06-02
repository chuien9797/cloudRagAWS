import { useState, useEffect, useRef } from 'react'
import { FileText, ChevronDown, ChevronUp, ExternalLink, BookOpen, Zap } from 'lucide-react'
import { openDocumentFile } from '../api.js'

function HighlightedExcerpt({ text, highlight }) {
  if (!text) return null
  if (!highlight || !text.toLowerCase().includes(highlight.toLowerCase())) {
    return <>{text}</>
  }

  const index = text.toLowerCase().indexOf(highlight.toLowerCase())
  const before = text.slice(0, index)
  const match = text.slice(index, index + highlight.length)
  const after = text.slice(index + highlight.length)
  return (
    <>
      {before}
      <mark style={{ background: '#fef08a', padding: '0 1px' }}>{match}</mark>
      {after}
    </>
  )
}

function SourceCard({ source, index, isHighlighted }) {
  const [expanded, setExpanded] = useState(false)
  const [actionError, setActionError] = useState(null)
  const cardRef = useRef()

  useEffect(() => {
    if (isHighlighted && cardRef.current) {
      setExpanded(true)
      cardRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [isHighlighted])

  const score = source.relevance_score != null
    ? (source.relevance_score > 1
        ? (source.relevance_score / 10).toFixed(2)
        : Math.abs(source.relevance_score).toFixed(2))
    : null

  async function handleOpen(pageNumber = null) {
    setActionError(null)
    if (!source.doc_id) {
      setActionError('Source document id is missing for this citation.')
      return
    }
    try {
      await openDocumentFile(source.doc_id, pageNumber)
    } catch (err) {
      setActionError(err.message)
    }
  }

  return (
    <div
      ref={cardRef}
      style={{
        background: 'var(--surface)',
        border: isHighlighted ? '1.5px solid var(--accent)' : '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        boxShadow: isHighlighted ? '0 0 0 3px rgba(37,99,235,0.1)' : 'var(--shadow-sm)',
        transition: 'border-color 0.2s, box-shadow 0.2s',
        marginBottom: '10px',
      }}
      className="fade-in"
    >
      {/* Card header */}
      <div style={{ padding: '12px 14px 0' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', flex: 1, minWidth: 0 }}>
            <div style={{
              width: 20, height: 20, borderRadius: '50%',
              background: isHighlighted ? 'var(--accent)' : 'var(--surface-2)',
              border: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, fontSize: '10px', fontWeight: 700,
              color: isHighlighted ? '#fff' : 'var(--text-tertiary)',
              transition: 'background 0.2s, color 0.2s',
            }}>
              {index + 1}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{
                fontSize: '12px', fontWeight: 600,
                color: 'var(--text-primary)',
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              }}>
                {source.citation || `[${index + 1}]`} {source.filename}
              </div>
              <div style={{ display: 'flex', gap: '8px', marginTop: '3px', flexWrap: 'wrap' }}>
                {source.page_number != null && (
                  <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                    Page {source.page_number}
                  </span>
                )}
                {source.paragraph_number != null && (
                  <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                    Paragraph {source.paragraph_number}
                  </span>
                )}
                {source.paragraph_number == null && source.chunk_id != null && source.chunk_id >= 0 && (
                  <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                    Chunk {source.chunk_id}
                  </span>
                )}
                {score != null && (
                  <span style={{
                    fontSize: '11px', color: 'var(--accent)', fontWeight: 500,
                    display: 'flex', alignItems: 'center', gap: '2px',
                  }}>
                    <Zap size={9} />
                    {score}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Collapse toggle */}
          <button
            onClick={() => setExpanded(v => !v)}
            style={{
              flexShrink: 0, padding: '2px',
              color: 'var(--text-tertiary)',
              borderRadius: 'var(--radius-sm)',
              transition: 'color 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--text-primary)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--text-tertiary)'}
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>

        {/* Chunk preview / expanded */}
        <div style={{
          marginTop: '10px',
          fontSize: '12px',
          lineHeight: '1.6',
          color: 'var(--text-secondary)',
          maxHeight: expanded ? '400px' : '52px',
          overflow: 'hidden',
          transition: 'max-height 0.25s ease',
        }}>
        {source.location && (
            <div style={{
              fontSize: '11px',
              fontWeight: 600,
              color: isHighlighted ? 'var(--accent)' : 'var(--text-tertiary)',
              marginBottom: '6px',
            }}>
              {source.location}
            </div>
          )}
          <HighlightedExcerpt
            text={source.chunk}
            highlight={isHighlighted ? (source.highlight_text || source.chunk_text || source.chunk) : null}
          />
        </div>

        {actionError && (
          <div style={{
            fontSize: '11px',
            color: 'var(--error)',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: 'var(--radius-sm)',
            padding: '6px 8px',
            marginTop: '8px',
          }}>
            {actionError}
          </div>
        )}

        {!expanded && (
          <div style={{
            fontSize: '11px', color: 'var(--accent)',
            cursor: 'pointer', marginTop: '4px',
            paddingBottom: '10px',
          }}
          onClick={() => setExpanded(true)}
          >
            Show more ↓
          </div>
        )}
      </div>

      {/* Actions */}
      <div style={{
        display: 'flex', gap: '6px',
        padding: '8px 14px',
        borderTop: '1px solid var(--border-light)',
        background: 'var(--surface-2)',
      }}>
        <button
        onClick={() => handleOpen(null)}
        style={{
          display: 'flex', alignItems: 'center', gap: '4px',
          padding: '4px 8px', borderRadius: 'var(--radius-sm)',
          background: 'var(--surface)', border: '1px solid var(--border)',
          fontSize: '11px', color: 'var(--text-secondary)',
          transition: 'background 0.15s, color 0.15s',
        }}
        onMouseEnter={e => { e.currentTarget.style.background = 'var(--accent-light)'; e.currentTarget.style.color = 'var(--accent)' }}
        onMouseLeave={e => { e.currentTarget.style.background = 'var(--surface)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
        title="Open original document"
        >
          <ExternalLink size={10} />
          Open PDF
        </button>
        {source.page_number != null && (
          <button
          onClick={() => handleOpen(source.page_number)}
          style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            padding: '4px 8px', borderRadius: 'var(--radius-sm)',
            background: 'var(--surface)', border: '1px solid var(--border)',
            fontSize: '11px', color: 'var(--text-secondary)',
            transition: 'background 0.15s, color 0.15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--accent-light)'; e.currentTarget.style.color = 'var(--accent)' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'var(--surface)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
          title={`Open original document at page ${source.page_number}`}
          >
            <BookOpen size={10} />
            Jump to page {source.page_number}
          </button>
        )}
      </div>
    </div>
  )
}

export default function SourcesPanel({ sources, tokenUsage, highlightedIndex }) {
  return (
    <aside style={{
      width: 'var(--sources-w)',
      flexShrink: 0,
      background: 'var(--bg)',
      borderLeft: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '14px 16px 10px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--surface)',
        flexShrink: 0,
      }}>
        <div style={{
          fontSize: '11px', fontWeight: 600, letterSpacing: '0.06em',
          textTransform: 'uppercase', color: 'var(--text-tertiary)',
        }}>
          Sources
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px' }}>
        {sources.length === 0 ? (
          <div style={{
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            height: '200px', gap: '8px',
            color: 'var(--text-tertiary)',
          }}>
            <FileText size={24} strokeWidth={1.5} />
            <span style={{ fontSize: '12px' }}>Sources appear here after each answer</span>
          </div>
        ) : (
          sources.map((source, i) => (
            <SourceCard
              key={i}
              source={source}
              index={i}
              isHighlighted={highlightedIndex === i}
            />
          ))
        )}
      </div>

      {/* Token usage */}
      {tokenUsage && (
        <div style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--border)',
          background: 'var(--surface)',
          flexShrink: 0,
        }}>
          <div style={{
            fontSize: '11px', fontWeight: 600, letterSpacing: '0.06em',
            textTransform: 'uppercase', color: 'var(--text-tertiary)',
            marginBottom: '8px',
          }}>
            Token usage
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            {[
              { label: 'Prompt',     value: tokenUsage.prompt_tokens },
              { label: 'Completion', value: tokenUsage.completion_tokens },
              { label: 'Total',      value: tokenUsage.total_tokens },
            ].map(({ label, value }) => (
              <div key={label} style={{ flex: 1 }}>
                <div style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>{label}</div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {value ?? '—'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </aside>
  )
}
