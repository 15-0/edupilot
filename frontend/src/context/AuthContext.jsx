import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api, { getToken, setToken } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!getToken()) { setReady(true); return }
    api.get('/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => setToken(null))
      .finally(() => setReady(true))
  }, [])

  useEffect(() => {
    const onLogout = () => setUser(null)
    window.addEventListener('edupilot:logout', onLogout)
    return () => window.removeEventListener('edupilot:logout', onLogout)
  }, [])

  const handleAuth = (data) => {
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }
  const login = useCallback(async (email, password) =>
    handleAuth((await api.post('/auth/login', { email, password })).data), [])
  const register = useCallback(async (payload) =>
    handleAuth((await api.post('/auth/register', payload)).data), [])
  const logout = useCallback(() => { setToken(null); setUser(null) }, [])

  return (
    <AuthContext.Provider value={{ user, ready, login, register, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
