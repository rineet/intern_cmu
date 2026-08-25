import React from 'react'

// CHANGED: Removed 'source' and 'setSource' from props
export default function FiltersBar({ year, setYear, text, setText, years }) {
  return (
    <div className="card p-4">
      {/* CHANGED: Adjusted grid columns since we removed one item */}
      <div className="grid gap-3 lg:grid-cols-[180px_minmax(0,1fr)]">
        
        {/* THE SOURCE LABEL BLOCK WAS DELETED HERE */}

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