import React, { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }){
  // Keep the JWT in memory so signing out or closing the tab clears the session.
  const [token, setToken] = useState(null)

  const login = async (email, password) => {
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    const res = await fetch((import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000') + '/auth/login', { method: 'POST', body: form })
    if(!res.ok) throw new Error(await res.text())
    const data = await res.json()
    setToken(data.access_token)
    return data
  }

  const logout = ()=> setToken(null)

  return <AuthContext.Provider value={{ token, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth(){ return useContext(AuthContext) }
