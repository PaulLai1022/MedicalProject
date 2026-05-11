import { useEffect, useMemo, useRef } from "react";
import { FileText } from "lucide-react";

interface SourceNoteProps {
  rawText: string;
  highlights: string[];
}

export function SourceNote({ rawText, highlights }: SourceNoteProps) {
  const firstMarkRef = useRef<HTMLElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const segments = useMemo(() => buildSegments(rawText, highlights), [rawText, highlights]);
  const hitCount = segments.filter((s) => s.hit).length;

  useEffect(() => {
    if (firstMarkRef.current && containerRef.current) {
      const mark = firstMarkRef.current;
      const container = containerRef.current;
      const markTop = mark.offsetTop;
      const target = markTop - container.clientHeight / 2 + mark.offsetHeight / 2;
      container.scrollTo({ top: Math.max(0, target), behavior: "smooth" });
    }
  }, [highlights]);

  let firstHitAssigned = false;

  return (
    <div className="surface flex h-full min-h-[420px] flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-ink-100 bg-ink-50/60 px-4 py-2.5">
        <div className="flex items-center gap-2 text-[12px] font-semibold uppercase tracking-[0.08em] text-ink-500">
          <FileText size={13} />
          Source note
        </div>
        <div className="flex items-center gap-3 text-[11px] text-ink-400">
          <span>{rawText.length.toLocaleString()} chars</span>
          {highlights.length > 0 && (
            <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-brand-700">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-600" />
              {hitCount} match{hitCount === 1 ? "" : "es"}
            </span>
          )}
        </div>
      </div>

      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto px-5 py-4 font-mono text-[12.5px] leading-[1.7] text-ink-700"
      >
        <pre className="whitespace-pre-wrap break-words font-mono">
          {segments.map((seg, i) => {
            if (!seg.hit) return <span key={i}>{seg.text}</span>;
            const assignRef = !firstHitAssigned;
            firstHitAssigned = true;
            return (
              <mark
                key={i}
                ref={(el) => { if (assignRef) firstMarkRef.current = el; }}
                className="rounded-md bg-brand-100 px-0.5 py-px text-brand-900 ring-1 ring-brand-200/60 transition-colors"
              >
                {seg.text}
              </mark>
            );
          })}
        </pre>

        {segments.length === 0 && (
          <p className="text-ink-400">No source text.</p>
        )}
      </div>
    </div>
  );
}

interface Segment { text: string; hit: boolean; }

function buildSegments(text: string, highlights: string[]): Segment[] {
  if (!text) return [];
  const valid = highlights
    .map((h) => (h ?? "").trim())
    .filter((h) => h.length >= 4);
  if (valid.length === 0) return [{ text, hit: false }];

  const ranges: Array<[number, number]> = [];
  for (const h of valid) {
    let i = text.indexOf(h);
    while (i !== -1) {
      ranges.push([i, i + h.length]);
      i = text.indexOf(h, i + h.length);
    }
  }
  if (ranges.length === 0) return [{ text, hit: false }];

  ranges.sort((a, b) => a[0] - b[0]);
  const merged: Array<[number, number]> = [];
  for (const r of ranges) {
    const last = merged[merged.length - 1];
    if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]);
    else merged.push([r[0], r[1]]);
  }

  const out: Segment[] = [];
  let cursor = 0;
  for (const [start, end] of merged) {
    if (start > cursor) out.push({ text: text.slice(cursor, start), hit: false });
    out.push({ text: text.slice(start, end), hit: true });
    cursor = end;
  }
  if (cursor < text.length) out.push({ text: text.slice(cursor), hit: false });
  return out;
}
