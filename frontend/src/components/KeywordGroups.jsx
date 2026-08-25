import React from 'react'

function KeywordList({ title, values }) {
  if (!values?.length) {
    return null
  }

  return (
    <div className="space-y-3 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
      <p className="label">{title}</p>
      <div className="flex flex-wrap gap-2">
        {values.map((value) => (
          <span key={value} className="chip">
            {value}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function KeywordGroups({ expandedKeywords }) {
  if (!expandedKeywords) {
    return null
  }

  return (
    <section className="card p-5">
      <div className="mb-4">
        <p className="eyebrow">Keywords</p>
        <h2 className="mt-2 text-xl font-semibold text-gray-900">Expanded search terms</h2>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
        {/* <KeywordList title="Canonical" values={expandedKeywords.canonical_terms} /> */}
        {/* <KeywordList title="Acronyms" values={expandedKeywords.acronyms} /> */}
        {/* <KeywordList title="Expanded" values={expandedKeywords.expanded_terms} /> */}
        {/* <KeywordList title="Related" values={expandedKeywords.related_terms} /> */}
        {/* <KeywordList title="Domains" values={expandedKeywords.research_domains} /> */}
        <KeywordList title="Queries" values={expandedKeywords.search_queries} />
      </div>
    </section>
  )
}
