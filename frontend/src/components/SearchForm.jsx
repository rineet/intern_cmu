import React, { useEffect, useState } from 'react'

const samplePrompts = [
  'Federated Learning for Healthcare',
  'Silent VOLE for MPC',
  'Vision Language Models for Education',
]

const timelineOptions = [
  { value: 'all', label: 'Any time' },
  { value: '1', label: 'Last month' },
  { value: '2', label: 'Last 2 months' },
  { value: '6', label: 'Last 6 months' },
  { value: '12', label: 'Last 12 months' },
]

export default function SearchForm({ value, onChange, onSubmit, isLoading, variant = 'hero', timelineMonths = null, onTimelineChange = () => {} }) {
  const [draft, setDraft] = useState(value || '')
  const [timelineDraft, setTimelineDraft] = useState(timelineMonths == null ? 'all' : String(timelineMonths))

  useEffect(() => {
    setDraft(value || '')
  }, [value])

  useEffect(() => {
    setTimelineDraft(timelineMonths == null ? 'all' : String(timelineMonths))
  }, [timelineMonths])

  function handleSubmit(event) {
    event.preventDefault()
    onSubmit({
      query: draft.trim(),
      timelineMonths: timelineDraft === 'all' ? null : Number(timelineDraft),
    })
  }

  function handleExample(prompt) {
    setDraft(prompt)
    onChange(prompt)
  }

  const isCompact = variant === 'compact'

  return (
    <form onSubmit={handleSubmit} className={isCompact ? 'card p-4' : 'card p-6 md:p-7'}>
      <div className="space-y-5">
        <label className="block space-y-2">
          {!isCompact && <span className="label">Research query</span>}
          <textarea
            value={draft}
            onChange={(event) => {
              setDraft(event.target.value)
              onChange(event.target.value)
            }}
            rows={isCompact ? 2 : 4}
            className={isCompact ? 'input resize-none' : 'input resize-none text-base'}
            placeholder="Describe the research topic in natural language"
          />
        </label>

        <div className={`grid gap-4 ${isCompact ? 'md:grid-cols-[minmax(0,1fr)_180px]' : 'md:grid-cols-[minmax(0,1fr)_220px]'}`}>
          <label className="block space-y-2">
            <span className="label">Timeline</span>
            <select
              value={timelineDraft}
              onChange={(event) => {
                setTimelineDraft(event.target.value)
                onTimelineChange(event.target.value === 'all' ? null : Number(event.target.value))
              }}
              className="input"
            >
              {timelineOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <div className="flex items-end gap-3">
            <button type="button" onClick={() => handleExample('')} className="soft-button flex-1">
              Clear
            </button>
            <button type="submit" className="primary-button flex-1" disabled={isLoading}>
              {isLoading ? 'Searching…' : 'Search'}
            </button>
          </div>
        </div>

        {!isCompact && (
          <div className="flex flex-wrap gap-2">
            {samplePrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => handleExample(prompt)}
                className="chip hover:bg-white/[0.08]"
              >
                {prompt}
              </button>
            ))}
          </div>
        )}
      </div>
    </form>
  )
}
