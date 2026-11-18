const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface RunSummary {
  id: string;
  started_at: string;
  ended_at: string | null;
  server_name: string;
  model_name: string | null;
  tool_call_count: number;
  parent_run_id: string | null;
}

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail?.detail ?? `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function listRuns(): Promise<RunSummary[]> {
  return apiFetch<RunSummary[]>("/runs");
}

export function getRun(id: string): Promise<RunSummary> {
  return apiFetch<RunSummary>(`/runs/${id}`);
}

export interface ToolCallRead {
  id: string;
  span_id: string;
  run_id: string;
  tool_name: string;
  args_json: string;
  result_json: string | null;
  error: string | null;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
}

export interface SpanRead {
  id: string;
  run_id: string;
  direction: string;
  method: string | null;
  msg_id: string | null;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  tool_calls: ToolCallRead[];
}

export function getRunSpans(runId: string): Promise<SpanRead[]> {
  return apiFetch<SpanRead[]>(`/runs/${runId}/spans`);
}

export interface ReplayRequest {
  server_name: string;
  model_name?: string;
}

export function replayRun(runId: string, body: ReplayRequest): Promise<RunSummary> {
  return apiPost<RunSummary>(`/runs/${runId}/replay`, body);
}

export interface DiffEntry {
  tool_name: string;
  call_index: number;
  tool_call_a: ToolCallRead | null;
  tool_call_b: ToolCallRead | null;
  args_changed: boolean;
  result_changed: boolean;
  latency_delta_ms: number | null;
}

export interface DiffResult {
  run_a: RunSummary;
  run_b: RunSummary;
  entries: DiffEntry[];
}

export function getDiff(runIdA: string, runIdB: string): Promise<DiffResult> {
  return apiFetch<DiffResult>(`/runs/${runIdA}/diff/${runIdB}`);
}
