"use client";
import { Loader2 } from "lucide-react";
import { type ScanDetail } from "@/lib/api";

interface Props {
  scan: ScanDetail;
}

export function ScanProgress({ scan }: Props) {
  const pct = scan.engines_requested
    ? Math.round((100 * scan.engines_completed) / scan.engines_requested)
    : 0;
  const done = scan.status === "completed" || scan.status === "failed";

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {!done && <Loader2 className="text-accent animate-spin" size={18} />}
          <span className="font-medium">
            {done ? "Scan complete" : "Scanning in progress…"}
          </span>
        </div>
        <span className="text-sm text-text-muted font-mono">
          {scan.engines_completed}/{scan.engines_requested}
        </span>
      </div>
      <div className="h-2 bg-bg-elevated rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-accent to-accent-hover transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-2 text-xs text-text-subtle">
        {done
          ? `Finished in ${
              scan.started_at && scan.completed_at
                ? `${Math.round(
                    (new Date(scan.completed_at).getTime() -
                      new Date(scan.started_at).getTime()) /
                      1000
                  )}s`
                : "—"
            }`
          : `Live updates over WebSocket — ${pct}% complete`}
      </div>
    </div>
  );
}
