import { useState } from "react";
import { AlertTriangle, FlaskConical, Stethoscope } from "lucide-react";
import { Chip } from "@/components/ui/Chip";
import { OriginDot } from "@/components/ui/OriginDot";
import type { CaseStructured } from "@/api/types";

export type EditValue = string | string[] | null;

interface StructuredPanelProps {
  structured: CaseStructured;
  edits: Record<string, EditValue>;
  setEdit: (key: string, value: EditValue) => void;
}

export function StructuredPanel({ structured, edits, setEdit }: StructuredPanelProps) {
  const cc = (edits["chiefComplaint"] as string | undefined) ?? structured.chiefComplaint.value;
  const hpi = (edits["hpiSummary"] as string | undefined) ?? structured.hpiSummary.value;

  const findings = (edits["keyFindings"] as string[] | undefined)
    ?? (structured.keyFindings.value ?? []);
  const conditions = (edits["suspectedConditions"] as string[] | undefined)
    ?? (structured.suspectedConditions.value ?? []);
  const uncertainties = (edits["uncertainties"] as string[] | undefined)
    ?? (structured.uncertainties.value ?? []);

  const isFieldEdited = (key: string) => key in edits;

  return (
    <div className="space-y-4">
      <FieldShell
        label="Chief complaint"
        origin={isFieldEdited("chiefComplaint") ? "user" : structured.chiefComplaint.origin}
        machineValue={structured.chiefComplaint.machineValue}
        onReset={isFieldEdited("chiefComplaint") ? () => setEdit("chiefComplaint", null) : undefined}
      >
        <input
          value={cc ?? ""}
          onChange={(e) => setEdit("chiefComplaint", e.target.value)}
          placeholder="(empty)"
          className="w-full bg-transparent text-[14px] text-ink-800 placeholder-ink-300 outline-none focus:outline-none"
        />
      </FieldShell>

      <FieldShell
        label="HPI summary"
        origin={isFieldEdited("hpiSummary") ? "user" : structured.hpiSummary.origin}
        machineValue={structured.hpiSummary.machineValue}
        onReset={isFieldEdited("hpiSummary") ? () => setEdit("hpiSummary", null) : undefined}
      >
        <textarea
          value={hpi ?? ""}
          onChange={(e) => setEdit("hpiSummary", e.target.value)}
          placeholder="(empty)"
          rows={3}
          className="block w-full resize-y bg-transparent text-[13.5px] leading-relaxed text-ink-700 placeholder-ink-300 outline-none focus:outline-none"
        />
      </FieldShell>

      <FieldShell
        label="Key findings"
        icon={<FlaskConical size={12} className="text-ink-400" />}
        origin={isFieldEdited("keyFindings") ? "user" : structured.keyFindings.origin}
        machineValue={structured.keyFindings.machineValue}
        onReset={isFieldEdited("keyFindings") ? () => setEdit("keyFindings", null) : undefined}
      >
        <ChipListEditor
          items={findings}
          onChange={(items) => setEdit("keyFindings", items)}
          tone="brand"
          placeholder="Add a finding…"
        />
      </FieldShell>

      <FieldShell
        label="Suspected conditions"
        icon={<Stethoscope size={12} className="text-ink-400" />}
        origin={isFieldEdited("suspectedConditions") ? "user" : structured.suspectedConditions.origin}
        machineValue={structured.suspectedConditions.machineValue}
        onReset={isFieldEdited("suspectedConditions") ? () => setEdit("suspectedConditions", null) : undefined}
      >
        <ChipListEditor
          items={conditions}
          onChange={(items) => setEdit("suspectedConditions", items)}
          tone="neutral"
          placeholder="Add a condition…"
        />
      </FieldShell>

      <FieldShell
        label="Uncertainties"
        icon={<AlertTriangle size={12} className="text-observe-600" />}
        accent="warn"
        origin={isFieldEdited("uncertainties") ? "user" : structured.uncertainties.origin}
        machineValue={structured.uncertainties.machineValue}
        onReset={isFieldEdited("uncertainties") ? () => setEdit("uncertainties", null) : undefined}
      >
        <ChipListEditor
          items={uncertainties}
          onChange={(items) => setEdit("uncertainties", items)}
          tone="warn"
          placeholder="Add an uncertainty…"
        />
      </FieldShell>
    </div>
  );
}

interface FieldShellProps {
  label: string;
  icon?: React.ReactNode;
  origin: "machine" | "user";
  machineValue?: string | string[] | null;
  onReset?: () => void;
  accent?: "default" | "warn";
  children: React.ReactNode;
}

function FieldShell({ label, icon, origin, machineValue, onReset, accent = "default", children }: FieldShellProps) {
  const accentBorder = accent === "warn" ? "border-observe-100/80" : "border-ink-100";
  return (
    <div className={`surface px-4 py-3 transition-colors duration-200 ease-ios ${accentBorder}`}>
      <div className="mb-1.5 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          {icon}
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">
            {label}
          </span>
          <OriginDot origin={origin} machineValue={machineValue} />
        </div>
        {onReset && (
          <button
            onClick={onReset}
            className="text-[11px] font-medium text-ink-400 transition-colors duration-150 hover:text-ink-700"
          >
            Reset
          </button>
        )}
      </div>
      {children}
    </div>
  );
}

function ChipListEditor({
  items,
  onChange,
  tone,
  placeholder,
}: {
  items: string[];
  onChange: (items: string[]) => void;
  tone: "neutral" | "brand" | "warn";
  placeholder: string;
}) {
  const [draft, setDraft] = useState("");
  const submit = () => {
    const v = draft.trim();
    if (!v) return;
    onChange([...items, v]);
    setDraft("");
  };
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {items.map((item, i) => (
        <Chip
          key={`${item}-${i}`}
          tone={tone}
          onRemove={() => onChange(items.filter((_, j) => j !== i))}
        >
          {item}
        </Chip>
      ))}
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            submit();
          } else if (e.key === "Backspace" && draft === "" && items.length > 0) {
            onChange(items.slice(0, -1));
          }
        }}
        onBlur={submit}
        placeholder={items.length === 0 ? placeholder : "+"}
        className="min-w-[80px] flex-1 bg-transparent text-[12.5px] text-ink-700 placeholder-ink-300 outline-none focus:outline-none"
      />
    </div>
  );
}
