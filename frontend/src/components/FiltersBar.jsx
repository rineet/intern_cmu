import React from 'react'

export default function FiltersBar({ source, setSource, year, setYear, text, setText, years }) {
  return (
    <div className="card p-4">
      <div className="grid gap-3 lg:grid-cols-[180px_180px_minmax(0,1fr)]">
        <label className="block space-y-2">
          <span className="label">Source</span>
          <select value={source} onChange={(event) => setSource(event.target.value)} className="input">
            <option value="all">All sources</option>
            <option value="openalex">OpenAlex</option>
            <option value="arxiv">arXiv</option>
          </select>
        </label>

        <label className="block space-y-2">
          <span className="label">Publication year</span>
          <select value={year} onChange={(event) => setYear(event.target.value)} className="input">
            <option value="all">Any year</option>
            {years.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label className="block space-y-2">
          <span className="label">Find in results</span>
          <input
            value={text}
            onChange={(event) => setText(event.target.value)}
            className="input"
            placeholder="Title, abstract, author, or venue"
          />
        </label>
      </div>
    </div>
  )
}
