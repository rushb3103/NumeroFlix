import { Clapperboard, FolderHeart, Home, Library, Lock, Menu, Search, Settings } from 'lucide-react'
import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import api from '../services/api'

const nav = [
  ['/', Home, 'Home'],
  ['/library', Library, 'Library'],
  ['/collections', FolderHeart, 'Collections'],
  ['/settings', Settings, 'Settings'],
]

export default function Layout({ children }) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [expanded, setExpanded] = useState(true)

  const search = event => {
    event.preventDefault()
    const value = query.trim()
    navigate(value ? `/library?q=${encodeURIComponent(value)}` : '/library')
  }
  const logout = async () => {
    await api.post('/auth/logout')
    window.dispatchEvent(new Event('numeroflix:unauthorized'))
  }

  return <div className="min-h-screen bg-ink">
    <header className="fixed inset-x-0 top-0 z-40 flex h-16 items-center gap-3 border-b border-zinc-800 bg-ink/95 px-3 backdrop-blur md:px-5">
      <button aria-label="Toggle menu" onClick={() => setExpanded(value => !value)} className="hidden rounded-full p-2 hover:bg-zinc-800 md:block"><Menu size={21}/></button>
      <NavLink to="/" className="flex shrink-0 items-center gap-2 font-bold tracking-tight"><span className="rounded-lg bg-red-600 p-1.5"><Clapperboard size={19}/></span><span className="hidden sm:inline">NumeroFlix</span></NavLink>
      <form onSubmit={search} className="mx-auto flex w-full max-w-2xl"><input value={query} onChange={event => setQuery(event.target.value)} className="min-w-0 flex-1 rounded-l-full border border-zinc-700 bg-zinc-950 px-5 py-2 text-sm focus:border-blue-500" placeholder="Search your library"/><button aria-label="Search" className="rounded-r-full border border-l-0 border-zinc-700 bg-zinc-800 px-5 hover:bg-zinc-700"><Search size={19}/></button></form>
      <button onClick={logout} title="Lock NumeroFlix" className="shrink-0 rounded-full p-2 text-zinc-400 hover:bg-zinc-800 hover:text-white"><Lock size={20}/></button>
    </header>

    <aside className={`fixed bottom-0 left-0 top-16 z-30 hidden border-r border-zinc-900 bg-ink px-2 py-3 transition-[width] md:block ${expanded ? 'w-56' : 'w-[72px]'}`}>
      <nav className="space-y-1">{nav.map(([to, Icon, label]) => <NavLink key={to} to={to} end={to === '/'} title={!expanded ? label : undefined} className={({ isActive }) => `flex items-center rounded-xl py-3 text-sm transition ${expanded ? 'gap-5 px-4' : 'justify-center px-2'} ${isActive ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:bg-zinc-900 hover:text-white'}`}><Icon size={20}/>{expanded && <span>{label}</span>}</NavLink>)}</nav>
    </aside>

    <main className={`min-w-0 pb-20 pt-16 transition-[padding] md:pb-0 ${expanded ? 'md:pl-56' : 'md:pl-[72px]'}`}><div className="p-4 md:p-6">{children}</div></main>

    <nav className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t border-zinc-800 bg-ink/95 py-2 backdrop-blur md:hidden">{nav.map(([to, Icon, label]) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `flex min-w-16 flex-col items-center gap-1 text-[10px] ${isActive ? 'text-white' : 'text-zinc-500'}`}><Icon size={19}/>{label}</NavLink>)}</nav>
  </div>
}
