import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'

export default function AdminVideos() {
  const [file, setFile] = useState(null)
  const [progress, setProgress] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [result, setResult] = useState({ items: [], total: 0 })
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    let active = true
    const timer = setTimeout(() => {
      api.get('/movies', {params: {search: search || undefined, page, page_size: 12}})
        .then(({data}) => { if (active) setResult(data) })
        .catch(() => { if (active) setError('Could not load videos.') })
    }, 200)
    return () => { active = false; clearTimeout(timer) }
  }, [search, page, revision])
  const upload = async event => {
    event.preventDefault()
    if (!file) return
    if (!file.size) { setError('Choose a video file that is not empty.'); return }
    setBusy(true); setProgress(0); setError(''); setNotice('')
    const form = event.currentTarget
    let uploadId = null
    try {
      const {data} = await api.post('/library/uploads', {filename: file.name, size: file.size})
      uploadId = data.id
      for (let offset = 0; offset < file.size; offset += data.chunk_size) {
        const part = file.slice(offset, Math.min(offset + data.chunk_size, file.size))
        await api.put(`/library/uploads/${uploadId}`, part, {params: {offset}, timeout: 0, headers: {'Content-Type': 'application/octet-stream'}, onUploadProgress: progressEvent => setProgress(Math.min(99, Math.round((offset + progressEvent.loaded) * 100 / file.size)))})
      }
      setProgress(100)
      const response = await api.post(`/library/uploads/${uploadId}/complete`, null, {timeout: 0})
      uploadId = null
      setNotice(`Added ${response.data.title}.`); setFile(null); form.reset(); setPage(1); setRevision(value => value + 1)
    } catch (err) {
      if (uploadId) await api.delete(`/library/uploads/${uploadId}`).catch(() => {})
      const detail = err.response?.data?.detail
      setError(err.response?.status === 413 ? 'Upload request is too large for the connection.' : typeof detail === 'string' ? detail : 'Could not upload the video. Check your connection and try again.')
    } finally { setBusy(false); setProgress(null) }
  }

  const remove = async movie => {
    if (!window.confirm(`Permanently delete "${movie.title}"?\n\nThis deletes the source file from your library and removes its catalog entry. This cannot be undone.`)) return
    setBusy(true); setError(''); setNotice('')
    try {
      await api.delete(`/library/videos/${movie.id}`)
      setNotice(`Deleted ${movie.title}.`); setRevision(value => value + 1)
      if (result.items.length === 1 && page > 1) setPage(value => value - 1)
    } catch (err) { setError(err.response?.data?.detail || 'Could not delete the video.') }
    finally { setBusy(false) }
  }
  return <section className="mt-6 rounded-xl border border-zinc-800 bg-panel p-6"><h2 className="text-lg font-semibold">Manage videos</h2><p className="mt-1 text-sm text-zinc-400">Upload to the library root or permanently delete a video and its source file.</p>
    <form onSubmit={upload} className="mt-4 flex flex-wrap items-center gap-3"><label className="text-sm text-zinc-300">Video file <input type="file" accept=".mp4,.mkv,.avi,.mov,.webm,.m4v" onChange={event => setFile(event.target.files[0] || null)} className="mt-2 block max-w-full text-sm text-zinc-400 file:mr-3 file:rounded-lg file:border-0 file:bg-zinc-700 file:px-3 file:py-2 file:text-white" /></label><button className="button" disabled={!file || busy}>{progress === null ? 'Upload video' : `Uploading ${progress}%`}</button></form>
    {progress === 100 && <p className="mt-2 text-sm text-zinc-400">Saving to library…</p>}{error && <p role="alert" className="mt-4 text-sm text-red-300">{error}</p>}{notice && <p role="status" className="mt-4 text-sm text-emerald-400">{notice}</p>}
    <div className="mt-7 flex flex-wrap items-center justify-between gap-3"><h3 className="font-semibold">Library videos <span className="text-sm font-normal text-zinc-500">({result.total})</span></h3><input value={search} onChange={event => { setSearch(event.target.value); setPage(1) }} className="control" placeholder="Search videos" aria-label="Search videos to manage"/></div>
    <div className="mt-3 divide-y divide-zinc-800">{result.items.map(movie => <div key={movie.id} className="flex items-center gap-3 py-3"><div className="min-w-0 flex-1"><Link to={`/movies/${movie.id}/edit`} className="block truncate font-medium hover:underline">{movie.title}</Link><p className="truncate text-xs text-zinc-500">{movie.relative_path}{!movie.is_available && ' • Unavailable'}</p></div><Link to={`/movies/${movie.id}/edit`} className="text-sm text-zinc-400 hover:text-white">Edit</Link><button type="button" onClick={() => remove(movie)} disabled={busy || !movie.is_available} className="text-sm text-red-400 hover:text-red-300 disabled:opacity-40" title={!movie.is_available ? 'Reconnect storage before deleting' : undefined}>Delete</button></div>)}{!result.items.length && <p className="py-4 text-sm text-zinc-500">No videos found.</p>}</div>
    {result.total > 12 && <div className="mt-4 flex items-center gap-4 text-sm"><button className="button-secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><span className="text-zinc-400">Page {page}</span><button className="button-secondary" disabled={page * 12 >= result.total} onClick={() => setPage(page + 1)}>Next</button></div>}
  </section>
}
