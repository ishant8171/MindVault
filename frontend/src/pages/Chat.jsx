import React, { useState } from 'react'
import api from '../services/api'
import { useAuth } from '../services/auth'

export default function Chat(){
  const { token } = useAuth()
  const [prompt, setPrompt] = useState('')
  const [reply, setReply] = useState(null)
  const [memoriesUsed, setMemoriesUsed] = useState([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)

  const send = async ()=>{
    if(!prompt.trim() || loading) return
    setLoading(true)
    setErr(null)
    try {
      const data = await api.post('/ai/chat', { prompt }, token)
      setReply(data.text)
      setMemoriesUsed(data.memories_used || [])
    } catch(ex) {
      setErr(ex.message)
      setReply(null)
      setMemoriesUsed([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page-shell chat-page" style={{ padding: 24 }}>
      <div className="page-heading"><div><div className="eyebrow">Think out loud</div><h2>Chat</h2><p className="muted">Ask your AI companion to help connect the context in your vault.</p></div></div>
      <div className="chat-panel">
        <textarea rows={6} value={prompt} onChange={e=>setPrompt(e.target.value)} style={{ width: '100%' }} placeholder="What are you thinking about?" />
        <div className="chat-actions">
          <button onClick={send} disabled={loading}>{loading ? 'Thinking...' : 'Send'}</button>
        </div>
        {err && <div className="error-banner">{err}</div>}
        {reply && (
          <div className="chat-reply" style={{ marginTop: 14, whiteSpace: 'pre-wrap' }}>
            {memoriesUsed.length > 0 && (
              <div style={{ fontSize: '0.85em', color: 'var(--coral)', marginBottom: 8, fontWeight: 600 }}>
                Vault context: {memoriesUsed.length} {memoriesUsed.length === 1 ? 'memory' : 'memories'} referenced
              </div>
            )}
            {reply}
          </div>
        )}
      </div>
    </main>
  )
}

