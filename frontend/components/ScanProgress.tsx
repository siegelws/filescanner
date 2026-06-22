"use client";
import { Loader2, Sparkles } from "lucide-react";
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
    <div className="card p-6 relative overflow-hidden">
      <div
        className="pointer-events-none absolute inset-0 opacity-50"
        style={{ background: "radial-gradient(400px 120px at 90% 0%, rgba(247,184,214,0.4), transparent 70%)" }}
      />
      <div className="relative flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {!done ? (
            <Loader2 className="text-accent animate-spin" size={20} />
          ) : (
            <Sparkles className="text-accent" size={20} />
          )}
          <span className="font-display text-lg">
            {done ? "Scan complete" : "Scanning in progress…"}
          </span>
        </div>
        <span className="text-sm font-mono font-semibold text-accent">
          {scan.engines_completed} / {scan.engines_requested}
        </span>
      </div>
      <div className="relative h-2.5 bg-bg-elevated rounded-full overflow-hidden border border-border">
        <div
          className="h-full bg-gold-gradient transition-all duration-500 relative"
          style={{ width: `${pct}%` }}
        >
          {!done && (
            <div
              className="absolute inset-0 opacity-60 animate-shimmer"
              style={{
                backgroundImage:
                  "linear-gradient(110deg, transparent 30%, rgba(255,255,255,0.6) 50%, transparent 70%)",
                backgroundSize: "200% 100%",
              }}
            />
          )}
        </div>
      </div>
      <div className="mt-2.5 text-xs text-text-muted">
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
          : `${pct}% complete — live updates over WebSocket`}
      </div>
    </div>
  );
}
