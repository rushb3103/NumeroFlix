import { Clapperboard, LockKeyhole } from 'lucide-react'
import { useState } from 'react'
import api from '../services/api'

export default function LoginScreen({ onAuthenticated }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async event => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await api.post('/auth/login', { password })
      setPassword('')
      onAuthenticated()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not unlock NumeroFlix.')
    } finally {
      setSubmitting(false)
    }
  }

  return <main className="flex min-h-screen items-center justify-center bg-ink p-5">
    <section className="w-full max-w-sm rounded-2xl border border-zinc-800 bg-panel p-8 shadow-2xl shadow-black/40">
      <div className="mb-8 flex items-center gap-3"><span className="rounded-xl bg-accent p-2"><Clapperboard size={22}/></span><div><h1 className="text-xl font-bold">NumeroFlix</h1><p className="text-xs text-zinc-500">Private library</p></div></div>
      <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-900 text-zinc-300"><LockKeyhole size={22}/></div>
      <h2 className="text-2xl font-semibold">Unlock your vault</h2>
      <p className="mt-2 text-sm leading-6 text-zinc-500">Enter the master password configured on this server.</p>
      <form onSubmit={submit} className="mt-6 space-y-3">
        <input autoFocus required type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} className="control w-full" placeholder="Master password"/>
        {error && <p role="alert" className="text-sm text-red-400">{error}</p>}
        <button disabled={submitting} className="button w-full">{submitting ? 'Unlocking…' : 'Unlock NumeroFlix'}</button>
      </form>
    </section>
  </main>
}

