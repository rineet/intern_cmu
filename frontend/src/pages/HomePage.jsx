import React from 'react'
import SearchForm from '../components/SearchForm'

export default function HomePage({
  query,
  setQuery,
  timelineMonths,
  setTimelineMonths,
  onSearch,
  isSearching,
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