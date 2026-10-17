import { ChevronLeft, ChevronRight } from 'lucide-react'

function pageItems(currentPage, totalPages) {
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, index) => index + 1)

  const pages = new Set([1, totalPages, currentPage - 1, currentPage, currentPage + 1])
  const visiblePages = [...pages].filter(page => page >= 1 && page <= totalPages).sort((a, b) => a - b)
  const items = []
  visiblePages.forEach((page, index) => {
    if (index > 0 && page - visiblePages[index - 1] > 1) items.push(`ellipsis-${page}`)
    items.push(page)
  })
  return items
}

export default function Pagination({ page, pageSize, total, onChange }) {
  const totalPages = Math.ceil(total / pageSize)
  if (totalPages <= 1) return null

  return <nav className="mt-10 flex flex-wrap items-center justify-center gap-1" aria-label="Library pages">
    <button className="button-secondary px-3" disabled={page === 1} onClick={() => onChange(page - 1)} aria-label="Previous page"><ChevronLeft size={17}/><span className="hidden sm:inline">Previous</span></button>
    {pageItems(page, totalPages).map(item => typeof item === 'number'
      ? <button
        key={item}
        onClick={() => onChange(item)}
        aria-label={`Page ${item}`}
        aria-current={item === page ? 'page' : undefined}
        className={`min-w-10 rounded-lg px-3 py-2 text-sm font-medium transition ${item === page ? 'bg-white text-black' : 'text-zinc-400 hover:bg-zinc-800 hover:text-white'}`}
      >{item}</button>
      : <span key={item} className="px-2 text-zinc-600" aria-hidden="true">…</span>
    )}
    <button className="button-secondary px-3" disabled={page === totalPages} onClick={() => onChange(page + 1)} aria-label="Next page"><span className="hidden sm:inline">Next</span><ChevronRight size={17}/></button>
  </nav>
}
