import { apiClient } from "./client";

export interface SearchResults {
  query: string;
  jobs: { id: string; title: string; req_id: string; status: string }[];
  candidates: {
    id: string;
    full_name: string;
    email: string | null;
    current_title: string | null;
  }[];
  clients: { id: string; name: string }[];
  vendors: { id: string; name: string }[];
}

/** Header search across jobs, candidates, clients and vendors the viewer can read. */
export function globalSearch(q: string, limit = 5) {
  const params = new URLSearchParams({ q, limit: String(limit) });
  return apiClient.get<SearchResults>(`/search?${params}`);
}
