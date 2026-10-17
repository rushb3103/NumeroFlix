import { Heart, Play } from 'lucide-react'
import { Link } from 'react-router-dom'
import WatchProgressBar from './WatchProgressBar'

function formatDuration(seconds) {
  if (!seconds) return null
  const total = Math.round(seconds)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const remaining = total % 60
  return hours ? `${hours}:${String(minutes).padStart(2, '0')}:${String(remaining).padStart(2, '0')}` : `${minutes}:${String(remaining).padStart(2, '0')}`
}

function formatSize(bytes) {
  if (!bytes) return null
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / (1024 ** index)).toFixed(index > 2 ? 1 : 0)} ${units[index]}`
}

function formatQuality(resolution) {
  if (!resolution) return null
  if (resolution.endsWith('p')) return resolution
  const height = Number(resolution.split('x')[1])
  return height ? `${height}p` : resolution
}

export default function MovieCard({ movie }) {
  const artworkPath = movie.backdrop_path || movie.poster_path
  const artwork = artworkPath ? `/artwork/${artworkPath}` : null
  const duration = formatDuration(movie.duration_seconds)
  const quality = formatQuality(movie.resolution)
  const size = formatSize(movie.file_size)
  return <Link to={`/watch/${movie.id}`} className="group min-w-0">
    <div className="relative aspect-video overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900 shadow-lg shadow-black/10">
      {artwork ? <img src={artwork} alt="" className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.03]"/> : <div className="flex h-full items-center justify-center bg-gradient-to-br from-zinc-800 to-zinc-950 p-6 text-center text-sm text-zinc-500">No thumbnail</div>}
      <div className="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition group-hover:bg-black/35 group-hover:opacity-100"><span className="rounded-full bg-white/95 p-2.5 text-black"><Play size={18} fill="currentColor"/></span></div>
      {!movie.is_available && <span className="absolute left-2 top-2 rounded bg-black/85 px-2 py-1 text-[11px] text-amber-300">Unavailable</span>}
      {quality && <span className="absolute bottom-2 left-2 rounded bg-black/85 px-1.5 py-0.5 text-[11px] font-semibold text-white">{quality}</span>}
      {duration && <span className="absolute bottom-2 right-2 rounded bg-black/85 px-1.5 py-0.5 text-[11px] font-semibold text-white">{duration}</span>}
      {movie.is_favorite && <Heart className="absolute right-2 top-2 text-rose-400 drop-shadow" size={18} fill="currentColor"/>}
      <WatchProgressBar movie={movie}/>
    </div>
    <h3 className="mt-3 line-clamp-2 text-sm font-semibold leading-5 group-hover:text-white">{movie.title}</h3>
    <p className="mt-1 text-xs text-zinc-500">{[movie.release_year, size].filter(Boolean).join(' • ') || 'Details unavailable'}</p>
  </Link>
}

