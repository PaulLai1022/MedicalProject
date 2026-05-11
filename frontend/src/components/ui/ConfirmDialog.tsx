import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Info } from "lucide-react";
import { Button } from "./Button";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "danger" | "primary";
  loading?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "danger",
  loading = false,
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !loading) onClose();
    };
    window.addEventListener("keydown", onKey);
    const t = window.setTimeout(() => cancelRef.current?.focus(), 60);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.clearTimeout(t);
    };
  }, [open, loading, onClose]);

  if (typeof document === "undefined") return null;

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18, ease: [0.32, 0.72, 0, 1] }}
          onMouseDown={(e) => {
            if (e.target === e.currentTarget && !loading) onClose();
          }}
          role="presentation"
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 px-4 backdrop-blur-[2px]"
        >
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.98 }}
            transition={{ duration: 0.22, ease: [0.32, 0.72, 0, 1] }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
            aria-describedby={description ? "confirm-desc" : undefined}
            className="w-full max-w-sm rounded-2xl2 border border-ink-100 bg-white p-5 shadow-lift"
          >
            <div className="flex items-start gap-3">
              <div
                className={[
                  "grid h-9 w-9 flex-none place-items-center rounded-xl ring-1",
                  tone === "danger"
                    ? "bg-admit-50 ring-admit-100"
                    : "bg-brand-50 ring-brand-100",
                ].join(" ")}
              >
                {tone === "danger" ? (
                  <AlertTriangle size={16} className="text-admit-600" />
                ) : (
                  <Info size={16} className="text-brand-600" />
                )}
              </div>
              <div className="min-w-0 flex-1 pt-0.5">
                <h2
                  id="confirm-title"
                  className="text-[15px] font-semibold text-ink-900"
                >
                  {title}
                </h2>
                {description && (
                  <p
                    id="confirm-desc"
                    className="mt-1 text-[13px] leading-relaxed text-ink-500"
                  >
                    {description}
                  </p>
                )}
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button
                ref={cancelRef}
                variant="secondary"
                size="md"
                onClick={onClose}
                disabled={loading}
              >
                {cancelLabel}
              </Button>
              <Button
                variant={tone === "danger" ? "danger" : "primary"}
                size="md"
                onClick={onConfirm}
                loading={loading}
              >
                {confirmLabel}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
