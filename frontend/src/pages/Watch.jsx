import { Check, Heart, ListPlus, Play, Tag as TagIcon } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api from '../services/api'

function durationLabel(seconds) {
  if (!seconds) return null
  const total = Math.round(seconds)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const remaining = total % 60
  return hours ? `${hours}:${String(minutes).padStart(2, '0')}:${String(remaining).padStart(2, '0')}` : `${minutes}:${String(remaining).padStart(2, '0')}`
}

function sizeLabel(bytes) {
  if (!bytes) return 'Unknown size'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / (1024 ** index)).toFixed(index > 2 ? 1 : 0)} ${units[index]}`
}

function RelatedVideo({ movie }) {
  const artwork = movie.backdrop_path || movie.poster_path
  return <Link to={`/watch/${movie.id}`} className="group flex gap-2.5">
    <div className="relative aspect-video w-40 shrink-0 overflow-hidden rounded-lg bg-zinc-900">{artwork ? <img src={`/artwork/${artwork}`} alt="" className="h-full w-full object-cover"/> : <div className="flex h-full items-center justify-center text-xs text-zinc-600">No thumbnail</div>}{movie.duration_seconds && <span className="absolute bottom-1 right-1 rounded bg-black/85 px-1 text-[10px]">{durationLabel(movie.duration_seconds)}</span>}</div>
    <div className="min-w-0"><h3 className="line-clamp-2 text-sm font-semibold leading-5 group-hover:text-white">{movie.title}</h3><p className="mt-1 text-xs text-zinc-500">{[movie.release_year, movie.resolution].filter(Boolean).join(' • ') || 'NumeroFlix'}</p><p className="mt-1 text-xs text-zinc-600">{sizeLabel(movie.file_size)}</p></div>
  </Link>
}

export default function Watch() {
  const { id } = useParams()
  return <WatchView key={id} id={id}/>
}

function WatchView({ id }) {
  const player = useRef(null)
  const lastSaved = useRef(0)
  const inspectionAttempted = useRef(false)
  const [movie, setMovie] = useState(null)
  const [tags, setTags] = useState([])
  const [collections, setCollections] = useState([])
  const [related, setRelated] = useState([])
  const [playing, setPlaying] = useState(false)
  const [playerError, setPlayerError] = useState('')

  const loadMovie = useCallback(() => api.get(`/movies/${id}`).then(({ data }) => setMovie(data)), [id])

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' })
    void Promise.all([
      loadMovie(),
      api.get('/tags').then(({ data }) => setTags(data)),
      api.get('/collections').then(({ data }) => setCollections(data)),
      api.get('/movies', { params: { page_size: 16, sort: 'created_at', order: 'desc' } }).then(({ data }) => setRelated(data.items.filter(item => String(item.id) !== String(id)))),
    ])
  }, [id, loadMovie])

  useEffect(() => {
    if (!movie || !movie.is_available || inspectionAttempted.current) return
    if (movie.duration_seconds && movie.video_codec && movie.resolution) return
    inspectionAttempted.current = true
    api.post(`/metadata/movies/${id}/inspect`).then(({ data }) => setMovie(current => ({ ...current, ...data }))).catch(() => {})
  }, [id, movie])

  const patchMovie = async changes => {
    const { data } = await api.patch(`/movies/${id}`, changes)
    setMovie(current => ({ ...current, ...data }))
  }
  const saveProgress = (completed = false) => {
    const video = player.current
    if (!video) return
    void api.put(`/movies/${id}/progress`, { position_seconds: completed ? 0 : video.currentTime, completed }).catch(() => {})
  }
  const trackProgress = () => {
    const video = player.current
    if (!video || Math.abs(video.currentTime - lastSaved.current) < 10) return
    lastSaved.current = video.currentTime
    saveProgress(video.duration > 0 && video.currentTime / video.duration > 0.92)
  }
  const ready = () => {
    if (movie?.progress?.position_seconds && player.current) {
      player.current.currentTime = movie.progress.position_seconds
      lastSaved.current = movie.progress.position_seconds
    }
  }
  const play = () => {
    setPlayerError('')
    player.current?.play().catch(() => setPlayerError('Your browser could not start this video. The codec may not be supported.'))
  }
  const toggleTag = async tag => {
    const hasTag = movie.tags.some(item => item.id === tag.id)
    await api.post('/movies/bulk/tags', { movie_ids: [movie.id], tag_ids: [tag.id], operation: hasTag ? 'remove' : 'add' })
    await loadMovie()
  }
  const toggleCollection = async collection => {
    const included = movie.collections.some(item => item.id === collection.id)
    if (included) await api.delete(`/collections/${collection.id}/movies/${movie.id}`)
    else await api.post(`/collections/${collection.id}/movies`, { movie_ids: [movie.id] })
    await loadMovie()
  }

  if (!movie) return <div className="mx-auto max-w-[1600px] animate-pulse"><div className="aspect-video max-h-[70vh] rounded-xl bg-zinc-900"/><div className="mt-4 h-6 w-1/2 rounded bg-zinc-900"/></div>

  return <div className="mx-auto max-w-[1700px] lg:grid lg:grid-cols-[minmax(0,1fr)_390px] lg:gap-6">
    <div className="min-w-0">
      <div className="relative flex aspect-video max-h-[78vh] items-center justify-center overflow-hidden rounded-xl bg-black shadow-2xl shadow-black/40">
        {movie.is_available ? <video key={movie.id} ref={player} src={`/api/movies/${movie.id}/stream`} controls playsInline preload="metadata" className="h-full w-full" onLoadedMetadata={ready} onPlay={() => setPlaying(true)} onPause={() => { setPlaying(false); saveProgress(false) }} onTimeUpdate={trackProgress} onEnded={() => saveProgress(true)} onError={() => setPlayerError('This video format or codec is not supported by your browser.')}/> : <p className="text-amber-300">This file is currently unavailable.</p>}
        {movie.is_available && !playing && <button aria-label="Play video" onClick={play} className="absolute rounded-full bg-white/95 p-5 text-black shadow-xl transition hover:scale-105"><Play size={30} fill="currentColor"/></button>}
      </div>
      {playerError && <div className="mt-3 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">{playerError}</div>}

      <h1 className="mt-4 text-xl font-bold leading-7 md:text-2xl">{movie.title}</h1>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 pb-4">
        <div><p className="text-sm font-semibold">NumeroFlix Library</p><p className="text-xs text-zinc-500">{movie.relative_path}</p></div>
        <div className="flex flex-wrap gap-2"><button onClick={() => patchMovie({ is_favorite: !movie.is_favorite })} className={`button-secondary rounded-full ${movie.is_favorite ? 'bg-zinc-700' : ''}`}><Heart size={17} fill={movie.is_favorite ? 'currentColor' : 'none'}/>{movie.is_favorite ? 'Favorited' : 'Favorite'}</button><button onClick={() => patchMovie({ is_watched: !movie.is_watched })} className={`button-secondary rounded-full ${movie.is_watched ? 'bg-zinc-700' : ''}`}><Check size={17}/>{movie.is_watched ? 'Watched' : 'Mark watched'}</button></div>
      </div>

      <section className="mt-4 rounded-xl bg-zinc-900 p-4 text-sm"><div className="flex flex-wrap gap-x-4 gap-y-1 font-semibold"><span>{movie.release_year || 'Unknown year'}</span><span>{durationLabel(movie.duration_seconds) || 'Duration analyzing…'}</span><span>{movie.resolution || 'Quality analyzing…'}</span><span>{sizeLabel(movie.file_size)}</span></div><p className="mt-3 whitespace-pre-wrap leading-6 text-zinc-300">{movie.description || 'No description has been added for this movie.'}</p><p className="mt-3 text-xs text-zinc-500">{[movie.video_codec, movie.audio_codec, movie.file_extension].filter(Boolean).join(' • ')}</p></section>

      <section className="mt-4 grid gap-4 pb-20 md:grid-cols-2"><div className="rounded-xl border border-zinc-800 p-4"><h2 className="flex items-center gap-2 text-sm font-semibold"><TagIcon size={17}/>Tags</h2><div className="mt-3 flex flex-wrap gap-2">{tags.length ? tags.map(tag => <button key={tag.id} onClick={() => toggleTag(tag)} style={{ borderColor: tag.color }} className={`rounded-full border px-3 py-1 text-xs ${movie.tags.some(item => item.id === tag.id) ? 'bg-zinc-700 text-white' : 'text-zinc-500'}`}>{tag.name}</button>) : <span className="text-xs text-zinc-600">Create tags in Settings.</span>}</div></div><div className="rounded-xl border border-zinc-800 p-4"><h2 className="flex items-center gap-2 text-sm font-semibold"><ListPlus size={17}/>Collections</h2><div className="mt-3 flex flex-wrap gap-2">{collections.length ? collections.map(collection => <button key={collection.id} onClick={() => toggleCollection(collection)} className={`rounded-full border border-zinc-700 px-3 py-1 text-xs ${movie.collections.some(item => item.id === collection.id) ? 'bg-zinc-700 text-white' : 'text-zinc-500'}`}>{collection.name}</button>) : <span className="text-xs text-zinc-600">Create collections first.</span>}</div></div></section>
    </div>

    <aside className="mt-7 space-y-3 lg:mt-0"><h2 className="mb-3 text-base font-semibold">More from your library</h2>{related.slice(0, 12).map(item => <RelatedVideo key={item.id} movie={item}/>)}</aside>
  </div>
}
