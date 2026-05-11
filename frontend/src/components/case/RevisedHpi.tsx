import { motion } from "framer-motion";
import { Quote, BookMarked, FileText } from "lucide-react";
import { OriginDot } from "@/components/ui/OriginDot";
import { Badge } from "@/components/ui/Badge";
import type { Sentence } from "@/api/types";

interface RevisedHpiProps {
  sentences: Sentence[];
  sentenceEdits: Record<string, string>;
  setSentenceEdit: (id: string, text: string) => void;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

export function RevisedHpi({
  sentences,
  sentenceEdits,
  setSentenceEdit,
  selectedId,
  onSelect,
}: RevisedHpiProps) {
  if (sentences.length === 0) {
    return (
      <div className="surface px-6 py-10 text-center">
        <FileText size={20} className="mx-auto mb-2 text-ink-300" />
        <p className="text-[13px] text-ink-500">
          No narrative available — LLM is not configured or call failed.
        </p>
        <p className="mt-1 text-[12px] text-ink-400">
          Structured fields are still available for review on the right.
        </p>
      </div>
    );
  }

  return (
    <section className="surface overflow-hidden">
      <header className="flex items-center justify-between border-b border-ink-100 bg-ink-50/60 px-5 py-3">
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-ink-500" />
          <h2 className="text-[14px] font-semibold text-ink-800">Revised HPI</h2>
          <Badge tone="neutral" size="sm">{sentences.length} sentences</Badge>
        </div>
        <p className="hidden text-[11.5px] text-ink-400 sm:block">
          Click a sentence to highlight its source on the left
        </p>
      </header>

      <ol className="divide-y divide-ink-100">
        {sentences.map((sent, i) => (
          <SentenceRow
            key={sent.id}
            sentence={sent}
            index={i}
            edited={sentenceEdits[sent.id]}
            onChange={(text) => setSentenceEdit(sent.id, text)}
            selected={selectedId === sent.id}
            onSelect={() => onSelect(selectedId === sent.id ? null : sent.id)}
          />
        ))}
      </ol>
    </section>
  );
}

function SentenceRow({
  sentence,
  index,
  edited,
  onChange,
  selected,
  onSelect,
}: {
  sentence: Sentence;
  index: number;
  edited?: string;
  onChange: (text: string) => void;
  selected: boolean;
  onSelect: () => void;
}) {
  const value = edited ?? sentence.text;
  const isEdited = edited !== undefined || sentence.origin === "user";

  return (
    <motion.li
      layout
      initial={false}
      animate={{ backgroundColor: selected ? "rgba(10,108,255,0.04)" : "rgba(255,255,255,0)" }}
      transition={{ duration: 0.2, ease: [0.32, 0.72, 0, 1] }}
      className="relative px-5 py-4"
    >
      {selected && (
        <motion.span
          layoutId="sentence-active-indicator"
          className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-brand-600"
        />
      )}

      <div className="mb-2 flex items-center justify-between">
        <button
          type="button"
          onClick={onSelect}
          className="group inline-flex items-center gap-2"
        >
          <span className="grid h-5 w-5 place-items-center rounded-full bg-ink-100 text-[10.5px] font-semibold text-ink-600 transition-colors group-hover:bg-brand-100 group-hover:text-brand-700">
            {index + 1}
          </span>
          <span className="text-[11px] font-medium text-ink-400 group-hover:text-brand-600">
            {selected ? "Tracing source" : "Click to trace"}
          </span>
        </button>
        <OriginDot
          origin={isEdited ? "user" : "machine"}
          machineValue={sentence.machineText}
          showLabel
          size="sm"
        />
      </div>

      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={2}
        className="block w-full resize-y rounded-lg bg-transparent px-0 py-1 text-[14px] leading-relaxed text-ink-800 outline-none focus:outline-none"
      />

      {(sentence.sources.length > 0 || sentence.reasonGuideline) && (
        <div className="mt-2 grid gap-1.5 text-[12px]">
          {sentence.sources.length > 0 && (
            <div className="flex items-start gap-2 text-ink-500">
              <Quote size={11} className="mt-1 flex-none text-ink-400" />
              <p className="leading-relaxed">
                {sentence.sources.map((src, i) => (
                  <span key={i}>
                    <span className="italic">"{src}"</span>
                    {i < sentence.sources.length - 1 && <span className="text-ink-300"> · </span>}
                  </span>
                ))}
              </p>
            </div>
          )}
          {sentence.reasonGuideline && (
            <div className="flex items-start gap-2 text-brand-700">
              <BookMarked size={11} className="mt-1 flex-none text-brand-500" />
              <p className="leading-relaxed">{sentence.reasonGuideline}</p>
            </div>
          )}
        </div>
      )}
    </motion.li>
  );
}
