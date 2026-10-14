import { useEffect, useState } from 'react'
import api from '../services/api'
import MovieRow from '../components/MovieRow'

export default function Dashboard() {
  const [data, setData] = useState({recent: [], favorites: [], continue_watching: []})
  const [error, setError] = useState('')
  useEffect(() => { api.get('/library/dashboard').then(({data}) => setData(data)).catch(() => setError('The NumeroFlix API is unavailable.')) }, [])
  return <>{error && <div className="mb-6 rounded-lg border border-red-900 bg-red-950/40 p-4 text-red-200">{error}</div>}<MovieRow title="Continue watching" movies={data.continue_watching}/><MovieRow title="Recently added" movies={data.recent}/><MovieRow title="Favorites" movies={data.favorites}/>{!error && !data.recent.length && <div className="rounded-xl border border-dashed border-zinc-700 p-10 text-center text-zinc-400">Your library is empty. Open Settings to scan your movie folder.</div>}</>
}

