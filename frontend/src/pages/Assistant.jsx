import React, { useState } from 'react'
import api from '../services/api'
import { useAuth } from '../services/auth'

export default function Assistant(){
  const { token } = useAuth()
  const [question, setQuestion] = useState('')
  const [conversationId, setConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const ask = async (event) => {
    event.preventDefault()
    const text = question.trim()
    if (!text || busy) return
    setError(null)
    setQuestion('')
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setBusy(true)
    try {
      const result = await api.post('/assistant/ask', { question: text, conversation_id: conversationId }, token)
      setConversationId(result.conversation_id)
      setMessages(prev => [...prev, { role: 'assistant', content: result.response }])
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="page-shell chat-page">
      <div className="page-heading">
        <div><div className="eyebrow">Virtual brain</div><h2>Assistant</h2><p className="muted">Ask questions and let MindVault assemble your context from memory, concepts, goals, and documents.</p></div>
      </div>
      <section className="chat-panel assistant-panel">
        <div className="message-list">
          {messages.length === 0 && <div className="empty-state">Your conversation will appear here. Ask something connected to what you are learning.</div>}
          {messages.map((message, index) => <div className={`message message-${message.role}`} key={`${message.role}-${index}`}><span className="message-label">{message.role === 'user' ? 'You' : 'MindVault'}</span><p>{message.content}</p></div>)}
          {busy && <div className="message message-assistant"><span className="message-label">MindVault</span><p>Assembling your context...</p></div>}
        </div>
        {error && <div className="error-banner">{error}</div>}
        <form className="chat-composer" onSubmit={ask}>
          <textarea value={question} onChange={event => setQuestion(event.target.value)} placeholder="Ask about your goals, concepts, or learning direction..." rows={3} />
          <button type="submit" disabled={busy || !question.trim()}>{busy ? 'Thinking...' : 'Ask assistant'}</button>
        </form>
      </section>
    </main>
  )
}
