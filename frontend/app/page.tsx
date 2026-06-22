"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, Server, Zap } from "lucide-react";
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
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="text-center mb-10">
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight">
          Scan with <span className="text-accent">multiple AV engines</span> at once
        </h1>
        <p className="mt-4 text-text-muted max-w-2xl mx-auto">
          Upload an executable, script, document or archive. Each engine runs in its own
          isolated VM — your file is never executed on this server.
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
        <div className="text-xs text-text-subtle">
          {selected.size === 0
            ? "Select at least one engine"
            : `Will scan with ${selected.size} engine${selected.size === 1 ? "" : "s"}`}
        </div>
        <button
          disabled={!file || selected.size === 0 || submitting}
          onClick={submit}
          className="btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Zap size={16} /> {submitting ? "Uploading…" : "Start scan"}
        </button>
      </div>

      {error && (
        <div className="mt-4 text-danger text-sm bg-danger-soft/40 border border-danger/30 px-3 py-2 rounded-lg">
          {error}
        </div>
      )}

      <div className="mt-16 grid sm:grid-cols-3 gap-4">
        <Feature icon={ShieldCheck} title="Sandbox-only execution">
          Files are processed in disposable VMs. Snapshots are reverted between scans.
        </Feature>
        <Feature icon={Server} title="Multi-engine parallel">
          Up to a dozen AV vendors scan your file simultaneously, results streamed live.
        </Feature>
        <Feature icon={Zap} title="Real-time results">
          A WebSocket pushes per-engine verdicts the moment each VM completes.
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
    <div className="card p-4">
      <Icon className="text-accent mb-2" size={20} />
      <div className="font-medium">{title}</div>
      <div className="text-sm text-text-muted mt-1">{children}</div>
    </div>
  );
}
