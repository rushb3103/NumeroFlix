import { Grid2X2, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import MovieCard from '../components/MovieCard'
import Pagination from '../components/Pagination'
import api from '../services/api'

const PAGE_SIZE = 24

export default function Library() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [result, setResult] = useState({ items: [], total: 0 })
  const [allTags, setAllTags] = useState([])
  const [selectedTags, setSelectedTags] = useState([])
  const search = searchParams.get('q') || ''
  const [genre, setGenre] = useState('')
  const [status, setStatus] = useState('all')
  const [sort, setSort] = useState('title')
  const [page, setPage] = useState(1)

  useEffect(() => { api.get('/tags').then(({ data }) => setAllTags(data)) }, [])
  useEffect(() => {
    const timer = setTimeout(() => {
      const params = { search: search || undefined, genre: genre || undefined, tags: selectedTags, sort, page, page_size: PAGE_SIZE }
      if (status === 'favorite') params.favorite = true
      if (status === 'watched') params.watched = true
      if (status === 'unwatched') params.watched = false
      api.get('/movies', { params }).then(({ data }) => setResult(data))
    }, 250)
    return () => clearTimeout(timer)
  }, [search, genre, status, selectedTags, sort, page])

  const toggleTag = tagId => {
    setSelectedTags(current => current.includes(tagId) ? current.filter(id => id !== tagId) : [...current, tagId])
    setPage(1)
  }

  const changePage = nextPage => {
    setPage(nextPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return <>
    <header className="mb-7"><div className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-3xl font-bold">Movie library</h1><p className="mt-1 text-sm text-zinc-500">{result.total} titles</p></div><div className="flex flex-wrap gap-2"><label className="control flex items-center gap-2"><Search size={16}/><input value={search} onChange={event => { const value = event.target.value; setSearchParams(value ? { q: value } : {}); setPage(1) }} placeholder="Search titles" className="bg-transparent"/></label><input className="control w-36" value={genre} onChange={event => { setGenre(event.target.value); setPage(1) }} placeholder="Genre"/><select className="control" value={status} onChange={event => { setStatus(event.target.value); setPage(1) }}><option value="all">All status</option><option value="favorite">Favorites</option><option value="watched">Watched</option><option value="unwatched">Unwatched</option></select><select className="control" value={sort} onChange={event => { setSort(event.target.value); setPage(1) }}><option value="title">Title</option><option value="release_year">Release year</option><option value="created_at">Date added</option><option value="file_size">File size</option></select><span className="control"><Grid2X2 size={18}/></span></div></div>{allTags.length > 0 && <div className="mt-5 flex flex-wrap gap-2">{allTags.map(tag => <button key={tag.id} onClick={() => toggleTag(tag.id)} style={{ borderColor: tag.color }} className={`rounded-full border px-3 py-1 text-xs ${selectedTags.includes(tag.id) ? 'bg-zinc-700 text-white' : 'text-zinc-500'}`}>{tag.name}</button>)}</div>}</header>
    <div className="grid grid-cols-1 gap-x-5 gap-y-8 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">{result.items.map(movie => <MovieCard key={movie.id} movie={movie}/>)}</div>
    <Pagination page={page} pageSize={PAGE_SIZE} total={result.total} onChange={changePage}/>
  </>
}
