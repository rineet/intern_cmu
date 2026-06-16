import { useMutation, useQuery } from '@tanstack/react-query'
import { fetchSearchHistory, searchResearch } from '../api/researchFinderApi'

export function useResearchSearch() {
  return useMutation({
    mutationFn: searchResearch,
  })
}

export function useSearchHistory() {
  return useQuery({
    queryKey: ['search-history'],
    queryFn: fetchSearchHistory,
    staleTime: 30_000,
  })
}