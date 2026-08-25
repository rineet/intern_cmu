import React, { useEffect, useState } from 'react'
import FiltersBar from '../components/FiltersBar'
import PaperCard from '../components/PaperCard'
import PaperDetailModal from '../components/PaperDetailModal'

// --- Citation Generators ---
function generateAPA(paper) {
  const authors = paper.authors?.length ? paper.authors.join(', ') : 'Unknown Authors'
  const year = paper.year ? `(${paper.year})` : '(n.d.)'
  const venue = paper.venue ? ` ${paper.venue}.` : ''
  const doi = paper.doi ? ` https://doi.org/${paper.doi}` : ''
  return `${authors}. ${year}. ${paper.title}.${venue}${doi}`
}

function generateBibTeX(paper) {
  const firstAuthor = paper.authors?.[0]?.split(' ').pop() || 'Unknown'
  const citeKey = `${firstAuthor}${paper.year || 'YYYY'}`.replace(/[^a-zA-Z0-9]/g, '').toLowerCase()
  const authorList = (paper.authors || []).join(' and ')
  return `@article{${citeKey},
  title={${paper.title}},
  author={${authorList}},
  journal={${paper.venue || ''}},
  year={${paper.year || ''}},
  doi={${paper.doi || ''}}
}`
}

function normalizeText(value) {
  return value.toLowerCase().trim()
}

export default function ResultsPage({ searchResult, onBack, limit, setLimit }) {
  const [year, setYear] = useState('all')
  const [text, setText] = useState('')
  const [paper, setPaper] = useState(null)
  
  // NEW: Keep track of selected papers
  const [selectedPaperIds, setSelectedPaperIds] = useState(new Set())

  useEffect(() => {
    setPaper(null)
    setYear('all')
    setText('')
    setSelectedPaperIds(new Set()) // Clear selection on new search
  }, [searchResult])

  const papers = searchResult?.papers || []
  const years = Array.from(new Set(papers.map((entry) => entry.year).filter(Boolean))).sort((a, b) => b - a)

  const filteredPapers = papers.filter((entry) => {
    const matchesYear = year === 'all' || String(entry.year) === String(year)
    const haystack = normalizeText([entry.title, entry.abstract, entry.venue, ...(entry.authors || [])].join(' '))
    const matchesText = !text.trim() || haystack.includes(normalizeText(text))
    return matchesYear && matchesText
  })

  const displayedPapers = filteredPapers.slice(0, limit)

  // NEW: Toggle function for checkboxes
  const toggleSelection = (id) => {
    setSelectedPaperIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // NEW: Download Bibliography file
  const downloadBibliography = (format) => {
    // Find the full paper objects for all selected IDs
    const selectedPapers = papers.filter(p => selectedPaperIds.has(p.id))
    if (!selectedPapers.length) return

    let content = ''
    let filename = ''

    if (format === 'apa') {
      content = selectedPapers.map(generateAPA).join('\n\n')
      filename = 'bibliography.txt'
    } else {
      content = selectedPapers.map(generateBibTeX).join('\n\n')
      filename = 'bibliography.bib'
    }

    // Create file blob and trigger download
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8 relative">
      
      {/* NEW: Floating Action Bar when papers are selected */}
      {selectedPaperIds.size > 0 && (
        <div className="sticky top-4 z-40 mb-6 flex items-center justify-between rounded-xl bg-blue-600 px-6 py-4 text-white shadow-xl">
          <div className="flex items-center gap-4">
            <span className="font-semibold text-lg">{selectedPaperIds.size} papers selected</span>
            <button onClick={() => setSelectedPaperIds(new Set())} className="text-sm text-blue-200 hover:text-white underline">
              Clear Selection
            </button>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => downloadBibliography('apa')} className="rounded-lg bg-white/20 px-4 py-2 text-sm font-medium hover:bg-white/30 transition-colors">
              Download APA (.txt)
            </button>
            <button onClick={() => downloadBibliography('bibtex')} className="rounded-lg bg-white/20 px-4 py-2 text-sm font-medium hover:bg-white/30 transition-colors">
              Download BibTeX (.bib)
            </button>
          </div>
        </div>
      )}

      <button onClick={onBack} className="secondary-button mb-6">
        New Search
      </button>

      <div className="mb-6 rounded-xl bg-gray-50 border border-gray-200 p-5 shadow-sm">
         <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">Search Query</p>
         <p className="text-base text-gray-700 leading-relaxed line-clamp-4" title={searchResult?.query}>
            {searchResult?.query}
         </p>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-4">
        <span className="chip">
          {displayedPapers.length} of {filteredPapers.length} Papers
        </span>

        {searchResult?.timeline_months && (
          <span className="chip">
            Last {searchResult.timeline_months} Months
          </span>
        )}
        
        <div className="flex items-center gap-2">
            <label htmlFor="limit" className="text-sm font-medium text-gray-700">Display:</label>
            <select
                id="limit"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="rounded-md border border-gray-300 py-1 pl-3 pr-8 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
                <option value={50}>50 papers</option>
                <option value={100}>100 papers</option>
                <option value={150}>150 papers</option>
                <option value={500}>500 papers</option>
            </select>
        </div>
      </div>

      <div className="mt-8">
        <FiltersBar
          year={year}
          setYear={setYear}
          text={text}
          setText={setText}
          years={years}
        />
      </div>

      <div className="mt-8">
        <div className="flex items-center justify-between mb-4">
           <h2 className="section-title">Papers</h2>
        </div>

        <div className="space-y-4">
          {displayedPapers.map((entry) => (
            <PaperCard 
              key={entry.id} 
              paper={entry} 
              onOpen={setPaper} 
              isSelected={selectedPaperIds.has(entry.id)}
              onToggleSelect={toggleSelection}
            />
          ))}
        </div>

        {!displayedPapers.length && (
          <div className="card p-6 text-gray-500">
            No papers match the current filters.
          </div>
        )}
      </div>

      <PaperDetailModal paper={paper} onClose={() => setPaper(null)} />
    </div>
  )
}