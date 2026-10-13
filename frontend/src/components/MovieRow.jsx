import MovieCard from './MovieCard'

export default function MovieRow({ title, movies = [] }) {
  if (!movies.length) return null
  return <section className="mb-10"><h2 className="mb-4 text-lg font-semibold">{title}</h2><div className="grid grid-cols-1 gap-x-5 gap-y-7 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">{movies.map(movie => <MovieCard key={movie.id} movie={movie}/>)}</div></section>
}

