import { RefreshCw, Square } from 'lucide-react'
import { useEffect, useState } from 'react'
import api from '../services/api'
import AdminVideos from '../components/AdminVideos'

export default function Settings() {
  const [status, setStatus] = useState(null)
  const [tags, setTags] = useState([])
  const [categories, setCategories] = useState([])
  const [error, setError] = useState('')

  const loadStatus = () => api.get('/library/status').then(({ data }) => setStatus(data))

  useEffect(() => {
    const refreshStatus = () => api.get('/library/status').then(({ data }) => setStatus(data))
    void Promise.all([
      refreshStatus(),
      api.get('/tags').then(({ data }) => setTags(data)),
      api.get('/collections').then(({ data }) => setCategories(data)),
    ]).catch(() => setError('Could not load settings.'))
    const timer = setInterval(() => { void refreshStatus().catch(() => {}) }, 1000)
    return () => clearInterval(timer)
  }, [])

  const scan = async () => {
    setError('')
    try {
      const { data } = await api.post('/library/scan')
      setStatus(current => ({ ...current, scan: data }))
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not start the library scan.')
      await loadStatus().catch(() => {})
    }
  }

  const cancelScan = async () => {
    await api.post('/library/scan/cancel').catch(requestError => setError(requestError.response?.data?.detail || 'Could not cancel the scan.'))
  }

  const manage = async (kind, action, item) => {
    setError('')
    const label = kind === 'tags' ? 'tag' : 'category'
    if (action === 'delete' && !window.confirm(`Delete ${item.name}? Its video assignments will be removed.`)) return
    const name = action === 'delete' ? null : window.prompt(`${action === 'create' ? 'New' : 'Rename'} ${label}`, item?.name || '')
    if (action !== 'delete' && !name?.trim()) return
    try {
      if (action === 'delete') await api.delete(`/${kind}/${item.id}`)
      else {
        const payload = kind === 'tags' ? {name: name.trim(), color: item?.color || '#7c3aed'} : {name: name.trim(), description: item?.description || null}
        if (action === 'create') await api.post(`/${kind}`, payload)
        else await api.put(`/${kind}/${item.id}`, payload)
      }
      const {data} = await api.get(`/${kind}`)
      if (kind === 'tags') setTags(data); else setCategories(data)
    } catch (requestError) { setError(requestError.response?.data?.detail || `Could not update ${label}.`) }
  }

  const scanState = status?.scan
  return <div className="max-w-4xl">
    <h1 className="text-3xl font-bold">Settings</h1>
    {error && <div className="mt-5 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">{error}</div>}
    <section className="mt-7 rounded-xl border border-zinc-800 bg-panel p-6">
      <div className="flex items-start justify-between gap-5"><div><h2 className="font-semibold">Library storage</h2><p className="mt-1 break-all text-sm text-zinc-500">{status?.movie_root}</p><p className={`mt-3 text-sm ${status?.root_available ? 'text-emerald-400' : 'text-amber-400'}`}>{status?.root_available ? 'Storage available' : 'Storage disconnected or locked'}</p></div><div className="flex gap-2">{scanState?.status === 'running' && <button className="button-secondary" onClick={cancelScan}><Square size={15}/>Cancel</button>}<button className="button" onClick={scan} disabled={!status?.root_available || scanState?.status === 'running'}><RefreshCw size={17} className={scanState?.status === 'running' ? 'animate-spin' : ''}/>{scanState?.status === 'running' ? 'Scanning…' : 'Scan library'}</button></div></div>
      {scanState?.status === 'running' && <div className="mt-5"><div className="h-1.5 overflow-hidden rounded-full bg-zinc-800"><div className="h-full w-1/2 animate-pulse rounded-full bg-rose-500"/></div><div className="mt-2 flex items-center justify-between gap-4"><p className="text-sm text-zinc-400">{scanState.processed || 0} media files checked</p><span className="rounded bg-zinc-900 px-2 py-1 text-[10px] uppercase tracking-wider text-zinc-500">{scanState.phase || 'discovering'}</span></div><p className="mt-1 truncate text-xs text-zinc-600">Current: {scanState.current_file || 'Reading library…'}</p></div>}
      {scanState?.events?.length > 0 && <div className="mt-4 overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950"><div className="flex items-center justify-between border-b border-zinc-800 px-3 py-2"><span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Scan activity</span><span className="text-xs text-zinc-600">Latest {Math.min(scanState.events.length, 15)}</span></div><div className="max-h-56 overflow-y-auto p-2 font-mono text-xs">{scanState.events.slice(-15).reverse().map(event => <div key={`${event.processed}-${event.file}`} className="flex gap-3 border-b border-zinc-900 px-2 py-1.5 last:border-0"><span className={`w-16 shrink-0 ${event.action === 'added' ? 'text-emerald-400' : event.action === 'updated' ? 'text-amber-400' : event.action === 'duplicate' ? 'text-blue-400' : 'text-zinc-600'}`}>{event.action}</span><span className="min-w-0 truncate text-zinc-400" title={event.file}>{event.file}</span></div>)}</div></div>}
      {scanState?.status === 'complete' && scanState.result && <p className="mt-4 text-sm text-zinc-400">Scan complete: {scanState.result.processed || 0} checked, {scanState.result.discovered || 0} added, {scanState.result.updated || 0} updated{scanState.result.duplicates_removed ? `, ${scanState.result.duplicates_removed} duplicate records merged` : ''}{scanState.result.duplicates_skipped ? `, ${scanState.result.duplicates_skipped} duplicate source copies hidden` : ''}.</p>}
      {scanState?.error && <p className="mt-4 text-sm text-red-400">{scanState.error}</p>}
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">{Object.entries(status?.statistics || {}).map(([key, value]) => <div key={key} className="rounded-lg bg-zinc-900 p-4"><strong className="text-xl">{value}</strong><p className="mt-1 text-xs capitalize text-zinc-500">{key}</p></div>)}</div>
    </section>
    <AdminVideos/>
    {[['collections', 'Categories', categories], ['tags', 'Tags', tags]].map(([kind, label, items]) => <section key={kind} className="mt-6 rounded-xl border border-zinc-800 bg-panel p-6"><div className="flex items-center justify-between"><h2 className="font-semibold">{label}</h2><button className="button-secondary" onClick={() => manage(kind, 'create')}>Add {kind === 'tags' ? 'tag' : 'category'}</button></div><div className="mt-4 divide-y divide-zinc-800">{items.map(item => <div key={item.id} className="flex items-center gap-3 py-3"><span className="min-w-0 flex-1 truncate">{item.name}</span><button className="text-sm text-zinc-400 hover:text-white" onClick={() => manage(kind, 'edit', item)}>Rename</button><button className="text-sm text-red-400 hover:text-red-300" onClick={() => manage(kind, 'delete', item)}>Delete</button></div>)}{!items.length && <p className="text-sm text-zinc-500">None yet.</p>}</div></section>)}
  </div>
}
