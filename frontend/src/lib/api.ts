const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface RunSummary {
  id: string;
  started_at: string;
  ended_at: string | null;
  server_name: string;
  model_name: string | null;
  tool_call_count: number;
}

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function listRuns(): Promise<RunSummary[]> {
  return apiFetch<RunSummary[]>("/runs");
}

export function getRun(id: string): Promise<RunSummary> {
  return apiFetch<RunSummary>(`/runs/${id}`);
}
