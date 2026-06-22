"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, Server, Zap, Sparkles } from "lucide-react";
import { UploadZone } from "@/components/UploadZone";
import { EngineSelector } from "@/components/EngineSelector";
import { api, type EngineInfo } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [engines, setEngines] = useState<EngineInfo[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [uploadPct, setUploadPct] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listEngines()
      .then((list) => {
        setEngines(list);
        setSelected(new Set(list.filter((e) => e.enabled).map((e) => e.id)));
      })
      .catch((e) => setError(e.message));
  }, []);

  async function submit() {
    if (!file) return;
    setError(null);
    setSubmitting(true);
    setUploadPct(0);
    try {
      const res = await api.createScan(
        file,
        selected.size === engines.length ? null : Array.from(selected),
        (loaded, total) => setUploadPct(Math.round((100 * loaded) / total))
      );
      router.push(`/scan/${res.id}`);
    } catch (e: any) {
      setError(e.message || "Upload failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-border shadow-soft mb-5">
          <Sparkles className="text-accent" size={14} />
          <span className="text-xs font-semibold tracking-wide text-text-muted uppercase">
            Multi-engine malware analysis
          </span>
        </div>
        <h1 className="font-display text-5xl sm:text-6xl font-semibold tracking-tight leading-[1.05]">
          Scan with <span className="text-lux">85+&nbsp;antivirus engines</span>
          <br />
          <span className="text-text-muted text-3xl sm:text-4xl">in a single click.</span>
        </h1>
        <p className="mt-5 text-text-muted max-w-2xl mx-auto text-base leading-relaxed">
          Drag any file in and instantly get verdicts from ClamAV, YARA, plus
          every major commercial vendor via VirusTotal, MetaDefender and Hybrid
          Analysis — all from one elegant dashboard.
        </p>
      </div>

      <UploadZone
        file={file}
        onFile={setFile}
        submitting={submitting}
        uploadPct={uploadPct}
      />

      {engines.length > 0 && (
        <div className="mt-6">
          <EngineSelector engines={engines} selected={selected} onChange={setSelected} />
        </div>
      )}

      <div className="mt-6 flex items-center justify-between gap-4">
        <div className="text-xs text-text-muted">
          {selected.size === 0
            ? "Select at least one engine"
            : <>Will scan with <span className="font-semibold text-text">{selected.size}</span> engine{selected.size === 1 ? "" : "s"}</>}
        </div>
        <button
          disabled={!file || selected.size === 0 || submitting}
          onClick={submit}
          className="btn-primary"
        >
          <Zap size={16} /> {submitting ? "Uploading…" : "Start scan"}
        </button>
      </div>

      {error && (
        <div className="mt-4 text-danger text-sm bg-danger-soft border border-danger-border px-3 py-2 rounded-xl">
          {error}
        </div>
      )}

      <div className="mt-20 grid sm:grid-cols-3 gap-5">
        <Feature icon={ShieldCheck} title="Container-isolated">
          Files are scanned in sealed containers and never executed on this host.
        </Feature>
        <Feature icon={Server} title="Parallel multi-engine">
          Up to ~85 vendor verdicts in seconds. Expand any tile to see receipts.
        </Feature>
        <Feature icon={Zap} title="Real-time results">
          WebSocket pushes per-engine verdicts the moment each one completes.
        </Feature>
      </div>
    </div>
  );
}

function Feature({
  icon: Icon,
  title,
  children,
}: {
  icon: any;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-5 hover:shadow-pop transition-shadow">
      <div className="w-10 h-10 rounded-full bg-pink-soft flex items-center justify-center mb-3">
        <Icon className="text-pink-deep" size={18} />
      </div>
      <div className="font-display text-lg font-semibold">{title}</div>
      <div className="text-sm text-text-muted mt-1.5 leading-relaxed">{children}</div>
    </div>
  );
}
