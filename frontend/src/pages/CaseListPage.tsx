import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { FileText, Plus, Search, Trash2, X } from "lucide-react";
import { deleteCase, listCases } from "@/api/cases";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import type { CaseListItem } from "@/api/types";

type Bucket = "Today" | "Yesterday" | "This week" | "Earlier";
const BUCKET_ORDER: Bucket[] = ["Today", "Yesterday", "This week", "Earlier"];

const DISPO_BAR: Record<string, string> = {
  Admit:     "bg-admit-600",
  Observe:   "bg-observe-600",
  Discharge: "bg-discharge-600",
  Unknown:   "bg-unknown-600",
};

const DISPO_TONE: Record<string, "admit" | "observe" | "discharge" | "unknown"> = {
  Admit: "admit", Observe: "observe", Discharge: "discharge", Unknown: "unknown",
};

export function CaseListPage() {
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [confirmTargetId, setConfirmTargetId] = useState<string | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: (caseId: string) => deleteCase(caseId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cases"] }),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["cases", page],
    queryFn: () => listCases(page, 20),
  });

  const filtered = useMemo(() => {
    const items = data?.items ?? [];
    if (!query.trim()) return items;
    const q = query.toLowerCase();
    return items.filter((it) =>
      (it.chiefComplaintPreview || "").toLowerCase().includes(q) ||
      (it.disposition || "").toLowerCase().includes(q),
    );
  }, [data, query]);

  const grouped = useMemo(() => groupByTime(filtered), [filtered]);
  const totalPages = data ? Math.ceil(data.total / data.pageSize) : 0;

  return (
    <div className="mx-auto max-w-3xl">
      {/* Toolbar */}
      <div className="mb-7 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-display text-ink-900">My cases</h1>
          {data && (
            <p className="mt-1 text-[13px] text-ink-500">
              {data.total} {data.total === 1 ? "case" : "cases"} saved
            </p>
          )}
        </div>
        <div className="flex items-center gap-2.5">
          <SearchInput value={query} onChange={setQuery} />
          <Button
            size="md"
            onClick={() => navigate("/")}
            iconLeft={<Plus size={15} strokeWidth={2.5} />}
          >
            New
          </Button>
        </div>
      </div>

      {/* Body */}
      {isLoading ? (
        <ListSkeleton />
      ) : !data || data.items.length === 0 ? (
        <EmptyState onCreate={() => navigate("/")} />
      ) : filtered.length === 0 ? (
        <NoMatch query={query} onClear={() => setQuery("")} />
      ) : (
        <div className="space-y-7">
          {BUCKET_ORDER.map((bucket) => {
            const items = grouped[bucket];
            if (!items || items.length === 0) return null;
            return (
              <section key={bucket}>
                <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-400">
                  {bucket}
                </h2>
                <ul className="space-y-2">
                  {items.map((item, i) => (
                    <CaseRow
                      key={item.id}
                      item={item}
                      index={i}
                      onClick={() => navigate(`/cases/${item.id}`)}
                      onDelete={() => setConfirmTargetId(item.id)}
                      deleting={
                        deleteMutation.isPending && deleteMutation.variables === item.id
                      }
                    />
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && !query && (
        <div className="mt-9 flex items-center justify-center gap-3">
          <Button
            size="sm"
            variant="secondary"
            disabled={page === 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </Button>
          <span className="text-[12.5px] text-ink-500">
            Page {page} of {totalPages}
          </span>
          <Button
            size="sm"
            variant="secondary"
            disabled={page === totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Next
          </Button>
        </div>
      )}

      <ConfirmDialog
        open={confirmTargetId !== null}
        title="Delete this case?"
        description="The case, its structured output, and edit history will be permanently removed."
        confirmLabel="Delete"
        tone="danger"
        loading={
          deleteMutation.isPending && deleteMutation.variables === confirmTargetId
        }
        onConfirm={() => {
          if (!confirmTargetId) return;
          deleteMutation.mutate(confirmTargetId, {
            onSuccess: () => setConfirmTargetId(null),
          });
        }}
        onClose={() => setConfirmTargetId(null)}
      />
    </div>
  );
}

function CaseRow({
  item,
  index,
  onClick,
  onDelete,
  deleting,
}: {
  item: CaseListItem;
  index: number;
  onClick: () => void;
  onDelete: () => void;
  deleting: boolean;
}) {
  const dispoBar  = (item.disposition && DISPO_BAR[item.disposition])  || "bg-ink-300";
  const dispoTone = (item.disposition && DISPO_TONE[item.disposition]) || "neutral";
  const isEdited = item.origin === "user";

  return (
    <motion.li
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: Math.min(index * 0.035, 0.25), ease: [0.32, 0.72, 0, 1] }}
      className="group/row relative"
    >
      <button
        type="button"
        onClick={onClick}
        className="surface group relative w-full overflow-hidden text-left transition-all duration-200 ease-ios hover:-translate-y-0.5 hover:border-ink-200 hover:shadow-lift"
      >
        <span className={`absolute inset-y-0 left-0 w-1 ${dispoBar}`} />
        <div className="flex items-center justify-between gap-4 py-4 pl-6 pr-5">
          <div className="min-w-0 flex-1">
            <p className="truncate text-[14px] font-medium text-ink-800">
              {item.chiefComplaintPreview || (
                <span className="italic text-ink-400">Pending generation…</span>
              )}
            </p>
            <div className="mt-1.5 flex flex-wrap items-center gap-2">
              {item.disposition ? (
                <Badge size="sm" tone={dispoTone} dot>
                  {item.disposition}
                </Badge>
              ) : (
                <Badge size="sm" tone="neutral">
                  No disposition
                </Badge>
              )}
              {isEdited && (
                <Badge size="sm" tone="edited" dot>
                  Edited
                </Badge>
              )}
            </div>
          </div>
          <div className="flex flex-none items-center gap-3 text-[12px] text-ink-400">
            <span>{relativeTime(item.createdAt)}</span>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-ink-300 transition-transform duration-200 ease-ios group-hover:translate-x-0.5 group-hover:text-brand-500"
            >
              <path d="M9 18l6-6-6-6" />
            </svg>
          </div>
        </div>
      </button>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        disabled={deleting}
        aria-label="Delete case"
        className="absolute right-2 top-2 grid h-7 w-7 place-items-center rounded-lg bg-white text-ink-300 opacity-0 shadow-soft ring-1 ring-ink-100 transition-all duration-200 ease-ios group-hover/row:opacity-100 hover:bg-admit-50 hover:text-admit-600 hover:ring-admit-100 focus-visible:opacity-100 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <Trash2 size={13} strokeWidth={2.25} />
      </button>
    </motion.li>
  );
}

function SearchInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="relative">
      <Search
        size={14}
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-400"
      />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search cases…"
        className="h-10 w-56 rounded-full border border-ink-200 bg-white pl-9 pr-9 text-[13px] text-ink-800 placeholder-ink-400 outline-none transition-colors duration-200 ease-ios focus:border-brand-300 focus:bg-white focus:!shadow-none"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Clear search"
          className="absolute right-2.5 top-1/2 grid h-6 w-6 -translate-y-1/2 place-items-center rounded-full text-ink-400 transition-colors duration-150 hover:bg-ink-100 hover:text-ink-700"
        >
          <X size={12} />
        </button>
      )}
    </div>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="surface flex flex-col items-center px-6 py-16 text-center">
      <div className="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-brand-50">
        <FileText size={22} className="text-brand-600" />
      </div>
      <h2 className="font-display text-[18px] font-semibold text-ink-800">
        No cases yet
      </h2>
      <p className="mt-1 max-w-sm text-[13px] leading-relaxed text-ink-500">
        Paste a clinical note on the home page to create your first case. Saved cases
        will appear here grouped by date.
      </p>
      <Button className="mt-5" onClick={onCreate} iconLeft={<Plus size={14} />}>
        Create case
      </Button>
    </div>
  );
}

function NoMatch({ query, onClear }: { query: string; onClear: () => void }) {
  return (
    <div className="surface flex flex-col items-center px-6 py-12 text-center">
      <Search size={20} className="mb-2 text-ink-300" />
      <p className="text-[13.5px] text-ink-700">
        No cases match "<span className="font-medium">{query}</span>"
      </p>
      <button
        onClick={onClear}
        className="mt-3 text-[12.5px] font-medium text-brand-600 hover:text-brand-700"
      >
        Clear search
      </button>
    </div>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-2">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="h-[72px] animate-pulse rounded-2xl2 bg-ink-100/60" />
      ))}
    </div>
  );
}

function relativeTime(iso: string): string {
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 30)   return "just now";
  if (sec < 60)   return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60)   return `${min} min ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24)    return `${hr} hr ago`;
  const day = Math.floor(hr / 24);
  if (day < 7)    return `${day}d ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function groupByTime(items: CaseListItem[]): Record<Bucket, CaseListItem[]> {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const weekAgo = new Date(today);
  weekAgo.setDate(today.getDate() - 7);

  const out: Record<Bucket, CaseListItem[]> = {
    "Today": [], "Yesterday": [], "This week": [], "Earlier": [],
  };
  for (const item of items) {
    const d = new Date(item.createdAt);
    if      (d >= today)     out["Today"].push(item);
    else if (d >= yesterday) out["Yesterday"].push(item);
    else if (d >= weekAgo)   out["This week"].push(item);
    else                     out["Earlier"].push(item);
  }
  return out;
}
