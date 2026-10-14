import { Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import api from '../services/api'

export default function Collections() {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const load = () => api.get('/collections').then(({data}) => setItems(data))
  useEffect(() => {
    // An effect may only return a cleanup function, never the Axios Promise.
    void load().catch(() => setError('Could not load collections.'))
  }, [])
  const create = async e => {
    e.preventDefault()
    setError('')
    const form = new FormData(e.currentTarget)
    try {
      const { data } = await api.post('/collections', {name: form.get('name'), description: form.get('description')})
      setItems(current => [...current.filter(item => item.id !== data.id), data].sort((a, b) => a.name.localeCompare(b.name)))
      e.currentTarget.reset()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not create the collection.')
    }
  }
  return <><h1 className="text-3xl font-bold">Collections</h1><form onSubmit={create} className="my-7 flex max-w-2xl flex-wrap gap-2"><input required name="name" className="control flex-1" placeholder="Collection name"/><input name="description" className="control flex-[2]" placeholder="Description (optional)"/><button className="button"><Plus size={17}/>Create</button></form>{error && <div className="mb-5 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">{error}</div>}<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{items.map(item => <article key={item.id} className="rounded-xl border border-zinc-800 bg-panel p-6"><h2 className="font-semibold">{item.name}</h2><p className="mt-2 min-h-10 text-sm text-zinc-500">{item.description || 'No description'}</p><p className="mt-5 text-xs uppercase tracking-widest text-zinc-600">{item.movie_count} movies</p></article>)}</div></>
}

