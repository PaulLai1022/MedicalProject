import { ChevronDown, Activity } from "lucide-react";
import { OriginDot } from "@/components/ui/OriginDot";

type Dispo = "Admit" | "Observe" | "Discharge" | "Unknown";

const META: Record<Dispo, {
  label: string;
  desc: string;
  border: string;
  ringBg: string;
  ringDot: string;
  text: string;
  shadow: string;
}> = {
  Admit:     { label: "Admit",     desc: "Inpatient admission",      border: "border-admit-100",     ringBg: "bg-admit-100",     ringDot: "bg-admit-600",     text: "text-admit-700",     shadow: "shadow-[inset_4px_0_0_0_theme(colors.admit.600)]" },
  Observe:   { label: "Observe",   desc: "Observation status",       border: "border-observe-100",   ringBg: "bg-observe-100",   ringDot: "bg-observe-600",   text: "text-observe-700",   shadow: "shadow-[inset_4px_0_0_0_theme(colors.observe.600)]" },
  Discharge: { label: "Discharge", desc: "Outpatient appropriate",   border: "border-discharge-100", ringBg: "bg-discharge-100", ringDot: "bg-discharge-600", text: "text-discharge-700", shadow: "shadow-[inset_4px_0_0_0_theme(colors.discharge.600)]" },
  Unknown:   { label: "Unknown",   desc: "Insufficient evidence",    border: "border-unknown-100",   ringBg: "bg-unknown-100",   ringDot: "bg-unknown-600",   text: "text-unknown-700",   shadow: "shadow-[inset_4px_0_0_0_theme(colors.unknown.600)]" },
};

interface DispositionCardProps {
  value: string;
  machineValue: string;
  origin: "machine" | "user";
  mcgHitCount: number;
  onChange: (value: string) => void;
}

export function DispositionCard({
  value,
  machineValue,
  origin,
  mcgHitCount,
  onChange,
}: DispositionCardProps) {
  const meta = META[value as Dispo] ?? META.Unknown;
  return (
    <div className={`relative overflow-hidden rounded-2xl2 border bg-white p-5 ${meta.border} ${meta.shadow}`}>
      <div className="flex items-start gap-4">
        <div className={`grid h-12 w-12 flex-none place-items-center rounded-2xl ${meta.ringBg}`}>
          <Activity size={22} className={meta.text} strokeWidth={2.25} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span className={`text-[11px] font-semibold uppercase tracking-[0.08em] ${meta.text}`}>
              Disposition
            </span>
            <OriginDot origin={origin} machineValue={machineValue} />
          </div>

          <div className="relative inline-flex items-center">
            <select
              value={value}
              onChange={(e) => onChange(e.target.value)}
              className={`appearance-none cursor-pointer bg-transparent pr-7 font-display text-[28px] font-bold tracking-tight outline-none ${meta.text}`}
            >
              {Object.keys(META).map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
            <ChevronDown size={20} className={`pointer-events-none absolute right-0 ${meta.text}`} />
          </div>

          <p className="mt-1 text-[13px] text-ink-500">
            {meta.desc}
            {mcgHitCount > 0 && (
              <>
                <span className="mx-1.5 text-ink-300">·</span>
                <span className="font-medium text-ink-700">{mcgHitCount}</span> MCG criteria met
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
