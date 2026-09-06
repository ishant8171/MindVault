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
    <form className="editor-form" onSubmit={submit} style={{border:'1px solid #ddd', padding:10, marginBottom:10}}>
      <div><textarea rows={3} placeholder="Content" value={content} onChange={e=>setContent(e.target.value)} style={{width:'100%'}} /></div>
      <div>
        <label>Category&nbsp;
          <select value={category} onChange={e=>setCategory(e.target.value)}>
            {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
      </div>
      <div>
        <label>Importance</label>
        <input type="range" min={0} max={1} step={0.01} value={importance} onChange={e=>setImportance(Number(e.target.value))} /> {importance}
      </div>
      <div>
        <label>Confidence</label>
        <input type="range" min={0} max={1} step={0.01} value={confidence} onChange={e=>setConfidence(Number(e.target.value))} /> {confidence}
      </div>
      <div><input placeholder="slot_key (optional)" value={slot_key} onChange={e=>setSlotKey(e.target.value)} /></div>
      <div><button type="submit">{initial.id ? 'Save' : 'Create'}</button></div>
      {err && <div style={{color:'red'}}>{err}</div>}
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
    <main className="page-shell" style={{padding:20}}>
      <div className="page-heading"><div><div className="eyebrow">Your archive</div><h2>Memories</h2><p className="muted">Keep the details that make your context richer.</p></div></div>
      <MemoryForm onSave={handleSave} onConflict={setConflict} token={token} />
      {conflict && (
        <div className="conflict-box" style={{border:'1px solid orange', padding:10}}>
          <h4>Conflict detected</h4>
          <div>Existing: {conflict.existing?.content}</div>
          <div>Candidate: {conflict.candidate?.content}</div>
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
      {memories.length===0 && !loading && <div>No memories</div>}
      <ul className="item-list">
        {memories.map(m=> (
          <li className="item-card" key={m.id} style={{border:'1px solid #eee', padding:8, marginBottom:6}}>
            <div><strong>{m.content.slice(0,120)}</strong></div>
            <div>Category: {m.category} — Importance: {m.importance_score} — Confidence: {m.confidence_score} — Status: {m.status}</div>
            <div>
              <button onClick={()=>setEditing(m)}>Edit</button>
              <button onClick={()=>handleDelete(m)}>Delete</button>
            </div>
            {editing && editing.id===m.id && <MemoryForm initial={editing} onSave={handleSave} token={token} />}
          </li>
        ))}
      </ul>
    </main>
  )
}
