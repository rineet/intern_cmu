import { apiClient } from '../lib/apiClient'

export async function searchResearch({ query, timelineMonths = null }) {
  // 1. Instantly start the job and get a ticket (Job ID)
  const startResponse = await apiClient.post('/api/search', {
    query,
    timeline_months: timelineMonths ?? null,
  })
  
  const jobId = startResponse.data.job_id

  // 2. Poll the server every 10 seconds
  while (true) {
    // Wait for 10 seconds before asking again
    await new Promise((resolve) => setTimeout(resolve, 10000))
    
    // Check the status
    const statusResponse = await apiClient.get(`/api/search/status/${jobId}`)
    const job = statusResponse.data

    if (job.status === 'completed') {
      // The GPU is done! Return the papers to React so the UI updates.
      return job.result
    } else if (job.status === 'failed') {
      // Something crashed in Python
      throw new Error(job.error || 'The search failed on the server.')
    }
    
    // If job.status is 'processing', the loop just repeats!
    console.log(`Job ${jobId} is still processing... waiting 10 more seconds.`)
  }
}

export async function fetchPaperById(paperId) {
  const response = await apiClient.get(`/api/papers/${paperId}`)
  return response.data
}

export async function fetchSearchHistory() {
  const response = await apiClient.get('/api/search-history')
  return response.data
}