"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getDiff } from "@/lib/api";
import { serverColor } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DiffTable } from "@/components/diff/DiffTable";

function formatDuration(a: string, b: string): string {
  const ms = new Date(b).getTime() - new Date(a).getTime();
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

interface RunCardProps {
  label: "A" | "B";
  run: {
    id: string;
    server_name: string;
    model_name: string | null;
    started_at: string;
    ended_at: string | null;
    tool_call_count: number;
  };
}

function RunCard({ label, run }: RunCardProps) {
  return (
    <div className="flex flex-1 flex-col gap-2 rounded-lg border p-4">
      <div className="flex items-center gap-2">
        <span className="rounded bg-muted px-1.5 py-0.5 text-xs font-bold">{label}</span>
        <Link
          href={`/runs/${run.id}`}
          className="font-mono text-xs text-muted-foreground hover:text-foreground underline"
        >
          {run.id.slice(0, 12)}…
        </Link>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${serverColor(run.server_name)}`}>
          {run.server_name}
        </span>
        {run.model_name && (
          <Badge variant="outline" className="text-xs">{run.model_name}</Badge>
        )}
        <span className="text-xs text-muted-foreground">{run.tool_call_count} calls</span>
        {run.ended_at && (
          <span className="text-xs text-muted-foreground">
            {formatDuration(run.started_at, run.ended_at)}
          </span>
        )}
      </div>
    </div>
  );
}

export default function DiffPage({
  params,
}: {
  params: Promise<{ id: string; compareId: string }>;
}) {
  const { id, compareId } = use(params);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["diff", id, compareId],
    queryFn: () => getDiff(id, compareId),
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          href={`/runs/${id}`}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
        <span className="text-sm font-medium">Run diff</span>
      </div>

      {/* Run summary cards */}
      {isLoading ? (
        <div className="flex gap-4">
          <Skeleton className="h-24 flex-1 rounded-lg" />
          <Skeleton className="h-24 flex-1 rounded-lg" />
        </div>
      ) : data ? (
        <div className="flex gap-4">
          <RunCard label="A" run={data.run_a} />
          <RunCard label="B" run={data.run_b} />
        </div>
      ) : null}

      {/* Diff table */}
      {isLoading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full rounded" />
          ))}
        </div>
      ) : isError ? (
        <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
          Could not load diff.
        </div>
      ) : data ? (
        <DiffTable entries={data.entries} />
      ) : null}
    </div>
  );
}
