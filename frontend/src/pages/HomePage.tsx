import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, FileText, Sparkles, Check } from "lucide-react";
import { createCase, generateCaseStream } from "@/api/cases";
import { Button } from "@/components/ui/Button";
import { SAMPLES } from "@/lib/samples";

const MIN_CHARS = 20;

// Labels mirror the stage descriptors emitted by the backend
// (see backend/app/services/generation_service.py:_STAGES). The actual
// progress is driven by SSE `stage` events at runtime; these labels are
// the rendering source of truth and assume the same ordering.
const PROGRESS_STEPS = [
  "Reading note",
  "Extracting facts with LLM",
  "Cross-checking values & matching MCG rules",
  "Composing Revised HPI",
];
const TOTAL_STEPS = PROGRESS_STEPS.length;

export function HomePage() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  // -1 = not started; 0..TOTAL_STEPS-1 = active step; TOTAL_STEPS = all done.
  const [currentStage, setCurrentStage] = useState(-1);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const abortRef = useRef<AbortController | null>(null);

  const trimmed = text.trim();
  const isValid = trimmed.length >= MIN_CHARS;

  // Cancel any in-flight stream when the component unmounts.
  useEffect(() => () => abortRef.current?.abort(), []);

  const handleGenerate = async () => {
    if (!isValid || loading) return;
    setLoading(true);
    setError("");
    setCurrentStage(-1);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const { id } = await createCase(text);
      await generateCaseStream(id, {
        signal: controller.signal,
        onStage: (e) => setCurrentStage(e.index),
      });
      setCurrentStage(TOTAL_STEPS);
      navigate(`/cases/${id}`);
    } catch (err: unknown) {
      if ((err as { name?: string })?.name === "AbortError") return;
      const msg = (err as Error)?.message || "Generation failed. Please try again.";
      setError(msg);
    } finally {
      abortRef.current = null;
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      {/* Hero */}
      <section className="mb-8 text-center">
        <div className="mb-5 inline-flex items-center gap-1.5 rounded-full border border-brand-100 bg-brand-50 px-3 py-1 text-[12px] font-medium text-brand-700">
          <Sparkles size={13} strokeWidth={2.25} />
          Rules + LLM, MCG-aligned
        </div>
        <h1 className="font-display text-display-lg text-ink-900">
          Structure a clinical note
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed text-ink-500">
          Paste an ER or H&amp;P note. Get a reviewable summary, MCG-aligned reasoning,
          and an admission-supporting Revised HPI in seconds.
        </p>
      </section>

      {/* Input surface */}
      <div className="surface overflow-hidden transition-all duration-250 ease-ios focus-within:border-brand-300 focus-within:shadow-lift">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste your clinical note here…"
          disabled={loading}
          spellCheck={false}
          className="block w-full resize-none border-0 bg-transparent p-5 font-mono text-[13.5px] leading-relaxed text-ink-800 placeholder-ink-400 outline-none focus:outline-none focus-visible:!shadow-none disabled:opacity-60"
          style={{ height: 320 }}
        />
        <div className="flex items-center justify-between border-t border-ink-100 bg-ink-50/60 px-5 py-3">
          <div className="flex items-center gap-2 text-[12.5px] text-ink-500">
            <FileText size={14} className="text-ink-400" />
            {trimmed.length === 0 ? (
              <span>Min {MIN_CHARS} characters to generate</span>
            ) : isValid ? (
              <span>{text.length.toLocaleString()} characters</span>
            ) : (
              <span className="text-observe-700">
                {trimmed.length}/{MIN_CHARS} characters
              </span>
            )}
          </div>
          <Button
            onClick={handleGenerate}
            disabled={!isValid}
            loading={loading}
            iconRight={!loading ? <ArrowRight size={16} /> : undefined}
          >
            {loading ? "Generating" : "Generate"}
          </Button>
        </div>
      </div>

      {/* Progress panel */}
      {loading && (
        <div className="mt-4 space-y-2.5 rounded-2xl2 border border-ink-100 bg-white px-5 py-4 shadow-soft animate-fade-in">
          {PROGRESS_STEPS.map((label, i) => (
            <ProgressLine
              key={label}
              label={label}
              state={
                i < currentStage ? "done" : i === currentStage ? "active" : "pending"
              }
            />
          ))}
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div
          role="alert"
          className="mt-4 flex items-start gap-2 rounded-xl2 border border-admit-100 bg-admit-50 px-4 py-3 text-[13px] text-admit-700 animate-fade-in"
        >
          <span className="mt-1 h-1.5 w-1.5 flex-none rounded-full bg-admit-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Sample chips */}
      {!loading && (
        <div className="mt-10">
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-400">
            Try a sample
          </p>
          <div className="flex flex-wrap gap-2">
            {SAMPLES.map((s) => (
              <button
                key={s.id}
                onClick={() => {
                  setText(s.text);
                  setError("");
                }}
                className="group flex items-center gap-2 rounded-full border border-ink-200 bg-white px-3.5 py-1.5 text-[13px] text-ink-700 shadow-soft transition-all duration-200 ease-ios hover:-translate-y-0.5 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 hover:shadow-card"
              >
                <span className="font-medium">{s.title}</span>
                <span className="text-[11.5px] text-ink-400 group-hover:text-brand-500">
                  {s.subtitle}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* How it works */}
      {!loading && (
        <section className="mt-12 rounded-2xl2 border border-ink-100 bg-white px-6 py-5 shadow-soft">
          <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-400">
            How it works
          </p>
          <ol className="grid gap-3 sm:grid-cols-2">
            {[
              ["1", "Extract facts",     "LLM reads the note and emits typed facts (labs, vitals, symptoms, meds, imaging) with source spans."],
              ["2", "Verify values",     "Regex cross-checks numeric labs/vitals against the source text to catch LLM hallucinations."],
              ["3", "Match MCG rules",   "Diabetes M-130 rules map verified facts to a disposition; the LLM cannot override it."],
              ["4", "Compose narrative", "LLM writes a 6-sentence Revised HPI citing both source quotes and guideline citations."],
            ].map(([n, title, desc]) => (
              <li key={n} className="flex gap-3">
                <span className="mt-0.5 grid h-6 w-6 flex-none place-items-center rounded-full bg-brand-50 text-[11px] font-semibold text-brand-700">
                  {n}
                </span>
                <div>
                  <p className="text-[13.5px] font-medium text-ink-800">{title}</p>
                  <p className="text-[12.5px] leading-relaxed text-ink-500">{desc}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

function ProgressLine({
  label,
  state,
}: {
  label: string;
  state: "done" | "active" | "pending";
}) {
  const textClass = {
    done:    "text-ink-500",
    active:  "text-ink-800 font-medium",
    pending: "text-ink-400",
  }[state];

  return (
    <div className="flex items-center gap-3 text-[13px]">
      <span
        className={[
          "grid h-5 w-5 place-items-center rounded-full",
          state === "done"   ? "bg-discharge-100"
            : state === "active" ? "bg-brand-100"
            : "bg-ink-100",
        ].join(" ")}
      >
        {state === "done" ? (
          <Check size={11} className="text-discharge-700" strokeWidth={3} />
        ) : state === "active" ? (
          <span className="h-3 w-3 rounded-full border-2 border-brand-200 border-t-brand-600 animate-spin" />
        ) : (
          <span className="h-1.5 w-1.5 rounded-full bg-ink-300" />
        )}
      </span>
      <span className={`flex-1 ${textClass}`}>{label}</span>
    </div>
  );
}
