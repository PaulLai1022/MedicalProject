import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, RotateCcw, Trash2, AlertTriangle, Info, Terminal } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { getCase, patchCase, generateCase, deleteCase, getLlmLog } from "@/api/cases";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Chip } from "@/components/ui/Chip";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { DispositionCard } from "@/components/case/DispositionCard";
import { SourceNote } from "@/components/case/SourceNote";
import { StructuredPanel, type EditValue } from "@/components/case/StructuredPanel";
import { RevisedHpi } from "@/components/case/RevisedHpi";
import { McgPath } from "@/components/case/McgPath";
import { ExtractedFactsPanel } from "@/components/case/ExtractedFactsPanel";

export function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [edits, setEdits] = useState<Record<string, EditValue>>({});
  const [sentenceEdits, setSentenceEdits] = useState<Record<string, string>>({});
  const [selectedSentenceId, setSelectedSentenceId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  const { data: caseData, isLoading } = useQuery({
    queryKey: ["case", id],
    queryFn: () => getCase(id!),
    enabled: !!id,
  });

  const { data: llmLog } = useQuery({
    queryKey: ["llm-log", id],
    queryFn: () => getLlmLog(id!),
    enabled: !!id,
  });

  const dirty = Object.keys(edits).length > 0 || Object.keys(sentenceEdits).length > 0;

  const saveMutation = useMutation({
    mutationFn: () => patchCase(id!, buildPatch(edits, sentenceEdits)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["case", id] });
      setEdits({});
      setSentenceEdits({});
      setToast("Saved");
      window.setTimeout(() => setToast(null), 2200);
    },
    onError: () => {
      setToast("Save failed");
      window.setTimeout(() => setToast(null), 3000);
    },
  });

  const regenerateMutation = useMutation({
    mutationFn: () => generateCase(id!, true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["case", id] });
      queryClient.invalidateQueries({ queryKey: ["llm-log", id] });
      setEdits({});
      setSentenceEdits({});
      setSelectedSentenceId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteCase(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      navigate("/cases");
    },
  });

  // Cmd+S / Ctrl+S to save
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (dirty && !saveMutation.isPending) saveMutation.mutate();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dirty, saveMutation]);

  const setEdit = (key: string, value: EditValue) => {
    setEdits((prev) => {
      if (value === null) {
        const next = { ...prev };
        delete next[key];
        return next;
      }
      return { ...prev, [key]: value };
    });
  };

  const setSentenceEdit = (sid: string, text: string) => {
    setSentenceEdits((prev) => ({ ...prev, [sid]: text }));
  };

  const s = caseData?.structured;
  const selectedSources = useMemo(() => {
    if (!selectedSentenceId || !s) return [];
    const sent = s.revisedHPI.sentences.find((x) => x.id === selectedSentenceId);
    return sent?.sources ?? [];
  }, [selectedSentenceId, s]);

  if (isLoading) return <DetailSkeleton />;
  if (!caseData) {
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <p className="text-[14px] text-ink-500">Case not found.</p>
        <Button
          variant="ghost"
          size="sm"
          className="mt-3"
          onClick={() => navigate("/cases")}
          iconLeft={<ArrowLeft size={14} />}
        >
          Back to Cases
        </Button>
      </div>
    );
  }

  const dispositionValue = (edits["disposition"] as string | undefined) ?? s?.disposition.value ?? "Unknown";

  return (
    <div className="space-y-5">
      {/* Sticky header */}
      <header className="sticky top-14 z-30 -mx-6 border-b border-ink-100 bg-ink-50/85 px-6 py-3 backdrop-blur lg:-mx-10 lg:px-10">
        <div className="mx-auto flex max-w-[1280px] items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/cases")}
              className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-[12.5px] font-medium text-ink-500 transition-colors hover:bg-ink-100 hover:text-ink-800"
            >
              <ArrowLeft size={14} />
              Cases
            </button>
            <span className="text-ink-300">/</span>
            <span className="font-mono text-[12.5px] text-ink-700">
              #{(id ?? "").slice(0, 8)}
            </span>
            <span className="text-[12px] text-ink-400">
              · {new Date(caseData.createdAt).toLocaleString()}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <AnimatePresence>
              {toast && (
                <motion.span
                  initial={{ opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 8 }}
                  className={[
                    "text-[12.5px] font-medium",
                    toast === "Saved" ? "text-discharge-700" : "text-admit-700",
                  ].join(" ")}
                >
                  {toast === "Saved" ? "✓ Saved" : toast}
                </motion.span>
              )}
            </AnimatePresence>
            {dirty && !toast && (
              <Badge tone="edited" size="sm" dot>
                Unsaved
              </Badge>
            )}
            <button
              type="button"
              onClick={() => setConfirmDeleteOpen(true)}
              disabled={deleteMutation.isPending}
              aria-label="Delete case"
              className="grid h-8 w-8 place-items-center rounded-lg text-ink-400 transition-all duration-200 ease-ios hover:bg-admit-50 hover:text-admit-600 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Trash2 size={14} strokeWidth={2.25} />
            </button>
            <Button
              variant="ghost"
              size="sm"
              loading={regenerateMutation.isPending}
              onClick={() => regenerateMutation.mutate()}
              iconLeft={!regenerateMutation.isPending ? <RotateCcw size={13} /> : undefined}
            >
              Regenerate
            </Button>
            <Button
              size="sm"
              disabled={!dirty}
              loading={saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
            >
              Save
            </Button>
          </div>
        </div>
      </header>

      {!s ? (
        <EmptyStructured onRegenerate={() => regenerateMutation.mutate()} pending={regenerateMutation.isPending} />
      ) : (
        <>
          <DispositionCard
            value={dispositionValue}
            machineValue={s.disposition.machineValue}
            origin={"disposition" in edits ? "user" : s.disposition.origin}
            mcgHitCount={s.mcgHits.length}
            onChange={(v) => setEdit("disposition", v)}
          />

          {dispositionValue === "Unknown" && (
            <UnknownExplainer
              decisionPath={s.decisionPath}
              missingCoreFields={s.missingCoreFields}
            />
          )}

          {/* Two columns */}
          <div className="grid gap-5 lg:min-h-[420px] lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
            <div className="lg:relative lg:min-h-0">
              <div className="lg:absolute lg:inset-0">
                <SourceNote rawText={caseData.rawText} highlights={selectedSources} />
              </div>
            </div>
            <StructuredPanel structured={s} edits={edits} setEdit={setEdit} />
          </div>

          <RevisedHpi
            sentences={s.revisedHPI.sentences}
            sentenceEdits={sentenceEdits}
            setSentenceEdit={setSentenceEdit}
            selectedId={selectedSentenceId}
            onSelect={setSelectedSentenceId}
          />

          <McgPath hits={s.mcgHits} decisionPath={s.decisionPath} />

          {(s.missingCoreFields.length > 0 || s.warnings.length > 0) && (
            <div className="grid gap-4 sm:grid-cols-2">
              {s.missingCoreFields.length > 0 && (
                <NoticeCard
                  tone="warn"
                  icon={<AlertTriangle size={14} />}
                  title="Missing core fields"
                  items={s.missingCoreFields}
                />
              )}
              {s.warnings.length > 0 && (
                <NoticeCard
                  tone="info"
                  icon={<Info size={14} />}
                  title="Warnings"
                  items={s.warnings}
                />
              )}
            </div>
          )}

          <ExtractedFactsPanel facts={s.extractedFacts} />

          {llmLog?.enabled && llmLog.items.length > 0 && (
            <details className="surface px-5 py-3">
              <summary className="flex cursor-pointer items-center gap-2 text-[12.5px] font-medium text-ink-600">
                <Terminal size={13} className="text-ink-400" />
                LLM call log ({llmLog.items.length})
              </summary>
              <div className="mt-3 space-y-1.5">
                {llmLog.items.map((log) => (
                  <div
                    key={log.id}
                    className="flex items-center justify-between rounded-lg border border-ink-100 bg-ink-50/60 px-3 py-2 text-[11.5px]"
                  >
                    <span className="font-mono text-ink-700">{log.model}</span>
                    <div className="flex items-center gap-3 text-ink-500">
                      <span>{log.durationMs} ms</span>
                      <Badge size="sm" tone={log.status === "ok" ? "discharge" : "admit"}>
                        {log.status}
                      </Badge>
                      <span>{new Date(log.createdAt).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          )}
        </>
      )}

      <ConfirmDialog
        open={confirmDeleteOpen}
        title="Delete this case?"
        description="The case, its structured output, and edit history will be permanently removed."
        confirmLabel="Delete"
        tone="danger"
        loading={deleteMutation.isPending}
        onConfirm={() => {
          deleteMutation.mutate(undefined, {
            onSuccess: () => setConfirmDeleteOpen(false),
          });
        }}
        onClose={() => setConfirmDeleteOpen(false)}
      />
    </div>
  );
}

function EmptyStructured({ onRegenerate, pending }: { onRegenerate: () => void; pending: boolean }) {
  return (
    <div className="surface flex flex-col items-center px-6 py-16 text-center">
      <div className="mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-brand-50">
        <Info size={20} className="text-brand-600" />
      </div>
      <h2 className="font-display text-[18px] font-semibold text-ink-800">
        No structured output yet
      </h2>
      <p className="mt-1 max-w-sm text-[13px] text-ink-500">
        Generation may have been skipped or failed. Run it now to extract fields and compose the Revised HPI.
      </p>
      <Button
        className="mt-5"
        onClick={onRegenerate}
        loading={pending}
        iconLeft={!pending ? <RotateCcw size={14} /> : undefined}
      >
        Generate
      </Button>
    </div>
  );
}

function NoticeCard({
  tone,
  icon,
  title,
  items,
}: {
  tone: "warn" | "info";
  icon: React.ReactNode;
  title: string;
  items: string[];
}) {
  const styles =
    tone === "warn"
      ? { wrap: "border-observe-100 bg-observe-50",  title: "text-observe-700", item: "text-observe-700" }
      : { wrap: "border-ink-100      bg-white",      title: "text-ink-700",     item: "text-ink-500"     };
  return (
    <div className={`rounded-2xl2 border p-4 ${styles.wrap}`}>
      <div className={`mb-2 flex items-center gap-1.5 text-[12.5px] font-semibold ${styles.title}`}>
        {icon}
        {title}
      </div>
      <ul className="space-y-1 text-[12.5px] leading-relaxed">
        {items.map((it, i) => (
          <li key={i} className={`flex gap-2 ${styles.item}`}>
            <span className="mt-1.5 h-1 w-1 flex-none rounded-full bg-current opacity-50" />
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-5">
      <div className="h-12 animate-pulse rounded-xl2 bg-ink-100/60" />
      <div className="h-24 animate-pulse rounded-2xl2 bg-ink-100/60" />
      <div className="grid gap-5 lg:grid-cols-[1.1fr_1fr]">
        <div className="h-[420px] animate-pulse rounded-2xl2 bg-ink-100/60" />
        <div className="space-y-3">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-2xl2 bg-ink-100/60" />
          ))}
        </div>
      </div>
      <div className="h-64 animate-pulse rounded-2xl2 bg-ink-100/60" />
    </div>
  );
}

function UnknownExplainer({
  decisionPath,
  missingCoreFields,
}: {
  decisionPath: string;
  missingCoreFields: string[];
}) {
  const body = explainerBody(decisionPath);
  return (
    <div className="rounded-2xl2 border border-unknown-100 bg-white px-5 py-4 shadow-soft">
      <div className="flex items-start gap-3">
        <div className="grid h-9 w-9 flex-none place-items-center rounded-xl bg-unknown-100">
          <Info size={16} className="text-unknown-600" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-[14px] font-semibold text-ink-800">
            Why is the disposition Unknown?
          </h3>
          <p className="mt-1 text-[13px] leading-relaxed text-ink-600">{body}</p>

          {missingCoreFields.length > 0 && (
            <div className="mt-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-400">
                Missing core fields
              </p>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {missingCoreFields.map((f) => (
                  <Chip key={f} tone="neutral">{f}</Chip>
                ))}
              </div>
            </div>
          )}

          <div className="mt-3 flex items-start gap-2 rounded-xl bg-brand-50 px-3 py-2 text-[12.5px] leading-relaxed text-brand-700">
            <Info size={13} className="mt-0.5 flex-none text-brand-500" />
            <span>
              This system follows MCG Diabetes M-130 (30th Ed). For inputs outside
              the diabetes domain, the disposition is held at Unknown to avoid
              fabricating evidence-free decisions.
            </span>
          </div>

          {decisionPath && (
            <p className="mt-2 font-mono text-[11px] text-ink-400">
              decisionPath: {decisionPath}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function explainerBody(decisionPath: string): string {
  if (decisionPath.startsWith("5.1")) {
    return "All three core markers required by MCG Diabetes M-130 (glucose, ketones, acidosis marker) are absent from this note. Without any of them the system cannot evaluate inpatient criteria.";
  }
  if (decisionPath.startsWith("5.2")) {
    return "Two or more core diabetic markers required by MCG Diabetes M-130 are missing from this note. Rather than guess, the system declines to commit to an admission decision.";
  }
  if (decisionPath.startsWith("5.5")) {
    return "Core fields are present but no MCG admission criteria were triggered. The case appears to fall below the inpatient threshold defined by Diabetes M-130 — but the system held back on a Discharge label since it has not been clinically validated for that decision.";
  }
  return "The system was unable to map this input to a confident MCG-supported disposition. See the decisionPath below for the routing reason.";
}

function buildPatch(
  edits: Record<string, EditValue>,
  sentenceEdits: Record<string, string>,
) {
  const structured: Record<string, unknown> = {};

  for (const [key, val] of Object.entries(edits)) {
    if (val === null || val === undefined) continue;
    structured[key] = { userValue: val };
  }

  const sentencePatches = Object.entries(sentenceEdits).map(([id, text]) => ({
    id,
    userText: text,
  }));
  if (sentencePatches.length > 0) {
    structured.revisedHPI = { sentences: sentencePatches };
  }

  return { structured };
}
