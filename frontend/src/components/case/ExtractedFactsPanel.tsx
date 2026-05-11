import { Microscope, ShieldCheck, ShieldAlert, ShieldQuestion } from "lucide-react";
import { Badge, type Tone } from "@/components/ui/Badge";
import type { ExtractedFacts, FactVerification } from "@/api/types";

interface ExtractedFactsPanelProps {
  facts: ExtractedFacts | null;
}

export function ExtractedFactsPanel({ facts }: ExtractedFactsPanelProps) {
  if (!facts) return null;

  const totalAtomic =
    facts.labs.length +
    facts.vitals.length +
    facts.symptoms.length +
    facts.medications.length +
    facts.imagingFindings.length +
    facts.interventions.length +
    facts.history.length;

  if (totalAtomic === 0 && facts.suspectedConditions.length === 0) {
    return null;
  }

  return (
    <details className="surface overflow-hidden">
      <summary className="flex cursor-pointer items-center justify-between border-b border-ink-100 bg-ink-50/60 px-5 py-3">
        <div className="flex items-center gap-2">
          <Microscope size={14} className="text-ink-500" />
          <h2 className="text-[14px] font-semibold text-ink-800">LLM-extracted facts</h2>
          <span className="text-[11.5px] text-ink-400">
            {totalAtomic} facts · verified by regex cross-check
          </span>
        </div>
        <Badge tone="brand" size="sm" dot>
          {totalAtomic} items
        </Badge>
      </summary>

      <div className="space-y-5 px-5 py-4">
        {facts.suspectedConditions.length > 0 && (
          <ChipGroup label="Suspected conditions" items={facts.suspectedConditions} />
        )}

        {facts.labs.length > 0 && (
          <FactTable
            label="Labs"
            rows={facts.labs.map((l) => ({
              name: l.name,
              detail: `${l.value}${l.unit ? " " + l.unit : ""}`,
            }))}
          />
        )}

        {facts.vitals.length > 0 && (
          <FactTable
            label="Vitals"
            rows={facts.vitals.map((v) => ({
              name: v.name,
              detail: `${v.value}${v.unit ? " " + v.unit : ""}`,
            }))}
          />
        )}

        {facts.symptoms.length > 0 && (
          <FactTable
            label="Symptoms"
            rows={facts.symptoms.map((s) => ({
              name: s.name,
              detail: s.description,
            }))}
          />
        )}

        {facts.medications.length > 0 && (
          <FactTable
            label="Medications"
            rows={facts.medications.map((m) => ({
              name: m.name,
              detail: [m.dose, m.route].filter(Boolean).join(" · ") || "—",
            }))}
          />
        )}

        {facts.imagingFindings.length > 0 && (
          <BulletList label="Imaging findings" items={facts.imagingFindings} />
        )}

        {facts.interventions.length > 0 && (
          <BulletList label="ER interventions" items={facts.interventions} />
        )}

        {facts.history.length > 0 && (
          <BulletList label="History" items={facts.history} />
        )}

        {facts.verifications.length > 0 && (
          <VerificationsList verifications={facts.verifications} />
        )}
      </div>
    </details>
  );
}

function ChipGroup({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <SectionHeader>{label}</SectionHeader>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, i) => (
          <Badge key={i} tone="neutral" size="sm">
            {item}
          </Badge>
        ))}
      </div>
    </div>
  );
}

function FactTable({
  label,
  rows,
}: {
  label: string;
  rows: { name: string; detail: string }[];
}) {
  return (
    <div>
      <SectionHeader>{label}</SectionHeader>
      <ul className="grid gap-1 sm:grid-cols-2">
        {rows.map((row, i) => (
          <li
            key={i}
            className="flex items-baseline justify-between gap-3 rounded-lg border border-ink-100 bg-white px-3 py-1.5 text-[12.5px]"
          >
            <span className="font-mono text-ink-500">{row.name}</span>
            <span className="text-right font-medium text-ink-800">{row.detail}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function BulletList({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <SectionHeader>{label}</SectionHeader>
      <ul className="space-y-1 text-[12.5px] leading-relaxed text-ink-700">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2">
            <span className="mt-1.5 h-1 w-1 flex-none rounded-full bg-ink-400" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function VerificationsList({ verifications }: { verifications: FactVerification[] }) {
  return (
    <div>
      <SectionHeader>Verification status</SectionHeader>
      <ul className="space-y-1.5">
        {verifications.map((v, i) => {
          const meta = STATUS_META[v.status];
          return (
            <li
              key={i}
              className="flex items-start gap-2.5 rounded-lg border border-ink-100 bg-white px-3 py-2 text-[12px]"
            >
              <Badge tone={meta.tone} size="sm" icon={meta.icon}>
                {v.status}
              </Badge>
              <div className="min-w-0 flex-1">
                <p className="text-ink-800">
                  <span className="font-mono text-[11px] text-ink-500">
                    {v.kind}.{v.name}
                  </span>{" "}
                  = <span className="font-medium">{String(v.value)}</span>
                </p>
                {v.detail && (
                  <p className="mt-0.5 text-[11.5px] text-ink-500">{v.detail}</p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-400">
      {children}
    </p>
  );
}

const STATUS_META: Record<
  FactVerification["status"],
  { tone: Tone; icon: React.ReactNode }
> = {
  verified: { tone: "discharge", icon: <ShieldCheck size={11} /> },
  failed: { tone: "admit", icon: <ShieldAlert size={11} /> },
  unverifiable: { tone: "neutral", icon: <ShieldQuestion size={11} /> },
};
