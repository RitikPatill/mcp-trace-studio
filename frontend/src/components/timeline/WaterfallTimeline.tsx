"use client";

import { useEffect, useRef, useState } from "react";
import type { SpanRead } from "@/lib/api";
import { serverBarColor } from "@/lib/utils";

interface Props {
  spans: SpanRead[];
  runStartedAt: string;
  serverName: string;
  selectedSpanId: string | null;
  onSelectSpan: (id: string) => void;
  liveSpanIds?: Set<string>;
}

function computeTicks(totalMs: number, zoom: number): number[] {
  const visibleMs = totalMs / zoom;
  const rawInterval = visibleMs / 6;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawInterval)));
  const nice = [1, 2, 5, 10].map((m) => m * magnitude);
  const interval = nice.find((n) => visibleMs / n <= 8) ?? nice[nice.length - 1];
  const ticks: number[] = [];
  for (let t = 0; t <= totalMs; t += interval) ticks.push(t);
  return ticks;
}

export function WaterfallTimeline({ spans, runStartedAt, serverName, selectedSpanId, onSelectSpan, liveSpanIds }: Props) {
  const [zoom, setZoom] = useState(1);
  const [newSpanIds, setNewSpanIds] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  const runStart = new Date(runStartedAt).getTime();
  const allEnds = spans.map((s) =>
    s.ended_at ? new Date(s.ended_at).getTime() : new Date(s.started_at).getTime()
  );
  const totalDurationMs = Math.max(1, Math.max(...allEnds) - runStart);

  // Track newly arriving spans for pulse animation
  useEffect(() => {
    if (!liveSpanIds || liveSpanIds.size === 0) return;
    setNewSpanIds((prev) => new Set([...prev, ...liveSpanIds]));
    const timer = setTimeout(() => {
      setNewSpanIds((prev) => {
        const next = new Set(prev);
        liveSpanIds.forEach((id) => next.delete(id));
        return next;
      });
    }, 1500);
    return () => clearTimeout(timer);
  }, [liveSpanIds]);

  function handleWheel(e: React.WheelEvent) {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.5 : 0.5;
      setZoom((z) => Math.min(20, Math.max(1, z + delta)));
    }
  }

  const ticks = computeTicks(totalDurationMs, zoom);
  const RULER_H = 24;
  const ROW_H = 36;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* Zoom controls */}
      <div className="flex items-center justify-end gap-1 px-3 py-1">
        <span className="text-xs text-muted-foreground mr-2">Zoom: {zoom.toFixed(1)}×</span>
        <button
          onClick={() => setZoom((z) => Math.min(20, z + 1))}
          className="rounded border border-border px-2 py-0.5 text-xs hover:bg-accent"
        >
          +
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(1, z - 1))}
          className="rounded border border-border px-2 py-0.5 text-xs hover:bg-accent"
        >
          −
        </button>
      </div>

      {/* Scrollable area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-x-auto overflow-y-auto"
        onWheel={handleWheel}
      >
        <div style={{ width: `${zoom * 100}%`, minWidth: "100%", position: "relative" }}>
          {/* Time ruler */}
          <svg
            width="100%"
            height={RULER_H}
            className="sticky top-0 z-10 bg-background border-b border-border"
          >
            {ticks.map((ms) => {
              const pct = (ms / totalDurationMs) * 100;
              const label = ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
              return (
                <g key={ms}>
                  <line
                    x1={`${pct}%`}
                    y1={0}
                    x2={`${pct}%`}
                    y2={RULER_H}
                    stroke="currentColor"
                    strokeOpacity={0.2}
                    strokeWidth={1}
                  />
                  <text
                    x={`${pct}%`}
                    y={RULER_H - 4}
                    fontSize={10}
                    fill="currentColor"
                    fillOpacity={0.6}
                    textAnchor="middle"
                  >
                    {label}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Span rows */}
          <div className="flex flex-col gap-0.5 py-1">
            {spans.map((span) => {
              const spanStart = new Date(span.started_at).getTime();
              const spanEnd = span.ended_at ? new Date(span.ended_at).getTime() : null;
              const left = ((spanStart - runStart) / totalDurationMs) * 100;
              const widthPct = spanEnd
                ? ((spanEnd - spanStart) / totalDurationMs) * 100
                : null;

              const isSelected = span.id === selectedSpanId;
              const isInFlight = span.ended_at === null;
              const isNew = newSpanIds.has(span.id);
              const barColor = serverBarColor(serverName);
              const label = span.tool_calls[0]?.tool_name ?? span.method ?? span.direction;

              return (
                <div
                  key={span.id}
                  className={`relative flex items-center`}
                  style={{ height: ROW_H }}
                  onClick={() => onSelectSpan(span.id)}
                >
                  {/* Label column */}
                  <div
                    className="sticky left-0 z-10 bg-background w-40 flex-shrink-0 truncate pr-2 text-xs text-muted-foreground"
                    title={label}
                  >
                    {label}
                  </div>

                  {/* Bar area */}
                  <div className="relative flex-1" style={{ height: ROW_H }}>
                    <div
                      className={`absolute top-1/2 -translate-y-1/2 h-5 cursor-pointer rounded-sm transition-shadow
                        ${isSelected ? "ring-2 ring-blue-500" : ""}
                        ${isNew ? "animate-pulse" : ""}
                        ${isInFlight ? "opacity-70" : ""}
                      `}
                      style={{
                        left: `${left}%`,
                        width: widthPct != null ? `max(2px, ${widthPct}%)` : "40px",
                        minWidth: "2px",
                        backgroundColor: barColor,
                        backgroundImage: isInFlight
                          ? "repeating-linear-gradient(45deg, transparent, transparent 4px, rgba(255,255,255,0.2) 4px, rgba(255,255,255,0.2) 8px)"
                          : "none",
                      }}
                      title={`${label} — ${span.duration_ms != null ? `${span.duration_ms}ms` : "in-flight"}`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
