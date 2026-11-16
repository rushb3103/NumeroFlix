import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'

export default function Collections() {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  useEffect(() => { api.get('/collections').then(({ data }) => setItems(data)).catch(() => setError('Could not load categories.')) }, [])
  return <div className="mx-auto max-w-7xl"><h1 className="text-3xl font-bold">Categories</h1><p className="mt-2 text-sm text-zinc-400">Browse videos by category.</p>{error && <p className="mt-5 text-red-300">{error}</p>}<div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{items.map(item => <Link key={item.id} to={`/library?category=${item.id}`} className="group rounded-xl border border-zinc-800 bg-zinc-900 p-6 transition hover:border-zinc-600 hover:bg-zinc-800"><h2 className="text-lg font-semibold group-hover:text-white">{item.name}</h2><p className="mt-2 min-h-10 text-sm text-zinc-400">{item.description || 'Browse videos'}</p><p className="mt-5 text-sm text-zinc-500">{item.movie_count} {item.movie_count === 1 ? 'video' : 'videos'} →</p></Link>)}</div>{!items.length && !error && <p className="mt-8 text-zinc-500">No categories yet. Turn on Admin to create one.</p>}</div>
}
