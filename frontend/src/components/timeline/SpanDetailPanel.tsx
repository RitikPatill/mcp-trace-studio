"use client";

import { useState } from "react";
import { X } from "lucide-react";
import type { SpanRead } from "@/lib/api";
import { JsonDisplay } from "./JsonDisplay";
import { LatencySparkline } from "./LatencySparkline";

interface Props {
  span: SpanRead;
  allSpans: SpanRead[];
  onClose: () => void;
}

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function SpanDetailPanel({ span, allSpans, onClose }: Props) {
  const [curlCopied, setCurlCopied] = useState(false);
  const [mcpCopied, setMcpCopied] = useState(false);

  const toolCall = span.tool_calls[0] ?? null;

  function copyText(text: string, setter: (v: boolean) => void) {
    navigator.clipboard.writeText(text).then(() => {
      setter(true);
      setTimeout(() => setter(false), 1500);
    });
  }

  function buildCurl(): string {
    if (!toolCall) return "";
    let args: unknown = {};
    try {
      args = JSON.parse(toolCall.args_json);
    } catch {
      args = {};
    }
    return (
      `curl -sX POST ${BASE}/mcp/call \\\n` +
      `  -H 'Content-Type: application/json' \\\n` +
      `  -d '${JSON.stringify({ method: "tools/call", params: { name: toolCall.tool_name, arguments: args } })}'`
    );
  }

  function buildMcpCall(): string {
    let params: unknown = {};
    if (toolCall) {
      try {
        params = { name: toolCall.tool_name, arguments: JSON.parse(toolCall.args_json) };
      } catch {
        params = { name: toolCall.tool_name };
      }
    }
    return JSON.stringify({ jsonrpc: "2.0", id: 1, method: span.method ?? "tools/call", params }, null, 2);
  }

  const durationLabel =
    span.duration_ms != null
      ? span.duration_ms < 1000
        ? `${span.duration_ms} ms`
        : `${(span.duration_ms / 1000).toFixed(2)} s`
      : "in-flight";

  return (
    <div className="flex h-full w-[420px] flex-shrink-0 flex-col border-l border-border bg-background overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div className="min-w-0 flex-1">
          <p className="truncate font-mono text-sm font-semibold">
            {span.method ?? span.direction}
          </p>
          <div className="mt-0.5 flex items-center gap-2">
            <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
              {span.direction}
            </span>
            <span className="text-xs text-muted-foreground">{durationLabel}</span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 hover:bg-accent"
          aria-label="Close panel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-4 py-3 text-sm">
        {/* Tool call section */}
        {toolCall && (
          <div className="mb-4">
            <h3 className="mb-2 font-semibold">{toolCall.tool_name}</h3>

            <JsonDisplay label="Arguments" json={toolCall.args_json} />
            <JsonDisplay label="Result" json={toolCall.result_json} />

            {toolCall.error && (
              <div className="mt-2 rounded border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
                <span className="font-semibold">Error: </span>
                {toolCall.error}
              </div>
            )}

            {/* Copy buttons */}
            <div className="mt-3 flex gap-2">
              <button
                onClick={() => copyText(buildCurl(), setCurlCopied)}
                className="rounded border border-border px-2.5 py-1 text-xs hover:bg-accent"
              >
                {curlCopied ? "Copied!" : "Copy as cURL"}
              </button>
              <button
                onClick={() => copyText(buildMcpCall(), setMcpCopied)}
                className="rounded border border-border px-2.5 py-1 text-xs hover:bg-accent"
              >
                {mcpCopied ? "Copied!" : "Copy as MCP call"}
              </button>
            </div>
          </div>
        )}

        {/* Raw span IDs */}
        <div className="mt-2 space-y-1 text-xs text-muted-foreground">
          <div>
            <span className="font-medium">Span: </span>
            <span className="font-mono">{span.id}</span>
          </div>
          <div>
            <span className="font-medium">Started: </span>
            {new Date(span.started_at).toLocaleTimeString()}
          </div>
          {span.ended_at && (
            <div>
              <span className="font-medium">Ended: </span>
              {new Date(span.ended_at).toLocaleTimeString()}
            </div>
          )}
        </div>

        {/* Latency sparkline */}
        <LatencySparkline spans={allSpans} highlightSpanId={span.id} />
      </div>
    </div>
  );
}
