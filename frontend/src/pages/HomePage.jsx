import React from 'react'
import SearchForm from '../components/SearchForm'

export default function HomePage({
  query,
  setQuery,
  timelineMonths,
  setTimelineMonths,
  onSearch,
  isSearching,
  error, // NEW: Accept error prop
}) {
  return (
    <div className="mx-auto max-w-4xl px-6 py-16">
      <div className="mb-12 text-center">
        <h1 className="text-5xl font-bold text-gray-900">
          Research Finder
        </h1>

        <p className="mt-4 text-lg text-gray-600">
          Search academic papers using natural language.
        </p>
      </div>
      
      {/* NEW: Error banner */}
      {error && (
        <div className="mb-6 rounded-xl bg-red-50 border border-red-200 p-4 text-center text-red-700">
          {error}
        </div>
      )}

      <SearchForm
        value={query}
        onChange={setQuery}
        onSubmit={onSearch}
        isLoading={isSearching}
        timelineMonths={timelineMonths}
        onTimelineChange={setTimelineMonths}
      />
    </div>
  )
}