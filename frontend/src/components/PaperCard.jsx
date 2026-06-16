import React from 'react'

function joinAuthors(authors) {
  if (!authors?.length) {
    return 'Unknown authors'
  }

  return authors.slice(0, 4).join(', ')
}

export default function PaperCard({ paper, onOpen }) {
  return (
    <article className="paper-card">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="text-sm uppercase tracking-wider text-gray-500">
            {paper.source}
          </p>
          <button onClick={() => onOpen(paper)} className="text-left text-xl font-semibold text-gray-900">
            {paper.title}
          </button>
        </div>
        <div className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-sm text-slate-300">
          {paper.year || 'n/a'}
        </div>
      </div>

      <div className="mt-4 space-y-3 text-sm text-gray-700">
        <p className="leading-6 text-slate-200/90">
          <span className="font-medium text-white">Authors:</span> {joinAuthors(paper.authors)}
        </p>
        <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.18em] text-gray-500">
          <span>{paper.venue || 'Unknown venue'}</span>
          <span>•</span>
          <span>{paper.year || 'n/a'}</span>
          {paper.doi ? (
            <>
              <span>•</span>
              <a className="text-slate-300 hover:text-white" href={`https://doi.org/${paper.doi}`} target="_blank" rel="noreferrer">
                DOI
              </a>
            </>
          ) : null}
        </div>
        <p className="line-clamp-4 leading-6 text-slate-300/85">
          {paper.abstract || 'No abstract available from the source.'}
        </p>
      </div>

      <div className="mt-4 flex items-center justify-between gap-3">
        {paper.pdf_url ? (
          <a className="soft-button px-3 py-2 text-sm" href={paper.pdf_url} target="_blank" rel="noreferrer">
            PDF
          </a>
        ) : (
          <span className="text-sm text-slate-500">PDF unavailable</span>
        )}
        <button onClick={() => onOpen(paper)} className="soft-button px-4 py-2 text-sm">
          Details
        </button>
      </div>
    </article>
  )
}
