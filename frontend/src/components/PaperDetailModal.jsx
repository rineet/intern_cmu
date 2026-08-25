import React, { useEffect } from 'react'

export default function PaperDetailModal({ paper, onClose }) {
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  if (!paper) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 px-4 py-8 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-[1.5rem] border border-gray-200 bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="eyebrow">Paper</p>
            <h3 className="mt-2 text-2xl font-semibold text-gray-900">{paper.title}</h3>
          </div>
          <button onClick={onClose} className="secondary-button px-3 py-2 text-sm">
            Close
          </button>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {/* CHANGED: Swapped transparent dark backgrounds for solid light gray (bg-gray-50) */}
          <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
            <p className="label">Metadata</p>
            {/* CHANGED: Fixed text colors for metadata to be fully opaque */}
            <dl className="mt-3 space-y-2 text-sm text-gray-800">
              <div className="flex gap-2">
                <dt className="w-24 text-gray-500">Venue</dt>
                <dd className="font-medium text-gray-900">{paper.venue || 'Unknown'}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="w-24 text-gray-500">Year</dt>
                <dd>{paper.year || 'n/a'}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="w-24 text-gray-500">Citations</dt>
                <dd>{paper.citation_count ?? '0'}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="w-24 text-gray-500">API Source</dt>
                <dd>{paper.source === 'openalex' ? 'OpenAlex' : 'Semantic Scholar'}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="w-24 text-gray-500">DOI</dt>
                <dd className="break-all">{paper.doi || 'Unavailable'}</dd>
              </div>
            </dl>
          </div>

          <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
            <p className="label">Links</p>
            <div className="mt-3 flex flex-col gap-3">
              {paper.pdf_url ? (
                <a className="primary-button" href={paper.pdf_url} target="_blank" rel="noreferrer">
                  Open PDF
                </a>
              ) : (
                <div className="rounded-xl border border-dashed border-gray-300 px-4 py-3 text-sm text-gray-500">
                  PDF link unavailable
                </div>
              )}
              {paper.doi ? (
                <a className="secondary-button" href={`https://doi.org/${paper.doi}`} target="_blank" rel="noreferrer">
                  Open DOI
                </a>
              ) : null}
            </div>
          </div>
        </div>

        <div className="mt-6 rounded-2xl border border-gray-200 bg-gray-50 p-4">
          <p className="label">Abstract</p>
          {/* CHANGED: Made abstract text highly readable with text-gray-800 */}
          <p className="mt-3 whitespace-pre-wrap leading-7 text-gray-800">
            {paper.abstract || 'No abstract available from the source.'}
          </p>
        </div>
      </div>
    </div>
  )
}