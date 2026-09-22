import React, { useEffect, useState } from 'react'
import api from '../services/api'
import { useAuth } from '../services/auth'

const CATEGORIES = [
  'personal', 'preference', 'goal', 'skill', 'education',
  'project', 'habit', 'interest', 'important_event', 'temporary', 'other'
]

function MemoryForm({ initial = {}, onSave, onConflict, token }){
  const [content, setContent] = useState(initial.content || '')
  const [category, setCategory] = useState(initial.category || 'other')
  const [importance, setImportance] = useState(initial.importance_score ?? 0.5)
  const [confidence, setConfidence] = useState(initial.confidence_score ?? 0.5)
  const [slot_key, setSlotKey] = useState(initial.slot_key || '')
  const [err, setErr] = useState(null)

  const submit = async (e)=>{
    e && e.preventDefault()
    setErr(null)
    try{
      const body = { content, category, importance_score: importance, confidence_score: confidence, slot_key: slot_key || null }
      if(initial.id){
        const updated = await api.patch(`/memories/${initial.id}`, body, token)
        onSave(updated)
      } else {
        const created = await api.post('/memories/', body, token)
        setContent('')
        setSlotKey('')
        onSave(created)
      }
    }catch(ex){
      // Try to parse a 409 conflict — api.js throws Error(responseText)
      // responseText is {"detail": {...conflict...}}
      try{
        const parsed = JSON.parse(ex.message)
        const detail = parsed.detail || parsed
        if(detail.conflict_id && onConflict){
          onConflict(detail)
          return
        }
      }catch(_){}
      setErr(ex.message)
    }
  }

  return (
    <form className="editor-form" onSubmit={submit} style={{ border: '1px solid rgba(139, 92, 246, 0.25)', borderRadius: 16, padding: 20, marginBottom: 20, background: 'rgba(24, 19, 53, 0.7)', backdropFilter: 'blur(16px)', boxShadow: '0 20px 45px -15px rgba(5, 4, 15, 0.7)' }}>
      <div style={{ width: '100%' }}><textarea rows={3} placeholder="Memory content or learned fact..." value={content} onChange={e=>setContent(e.target.value)} style={{ width: '100%' }} /></div>
      <div>
        <label>Category&nbsp;
          <select value={category} onChange={e=>setCategory(e.target.value)}>
            {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
      </div>
      <div>
        <label>Importance</label>
        <input type="range" min={0} max={1} step={0.01} value={importance} onChange={e=>setImportance(Number(e.target.value))} />
        <span style={{ marginLeft: 8, fontWeight: 700, color: 'var(--coral)', fontFamily: "'Space Grotesk', sans-serif" }}>{importance}</span>
      </div>
      <div>
        <label>Confidence</label>
        <input type="range" min={0} max={1} step={0.01} value={confidence} onChange={e=>setConfidence(Number(e.target.value))} />
        <span style={{ marginLeft: 8, fontWeight: 700, color: 'var(--coral)', fontFamily: "'Space Grotesk', sans-serif" }}>{confidence}</span>
      </div>
      <div><input placeholder="slot_key (optional)" value={slot_key} onChange={e=>setSlotKey(e.target.value)} /></div>
      <div><button type="submit">{initial.id ? 'Save Memory' : 'Create Memory'}</button></div>
      {err && <div style={{ color: '#fca5a5', marginTop: 8 }}>{err}</div>}
    </form>
  )
}

export default function Memories(){
  const { token } = useAuth()
  const [memories, setMemories] = useState([])
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState(null)
  const [conflict, setConflict] = useState(null)

  useEffect(()=>{
    if(!token) return
    setLoading(true)
    api.get('/memories/', token).then(m=>setMemories(m)).catch(()=>{}).finally(()=>setLoading(false))
  },[token])

  const handleSave = (m)=>{
    setMemories(prev=>{
      const idx = prev.findIndex(x=>x.id===m.id)
      if(idx>=0){ const copy=[...prev]; copy[idx]=m; return copy }
      return [m, ...prev]
    })
    setEditing(null)
    setConflict(null)
  }

  const handleDelete = async (m)=>{
    if(!confirm('Delete memory?')) return
    try{
      await api.del(`/memories/${m.id}`, token)
      setMemories(prev=>prev.filter(x=>x.id!==m.id))
    }catch(ex){ alert('Delete failed: '+ex.message) }
  }

  const resolveConflict = async (conflictId, action, mergedContent) => {
    try{
      await api.post(`/memories/conflicts/${conflictId}/resolve`, { action, merged_content: mergedContent }, token)
      // refresh list
      const m = await api.get('/memories/', token)
      setMemories(m)
      setConflict(null)
    }catch(ex){ alert('Resolve error: '+ex.message) }
  }

  return (
    <main className="page-shell" style={{ padding: 24 }}>
      <div className="page-heading"><div><div className="eyebrow">Your archive</div><h2>Memories</h2><p className="muted">Keep the details that make your context richer.</p></div></div>
      <MemoryForm onSave={handleSave} onConflict={setConflict} token={token} />
      {conflict && (
        <div className="conflict-box">
          <h4>Conflict detected</h4>
          <div style={{ color: '#fed7aa', marginBottom: 4 }}>Existing: {conflict.existing?.content}</div>
          <div style={{ color: '#fed7aa', marginBottom: 8 }}>Candidate: {conflict.candidate?.content}</div>
          <div>
            <button onClick={()=>resolveConflict(conflict.conflict_id, 'keep_old')}>Keep Old</button>
            <button onClick={()=>resolveConflict(conflict.conflict_id, 'keep_new')}>Keep New</button>
            <button onClick={()=>{
              const merged = prompt('Merged content', conflict.candidate?.content || '')
              if(merged!==null) resolveConflict(conflict.conflict_id, 'merge', merged)
            }}>Merge</button>
          </div>
        </div>
      )}
      {loading && <div>Loading...</div>}
      {memories.length===0 && !loading && <div className="empty-state">No memories stored yet. Record facts or notes above.</div>}
      <ul className="item-list">
        {memories.map(m=> (
          <li className="item-card" key={m.id} style={{ border: '1px solid rgba(139, 92, 246, 0.22)', padding: 18, borderRadius: 16, marginBottom: 10, background: 'rgba(22, 18, 48, 0.65)', backdropFilter: 'blur(16px)' }}>
            <div><strong style={{ fontSize: '1.05em', color: '#ffffff' }}>{m.content.slice(0,120)}</strong></div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginTop: 8, fontSize: '0.82em' }}>
              <span style={{ background: 'rgba(139, 92, 246, 0.2)', color: '#c4b5fd', border: '1px solid rgba(139, 92, 246, 0.35)', padding: '2px 10px', borderRadius: 9999, fontWeight: 600 }}>{m.category}</span>
              <span style={{ background: 'rgba(255, 107, 74, 0.15)', color: 'var(--coral)', border: '1px solid rgba(255, 107, 74, 0.35)', padding: '2px 10px', borderRadius: 9999, fontWeight: 700 }}>Importance: {m.importance_score}</span>
              <span style={{ background: 'rgba(16, 185, 129, 0.18)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.35)', padding: '2px 10px', borderRadius: 9999, fontWeight: 700 }}>Confidence: {m.confidence_score}</span>
              <span style={{ background: 'rgba(255, 255, 255, 0.06)', color: '#cbd5e1', border: '1px solid rgba(255, 255, 255, 0.1)', padding: '2px 10px', borderRadius: 9999 }}>{m.status}</span>
            </div>
            <div style={{ marginTop: 12 }}>
              <button className="quiet-button" onClick={()=>setEditing(m)} style={{ marginRight: 8, padding: '5px 14px', fontSize: '0.82em' }}>Edit</button>
              <button onClick={()=>handleDelete(m)} style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.35)', color: '#fca5a5', boxShadow: 'none', padding: '5px 14px', fontSize: '0.82em' }}>Delete</button>
            </div>
            {editing && editing.id===m.id && <MemoryForm initial={editing} onSave={handleSave} token={token} />}
          </li>
        ))}
      </ul>
    </main>
  )
}
