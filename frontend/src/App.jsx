import React from 'react'
import { useState } from 'react'
import { useResearchSearch } from './hooks/useResearchSearch'
import HomePage from './pages/HomePage'
import ResultsPage from './pages/ResultsPage'

export default function App() {
  const [query, setQuery] = useState('')
  const [timelineMonths, setTimelineMonths] = useState(null)
  const [view, setView] = useState('home')
  const [searchResult, setSearchResult] = useState(null)
  const searchMutation = useResearchSearch()

  async function handleSearch(value) {
    const payload = typeof value === 'string'
      ? { query: value.trim(), timelineMonths: null }
      : { query: value?.query?.trim() || '', timelineMonths: value?.timelineMonths ?? null }
    const nextQuery = payload.query
    if (!nextQuery) {
      return
    }

    setQuery(nextQuery)
    setTimelineMonths(payload.timelineMonths ?? null)
    const data = await searchMutation.mutateAsync(payload)
    setSearchResult(data)
    setView('results')
  }

  function handleBack() {
    setView('home')
  }

  return (
    <div className="min-h-full">
      {view === 'home' ? (
        <HomePage
          query={query}
          setQuery={setQuery}
          timelineMonths={timelineMonths}
          setTimelineMonths={setTimelineMonths}
          onSearch={handleSearch}
          isSearching={searchMutation.isPending}
        />
      ) : (
        <ResultsPage
          searchResult={searchResult}
          onBack={handleBack}
          onSearch={handleSearch}
          onReplaySearch={handleSearch}
        />
      )}
    </div>
  )
}
