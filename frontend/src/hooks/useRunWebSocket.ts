"use client";

import { useEffect, useRef, useState } from "react";
import type { SpanRead } from "@/lib/api";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function toWsUrl(runId: string): string {
  const wsBase = BASE.startsWith("https://")
    ? BASE.replace("https://", "wss://")
    : BASE.replace("http://", "ws://");
  return `${wsBase}/ws/runs/${runId}`;
}

export function useRunWebSocket(runId: string): {
  liveSpans: SpanRead[];
  connected: boolean;
} {
  const [liveSpans, setLiveSpans] = useState<SpanRead[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(toWsUrl(runId));
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (event: MessageEvent) => {
      try {
        const span = JSON.parse(event.data as string) as SpanRead;
        setLiveSpans((prev) => {
          const idx = prev.findIndex((s) => s.id === span.id);
          if (idx === -1) return [...prev, span];
          const next = [...prev];
          next[idx] = span;
          return next;
        });
      } catch {
        // ignore malformed frames
      }
    };

    return () => {
      ws.close();
    };
  }, [runId]);

  return { liveSpans, connected };
}
