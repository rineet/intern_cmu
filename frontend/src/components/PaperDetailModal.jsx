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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 px-4 py-8 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-[1.5rem] border border-white/10 bg-white p-6">
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
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <p className="label">Metadata</p>
            <dl className="mt-3 space-y-2 text-sm text-slate-200">
              <div className="flex gap-2">
                <dt className="w-20 text-slate-500">Venue</dt>
                <dd>{paper.venue || 'Unknown'}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="w-20 text-slate-500">Year</dt>
                <dd>{paper.year || 'n/a'}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="w-20 text-slate-500">Source</dt>
                <dd>{paper.source}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="w-20 text-slate-500">DOI</dt>
                <dd className="break-all">{paper.doi || 'Unavailable'}</dd>
              </div>
            </dl>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <p className="label">Links</p>
            <div className="mt-3 flex flex-col gap-3">
              {paper.pdf_url ? (
                <a className="primary-button" href={paper.pdf_url} target="_blank" rel="noreferrer">
                  Open PDF
                </a>
              ) : (
                <div className="rounded-xl border border-dashed border-white/10 px-4 py-3 text-sm text-slate-400">
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

        <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <p className="label">Abstract</p>
          <p className="mt-3 whitespace-pre-wrap leading-7 text-slate-200">
            {paper.abstract || 'No abstract available from the source.'}
          </p>
        </div>
      </div>
    </div>
  )
}
