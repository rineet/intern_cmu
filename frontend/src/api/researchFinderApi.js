import { apiClient } from '../lib/apiClient'

export async function searchResearch({ query, timelineMonths = null }) {
  const response = await apiClient.post('/api/search', {
    query,
    timeline_months: timelineMonths ?? null,
  })
  return response.data
}

export async function fetchPaperById(paperId) {
  const response = await apiClient.get(`/api/papers/${paperId}`)
  return response.data
}

export async function fetchSearchHistory() {
  const response = await apiClient.get('/api/search-history')
  return response.data
}
