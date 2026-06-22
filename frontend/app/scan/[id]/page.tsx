"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { ScanSummary } from "@/components/ScanSummary";
import { ScanProgress } from "@/components/ScanProgress";
import { ResultsTable } from "@/components/ResultsTable";
import { api, type ScanDetail, type EngineResult } from "@/lib/api";
import { openScanSocket, type ScanEvent } from "@/lib/ws";

export default function ScanPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Initial fetch — handles deep-linking to a completed scan and gives the
  // WS a baseline if it connects fast.
  useEffect(() => {
    api
      .getScan(id)
      .then(setScan)
      .catch((e) => setError(e.message));
  }, [id]);

  // Live updates — WebSocket sends a snapshot on connect, then per-engine
  // results, then a final `completed` event with the full ScanDetail.
  useEffect(() => {
    const close = openScanSocket(id, (event: ScanEvent) => {
      setScan((prev) => mergeEvent(prev, event));
    });
    return close;
  }, [id]);

  if (error)
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <div className="text-danger font-medium">Could not load scan</div>
        <div className="text-text-muted text-sm mt-2">{error}</div>
      </div>
    );

  if (!scan)
    return (
      <div className="max-w-3xl mx-auto px-4 py-24 flex items-center justify-center gap-3 text-text-muted">
        <Loader2 className="animate-spin text-accent" size={20} /> Loading scan…
      </div>
    );

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <ScanSummary scan={scan} />
      {scan.status !== "completed" && <ScanProgress scan={scan} />}
      <ResultsTable results={scan.results} />
    </div>
  );
}

/** Apply a single ScanEvent to the current ScanDetail in an immutable way. */
function mergeEvent(prev: ScanDetail | null, e: ScanEvent): ScanDetail | null {
  switch (e.type) {
    case "snapshot":
      return e.scan;
    case "completed":
      return e.scan;
    case "result": {
      if (!prev) return prev;
      const results = upsertResult(prev.results, e.result);
      return { ...prev, results };
    }
    case "engine_started": {
      if (!prev) return prev;
      const results = prev.results.map((r) =>
        r.engine_id === e.engine_id && r.status === "pending"
          ? { ...r, status: "running" as const }
          : r
      );
      return { ...prev, results };
    }
    case "progress": {
      if (!prev) return prev;
      return {
        ...prev,
        engines_completed: e.completed,
        detections: e.detections,
        progress: e.total ? Math.round((100 * e.completed) / e.total) : 0,
      };
    }
    case "started": {
      if (!prev) return prev;
      return { ...prev, status: "running" };
    }
    default:
      return prev;
  }
}

function upsertResult(list: EngineResult[], next: EngineResult): EngineResult[] {
  const idx = list.findIndex((r) => r.engine_id === next.engine_id);
  if (idx < 0) return [...list, next];
  const copy = list.slice();
  copy[idx] = next;
  return copy;
}
