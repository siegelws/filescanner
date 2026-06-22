"use client";
import { ShieldCheck, ShieldAlert, ShieldX, FileText, Hash } from "lucide-react";
import { type ScanDetail } from "@/lib/api";
import { formatBytes } from "@/lib/utils";
import { cn } from "@/lib/utils";

export function ScanSummary({ scan }: { scan: ScanDetail }) {
  const detections = scan.detections;
  const total = scan.engines_requested;
  const verdict =
    scan.status !== "completed"
      ? "pending"
      : detections === 0
      ? "clean"
      : detections >= Math.ceil(total / 2)
      ? "malicious"
      : "suspicious";

  const v = {
    clean: {
      icon: ShieldCheck,
      label: "Clean",
      tint: "bg-success/10 border-success/40 text-success",
      ring: "ring-success/30",
    },
    suspicious: {
      icon: ShieldAlert,
      label: "Suspicious",
      tint: "bg-warn/10 border-warn/40 text-warn",
      ring: "ring-warn/30",
    },
    malicious: {
      icon: ShieldX,
      label: "Malicious",
      tint: "bg-danger/10 border-danger/40 text-danger",
      ring: "ring-danger/30",
    },
    pending: {
      icon: ShieldAlert,
      label: "Pending",
      tint: "bg-bg-elevated border-border text-text-muted",
      ring: "ring-border",
    },
  }[verdict];

  const Icon = v.icon;

  return (
    <div className={cn("card p-6 ring-1", v.ring)}>
      <div className="flex items-start gap-5">
        <div className={cn("p-3 rounded-xl border", v.tint)}>
          <Icon size={32} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-3 flex-wrap">
            <h2 className="text-2xl font-bold">{v.label}</h2>
            <span className="text-text-muted text-sm">
              Detected by{" "}
              <span className="text-text font-mono font-semibold">
                {detections}/{total}
              </span>{" "}
              engines
            </span>
          </div>
          <div className="mt-3 flex items-center gap-2 text-sm text-text-muted">
            <FileText size={14} />
            <span className="truncate font-medium text-text">{scan.filename}</span>
            <span className="text-text-subtle">· {formatBytes(scan.file_size)}</span>
            {scan.mime_type && (
              <span className="text-text-subtle">· {scan.mime_type}</span>
            )}
          </div>
          <div className="mt-2 grid sm:grid-cols-3 gap-x-6 gap-y-1 text-xs font-mono">
            <HashRow label="MD5" value={scan.md5} />
            <HashRow label="SHA1" value={scan.sha1} />
            <HashRow label="SHA256" value={scan.sha256} />
          </div>
        </div>
      </div>
    </div>
  );
}

function HashRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5 min-w-0">
      <Hash size={11} className="text-text-subtle shrink-0" />
      <span className="text-text-subtle">{label}</span>
      <span className="truncate text-text-muted">{value}</span>
    </div>
  );
}
