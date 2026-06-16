import React from 'react'
import { useSearchHistory } from '../hooks/useResearchSearch'

export default function SearchHistorySidebar({ onReplay }) {
  const { data, isLoading, isError } = useSearchHistory()

  return (
    <aside className="glass-shell p-5">
      <div>
        <p className="eyebrow">History</p>
        <h2 className="mt-2 text-lg font-semibold text-white">Recent searches</h2>
      </div>

      <div className="mt-4 space-y-2.5">
        {isLoading && <p className="text-sm text-slate-400">Loading history…</p>}
        {isError && <p className="text-sm text-rose-300">Unable to load search history.</p>}
        {!isLoading && !isError && (!data || data.length === 0) && (
          <p className="rounded-xl border border-dashed border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-slate-400">
            No searches stored yet.
          </p>
        )}
        {data?.map((entry) => (
          <button
            key={entry.id}
            onClick={() => onReplay(entry.original_query)}
            className="block w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-left transition hover:bg-white/[0.06]"
          >
            <p className="line-clamp-2 font-medium text-white">{entry.original_query}</p>
            <p className="mt-1 text-sm text-slate-400">{entry.paper_count} papers</p>
          </button>
        ))}
      </div>
    </aside>
  )
}
