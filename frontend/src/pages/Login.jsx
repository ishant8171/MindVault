import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../services/auth'

export default function Login(){
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState(null)
  const auth = useAuth()
  const nav = useNavigate()

  const submit = async (e)=>{
    e.preventDefault()
    try{
      await auth.login(email, password)
      nav('/')
    }catch(ex){ setErr(ex.message) }
  }

  return (
    <div className="auth-page" style={{padding:20}}>
      <div className="auth-panel">
        <div className="eyebrow">Your personal knowledge space</div>
        <h2>Welcome back</h2>
        <p className="muted">Sign in to continue building your second brain.</p>
      <form onSubmit={submit}>
        <label>Email<input placeholder="email" value={email} onChange={e=>setEmail(e.target.value)} /></label>
        <label>Password<input placeholder="password" type="password" value={password} onChange={e=>setPassword(e.target.value)} /></label>
        <button type="submit">Login</button>
      </form>
      {err && <div style={{color:'red'}}>{err}</div>}
      <p style={{marginTop:12,fontSize:'0.875rem'}}>Don't have an account? <Link to="/register">Create one</Link></p>
      </div>
    </div>
  )
}
