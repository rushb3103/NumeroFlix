import { RefreshCw, Square, Tag as TagIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import api from '../services/api'

export default function Settings() {
  const [status, setStatus] = useState(null)
  const [tags, setTags] = useState([])
  const [error, setError] = useState('')

  const loadStatus = () => api.get('/library/status').then(({ data }) => setStatus(data))

  useEffect(() => {
    const refreshStatus = () => api.get('/library/status').then(({ data }) => setStatus(data))
    void Promise.all([
      refreshStatus(),
      api.get('/tags').then(({ data }) => setTags(data)),
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

  const createTag = async event => {
    event.preventDefault()
    setError('')
    const form = new FormData(event.currentTarget)
    try {
      const { data } = await api.post('/tags', { name: form.get('name'), color: form.get('color') })
      setTags(current => [...current.filter(tag => tag.id !== data.id), data].sort((a, b) => a.name.localeCompare(b.name)))
      event.currentTarget.reset()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not create the tag.')
    }
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
    <section className="mt-6 rounded-xl border border-zinc-800 bg-panel p-6"><h2 className="flex items-center gap-2 font-semibold"><TagIcon size={18}/>Custom tags</h2><form onSubmit={createTag} className="mt-4 flex gap-2"><input required name="name" className="control flex-1" placeholder="Tag name"/><input name="color" type="color" defaultValue="#7c3aed" className="h-10 w-12 rounded bg-transparent"/><button className="button">Add tag</button></form><div className="mt-4 flex flex-wrap gap-2">{tags.map(tag => <span key={tag.id} style={{ borderColor: tag.color }} className="rounded-full border px-3 py-1 text-sm">{tag.name}</span>)}</div></section>
    <section className="mt-6 rounded-xl border border-zinc-800 bg-panel p-6"><h2 className="font-semibold">Metadata & media</h2><p className="mt-2 text-sm leading-6 text-zinc-500">File size and filename quality are available immediately. Duration, codecs, and exact resolution are inspected lazily with ffprobe when a movie is opened, keeping remote-vault scans lightweight.</p></section>
  </div>
}
