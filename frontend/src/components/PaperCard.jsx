import React from 'react'

function joinAuthors(authors) {
  if (!authors?.length) {
    return 'Unknown authors'
  }
  return authors.slice(0, 4).join(', ')
}

export default function PaperCard({ paper, onOpen, isSelected, onToggleSelect }) {
  return (
    <article className={`paper-card transition-all ${isSelected ? 'ring-2 ring-blue-500 bg-blue-50' : ''}`}>
      <div className="flex items-start gap-4">
        
        {/* Checkbox to select the paper */}
        <div className="pt-1.5 pl-1">
          <input
            type="checkbox"
            checked={isSelected || false}
            onChange={() => onToggleSelect(paper.id)}
            className="h-5 w-5 cursor-pointer rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
        </div>

        {/* Existing Content Container */}
        <div className="flex-1">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <p className="text-sm font-semibold uppercase tracking-wider text-blue-600">
                {paper.venue || 'Unknown venue'}
              </p>
              <button onClick={() => onOpen(paper)} className="text-left text-xl font-semibold text-gray-900 hover:text-blue-600 transition-colors">
                {paper.title}
              </button>
            </div>
            <div className="flex flex-col items-end gap-2">
              <div className="rounded-full border border-gray-200 bg-gray-100 px-3 py-1 text-sm text-gray-700">
                {paper.year || 'n/a'}
              </div>
              {paper.citation_count !== undefined && (
                <div className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700">
                  {paper.citation_count} Citations
                </div>
              )}
            </div>
          </div>

          <div className="mt-4 space-y-3 text-sm">
            <p className="leading-6 text-gray-800">
              <span className="font-medium text-black">Authors:</span> {joinAuthors(paper.authors)}
            </p>
            <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.18em] text-gray-500">
              <span>{paper.source === 'openalex' ? 'OpenAlex' : 'Semantic Scholar'}</span>
              <span>•</span>
              <span>{paper.year || 'n/a'}</span>
              {paper.doi ? (
                <>
                  <span>•</span>
                  <a className="text-blue-600 hover:text-blue-800 hover:underline" href={`https://doi.org/${paper.doi}`} target="_blank" rel="noreferrer">
                    DOI
                  </a>
                </>
              ) : null}
            </div>
            <p className="line-clamp-4 leading-6 text-gray-700">
              {paper.abstract || 'No abstract available from the source.'}
            </p>
          </div>

          <div className="mt-4 flex items-center justify-between gap-3">
            {paper.pdf_url ? (
              <a className="soft-button px-3 py-2 text-sm" href={paper.pdf_url} target="_blank" rel="noreferrer">
                PDF
              </a>
            ) : (
              <span className="text-sm text-gray-400">PDF unavailable</span>
            )}
            <button onClick={() => onOpen(paper)} className="soft-button px-4 py-2 text-sm">
              Details
            </button>
          </div>
        </div>
      </div>
    </article>
  )
}