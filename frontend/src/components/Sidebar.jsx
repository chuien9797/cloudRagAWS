import { useState, useRef } from 'react'
import { Upload, FileText, MessageSquare, Plus, Trash2, Loader, Lock, Globe2 } from 'lucide-react'
import { uploadDocument, deleteDocument, fetchSessionMessages, updateDocumentVisibility, deleteSession } from '../api.js'

function StatusBadge({ status }) {
  const map = {
    indexed: { label: 'Indexed', color: 'var(--success)' },
    processing: { label: 'Processing', color: 'var(--warning)' },
    uploading: { label: 'Uploading', color: 'var(--warning)' },
    failed: { label: 'Failed', color: 'var(--error)' },
  }
  const s = map[status] || { label: status, color: 'var(--text-tertiary)' }
  return <span style={{ fontSize: '11px', color: s.color, fontWeight: 500 }}>{s.label}</span>
}

function VisibilityBadge({ isPublic }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 3,
      fontSize: '11px', color: 'var(--text-tertiary)',
    }}>
      {isPublic ? <Globe2 size={10} /> : <Lock size={10} />}
      {isPublic ? 'Shared' : 'Private'}
    </span>
  )
}

export default function Sidebar({
  documents, sessions, selectedDocId,
  onSelectDoc, onUploadComplete, onDeleteDoc,
  onSessionSelect, onNewChat, onSessionsChange, loading, currentUserId,
}) {
  const [uploading, setUploading] = useState(false)
  const [uploadErr, setUploadErr] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [uploadPublic, setUploadPublic] = useState(false)
  const [updatingVisibilityId, setUpdatingVisibilityId] = useState(null)
  const [documentView, setDocumentView] = useState('all')
  const [deletingSessionId, setDeletingSessionId] = useState(null)
  const fileRef = useRef()

  const filteredDocuments = documents.filter((doc) => {
    const isOwner = doc.owner_user_id === currentUserId
    if (documentView === 'private') return isOwner && !doc.is_public
    if (documentView === 'shared') return doc.is_public
    return true
  })

  async function handleUpload(e) {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    setUploadErr(null)
    try {
      await uploadDocument(file, uploadPublic)
      await onUploadComplete()
    } catch (err) {
      setUploadErr(err.message)
    } finally {
      setUploading(false)
      fileRef.current.value = ''
    }
  }

  async function handleDelete(e, docId) {
    e.stopPropagation()
    setDeletingId(docId)
    try {
      await deleteDocument(docId)
      await onDeleteDoc()
    } catch (err) {
      setUploadErr(err.message)
    } finally {
      setDeletingId(null)
    }
  }

  async function handleVisibilityToggle(e, doc) {
    e.stopPropagation()
    setUpdatingVisibilityId(doc.id)
    setUploadErr(null)
    try {
      await updateDocumentVisibility(doc.id, !doc.is_public)
      await onUploadComplete()
    } catch (err) {
      setUploadErr(err.message)
    } finally {
      setUpdatingVisibilityId(null)
    }
  }

  async function handleSessionClick(session) {
    try {
      const msgs = await fetchSessionMessages(session.id)
      onSessionSelect(session.id, msgs.map(m => ({
        role: m.role,
        content: m.content,
      })))
    } catch (e) {
      console.error(e)
    }
  }

  async function handleDeleteSession(e, sessionId) {
    e.stopPropagation()
    setDeletingSessionId(sessionId)
    try {
      await deleteSession(sessionId)
      await onSessionsChange()
      onNewChat()
    } catch (err) {
      setUploadErr(err.message)
    } finally {
      setDeletingSessionId(null)
    }
  }

  return (
    <aside style={{
      width: 'var(--sidebar-w)',
      flexShrink: 0,
      background: 'var(--surface)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      <div style={{ padding: '12px' }}>
        <button onClick={onNewChat} style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: '8px',
          padding: '8px 12px', borderRadius: 'var(--radius-md)',
          background: 'var(--accent)', color: '#fff',
          fontSize: '13px', fontWeight: 500,
          transition: 'background 0.15s',
        }}
        onMouseEnter={e => e.currentTarget.style.background = 'var(--accent-hover)'}
        onMouseLeave={e => e.currentTarget.style.background = 'var(--accent)'}
        >
          <Plus size={14} />
          New chat
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '0 12px 12px' }}>
        <div style={{ marginBottom: '20px' }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginBottom: '8px', gap: 6,
          }}>
            <span style={{
              fontSize: '11px', fontWeight: 600, letterSpacing: '0.06em',
              textTransform: 'uppercase', color: 'var(--text-tertiary)',
            }}>
              Documents
            </span>
            <button
              onClick={() => setUploadPublic(value => !value)}
              title={uploadPublic ? 'New uploads are shared' : 'New uploads are private'}
              style={{
                display: 'flex', alignItems: 'center', gap: '4px',
                padding: '4px 7px',
                borderRadius: 'var(--radius-sm)',
                background: uploadPublic ? 'var(--accent-light)' : 'var(--surface-2)',
                color: uploadPublic ? 'var(--accent)' : 'var(--text-secondary)',
                fontSize: '10px', fontWeight: 600,
              }}
            >
              {uploadPublic ? <Globe2 size={11} /> : <Lock size={11} />}
              {uploadPublic ? 'Shared' : 'Private'}
            </button>
            <button
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              style={{
                display: 'flex', alignItems: 'center', gap: '4px',
                padding: '3px 8px', borderRadius: 'var(--radius-sm)',
                background: 'var(--surface-2)', color: 'var(--text-secondary)',
                fontSize: '11px', fontWeight: 500,
                transition: 'background 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--border)'}
              onMouseLeave={e => e.currentTarget.style.background = 'var(--surface-2)'}
            >
              {uploading ? <Loader size={11} className="spinning" /> : <Upload size={11} />}
              {uploading ? 'Uploading...' : 'Upload'}
            </button>
            <input
              ref={fileRef}
              type="file"
              style={{ display: 'none' }}
              accept=".pdf,.docx,.txt,.csv,.log"
              onChange={handleUpload}
            />
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr 1fr',
            gap: 4,
            marginBottom: '8px',
          }}>
            {[
              { key: 'all', label: 'All' },
              { key: 'private', label: 'Private' },
              { key: 'shared', label: 'Shared' },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setDocumentView(tab.key)}
                style={{
                  padding: '5px 6px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid',
                  borderColor: documentView === tab.key ? '#bfdbfe' : 'var(--border)',
                  background: documentView === tab.key ? 'var(--accent-light)' : 'var(--surface)',
                  color: documentView === tab.key ? 'var(--accent)' : 'var(--text-secondary)',
                  fontSize: '11px',
                  fontWeight: 600,
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {uploadErr && (
            <div style={{
              fontSize: '11px', color: 'var(--error)',
              background: '#fef2f2', border: '1px solid #fecaca',
              borderRadius: 'var(--radius-sm)',
              padding: '6px 8px', marginBottom: '8px',
            }}>
              {uploadErr}
            </div>
          )}

          {loading ? (
            <div style={{ color: 'var(--text-tertiary)', fontSize: '12px', padding: '8px 0' }}>
              Loading...
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div style={{ color: 'var(--text-tertiary)', fontSize: '12px', padding: '8px 0' }}>
              No documents in this view
            </div>
          ) : (
            filteredDocuments.map(doc => {
              const isOwner = doc.owner_user_id === currentUserId
              return (
                <div
                  key={doc.id}
                  onClick={() => onSelectDoc(selectedDocId === doc.id ? null : doc.id)}
                  style={{
                    display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
                    gap: '6px', padding: '8px 10px',
                    borderRadius: 'var(--radius-md)',
                    background: selectedDocId === doc.id ? 'var(--accent-light)' : 'transparent',
                    border: selectedDocId === doc.id ? '1px solid #bfdbfe' : '1px solid transparent',
                    cursor: 'pointer', marginBottom: '2px',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => {
                    if (selectedDocId !== doc.id) e.currentTarget.style.background = 'var(--surface-2)'
                  }}
                  onMouseLeave={e => {
                    if (selectedDocId !== doc.id) e.currentTarget.style.background = 'transparent'
                  }}
                >
                  <div style={{ display: 'flex', gap: '8px', flex: 1, minWidth: 0 }}>
                    <FileText size={14} style={{ flexShrink: 0, marginTop: 2, color: 'var(--text-tertiary)' }} />
                    <div style={{ minWidth: 0 }}>
                      <div style={{
                        fontSize: '12px', fontWeight: 500,
                        color: 'var(--text-primary)',
                        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                      }}>
                        {doc.filename}
                      </div>
                      <div style={{ display: 'flex', gap: '6px', marginTop: '2px', flexWrap: 'wrap' }}>
                        <StatusBadge status={doc.status} />
                        <VisibilityBadge isPublic={doc.is_public} />
                        {!isOwner && (
                          <span style={{ fontSize: '11px', color: 'var(--accent)' }}>View-only</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {isOwner && (
                    <button
                      onClick={(e) => handleVisibilityToggle(e, doc)}
                      disabled={updatingVisibilityId === doc.id}
                      title={doc.is_public ? 'Make private' : 'Share with other users'}
                      style={{
                        flexShrink: 0, padding: '2px',
                        color: doc.is_public ? 'var(--accent)' : 'var(--text-tertiary)',
                        borderRadius: 'var(--radius-sm)',
                      }}
                    >
                      {updatingVisibilityId === doc.id
                        ? <Loader size={12} className="spinning" />
                        : doc.is_public ? <Globe2 size={12} /> : <Lock size={12} />
                      }
                    </button>
                  )}

                  <button
                    onClick={(e) => handleDelete(e, doc.id)}
                    disabled={!isOwner || deletingId === doc.id}
                    title={isOwner ? 'Delete document' : 'Only the owner can delete this document'}
                    style={{
                      flexShrink: 0, padding: '2px',
                      color: isOwner ? 'var(--text-tertiary)' : 'var(--border)',
                      borderRadius: 'var(--radius-sm)',
                      transition: 'color 0.15s',
                    }}
                    onMouseEnter={e => { if (isOwner) e.currentTarget.style.color = 'var(--error)' }}
                    onMouseLeave={e => { if (isOwner) e.currentTarget.style.color = 'var(--text-tertiary)' }}
                  >
                    {deletingId === doc.id
                      ? <Loader size={12} className="spinning" />
                      : <Trash2 size={12} />
                    }
                  </button>
                </div>
              )
            })
          )}
        </div>

        {sessions.length > 0 && (
          <div>
            <div style={{
              fontSize: '11px', fontWeight: 600, letterSpacing: '0.06em',
              textTransform: 'uppercase', color: 'var(--text-tertiary)',
              marginBottom: '8px',
            }}>
              History
            </div>
            {sessions.map(session => (
              <div
                key={session.id}
                onClick={() => handleSessionClick(session)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'space-between',
                  padding: '7px 10px',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  marginBottom: '2px',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-2)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
                  <MessageSquare size={13} style={{ flexShrink: 0, color: 'var(--text-tertiary)' }} />
                  <span style={{
                    fontSize: '12px', color: 'var(--text-secondary)',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {session.title}
                  </span>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(e, session.id)}
                  disabled={deletingSessionId === session.id}
                  title="Delete chat"
                  style={{
                    flexShrink: 0,
                    padding: '2px',
                    color: 'var(--text-tertiary)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--error)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-tertiary)'}
                >
                  {deletingSessionId === session.id
                    ? <Loader size={12} className="spinning" />
                    : <Trash2 size={12} />
                  }
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  )
}
