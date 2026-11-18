import { Heart } from 'lucide-react'
import { useCallback, useContext, useEffect, useRef, useState } from 'react'
import { AdminContext } from '../AdminContext'
import { Link, useParams } from 'react-router-dom'
import api from '../services/api'
import WatchProgressBar from '../components/WatchProgressBar'

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
  const artwork = movie.thumbnail_seconds != null ? `/api/movies/${movie.id}/frame?at=${movie.thumbnail_seconds}` : (movie.backdrop_path || movie.poster_path) && `/artwork/${movie.backdrop_path || movie.poster_path}`
  return <Link to={`/watch/${movie.id}`} className="group flex gap-2.5">
    <div className="relative aspect-video w-40 shrink-0 overflow-hidden rounded-lg bg-zinc-900">{artwork ? <img src={artwork} alt="" className="h-full w-full object-cover"/> : <div className="flex h-full items-center justify-center text-xs text-zinc-600">No thumbnail</div>}{movie.duration_seconds && <span className="absolute bottom-1 right-1 rounded bg-black/85 px-1 text-[10px]">{durationLabel(movie.duration_seconds)}</span>}<WatchProgressBar movie={movie}/></div>
    <div className="min-w-0"><h3 className="line-clamp-2 text-sm font-semibold leading-5 group-hover:text-white">{movie.title}</h3><p className="mt-1 text-xs text-zinc-500">{[movie.release_year, movie.first_frame_resolution || movie.resolution].filter(Boolean).join(' • ') || 'NumeroFlix'}</p><p className="mt-1 text-xs text-zinc-600">{sizeLabel(movie.file_size)}</p></div>
  </Link>
}

export default function Watch() {
  const { id } = useParams()
  return <WatchView key={id} id={id}/>
}

function WatchView({ id }) {
  const admin = useContext(AdminContext)
  const player = useRef(null)
  const lastSaved = useRef(0)
  const inspectionAttempted = useRef(false)
  const [movie, setMovie] = useState(null)
  const [related, setRelated] = useState([])
  const [loadError, setLoadError] = useState('')
  const [playerError, setPlayerError] = useState('')

  const loadMovie = useCallback(() => api.get(`/movies/${id}`).then(({ data }) => setMovie(data)), [id])

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' })
    loadMovie().catch(error => setLoadError(error.response?.status === 404 ? 'This video is no longer in the library.' : 'Could not load this video.'))
    api.get('/movies', { params: { page_size: 16, sort: 'created_at', order: 'desc' } })
      .then(({ data }) => setRelated(data.items.filter(item => String(item.id) !== String(id))))
      .catch(() => {})
  }, [id, loadMovie])

  useEffect(() => {
    if (!movie || !movie.is_available || inspectionAttempted.current) return
    if (movie.duration_seconds && movie.video_codec && (movie.first_frame_resolution || movie.resolution)) return
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
  if (loadError) return <p role="alert" className="text-sm text-zinc-400">{loadError}</p>
  if (!movie) return <div className="mx-auto max-w-[1600px] animate-pulse"><div className="aspect-video max-h-[70vh] rounded-xl bg-zinc-900"/><div className="mt-4 h-6 w-1/2 rounded bg-zinc-900"/></div>

  return <div className="mx-auto max-w-[1700px] lg:grid lg:grid-cols-[minmax(0,1fr)_390px] lg:gap-6">
    <div className="min-w-0">
      <div className="relative flex aspect-video max-h-[78vh] items-center justify-center overflow-hidden rounded-xl bg-black shadow-2xl shadow-black/40">
        {movie.is_available ? <video key={movie.id} ref={player} src={`/api/movies/${movie.id}/stream`} controls playsInline preload="metadata" className="h-full w-full" onLoadedMetadata={ready} onPlay={() => setPlayerError('')} onPause={() => saveProgress(false)} onTimeUpdate={trackProgress} onEnded={() => saveProgress(true)} onError={() => setPlayerError('This video format or codec is not supported by your browser.')}/> : <p className="text-amber-300">This file is currently unavailable.</p>}
      </div>
      {playerError && <div className="mt-3 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">{playerError}</div>}

      <h1 className="mt-4 text-xl font-bold leading-7 md:text-2xl">{movie.title}</h1>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 pb-4">
        <div><p className="text-sm font-semibold">NumeroFlix Library</p><p className="text-xs text-zinc-500">{movie.relative_path}</p></div>
        <div className="flex flex-wrap gap-2">{admin && <Link to={`/movies/${id}/edit`} className="button-secondary rounded-full">Edit video</Link>}<button onClick={() => patchMovie({ is_favorite: !movie.is_favorite })} className={`button-secondary rounded-full ${movie.is_favorite ? 'bg-zinc-700' : ''}`}><Heart size={17} fill={movie.is_favorite ? 'currentColor' : 'none'}/>{movie.is_favorite ? 'Favorited' : 'Favorite'}</button></div>
      </div>

      <section className="mt-4 rounded-xl bg-zinc-900 p-4 text-sm"><div className="flex flex-wrap gap-x-4 gap-y-1 font-semibold"><span>{movie.release_year || 'Unknown year'}</span><span>{durationLabel(movie.duration_seconds) || 'Duration analyzing…'}</span><span>{movie.first_frame_resolution || movie.resolution || 'Quality analyzing…'}</span><span>{sizeLabel(movie.file_size)}</span></div><p className="mt-3 whitespace-pre-wrap leading-6 text-zinc-300">{movie.description || 'No description has been added for this movie.'}</p><p className="mt-3 text-xs text-zinc-500">{[movie.video_codec, movie.audio_codec, movie.file_extension].filter(Boolean).join(' • ')}</p></section>

      <div className="mt-4 flex flex-wrap gap-2 pb-12">{movie.tags.map(tag => <span key={tag.id} className="rounded-full bg-zinc-800 px-3 py-1 text-xs text-zinc-300">{tag.name}</span>)}{movie.collections.map(category => <Link key={category.id} to={`/library?category=${category.id}`} className="rounded-full bg-zinc-800 px-3 py-1 text-xs text-zinc-300 hover:bg-zinc-700">{category.name}</Link>)}</div>
    </div>

    <aside className="mt-7 space-y-3 lg:mt-0"><h2 className="mb-3 text-base font-semibold">More from your library</h2>{related.slice(0, 12).map(item => <RelatedVideo key={item.id} movie={item}/>)}</aside>
  </div>
}
