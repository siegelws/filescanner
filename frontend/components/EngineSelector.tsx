"use client";
import { Check, Square, CheckSquare } from "lucide-react";
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
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="font-medium">AV engines</div>
          <div className="text-xs text-text-muted">
            {selected.size} of {engines.length} selected
          </div>
        </div>
        <button onClick={toggleAll} className="btn text-xs">
          {allSelected ? <Square size={14} /> : <CheckSquare size={14} />}
          {allSelected ? "Deselect all" : "Select all"}
        </button>
      </div>
      <div className="grid sm:grid-cols-2 gap-2">
        {engines.map((e) => {
          const isSel = selected.has(e.id);
          return (
            <button
              key={e.id}
              type="button"
              onClick={() => toggle(e.id)}
              disabled={!e.enabled}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition",
                isSel
                  ? "bg-accent/10 border-accent/50"
                  : "bg-bg-subtle border-border hover:border-border-strong",
                !e.enabled && "opacity-40 cursor-not-allowed"
              )}
            >
              <div
                className={cn(
                  "w-5 h-5 rounded border flex items-center justify-center shrink-0",
                  isSel ? "bg-accent border-accent" : "border-border-strong"
                )}
              >
                {isSel && <Check size={14} className="text-black" />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{e.name}</div>
                <div className="text-xs text-text-muted truncate">{e.vendor}</div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
