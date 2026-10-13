import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import LoginScreen from './components/LoginScreen'
import Collections from './pages/Collections'
import Dashboard from './pages/Dashboard'
import Library from './pages/Library'
import Settings from './pages/Settings'
import Watch from './pages/Watch'
import api from './services/api'

export default function App() {
  const [auth, setAuth] = useState(null)

  useEffect(() => {
    let active = true
    api.get('/auth/status')
      .then(({ data }) => { if (active) setAuth(data) })
      .catch(() => { if (active) setAuth({ required: true, authenticated: false }) })
    const lock = () => setAuth(current => ({ required: current?.required ?? true, authenticated: false }))
    window.addEventListener('numeroflix:unauthorized', lock)
    return () => {
      active = false
      window.removeEventListener('numeroflix:unauthorized', lock)
    }
  }, [])

  if (!auth) return <div className="flex min-h-screen items-center justify-center bg-ink text-sm text-zinc-500">Opening NumeroFlix…</div>
  if (auth.required && !auth.authenticated) {
    return <LoginScreen onAuthenticated={() => setAuth({ required: true, authenticated: true })}/>
  }

  return <Layout><Routes><Route path="/" element={<Dashboard/>}/><Route path="/library" element={<Library/>}/><Route path="/collections" element={<Collections/>}/><Route path="/settings" element={<Settings/>}/><Route path="/watch/:id" element={<Watch/>}/><Route path="/movies/:id" element={<Watch/>}/><Route path="/movies/:id/play" element={<Watch/>}/></Routes></Layout>
}
