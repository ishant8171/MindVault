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
    <form className="editor-form" onSubmit={submit} style={{border:'1px solid #ddd', padding:10, marginBottom:10}}>
      <div><input placeholder="Name" value={name} onChange={e=>setName(e.target.value)} /></div>
      <div><input placeholder="Category" value={category} onChange={e=>setCategory(e.target.value)} /></div>
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
        {initial.id && onCancel && <button type="button" onClick={onCancel} style={{marginLeft: 8}}>Cancel</button>}
      </div>
      {err && <div style={{color:'red'}}>{err}</div>}
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
    <main className="page-shell" style={{padding:20}}>
      <div className="page-heading"><div><div className="eyebrow">Keep learning</div><h2>Skills</h2><p className="muted">See what is growing, active, and ready to share.</p></div></div>
      <SkillForm onSave={handleSave} token={token} />
      {loading && <div>Loading...</div>}
      {skills.length===0 && !loading && <div>No skills</div>}
      <ul className="item-list">
        {skills.map(s=> (
          <li className="item-card" key={s.id} style={{border:'1px solid #eee', padding:8, marginBottom:6}}>
            <div><strong>{s.name}</strong> — {s.category} — {s.status}</div>
            <div>
              <button onClick={()=>setEditing(editing && editing.id===s.id ? null : s)}>
                {editing && editing.id===s.id ? 'Cancel' : 'Edit'}
              </button>
              <button onClick={()=>handleDelete(s)}>Delete</button>
            </div>
            {editing && editing.id===s.id && <SkillForm initial={editing} onSave={handleSave} onCancel={()=>setEditing(null)} token={token} />}
          </li>
        ))}
      </ul>
    </main>
  )
}
