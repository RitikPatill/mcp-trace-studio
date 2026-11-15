"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { listRuns, type RunSummary } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

function formatDuration(a: string, b: string): string {
  const ms = new Date(b).getTime() - new Date(a).getTime();
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function djb2(str: string): number {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 33) ^ str.charCodeAt(i);
  }
  return hash >>> 0;
}

const SERVER_COLORS = [
  "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  "bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200",
];

function serverColor(name: string): string {
  return SERVER_COLORS[djb2(name) % SERVER_COLORS.length];
}

function RunRow({ run }: { run: RunSummary }) {
  const isRunning = run.ended_at === null;

  return (
    <Link
      href={`/runs/${run.id}`}
      className="flex items-center gap-4 rounded-md border border-border px-4 py-3 transition-colors hover:bg-accent"
    >
      <div className="w-20 flex-shrink-0">
        {isRunning ? (
          <Badge variant="secondary">Running</Badge>
        ) : (
          <Badge variant="outline">Done</Badge>
        )}
      </div>

      <div className="w-24 flex-shrink-0 font-mono text-xs text-muted-foreground" title={run.id}>
        {run.id.slice(0, 8)}
      </div>

      <div className="flex-1 text-sm text-muted-foreground">
        {new Date(run.started_at).toLocaleString()}
      </div>

      <div className="w-20 flex-shrink-0 text-sm text-right text-muted-foreground">
        {run.ended_at ? formatDuration(run.started_at, run.ended_at) : "—"}
      </div>

      <div className="w-12 flex-shrink-0 text-sm text-right text-muted-foreground">
        {run.tool_call_count}
      </div>

      <div className="w-32 flex-shrink-0 text-right">
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${serverColor(run.server_name)}`}
        >
          {run.server_name}
        </span>
      </div>
    </Link>
  );
}

export default function RunsPage() {
  const { data: runs, isLoading } = useQuery({
    queryKey: ["runs"],
    queryFn: listRuns,
    refetchInterval: 5000,
  });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Runs</h1>

      {/* Table header */}
      <div className="mb-2 flex items-center gap-4 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        <div className="w-20 flex-shrink-0">Status</div>
        <div className="w-24 flex-shrink-0">ID</div>
        <div className="flex-1">Started</div>
        <div className="w-20 flex-shrink-0 text-right">Duration</div>
        <div className="w-12 flex-shrink-0 text-right">Tools</div>
        <div className="w-32 flex-shrink-0 text-right">Server</div>
      </div>

      <div className="flex flex-col gap-2">
        {isLoading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full rounded-md" />
          ))
        ) : !runs || runs.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-muted-foreground">
            No runs yet. Start the proxy and run an agent.
          </div>
        ) : (
          runs.map((run) => <RunRow key={run.id} run={run} />)
        )}
      </div>
    </div>
  );
}
