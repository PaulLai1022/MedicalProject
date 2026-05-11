import { useMemo } from "react";
import { BookMarked, Check } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import type { McgHit } from "@/api/types";

interface McgPathProps {
  hits: McgHit[];
  decisionPath: string;
}

export function McgPath({ hits, decisionPath }: McgPathProps) {
  const grouped = useMemo(() => groupBy(hits, (h) => h.category || "Other"), [hits]);

  if (hits.length === 0 && !decisionPath) {
    return null;
  }

  return (
    <section className="surface overflow-hidden">
      <header className="flex items-center justify-between border-b border-ink-100 bg-ink-50/60 px-5 py-3">
        <div className="flex items-center gap-2">
          <BookMarked size={14} className="text-ink-500" />
          <h2 className="text-[14px] font-semibold text-ink-800">MCG decision path</h2>
          <span className="text-[11.5px] text-ink-400">Diabetes M-130 · 30th Ed</span>
        </div>
        {hits.length > 0 && (
          <Badge tone="brand" size="sm" dot>
            {hits.length} criteria met
          </Badge>
        )}
      </header>

      <div className="space-y-5 px-5 py-4">
        {Object.entries(grouped).map(([cat, items]) => (
          <div key={cat}>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-400">
              {cat}
            </p>
            <ul className="space-y-1.5">
              {items.map((hit) => (
                <li
                  key={hit.ruleId}
                  className="flex items-start gap-3 rounded-xl border border-ink-100 bg-white px-3 py-2.5"
                >
                  <span className="mt-0.5 grid h-5 w-5 flex-none place-items-center rounded-full bg-discharge-100">
                    <Check size={11} className="text-discharge-700" strokeWidth={3} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="flex flex-wrap items-center gap-2 text-[13px] text-ink-800">
                      <span className="font-mono text-[11.5px] text-ink-400">{hit.ruleId}</span>
                      <span>{hit.citation}</span>
                      {hit.severity && hit.severity !== "info" && (
                        <Badge size="sm" tone={hit.severity === "high" ? "admit" : "observe"}>
                          {hit.severity}
                        </Badge>
                      )}
                    </p>
                    {hit.evidence && (
                      <p className="mt-0.5 text-[11.5px] text-ink-500">
                        Evidence:{" "}
                        <span className="font-mono text-ink-700">{hit.evidence}</span>
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ))}

        {decisionPath && (
          <div className="rounded-xl bg-brand-50 px-3.5 py-2.5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-brand-700">
              Decision
            </p>
            <p className="mt-0.5 text-[13px] leading-relaxed text-brand-800">{decisionPath}</p>
          </div>
        )}
      </div>
    </section>
  );
}

function groupBy<T>(items: T[], key: (item: T) => string): Record<string, T[]> {
  const out: Record<string, T[]> = {};
  for (const item of items) {
    const k = key(item);
    (out[k] ||= []).push(item);
  }
  return out;
}
