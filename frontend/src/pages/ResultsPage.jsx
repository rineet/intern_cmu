import React, { useEffect, useState } from 'react'
import FiltersBar from '../components/FiltersBar'
import KeywordGroups from '../components/KeywordGroups'
import PaperCard from '../components/PaperCard'
import PaperDetailModal from '../components/PaperDetailModal'
import SearchForm from '../components/SearchForm'

function normalizeText(value) {
return value.toLowerCase().trim()
}

export default function ResultsPage({
searchResult,
onBack,
onSearch,
}) {
const [source, setSource] = useState('all')
const [year, setYear] = useState('all')
const [text, setText] = useState('')
const [paper, setPaper] = useState(null)
const [queryDraft, setQueryDraft] = useState(searchResult?.query || '')

useEffect(() => {
setQueryDraft(searchResult?.query || '')
setPaper(null)
setSource('all')
setYear('all')
setText('')
}, [searchResult])

const papers = searchResult?.papers || []

const years = Array.from(
new Set(
papers
.map((entry) => entry.year)
.filter(Boolean)
)
)
.sort((a, b) => b - a)

const filteredPapers = papers.filter((entry) => {
const matchesSource =
source === 'all' || entry.source === source

const matchesYear =
  year === 'all' ||
  String(entry.year) === String(year)

const haystack = normalizeText(
  [
    entry.title,
    entry.abstract,
    entry.venue,
    entry.source,
    ...(entry.authors || []),
  ].join(' ')
)

const matchesText =
  !text.trim() ||
  haystack.includes(normalizeText(text))

return (
  matchesSource &&
  matchesYear &&
  matchesText
)


})

return ( <div className="mx-auto max-w-6xl px-6 py-8">


  <button
    onClick={onBack}
    className="secondary-button mb-6"
  >
    New Search
  </button>

  <h1 className="text-4xl font-bold text-gray-900">
    {searchResult?.query}
  </h1>

  <div className="mt-4 flex flex-wrap gap-2">
    <span className="chip">
      {papers.length} Papers
    </span>

    {searchResult?.timeline_months && (
      <span className="chip">
        Last {searchResult.timeline_months} Months
      </span>
    )}
  </div>

  <div className="mt-8">
    <SearchForm
      value={queryDraft}
      onChange={setQueryDraft}
      onSubmit={onSearch}
      isLoading={false}
      variant="compact"
      timelineMonths={
        searchResult?.timeline_months ?? null
      }
    />
  </div>

  <div className="mt-8">
    <KeywordGroups
      expandedKeywords={
        searchResult?.expanded_keywords
      }
    />
  </div>

  <div className="mt-8">
    <FiltersBar
      source={source}
      setSource={setSource}
      year={year}
      setYear={setYear}
      text={text}
      setText={setText}
      years={years}
    />
  </div>

  <div className="mt-8">
    <h2 className="section-title mb-4">
      Papers
    </h2>

    <div className="space-y-4">
      {filteredPapers.map((entry) => (
        <PaperCard
          key={entry.id}
          paper={entry}
          onOpen={setPaper}
        />
      ))}
    </div>

    {!filteredPapers.length && (
      <div className="card p-6 text-gray-500">
        No papers match the current filters.
      </div>
    )}
  </div>

  <PaperDetailModal
    paper={paper}
    onClose={() => setPaper(null)}
  />
</div>

)
}
