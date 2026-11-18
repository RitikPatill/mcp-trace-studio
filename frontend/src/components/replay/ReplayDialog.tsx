"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { replayRun } from "@/lib/api";

interface Props {
  runId: string;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export function ReplayDialog({ runId, open, onOpenChange }: Props) {
  const router = useRouter();
  const serverNameRef = useRef<HTMLInputElement>(null);
  const modelNameRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const serverName = serverNameRef.current?.value.trim() ?? "";
    if (!serverName) return;
    const modelName = modelNameRef.current?.value.trim() || undefined;

    setLoading(true);
    setError(null);
    try {
      const newRun = await replayRun(runId, { server_name: serverName, model_name: modelName });
      onOpenChange(false);
      router.push(`/runs/${newRun.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Replay failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Replay Run</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium" htmlFor="replay-server">
              Server name <span className="text-destructive">*</span>
            </label>
            <input
              id="replay-server"
              ref={serverNameRef}
              required
              disabled={loading}
              placeholder="filesystem"
              className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium" htmlFor="replay-model">
              Model name <span className="text-muted-foreground text-xs">(optional)</span>
            </label>
            <input
              id="replay-model"
              ref={modelNameRef}
              disabled={loading}
              placeholder="claude-opus-4-6"
              className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Starting…" : "Replay"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
