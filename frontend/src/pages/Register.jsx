import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'

export default function Register(){
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState(null)
  const nav = useNavigate()

  const submit = async (e)=>{
    e.preventDefault()
    try{
      const res = await fetch((import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000') + '/auth/register', { method: 'POST', headers: { 'Content-Type':'application/json' }, body: JSON.stringify({ email, username, password }) })
      if(!res.ok) throw new Error(await res.text())
      nav('/login')
    }catch(ex){ setErr(ex.message) }
  }

  return (
    <div className="auth-page" style={{padding:20}}>
      <div className="auth-panel">
        <div className="eyebrow">Start with a clear mind</div>
        <h2>Create your vault</h2>
        <p className="muted">Capture ideas, goals, and the things worth remembering.</p>
      <form onSubmit={submit}>
        <label>Email<input placeholder="email" value={email} onChange={e=>setEmail(e.target.value)} /></label>
        <label>Username<input placeholder="username" value={username} onChange={e=>setUsername(e.target.value)} /></label>
        <label>Password<input placeholder="password" type="password" value={password} onChange={e=>setPassword(e.target.value)} /></label>
        <button type="submit">Register</button>
      </form>
      {err && <div style={{color:'red'}}>{err}</div>}
      <p style={{marginTop:12,fontSize:'0.875rem'}}>Already have an account? <Link to="/login">Sign in</Link></p>
      </div>
    </div>
  )
}
