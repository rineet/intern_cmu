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
  const [error, setError] = useState(null) 
  
  // NEW: Add state for the paper limit
  const [limit, setLimit] = useState(50) 
  
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
    setError(null)

    try {
      // NOTE: You may also need to update your API hook to accept the limit parameter 
      // if you want the backend to limit the initial fetch, otherwise this limits it on the frontend.
      const data = await searchMutation.mutateAsync(payload)
      setSearchResult(data)
      setView('results')
    } catch (err) {
      const errorMessage = err.response?.data?.detail || "An unexpected error occurred while searching."
      setError(errorMessage)
    }
  }

  function handleBack() {
    setView('home')
    setError(null)
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
          error={error} 
        />
      ) : (
        <ResultsPage
          searchResult={searchResult}
          onBack={handleBack}
          onSearch={handleSearch}
          onReplaySearch={handleSearch}
          limit={limit}         // NEW: Pass limit state
          setLimit={setLimit}   // NEW: Pass setLimit function
        />
      )}
    </div>
  )
}