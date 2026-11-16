"use client";

import { use, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getRun, getRunSpans, type SpanRead } from "@/lib/api";
import { serverColor } from "@/lib/utils";
import { useRunWebSocket } from "@/hooks/useRunWebSocket";
import { WaterfallTimeline } from "@/components/timeline/WaterfallTimeline";
import { SpanDetailPanel } from "@/components/timeline/SpanDetailPanel";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

function formatDuration(a: string, b: string): string {
  const ms = new Date(b).getTime() - new Date(a).getTime();
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

export default function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const { data: run, isLoading: runLoading } = useQuery({
    queryKey: ["run", id],
    queryFn: () => getRun(id),
  });

  const { data: fetchedSpans = [], isLoading: spansLoading } = useQuery({
    queryKey: ["spans", id],
    queryFn: () => getRunSpans(id),
    refetchInterval: false,
  });

  const { liveSpans, connected } = useRunWebSocket(id);

  // Merge fetched + live spans, keeping most-recent version keyed by id
  const spans = useMemo<SpanRead[]>(() => {
    const map = new Map<string, SpanRead>();
    fetchedSpans.forEach((s) => map.set(s.id, s));
    liveSpans.forEach((s) => map.set(s.id, s));
    return Array.from(map.values()).sort(
      (a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime()
    );
  }, [fetchedSpans, liveSpans]);

  const liveSpanIds = useMemo(() => new Set(liveSpans.map((s) => s.id)), [liveSpans]);

  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null);
  const selectedSpan = selectedSpanId ? spans.find((s) => s.id === selectedSpanId) ?? null : null;

  const isLoading = runLoading || spansLoading;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Link
          href="/runs"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Runs
        </Link>

        {isLoading ? (
          <Skeleton className="h-6 w-48" />
        ) : run ? (
          <>
            <span className="font-mono text-sm text-muted-foreground">{run.id.slice(0, 12)}…</span>

            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${serverColor(run.server_name)}`}
            >
              {run.server_name}
            </span>

            {run.model_name && (
              <Badge variant="outline" className="text-xs">
                {run.model_name}
              </Badge>
            )}

            {run.ended_at ? (
              <>
                <Badge variant="outline">Done</Badge>
                <span className="text-sm text-muted-foreground">
                  {formatDuration(run.started_at, run.ended_at)}
                </span>
              </>
            ) : (
              <Badge variant="secondary">
                {connected ? "● Live" : "Running"}
              </Badge>
            )}
          </>
        ) : null}
      </div>

      {/* Main content */}
      {isLoading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-full rounded" />
          ))}
        </div>
      ) : spans.length === 0 ? (
        <div className="flex h-40 items-center justify-center text-muted-foreground">
          No spans recorded yet.
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-row overflow-hidden">
          <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
            <WaterfallTimeline
              spans={spans}
              runStartedAt={run?.started_at ?? spans[0].started_at}
              serverName={run?.server_name ?? ""}
              selectedSpanId={selectedSpanId}
              onSelectSpan={(id) => setSelectedSpanId((prev) => (prev === id ? null : id))}
              liveSpanIds={liveSpanIds}
            />
          </div>

          {selectedSpan && (
            <SpanDetailPanel
              span={selectedSpan}
              allSpans={spans}
              onClose={() => setSelectedSpanId(null)}
            />
          )}
        </div>
      )}
    </div>
  );
}
