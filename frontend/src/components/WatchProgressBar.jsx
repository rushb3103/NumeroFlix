function watchedPercentage(movie) {
  if (movie.progress?.completed || movie.is_watched) return 100
  if (!movie.progress?.position_seconds || !movie.duration_seconds) return 0
  return Math.min(100, Math.max(0, (movie.progress.position_seconds / movie.duration_seconds) * 100))
}

export default function WatchProgressBar({ movie }) {
  const percentage = watchedPercentage(movie)
  if (percentage <= 0) return null

  return <div
    className="absolute inset-x-0 bottom-0 z-10 h-1 bg-black/60"
    role="progressbar"
    aria-label="Watch progress"
    aria-valuemin={0}
    aria-valuemax={100}
    aria-valuenow={Math.round(percentage)}
  >
    <div className="h-full bg-red-600" style={{ width: `${percentage}%` }}/>
  </div>
}
