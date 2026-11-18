import { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import api from '../services/api'

const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']
const number = new Intl.NumberFormat()
const percent = new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 1 })

function formatBytes(bytes) {
  const unit = bytes > 0 ? Math.min(Math.floor(Math.log2(bytes) / 10), units.length - 1) : 0
  return `${(bytes / 1024 ** unit).toLocaleString(undefined, { maximumFractionDigits: unit ? 1 : 0 })} ${units[unit]}`
}

function Breakdown({ title, items, totalBytes }) {
  return <section className="min-w-0 rounded-xl border border-zinc-800 bg-panel p-4 sm:p-6">
    <h2 className="text-lg font-semibold">{title}</h2>
    {items.length === 0 ? <p className="mt-3 text-sm text-zinc-400">No videos in the library yet.</p> :
      <table className="mt-3 w-full table-fixed text-sm">
        <thead className="text-zinc-400">
          <tr><th className="py-2 text-left font-medium" scope="col">Group</th><th className="w-16 text-right font-medium sm:w-20" scope="col">Videos</th><th className="w-24 text-right font-medium sm:w-28" scope="col">Storage</th></tr>
        </thead>
        <tbody className="divide-y divide-zinc-800 border-t border-zinc-800">
          {items.map(item => {
            const share = totalBytes ? item.size_bytes / totalBytes : 0
            return <tr key={item.id ?? 'unassigned'}>
              <th className="break-words py-3 pr-2 text-left font-medium" scope="row">{item.name}</th>
              <td className="text-right tabular-nums text-zinc-300">{number.format(item.video_count)}</td>
              <td className="py-3 pl-2 text-right tabular-nums">
                {formatBytes(item.size_bytes)}
                <div className="text-xs text-zinc-400">{percent.format(share)}</div>
                <div aria-hidden="true" className="mt-1 h-1 overflow-hidden rounded-full bg-zinc-800">
                  <div className="h-full rounded-full bg-rose-500" style={{ width: `${share * 100}%` }}/>
                </div>
              </td>
            </tr>
          })}
        </tbody>
      </table>}
  </section>
}

export default function AdminAnalytics() {
  const revision = useOutletContext()
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    api.get('/library/analytics', {signal: controller.signal})
      .then(response => { setData(response.data); setError(false) })
      .catch(() => { if (!controller.signal.aborted) setError(true) })
    return () => controller.abort()
  }, [revision])

  if (error) return <p role="alert" className="mt-6 text-sm text-red-300">Could not load library analytics.</p>
  if (!data) return <p role="status" className="mt-6 text-sm text-zinc-400">Loading library analytics…</p>

  return <div className="mt-6 space-y-5">
    <dl className="grid grid-cols-2 gap-3">
      <div className="rounded-xl border border-zinc-800 bg-panel p-4"><dt className="text-sm text-zinc-400">Cataloged videos</dt><dd className="mt-1 text-xl font-semibold">{number.format(data.total_videos)}</dd></div>
      <div className="rounded-xl border border-zinc-800 bg-panel p-4"><dt className="text-sm text-zinc-400">Total video storage</dt><dd className="mt-1 text-xl font-semibold">{formatBytes(data.total_bytes)}</dd></div>
    </dl>
    <Breakdown title="Storage by first-frame resolution" items={data.resolutions} totalBytes={data.total_bytes}/>
    <p className="text-sm text-zinc-400">A video counts in every category and tag assigned to it, so those storage shares can overlap.</p>
    <div className="grid gap-5 lg:grid-cols-2">
      <Breakdown title="Categories" items={data.categories} totalBytes={data.total_bytes}/>
      <Breakdown title="Tags" items={data.tags} totalBytes={data.total_bytes}/>
    </div>
  </div>
}
