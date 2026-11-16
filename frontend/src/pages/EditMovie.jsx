import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api from '../services/api'

function timeLabel(seconds) {
  const total = Math.floor(seconds)
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

export default function EditMovie() {
  const { id } = useParams()
  const [movie, setMovie] = useState(null)
  const [tags, setTags] = useState([])
  const [categories, setCategories] = useState([])
  const [title, setTitle] = useState('')
  const [thumbnail, setThumbnail] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  useEffect(() => {
    api.get(`/movies/${id}`).then(async ({data}) => {
      setMovie(data); setTitle(data.title); setThumbnail(data.thumbnail_seconds)
      if (!data.duration_seconds && data.is_available) {
        const inspected = await api.post(`/metadata/movies/${id}/inspect`)
        setMovie(current => ({ ...current, ...inspected.data }))
      }
    }).catch(() => setError('Could not load video details. Check that the file and ffprobe are available.'))
    api.get('/tags').then(({data}) => setTags(data)).catch(() => setError('Could not load tags.'))
    api.get('/collections').then(({data}) => setCategories(data)).catch(() => setError('Could not load categories.'))
  }, [id])
  const toggle = async (type, item) => {
    setError(''); setNotice('')
    try {
      const assigned = movie[type === 'categories' ? 'collections' : type].some(value => value.id === item.id)
      if (type === 'tags') await api.post('/movies/bulk/tags', {movie_ids: [movie.id], tag_ids: [item.id], operation: assigned ? 'remove' : 'add'})
      else if (assigned) await api.delete(`/collections/${item.id}/movies/${movie.id}`)
      else await api.post(`/collections/${item.id}/movies`, {movie_ids: [movie.id]})
      const {data} = await api.get(`/movies/${id}`); setMovie(data)
    } catch { setError('Could not update the assignment.') }
  }
  const save = async event => {
    event.preventDefault(); setError(''); setNotice('')
    try { await api.patch(`/movies/${id}`, {title: title.trim(), thumbnail_seconds: thumbnail}); setNotice('Video details saved.') }
    catch (err) { setError(err.response?.data?.detail || 'Could not save video details.') }
  }
  if (!movie) return <p className="text-zinc-400">{error || 'Loading video…'}</p>
  const frames = movie.duration_seconds ? Array.from({length: 20}, (_, i) => Math.min(movie.duration_seconds - 0.01, i * movie.duration_seconds / 20)) : []
  return <div className="mx-auto max-w-7xl"><Link to={`/watch/${id}`} className="text-sm text-zinc-400 hover:text-white">← Back to video</Link><h1 className="mt-4 text-3xl font-bold">Edit video</h1><p className="mt-2 text-sm text-zinc-400">Choose a thumbnail and organize this video.</p>
    {error && <p role="alert" className="mt-5 rounded-lg bg-red-950 p-3 text-red-200">{error}</p>}{notice && <p role="status" className="mt-5 text-emerald-400">{notice}</p>}
    <form onSubmit={save}><label className="mt-6 block max-w-2xl text-sm font-semibold">Title<input required maxLength={300} value={title} onChange={e => setTitle(e.target.value)} className="control mt-2 w-full"/></label>
      <div className="mt-8 flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-semibold">Choose a thumbnail</h2><p className="mt-1 text-sm text-zinc-400">20 frames spread across the video. Frames are generated each time you visit.</p></div><button type="button" onClick={() => setThumbnail(null)} className="button-secondary">Use original artwork</button></div>
      {frames.length ? <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">{frames.map((at, i) => <button type="button" key={i} onClick={() => setThumbnail(at)} aria-pressed={thumbnail === at} className={`overflow-hidden rounded-lg border-2 text-left ${thumbnail === at ? 'border-red-500' : 'border-transparent hover:border-zinc-500'}`}><div className="aspect-video bg-zinc-800"><img src={`/api/movies/${id}/frame?at=${at}`} alt={`Frame at ${timeLabel(at)}`} loading="lazy" className="h-full w-full object-cover"/></div><span className="block bg-zinc-900 px-2 py-1 text-xs text-zinc-300">{timeLabel(at)} {thumbnail === at && '• Selected'}</span></button>)}</div> : <p className="mt-4 text-sm text-zinc-500">Frames are unavailable until the video duration can be inspected.</p>}
      <button className="button mt-5" disabled={!title.trim()}>Save details</button></form>
    {[['categories', 'Categories', categories], ['tags', 'Tags', tags]].map(([type, label, items]) => <section key={type} className="mt-8 border-t border-zinc-800 pt-6"><h2 className="text-lg font-semibold">{label}</h2><p className="mt-1 text-sm text-zinc-500">Select to add or remove. Changes save immediately.</p><div className="mt-4 flex flex-wrap gap-2">{items.map(item => <button key={item.id} type="button" onClick={() => toggle(type, item)} aria-pressed={movie[type === 'categories' ? 'collections' : type].some(value => value.id === item.id)} className={`rounded-full border px-4 py-2 text-sm ${movie[type === 'categories' ? 'collections' : type].some(value => value.id === item.id) ? 'border-red-500 bg-red-600 text-white' : 'border-zinc-700 text-zinc-400 hover:bg-zinc-800'}`}>{item.name}</button>)}{!items.length && <p className="text-sm text-zinc-500">Create {label.toLowerCase()} in Admin.</p>}</div></section>)}
  </div>
}
