import React, { useEffect, useState } from 'react'
import api from '../services/api'
import { useAuth } from '../services/auth'

function SkillForm({ initial = {}, onSave, onCancel, token }){
  const [name, setName] = useState(initial.name || '')
  const [category, setCategory] = useState(initial.category || '')
  const [status, setStatus] = useState(initial.status || 'not_started')
  const [err, setErr] = useState(null)

  const submit = async (e)=>{
    e && e.preventDefault()
    setErr(null)
    try{
      const body = { name, category, status }
      if(initial.id){
        const updated = await api.patch(`/skills/${initial.id}`, body, token)
        onSave(updated)
      } else {
        const created = await api.post('/skills/', body, token)
        setName('')
        setCategory('')
        setStatus('not_started')
        onSave(created)
      }
    }catch(ex){ setErr(ex.message) }
  }

  return (
    <form className="editor-form" onSubmit={submit} style={{ border: '1px solid rgba(139, 92, 246, 0.25)', borderRadius: 16, padding: 18, marginBottom: 20, background: 'rgba(24, 19, 53, 0.7)', backdropFilter: 'blur(16px)', boxShadow: '0 20px 45px -15px rgba(5, 4, 15, 0.7)' }}>
      <div><input placeholder="Skill Name (e.g. System Design)" value={name} onChange={e=>setName(e.target.value)} /></div>
      <div><input placeholder="Category (e.g. Architecture)" value={category} onChange={e=>setCategory(e.target.value)} /></div>
      <div>
        <label>Status</label>
        <select value={status} onChange={e=>setStatus(e.target.value)}>
          <option value="not_started">not_started</option>
          <option value="learning">learning</option>
          <option value="completed">completed</option>
        </select>
      </div>
      <div>
        <button type="submit">{initial.id ? 'Save' : 'Create'}</button>
        {initial.id && onCancel && <button type="button" onClick={onCancel} style={{ marginLeft: 10, background: 'rgba(255, 255, 255, 0.08)', border: '1px solid rgba(139, 92, 246, 0.25)', color: '#e2e8f0', boxShadow: 'none' }}>Cancel</button>}
      </div>
      {err && <div style={{ color: '#fca5a5', marginTop: 8 }}>{err}</div>}
    </form>
  )
}

export default function Skills(){
  const { token } = useAuth()
  const [skills, setSkills] = useState([])
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState(null)

  useEffect(()=>{
    if(!token) return
    setLoading(true)
    api.get('/skills/', token).then(s=>setSkills(s)).catch(()=>{}).finally(()=>setLoading(false))
  },[token])

  const handleSave = (s)=>{
    setSkills(prev=>{
      const idx = prev.findIndex(x=>x.id===s.id)
      if(idx>=0){ const copy=[...prev]; copy[idx]=s; return copy }
      return [s, ...prev]
    })
    setEditing(null)
  }

  const handleDelete = async (s)=>{
    if(!confirm('Delete skill?')) return
    try{
      await api.del(`/skills/${s.id}`, token)
      setSkills(prev=>prev.filter(x=>x.id!==s.id))
    }catch(ex){ alert('Failed to delete skill: '+ex.message) }
  }

  return (
    <main className="page-shell" style={{ padding: 24 }}>
      <div className="page-heading"><div><div className="eyebrow">Keep learning</div><h2>Skills</h2><p className="muted">See what is growing, active, and ready to share.</p></div></div>
      <SkillForm onSave={handleSave} token={token} />
      {loading && <div>Loading...</div>}
      {skills.length===0 && !loading && <div className="empty-state">No skills recorded yet. Add your first skill above.</div>}
      <ul className="item-list">
        {skills.map(s=> (
          <li className="item-card" key={s.id} style={{ border: '1px solid rgba(139, 92, 246, 0.22)', padding: 18, borderRadius: 16, marginBottom: 10, background: 'rgba(22, 18, 48, 0.65)', backdropFilter: 'blur(16px)' }}>
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
              <strong style={{ fontSize: '1.1em', color: '#ffffff' }}>{s.name}</strong>
              <span style={{ background: 'rgba(139, 92, 246, 0.2)', color: '#c4b5fd', border: '1px solid rgba(139, 92, 246, 0.35)', padding: '2px 10px', borderRadius: 9999, fontSize: '0.8em', fontWeight: 600 }}>{s.category}</span>
              <span style={{ background: s.status === 'completed' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 107, 74, 0.15)', color: s.status === 'completed' ? '#34d399' : 'var(--coral)', border: '1px solid ' + (s.status === 'completed' ? 'rgba(16, 185, 129, 0.35)' : 'rgba(255, 107, 74, 0.35)'), padding: '2px 10px', borderRadius: 9999, fontSize: '0.8em', fontWeight: 700 }}>{s.status}</span>
            </div>
            <div style={{ marginTop: 12 }}>
              <button className="quiet-button" onClick={()=>setEditing(editing && editing.id===s.id ? null : s)} style={{ marginRight: 8, padding: '5px 14px', fontSize: '0.82em' }}>
                {editing && editing.id===s.id ? 'Cancel' : 'Edit'}
              </button>
              <button onClick={()=>handleDelete(s)} style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.35)', color: '#fca5a5', boxShadow: 'none', padding: '5px 14px', fontSize: '0.82em' }}>Delete</button>
            </div>
            {editing && editing.id===s.id && <SkillForm initial={editing} onSave={handleSave} onCancel={()=>setEditing(null)} token={token} />}
          </li>
        ))}
      </ul>
    </main>
  )
}
