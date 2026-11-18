"use client";

import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { listRuns, type RunSummary } from "@/lib/api";
import { serverColor } from "@/lib/utils";

interface Props {
  currentRunId: string;
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSelect: (runId: string) => void;
}

function formatTs(ts: string): string {
  return new Date(ts).toLocaleString();
}

export function DiffRunPickerDialog({ currentRunId, open, onOpenChange, onSelect }: Props) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    listRuns()
      .then((data) => setRuns(data.filter((r) => r.id !== currentRunId)))
      .finally(() => setLoading(false));
  }, [open, currentRunId]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Select run to diff against</DialogTitle>
        </DialogHeader>
        <div className="max-h-96 overflow-y-auto">
          {loading ? (
            <p className="py-4 text-center text-sm text-muted-foreground">Loading…</p>
          ) : runs.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">No other runs available.</p>
          ) : (
            <ul className="divide-y">
              {runs.map((run) => (
                <li key={run.id}>
                  <button
                    className="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-accent transition-colors"
                    onClick={() => {
                      onOpenChange(false);
                      onSelect(run.id);
                    }}
                  >
                    <span className="font-mono text-xs text-muted-foreground w-24 shrink-0">
                      {run.id.slice(0, 8)}…
                    </span>
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium shrink-0 ${serverColor(run.server_name)}`}
                    >
                      {run.server_name}
                    </span>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {formatTs(run.started_at)}
                    </span>
                    <span className="ml-auto text-xs text-muted-foreground shrink-0">
                      {run.tool_call_count} calls
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
