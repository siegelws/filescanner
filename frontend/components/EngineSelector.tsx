"use client";
import { Check, Square, CheckSquare, Sparkles } from "lucide-react";
import { type EngineInfo } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  engines: EngineInfo[];
  selected: Set<string>;
  onChange: (sel: Set<string>) => void;
}

export function EngineSelector({ engines, selected, onChange }: Props) {
  const allSelected = selected.size === engines.length;

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange(next);
  }

  function toggleAll() {
    onChange(allSelected ? new Set() : new Set(engines.map((e) => e.id)));
  }

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-accent" />
          <div>
            <div className="font-display text-lg">AV engines</div>
            <div className="text-xs text-text-muted">
              {selected.size} of {engines.length} selected
            </div>
          </div>
        </div>
        <button onClick={toggleAll} className="btn text-xs">
          {allSelected ? <Square size={14} /> : <CheckSquare size={14} />}
          {allSelected ? "Deselect all" : "Select all"}
        </button>
      </div>
      <div className="grid sm:grid-cols-2 gap-3">
        {engines.map((e) => {
          const isSel = selected.has(e.id);
          return (
            <button
              key={e.id}
              type="button"
              onClick={() => toggle(e.id)}
              disabled={!e.enabled}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-xl border text-left transition-all",
                isSel
                  ? "bg-accent-soft border-accent shadow-soft"
                  : "bg-bg-elevated border-border hover:border-accent",
                !e.enabled && "opacity-40 cursor-not-allowed"
              )}
            >
              <div
                className={cn(
                  "w-5 h-5 rounded-md flex items-center justify-center shrink-0 transition",
                  isSel ? "bg-gold-gradient" : "bg-white border border-border-strong"
                )}
              >
                {isSel && <Check size={14} className="text-white" strokeWidth={3} />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold truncate">{e.name}</div>
                <div className="text-xs text-text-muted truncate">{e.vendor}</div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
