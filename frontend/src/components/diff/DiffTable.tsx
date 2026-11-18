"use client";

import { useState } from "react";
import { type DiffEntry } from "@/lib/api";
import { JsonLineDiff } from "./JsonLineDiff";

interface Props {
  entries: DiffEntry[];
}

function LatencyBadge({ delta }: { delta: number | null }) {
  if (delta === null) return <span className="text-muted-foreground">—</span>;
  const sign = delta >= 0 ? "+" : "−";
  const abs = Math.abs(delta).toFixed(1);
  const cls = delta >= 0 ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400";
  return <span className={`font-mono text-xs font-medium ${cls}`}>{sign}{abs}ms</span>;
}

function RowBg({ entry }: { entry: DiffEntry }) {
  if (entry.tool_call_a === null || entry.tool_call_b === null) {
    return "bg-muted/40";
  }
  if (entry.args_changed && entry.result_changed) return "bg-red-50 dark:bg-red-950/20";
  if (entry.args_changed) return "bg-yellow-50 dark:bg-yellow-950/20";
  if (entry.result_changed) return "bg-green-50 dark:bg-green-950/20";
  return "";
}

function DiffCell({
  changed,
  tcA,
  tcB,
  field,
}: {
  changed: boolean;
  tcA: string | null | undefined;
  tcB: string | null | undefined;
  field: "args" | "result";
}) {
  const [expanded, setExpanded] = useState(false);

  if (!changed) {
    return <span className="text-xs text-muted-foreground">same</span>;
  }
  if (!tcA || !tcB) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }

  return (
    <div>
      <button
        onClick={() => setExpanded((v) => !v)}
        className="text-xs underline text-primary hover:no-underline"
      >
        {expanded ? "hide" : "show diff"}
      </button>
      {expanded && (
        <div className="mt-1">
          <JsonLineDiff before={tcA} after={tcB} />
        </div>
      )}
    </div>
  );
}

export function DiffTable({ entries }: Props) {
  if (entries.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
        No tool calls to compare.
      </div>
    );
  }

  return (
    <div className="overflow-auto rounded-md border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50 text-xs text-muted-foreground">
            <th className="px-3 py-2 text-left font-medium">Tool</th>
            <th className="px-3 py-2 text-left font-medium">#</th>
            <th className="px-3 py-2 text-left font-medium">Args</th>
            <th className="px-3 py-2 text-left font-medium">Result</th>
            <th className="px-3 py-2 text-left font-medium">Δ Latency</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, i) => (
            <tr key={i} className={`border-b last:border-0 ${RowBg({ entry })}`}>
              <td className="px-3 py-2 font-mono text-xs">{entry.tool_name}</td>
              <td className="px-3 py-2 text-xs text-muted-foreground">{entry.call_index}</td>
              <td className="px-3 py-2">
                <DiffCell
                  changed={entry.args_changed}
                  tcA={entry.tool_call_a?.args_json}
                  tcB={entry.tool_call_b?.args_json}
                  field="args"
                />
              </td>
              <td className="px-3 py-2">
                <DiffCell
                  changed={entry.result_changed}
                  tcA={entry.tool_call_a?.result_json ?? undefined}
                  tcB={entry.tool_call_b?.result_json ?? undefined}
                  field="result"
                />
              </td>
              <td className="px-3 py-2">
                <LatencyBadge delta={entry.latency_delta_ms} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
