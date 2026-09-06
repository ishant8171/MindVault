import React from 'react'
import { Routes, Route, Link, useNavigate } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Goals from './pages/Goals'
import Skills from './pages/Skills'
import Memories from './pages/Memories'
import Assistant from './pages/Assistant'
import Documents from './pages/Documents'
import { AuthProvider, useAuth } from './services/auth'
import ProtectedRoute from './components/ProtectedRoute'

function NavBar() {
  const { token, logout } = useAuth()
  const nav = useNavigate()

  const handleLogout = () => {
    logout()
    nav('/login')
  }

  return (
    <nav className="app-nav">
      <Link className="brand" to="/"><span className="brand-mark">M</span><span>MindVault</span></Link>
      <div className="nav-links">
        {token ? (
          <>
            <Link to="/">Dashboard</Link>
            <Link to="/goals">Goals</Link>
            <Link to="/skills">Skills</Link>
            <Link to="/memories">Memories</Link>
            <Link to="/chat">Chat</Link>
            <Link to="/documents">Documents</Link>
            <button onClick={handleLogout} style={{background:'none',border:'none',cursor:'pointer',color:'inherit',font:'inherit',padding:'0 8px'}}>Logout</button>
          </>
        ) : (
          <>
            <Link to="/login">Login</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <NavBar />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/goals" element={<ProtectedRoute><Goals/></ProtectedRoute>} />
        <Route path="/skills" element={<ProtectedRoute><Skills/></ProtectedRoute>} />
        <Route path="/memories" element={<ProtectedRoute><Memories/></ProtectedRoute>} />
        <Route path="/chat" element={<ProtectedRoute><Assistant/></ProtectedRoute>} />
        <Route path="/assistant" element={<ProtectedRoute><Assistant/></ProtectedRoute>} />
        <Route path="/documents" element={<ProtectedRoute><Documents/></ProtectedRoute>} />
        <Route path="/" element={<ProtectedRoute><Dashboard/></ProtectedRoute>} />
      </Routes>
    </AuthProvider>
  )
}
