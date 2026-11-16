"use client";

import type { SpanRead } from "@/lib/api";

interface Props {
  spans: SpanRead[];
  highlightSpanId: string;
}

export function LatencySparkline({ spans, highlightSpanId }: Props) {
  const timed = spans
    .filter((s) => s.duration_ms != null)
    .sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime());

  if (timed.length === 0) return null;

  const maxMs = Math.max(...timed.map((s) => s.duration_ms!));
  const height = 56;
  const barWidth = Math.max(4, Math.floor(300 / timed.length));
  const svgWidth = timed.length * (barWidth + 2);

  return (
    <div className="mt-4">
      <p className="mb-1 text-xs font-medium text-muted-foreground">Latency (ms)</p>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${svgWidth} ${height}`}
        preserveAspectRatio="none"
        className="overflow-visible"
      >
        {timed.map((s, i) => {
          const barH = maxMs > 0 ? Math.max(2, (s.duration_ms! / maxMs) * (height - 10)) : 2;
          const x = i * (barWidth + 2);
          const y = height - barH;
          const isHighlighted = s.id === highlightSpanId;
          return (
            <g key={s.id}>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barH}
                fill={isHighlighted ? "hsl(var(--primary))" : "currentColor"}
                opacity={isHighlighted ? 1 : 0.4}
                rx={1}
              >
                <title>{`${s.method ?? s.direction}: ${s.duration_ms} ms`}</title>
              </rect>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
