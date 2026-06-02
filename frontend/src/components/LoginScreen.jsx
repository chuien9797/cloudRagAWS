import { useState } from 'react'
import { Loader, LockKeyhole } from 'lucide-react'

export default function LoginScreen({ onLogin }) {
  const [email, setEmail] = useState('admin@cloudrag.local')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    if (loading) return
    setLoading(true)
    setError('')
    try {
      await onLogin(email, password)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'grid',
      placeItems: 'center',
      background: 'var(--bg)',
      padding: '24px',
    }}>
      <form
        onSubmit={handleSubmit}
        style={{
          width: '100%',
          maxWidth: 420,
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          boxShadow: 'var(--shadow-lg)',
          padding: '28px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
          <div style={{
            width: 38,
            height: 38,
            borderRadius: 10,
            background: 'var(--surface-2)',
            border: '1px solid var(--border)',
            display: 'grid',
            placeItems: 'center',
            color: 'var(--text-secondary)',
          }}>
            <LockKeyhole size={18} />
          </div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>Sign in</div>
            <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>CloudRAG workspace access</div>
          </div>
        </div>

        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
          Email
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="username"
          style={{
            width: '100%',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '10px 12px',
            fontSize: 14,
            background: 'var(--bg)',
            color: 'var(--text-primary)',
            marginBottom: 14,
          }}
        />

        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
          Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          style={{
            width: '100%',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '10px 12px',
            fontSize: 14,
            background: 'var(--bg)',
            color: 'var(--text-primary)',
          }}
        />

        {error && (
          <div style={{
            marginTop: 12,
            fontSize: 12,
            color: 'var(--error)',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '8px',
            padding: '8px 10px',
          }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !email.trim() || !password}
          style={{
            width: '100%',
            marginTop: 18,
            borderRadius: '8px',
            padding: '11px 14px',
            background: loading ? '#1f2937' : 'var(--accent)',
            color: '#fff',
            fontSize: 13,
            fontWeight: 700,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: 8,
          }}
        >
          {loading && <Loader size={14} className="spinning" />}
          {loading ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
